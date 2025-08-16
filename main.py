import asyncio
import random
import uuid

import pyrogram
from nsdev import listen
from pyrogram import Client, filters, emoji
from pyrogram.enums import ChatMemberStatus
from pyrogram.errors import FloodWait, UserNotParticipant

from config import API_HASH, API_ID, BOT_TOKEN

app = Client(
    "TagallAssistant",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
)

TAGALL_PROCESSES = {}
db = app.ns.data.db(file_name="tagall_db")
log = app.ns.utils.log

RANDOM_EMOJIS = list(vars(emoji).values())


async def get_admin_groups(user_id):
    admin_groups = []
    groups_in_db = db.getListVars("bot_config", "groups") or []
    for group_info in groups_in_db:
        try:
            member = await app.get_chat_member(group_info["id"], user_id)
            if member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
                admin_groups.append(group_info)
        except (UserNotParticipant, Exception) as e:
            log.print(f"{log.ORANGE}Data grup {log.CYAN}{group_info['title']}{log.ORANGE} (stale) dihapus dari database karena bot tidak lagi menjadi anggota.")
            db.removeListVars("bot_config", "groups", group_info)
            continue
    return admin_groups


async def send_tagall_message(client, target_chat_id, original_message, tags):
    full_tags = " ".join(tags)

    if original_message.media:
        base_caption = original_message.caption.markdown if original_message.caption else ""
        reply_markup, cleaned_caption = client.ns.telegram.button.create_inline_keyboard(base_caption)
        final_caption = cleaned_caption + "\n\n" + full_tags
        
        if reply_markup and reply_markup.inline_keyboard:
            await original_message.copy(target_chat_id, caption=final_caption, reply_markup=reply_markup)
        else:
            await original_message.copy(target_chat_id, caption=final_caption)
    else:
        base_text = original_message.text.markdown if original_message.text else ""
        reply_markup, cleaned_text = client.ns.telegram.button.create_inline_keyboard(base_text)
        final_text = cleaned_text + "\n\n" + full_tags
        
        if reply_markup and reply_markup.inline_keyboard:
            await client.send_message(target_chat_id, final_text, reply_markup=reply_markup)
        else:
            await client.send_message(target_chat_id, final_text)


async def execute_tagall_process(process_id, chat_id, admin_id):
    process_data = TAGALL_PROCESSES.get(process_id)
    if not process_data:
        return
        
    status_message = await app.get_messages(admin_id, process_data["status_message_id"])

    total_tagged = 0
    try:
        user_mentions = []
        original_message = process_data["original_message"]

        async for member in app.get_chat_members(chat_id):
            if process_data["cancel_event"].is_set():
                break
            if not member.user.is_bot:
                emoji_char = random.choice(RANDOM_EMOJIS)
                mention = f'<a href="tg://user?id={member.user.id}">{emoji_char}</a>'
                user_mentions.append(mention)

            if len(user_mentions) == 5:
                await send_tagall_message(app, chat_id, original_message, user_mentions)
                total_tagged += len(user_mentions)
                user_mentions = []
                await asyncio.sleep(5)
        
        if user_mentions and not process_data["cancel_event"].is_set():
            await send_tagall_message(app, chat_id, original_message, user_mentions)
            total_tagged += len(user_mentions)
            
    except FloodWait as e:
        log.print(f"{log.YELLOW}FloodWait terdeteksi. Menunggu {log.CYAN}{e.value}{log.YELLOW} detik.")
        await asyncio.sleep(e.value)
    except Exception as e:
        log.print(f"{log.RED}Error saat tagall di grup {log.CYAN}{chat_id}{log.RED}: {e}")
        await app.send_message(admin_id, f"Proses tagall dihentikan karena error: `{e}`")
    finally:
        if process_data["cancel_event"].is_set():
            log.print(f"{log.YELLOW}Proses tagall di grup {log.CYAN}{chat_id}{log.YELLOW} dibatalkan.")
            await status_message.edit_text("❌ Proses tagall dibatalkan.")
            await app.send_message(admin_id, f"Proses tagall dihentikan. Total {total_tagged} pengguna ditandai.")
        else:
            log.print(f"{log.GREEN}Proses tagall di grup {log.CYAN}{chat_id}{log.GREEN} selesai. Total: {total_tagged}.")
            await status_message.edit_text("✅ Proses tagall telah selesai!")
            await app.send_message(admin_id, f"✅ Proses tagall selesai! Total {total_tagged} pengguna ditandai.")
        
        if process_id in TAGALL_PROCESSES:
            del TAGALL_PROCESSES[process_id]


@app.on_message(filters.command("start") & filters.private)
async def start_command(client, message):
    text = (
        "Halo! Saya adalah Asisten Tagall.\n\n"
        "Klik tombol di bawah untuk memulai proses, atau tambahkan saya ke grup Anda."
    )
    bot_username = client.me.username
    admin_rights = "invite_users+delete_messages+pin_messages+manage_chat+restrict_members"
    add_to_group_url = f"https://t.me/{bot_username}?startgroup=true&admin={admin_rights}"
    btn_text = f"| 🚀 Mulai Tagall - start_tagall_process |\n| ➕ Tambahkan Bot ke Grup - {add_to_group_url} |"
    markup, txt = client.ns.telegram.button.create_inline_keyboard(f"{text}\n\n{btn_text}")
    await message.reply_text(txt, reply_markup=markup)


@app.on_callback_query(filters.regex(r"^start_tagall_process$"))
async def select_group_for_tagall_callback(client, callback_query):
    user_id = callback_query.from_user.id
    admin_groups = await get_admin_groups(user_id)

    if not admin_groups:
        return await callback_query.answer("Anda bukan admin di grup manapun tempat saya berada. Silakan tambahkan bot terlebih dahulu.", show_alert=True)
    
    buttons_text = ""
    for group in admin_groups:
        buttons_text += f"| {group['title']} - ask_message_{group['id']} |\n"
    
    buttons_text += "| « Kembali - back_to_start |"

    markup, txt = client.ns.telegram.button.create_inline_keyboard(f"Silakan pilih grup untuk memulai proses tagall:\n\n{buttons_text}")
    await callback_query.message.edit_text(txt, reply_markup=markup)


@app.on_callback_query(filters.regex(r"^ask_message_(-?\d+)"))
async def ask_message_callback(client, callback_query):
    chat_id = int(callback_query.matches[0].group(1))
    user_id = callback_query.from_user.id
    await callback_query.message.delete()

    try:
        ask_msg = await client.ask(
            user_id,
            "Baik, sekarang kirimkan pesan yang akan digunakan untuk tagall (teks, media, dengan/tanpa tombol).\n\nKetik /batal untuk membatalkan.",
            timeout=600
        )
        if ask_msg.text and ask_msg.text.lower() == "/batal":
            raise listen.UserCancelled

        process_id = str(uuid.uuid4())
        
        btn_text = f"| ❌ Batalkan Proses - cancel_tagall_{process_id} |"
        markup, _ = client.ns.telegram.button.create_inline_keyboard(btn_text)
        status_message = await client.send_message(user_id, "✅ Proses tagall dimulai...", reply_markup=markup)
        
        TAGALL_PROCESSES[process_id] = {
            "original_message": ask_msg,
            "status_message_id": status_message.id,
            "cancel_event": asyncio.Event()
        }
        
        asyncio.create_task(execute_tagall_process(process_id, chat_id, user_id))

    except listen.UserCancelled:
        await client.send_message(user_id, "Proses dibatalkan.")
    except asyncio.TimeoutError:
        await client.send_message(user_id, "Waktu habis, silakan mulai lagi dari /start.")
    except Exception as e:
        log.print(f"{log.RED}Error pada alur 'ask' untuk user {log.CYAN}{user_id}{log.RED}: {e}")
        await client.send_message(user_id, f"Terjadi kesalahan: `{e}`")


@app.on_callback_query(filters.regex(r"^cancel_tagall_(.+)"))
async def cancel_tagall_callback(client, callback_query):
    process_id = callback_query.matches[0].group(1)
    
    if process_id in TAGALL_PROCESSES:
        TAGALL_PROCESSES[process_id]["cancel_event"].set()
        await callback_query.edit_message_text("⏳ Proses pembatalan sedang berjalan...")
        log.print(f"{log.YELLOW}Permintaan pembatalan untuk proses {log.CYAN}{process_id}{log.YELLOW}.")
    else:
        await callback_query.edit_message_text("Proses ini sudah tidak aktif atau selesai.")


@app.on_callback_query(filters.regex(r"^back_to_start$"))
async def back_to_start_callback(client, callback_query):
    await callback_query.message.delete()
    await start_command(client, callback_query.message)


@app.on_chat_member_updated()
async def member_update_handler(client, update):
    me = await client.get_me()
    if not update.new_chat_member or update.new_chat_member.user.id != me.id:
        return

    chat_id = update.chat.id
    chat_title = update.chat.title
    group_info = {"id": chat_id, "title": chat_title}
    admin_user = update.from_user
    
    current_groups = db.getListVars("bot_config", "groups") or []
    
    if update.new_chat_member.status in [ChatMemberStatus.LEFT, ChatMemberStatus.BANNED]:
        if any(g['id'] == chat_id for g in current_groups):
            db.removeListVars("bot_config", "groups", group_info)
            log.print(f"{log.ORANGE}Bot dikeluarkan dari: {log.CYAN}{chat_title} ({chat_id}){log.ORANGE}. Data dihapus.")
            if admin_user:
                try:
                    await client.send_message(admin_user.id, f"Saya telah dikeluarkan dari grup **{chat_title}**. Data grup tersebut telah dihapus dari database saya.")
                except Exception as e:
                    log.print(f"{log.YELLOW}Gagal notif keluar ke admin {log.CYAN}{admin_user.id}{log.YELLOW}: {e}")

    elif update.new_chat_member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.MEMBER]:
        if not any(g['id'] == chat_id for g in current_groups):
            db.setListVars("bot_config", "groups", group_info)
            log.print(f"{log.GREEN}Bot ditambahkan ke: {log.CYAN}{chat_title} ({chat_id}){log.GREEN}. Data disimpan.")
            if admin_user:
                admin_mention = client.ns.telegram.arg.getMention(admin_user)
                try:
                    await client.send_message(chat_id, f"Terima kasih {admin_mention} telah menambahkan saya! Saya siap membantu melakukan tagall.")
                except Exception as e:
                    log.print(f"{log.YELLOW}Gagal kirim sapaan ke grup {log.CYAN}{chat_id}{log.YELLOW}: {e}")
                
                try:
                    btn, _ = client.ns.telegram.button.create_inline_keyboard("| Kembali ke Menu Utama - back_to_start |")
                    await client.send_message(admin_user.id, f"Anda berhasil menambahkan saya ke **{chat_title}**. Gunakan menu di bawah untuk memulai.", reply_markup=btn)
                except Exception as e:
                    log.print(f"{log.YELLOW}Gagal notif tambah ke admin {log.CYAN}{admin_user.id}{log.YELLOW}: {e}")

if __name__ == "__main__":
    log.print(f"{log.GREEN}Memulai Bot Tagall Assistant...")
    app.run()
