# Tagall Assistant Bot

Sebuah bot Telegram canggih yang dirancang untuk menyederhanakan proses penyebutan (tagging) semua anggota dalam sebuah grup. Bot ini dikelola sepenuhnya melalui percakapan pribadi, menyediakan alur yang aman dan interaktif bagi para admin grup.

Dibangun menggunakan Pyrogram dan pustaka `norsodikin`, bot ini menawarkan pengalaman yang mulus mulai dari instalasi hingga penggunaan sehari-hari.

## ⭐ Fitur Unggulan

-   **Alur Interaktif & Aman**: Semua perintah, mulai dari pemilihan pesan hingga eksekusi tagall, dilakukan di chat pribadi bot untuk menjaga kebersihan obrolan grup.
-   **Dukungan Pesan Kaya Fitur**: Lakukan tagall menggunakan teks, foto, video, atau media lainnya. Semua format asli seperti **bold**, *italic*, dan `hyperlink` akan tetap terjaga.
-   **Dukungan Tombol Interaktif**: Sertakan tombol *inline* di dalam pesan tagall Anda. Bot akan secara otomatis mem-parsing sintaks `| Teks Tombol - data |` dari teks atau caption.
-   **Mention dengan Emoji Acak**: Alih-alih menggunakan nama, anggota grup akan di-*mention* menggunakan emoji acak, membuat tagall terlihat lebih menarik dan tidak monoton.
-   **Tagall Bertahap (Batching)**: Menyebut 5 anggota per pesan untuk menghindari *rate limit* Telegram dan mengurangi kesan spam di grup.
-   **Jeda Anti-Spam**: Jeda 5 detik antar setiap pengiriman pesan tagall untuk memastikan operasi yang aman dan lancar.
-   **Pembatalan Kontekstual**: Tombol **"❌ Batalkan Proses"** muncul langsung pada pesan status saat tagall dimulai. Tombol ini akan otomatis hilang setelah proses selesai atau dibatalkan.
-   **Instalasi Grup Mudah**: Tombol "Tambahkan Bot ke Grup" di menu utama akan secara otomatis meminta hak admin penuh, menyederhanakan proses penyiapan.
-   **Manajemen Database Dinamis**: Bot secara otomatis mengelola daftar grup di databasenya saat ia ditambahkan atau dikeluarkan dari sebuah grup.

## 🚀 Pengaturan dan Instalasi

Ikuti langkah-langkah mudah ini untuk menjalankan bot Anda.

### 1. Prasyarat

-   Python 3.9 atau lebih tinggi.
-   API ID dan API Hash dari [my.telegram.org](https://my.telegram.org).
-   Bot Token dari [@BotFather](https://t.me/BotFather).

### 2. Kloning Repositori

Pertama, kloning repositori ini ke mesin lokal atau server Anda.
```bash
git clone https://github.com/SenpaiSeeker/TagallAssistant.git
cd TagallAssistant
```

### 3. Instalasi Dependensi

Instal semua pustaka Python yang diperlukan menggunakan file `requirements.txt`.
```bash
pip3 install -r requirements.txt
```

### 4. Konfigurasi Menggunakan Skrip

Untuk mempermudah, gunakan skrip `config.sh` yang telah disediakan untuk membuat file environment Anda.

1.  Jalankan skrip di terminal Anda:
    ```bash
    bash config.sh
    ```

2.  Skrip akan memandu Anda untuk memasukkan informasi berikut secara berurutan:
    -   `API_ID` Anda.
    -   `API_HASH` Anda.
    -   `BOT_TOKEN` Anda.
    -   `OWNER_ID` numerik Anda (bisa didapat dari [@userinfobot](https://t.me/userinfobot)).

    Setelah selesai, skrip akan secara otomatis membuat file `.env` yang berisi semua kredensial Anda.

### 5. Menjalankan Bot

Setelah file `.env` dibuat, jalankan bot dengan perintah sederhana berikut:

```bash
python3 main.py
```

Bot Anda sekarang akan online dan siap untuk digunakan.

## 📖 Panduan Penggunaan

### Langkah 1: Menambahkan Bot ke Grup

1.  Mulai bot Anda melalui chat pribadi dan tekan tombol **"➕ Tambahkan Bot ke Grup"**.
2.  Pilih grup target dari daftar Anda.
3.  Telegram akan meminta Anda untuk memberikan hak admin kepada bot. Pastikan semua izin diberikan agar bot dapat berfungsi dengan baik.

### Langkah 2: Memulai Proses Tagall

1.  Buka chat pribadi dengan bot Anda dan kirim perintah `/start`.
2.  Tekan tombol **"🚀 Mulai Tagall"**.
3.  Bot akan meminta Anda untuk mengirimkan pesan yang ingin digunakan sebagai dasar tagall. Kirimkan pesan apa pun.
    -   **Untuk menyertakan tombol**, gunakan format `| Teks Tombol - data_callback |` di dalam teks atau caption Anda. Contoh:
        ```
        Ini adalah pengumuman penting!
        | Kunjungi Website - https://google.com | | Channel Kami - https://t.me/FakeCodeX |
        ```
4.  Setelah pesan terkirim, bot akan menampilkan daftar grup di mana Anda adalah admin. Pilih grup target.
5.  Konfirmasikan tindakan Anda dengan menekan tombol **"✅ Ya, Mulai"**.
6.  Proses tagall akan dimulai. Anda akan menerima pesan status di chat pribadi yang mengonfirmasi bahwa proses sedang berjalan.

### Langkah 3: Membatalkan Proses Tagall

Jika Anda perlu menghentikan proses tagall yang sedang berjalan:

1.  Cari pesan status **"✅ Proses tagall dimulai..."** di chat pribadi Anda dengan bot.
2.  Tekan tombol **"❌ Batalkan Proses"** yang ada di bawah pesan tersebut.
3.  Bot akan segera menghentikan proses tagall dan mengedit pesan status untuk mengonfirmasi pembatalan.

---
#### Dibuat oleh: [@NorSodikin](https://t.me/NorSodikin)
