import asyncio
import random

from nsdev import listen
from pyrogram import Client, emoji, filters
from pyrogram.enums import ChatMemberStatus, ChatType
from pyrogram.errors import FloodWait, UserNotParticipant

from config import API_HASH, API_ID, BOT_TOKEN

app = Client(
    "TagallAssistant",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
)

db = app.ns.data.db(file_name="tagall_db")
log = app.ns.utils.log

TAGS_PER_MESSAGE = 5
TAG_DELAY_SECONDS = 5
VERIFIED_GROUPS = set()
TAGALL_PROCESSES = {}

RANDOM_EMOJIS = list(vars(emoji).values())


@app.on_message(filters.group, group=-1)
async def group_filter_handler(client, message):
    chat_id = message.chat.id
    if chat_id in VERIFIED_GROUPS:
        return

    all_groups_in_db = db.getListVars("bot_config", "groups") or []
    known_group_ids = {g["id"] for g in all_groups_in_db}

    if chat_id in known_group_ids:
        VERIFIED_GROUPS.add(chat_id)
    else:
        group_info = {"id": chat_id, "title": message.chat.title}
        db.setListVars("bot_config", "groups", group_info)
        VERIFIED_GROUPS.add(chat_id)
        log.print(
            f"{log.GREEN}Grup baru terdeteksi dan otomatis ditambahkan ke database: {log.CYAN}{message.chat.title} ({chat_id})"
        )


async def get_admin_groups(user_id):
    admin_groups = []
    groups_in_db = db.getListVars("bot_config", "groups") or []
    for group_info in groups_in_db:
        try:
            member = await app.get_chat_member(group_info["id"], user_id)
            if member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
                admin_groups.append(group_info)
        except UserNotParticipant:
            continue
        except Exception as e:
            log.print(f"{log.YELLOW}Gagal memeriksa admin di grup {log.CYAN}{group_info['id']}{log.YELLOW}: {e}")
            continue
    return admin_groups


async def get_start_menu(client):
    text = (
        "Halo! Saya adalah Asisten Tagall.\n\n"
        "Klik tombol di bawah ini untuk memulai proses menandai semua anggota di grup Anda."
    )

    bot_username = client.me.username
    admin_rights = "invite_users+delete_messages+pin_messages+manage_chat+restrict_members"
    add_to_group_url = f"https://t.me/{bot_username}?startgroup=true&admin={admin_rights}"

    btn_text = "| 🚀 Mulai Tagall - start_tagall_process |\n"
    btn_text += f"| ➕ Tambahkan Bot ke Grup - {add_to_group_url} |"

    markup, txt = client.ns.telegram.button.create_inline_keyboard(f"{text}\n\n{btn_text}")
    return txt, markup


async def send_tagall_message(client, chat_id, original_message, tags):
    full_tags = " ".join(tags)

    if original_message.media:
        base_caption = original_message.caption.markdown if original_message.caption else ""
        reply_markup, cleaned_caption = client.ns.telegram.button.create_inline_keyboard(base_caption)
        final_caption = cleaned_caption + "\n\n" + full_tags

        if reply_markup and reply_markup.inline_keyboard:
            await original_message.copy(chat_id, caption=final_caption, reply_markup=reply_markup)
        else:
            await original_message.copy(chat_id, caption=final_caption)
    else:
        base_text = original_message.text.markdown if original_message.text else ""
        reply_markup, cleaned_text = client.ns.telegram.button.create_inline_keyboard(base_text)
        final_text = cleaned_text + "\n\n" + full_tags

        if reply_markup and reply_markup.inline_keyboard:
            await client.send_message(chat_id, final_text, reply_markup=reply_markup)
        else:
            await client.send_message(chat_id, final_text)


@app.on_message(filters.command("start") & filters.private)
async def start_command(client, message):
    txt, markup = await get_start_menu(client)
    await message.reply_text(txt, reply_markup=markup)


@app.on_callback_query(filters.regex(r"^back_to_start$"))
async def back_to_start_callback(client, callback_query):
    txt, markup = await get_start_menu(client)
    await callback_query.message.edit_text(txt, reply_markup=markup)


@app.on_callback_query(filters.regex(r"^start_tagall_process$"))
async def start_tagall_process_callback(client, callback_query):
    user_id = callback_query.from_user.id
    admin_groups = await get_admin_groups(user_id)

    if not admin_groups:
        return await callback_query.answer("Anda bukan admin di grup manapun tempat saya berada.", show_alert=True)

    await callback_query.message.delete()

    try:
        ask_msg = await client.ask(
            user_id,
            "Baik, kirimkan pesan yang akan digunakan untuk tagall.\n\nFormat tombol: `| Teks - data |`\nKetik /batal untuk membatalkan.",
            timeout=600,
        )

        if ask_msg.text and ask_msg.text.lower() == "/batal":
            raise listen.UserCancelled

        db.setVars(user_id, "last_message_to_tag", {"chat_id": ask_msg.chat.id, "message_id": ask_msg.id})

        buttons_text = "\n".join([f"| {g['title']} - select_group_{g['id']} |" for g in admin_groups])
        markup, txt = client.ns.telegram.button.create_inline_keyboard(f"Pesan diterima. Pilih grup:\n\n{buttons_text}")
        await client.send_message(user_id, txt, reply_markup=markup)

    except listen.UserCancelled:
        await client.send_message(user_id, "Proses dibatalkan.")
    except asyncio.TimeoutError:
        await client.send_message(user_id, "Waktu habis, silakan mulai lagi dari /start.")
    except Exception as e:
        log.print(f"{log.RED}Error pada alur 'ask' untuk user {log.CYAN}{user_id}{log.RED}: {e}")
        await client.send_message(user_id, f"Terjadi kesalahan: `{e}`")


@app.on_callback_query(filters.regex(r"^select_group_(-?\d+)"))
async def select_group_callback(client, callback_query):
    chat_id = int(callback_query.matches[0].group(1))

    if chat_id in TAGALL_PROCESSES:
        return await callback_query.answer("Proses tagall sudah berjalan di grup ini.", show_alert=True)

    btn_text = f"| ✅ Ya, Mulai - start_tagall_{chat_id} |\n| ❌ Tidak, Kembali - start_tagall_process |"
    markup, txt = client.ns.telegram.button.create_inline_keyboard(
        f"Anda yakin ingin memulai tagall di grup ini?\n\n{btn_text}"
    )
    await callback_query.edit_message_text(txt, reply_markup=markup)


async def run_tagall_process(client, user_id, chat_id, status_message, original_message, cancel_event):
    try:
        total_tagged = 0
        user_mentions = []
        async for member in client.get_chat_members(chat_id):
            if cancel_event.is_set():
                break

            if not member.user.is_bot:
                emoji_char = random.choice(RANDOM_EMOJIS)
                mention = f'<a href="tg://user?id={member.user.id}">{emoji_char}</a>'
                user_mentions.append(mention)

            if len(user_mentions) == TAGS_PER_MESSAGE:
                await send_tagall_message(client, chat_id, original_message, user_mentions)
                total_tagged += len(user_mentions)
                user_mentions = []
                await asyncio.sleep(TAG_DELAY_SECONDS)

        if user_mentions and not cancel_event.is_set():
            await send_tagall_message(client, chat_id, original_message, user_mentions)
            total_tagged += len(user_mentions)

    except FloodWait as e:
        log.print(f"{log.YELLOW}FloodWait terdeteksi. Menunggu {log.CYAN}{e.value}{log.YELLOW} detik.")
        await asyncio.sleep(e.value)
    except Exception as e:
        log.print(f"{log.RED}Error saat tagall di {log.CYAN}{chat_id}{log.RED}: {e}")
        await client.send_message(user_id, f"Proses tagall dihentikan karena error: `{e}`")
    finally:
        if cancel_event.is_set():
            log.print(f"{log.YELLOW}Tagall di grup {log.CYAN}{chat_id}{log.YELLOW} dibatalkan.")
            await status_message.edit_text("❌ Proses tagall dibatalkan.")
            await client.send_message(user_id, f"Proses tagall dihentikan. Total {total_tagged} pengguna ditandai.")
        else:
            log.print(f"{log.GREEN}Tagall di grup {log.CYAN}{chat_id}{log.GREEN} selesai. Total: {total_tagged}.")
            await status_message.edit_text("✅ Proses tagall telah selesai!")
            await client.send_message(user_id, f"✅ Proses tagall selesai! Total {total_tagged} pengguna ditandai.")

        if chat_id in TAGALL_PROCESSES:
            del TAGALL_PROCESSES[chat_id]


@app.on_callback_query(filters.regex(r"^start_tagall_(-?\d+)"))
async def start_tagall_callback(client, callback_query):
    chat_id = int(callback_query.matches[0].group(1))
    user_id = callback_query.from_user.id

    try:
        member = await client.get_chat_member(chat_id, user_id)
        if member.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
            return await callback_query.answer("Anda bukan admin lagi di grup ini.", show_alert=True)

        message_data = db.getVars(user_id, "last_message_to_tag")
        if not message_data:
            return await callback_query.edit_message_text("Pesan untuk tagall tidak ditemukan. Silakan mulai ulang.")
        original_message = await client.get_messages(message_data["chat_id"], message_data["message_id"])

    except Exception as e:
        return await callback_query.edit_message_text(
            f"Gagal memulai: Pesan asli mungkin telah dihapus atau terjadi kesalahan.\n`{e}`"
        )

    btn = client.ns.telegram.button.create_inline_keyboard(f"| ❌ Batalkan Proses - cancel_tagall_{chat_id} |")[0]
    status_message = await callback_query.edit_message_text("✅ Proses tagall dimulai...", reply_markup=btn)

    cancel_event = asyncio.Event()
    TAGALL_PROCESSES[chat_id] = cancel_event

    asyncio.create_task(run_tagall_process(client, user_id, chat_id, status_message, original_message, cancel_event))


@app.on_callback_query(filters.regex(r"^cancel_tagall_(-?\d+)"))
async def cancel_tagall_callback(client, callback_query):
    chat_id = int(callback_query.matches[0].group(1))
    user_id = callback_query.from_user.id

    try:
        member = await client.get_chat_member(chat_id, user_id)
        if member.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
            return await callback_query.answer("Anda tidak berhak membatalkan proses ini.", show_alert=True)
    except Exception:
        return await callback_query.answer("Gagal memverifikasi status admin Anda.", show_alert=True)

    if chat_id in TAGALL_PROCESSES:
        TAGALL_PROCESSES[chat_id].set()
        log.print(
            f"{log.YELLOW}Permintaan pembatalan tagall untuk {log.CYAN}{chat_id}{log.YELLOW} oleh {log.CYAN}{user_id}"
        )
        await callback_query.edit_message_text("⏳ Proses pembatalan sedang berjalan...")
    else:
        await callback_query.answer("Tidak ada proses yang sedang berjalan untuk dibatalkan.", show_alert=True)


@app.on_chat_member_updated()
async def member_update_handler(client, update):
    if not update.new_chat_member or update.new_chat_member.user.id != client.me.id:
        return

    if update.chat.type == ChatType.CHANNEL:
        try:
            await client.send_message(update.chat.id, "Maaf, saya hanya berfungsi di grup, bukan channel.")
        except Exception:
            pass
        await client.leave_chat(update.chat.id)
        return

    chat_id, chat_title, admin_user = update.chat.id, update.chat.title, update.from_user
    group_info = {"id": chat_id, "title": chat_title}

    current_groups = db.getListVars("bot_config", "groups") or []
    is_known_group = any(g["id"] == chat_id for g in current_groups)

    if update.new_chat_member.status in [ChatMemberStatus.LEFT, ChatMemberStatus.BANNED]:
        if is_known_group:
            db.removeListVars("bot_config", "groups", group_info)
            VERIFIED_GROUPS.discard(chat_id)
            log.print(f"{log.ORANGE}Bot dikeluarkan dari: {log.CYAN}{chat_title} ({chat_id})")
            if admin_user:
                try:
                    await client.send_message(admin_user.id, f"Saya telah dikeluarkan dari **{chat_title}**.")
                except Exception:
                    pass

    elif update.new_chat_member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.MEMBER]:
        if not is_known_group:
            db.setListVars("bot_config", "groups", group_info)
            VERIFIED_GROUPS.add(chat_id)
            log.print(f"{log.GREEN}Bot ditambahkan ke: {log.CYAN}{chat_title} ({chat_id})")
            if admin_user:
                mention = client.ns.telegram.arg.getMention(admin_user)
                try:
                    await client.send_message(chat_id, f"Terima kasih {mention} telah menambahkan saya!")
                except Exception:
                    pass

                try:
                    txt, markup = await get_start_menu(client)
                    await client.send_message(
                        admin_user.id, f"Anda berhasil menambahkan saya ke **{chat_title}**.", reply_markup=markup
                    )
                except Exception:
                    pass


if __name__ == "__main__":
    log.print(f"{log.GREEN}Memulai Bot Tagall Assistant...")
    app.run()
