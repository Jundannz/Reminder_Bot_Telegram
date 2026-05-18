# Telegram Calendar Bot

Bot Telegram yang membaca teks jadwal atau file PDF, lalu secara otomatis mencatat, memperbarui, atau menghapus event di Google Calendar dan Google Tasks menggunakan Gemini AI sebagai pemroses bahasa alami.

---

## Cara Kerja

1. Pengguna mengirim pesan teks atau file PDF ke bot Telegram.
2. Bot mengekstrak isi teks (jika PDF) lalu mengirimkannya ke Gemini AI.
3. Gemini mengurai informasi seperti nama acara, waktu, lokasi, deskripsi, dan jenis tindakan (tambah, ubah, hapus, atau buat tugas).
4. Berdasarkan jenis tindakan, bot menjalankan operasi yang sesuai ke Google Calendar API atau Google Tasks API.
5. Untuk tindakan yang bersifat destruktif (ubah atau hapus), bot meminta konfirmasi terlebih dahulu melalui tombol inline sebelum mengeksekusi.
6. Bot membalas dengan ringkasan hasil dan tautan langsung ke Google Calendar.

---

## Fitur

**Tambah event baru**
Kirim teks seperti "Besok jam 7 malam ada rapat himpunan di ruang A201" dan bot akan langsung membuat event di kalender.

**Perbarui event yang sudah ada**
Kirim teks revisi jadwal. Bot akan mencari event lama yang relevan dan meminta konfirmasi sebelum mengubahnya.

**Hapus event**
Kirim teks pembatalan. Bot akan mencari event yang dimaksud dan meminta konfirmasi sebelum menghapusnya.

**Buat tugas atau deadline**
Teks yang mengandung tugas, PR, pekerjaan freelance, atau deadline akan otomatis dicatat sebagai Google Task, bukan event kalender.

**Baca file PDF**
Kirim file PDF berisi undangan atau jadwal. Bot mengekstrak teks dari PDF dan memprosesnya sama seperti pesan teks biasa.

**Proses banyak agenda sekaligus**
Satu pesan bisa mengandung beberapa jadwal sekaligus. Semua akan diproses dalam satu respons.

---

## Struktur Proyek

```
.
├── bot_main.py          # Entry point, menangani pesan Telegram dan webhook FastAPI
├── llm_extractor.py     # Menghubungi Gemini AI untuk mengurai teks jadwal
├── calendar_service.py  # Operasi CRUD ke Google Calendar API dan Google Tasks API
├── requirements.txt     # Daftar dependensi Python
└── .env                 # Konfigurasi kunci API (tidak di-commit ke Git)
```

---

## Prasyarat

- Python 3.10 atau lebih baru
- Akun Google dengan Google Calendar API dan Google Tasks API aktif
- API Key Gemini dari Google AI Studio
- Bot Telegram yang sudah dibuat melalui BotFather
- Domain publik (untuk mode webhook saat deploy ke cloud)

---

## Instalasi

### 1. Clone repositori dan masuk ke direktori

```bash
git clone <url-repositori>
cd <nama-direktori>
```

### 2. Buat virtual environment dan aktifkan

```bash
python -m venv venv

# Linux / macOS
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 3. Install dependensi

```bash
pip install -r requirements.txt
```

---

## Konfigurasi

### Buat file `.env`

Salin file contoh dan isi dengan nilai yang sesuai:

```bash
cp .env.example .env
```

Isi variabel berikut di dalam `.env`:

```env
TELEGRAM_BOT_TOKEN=token_dari_botfather
GEMINI_API_KEY=api_key_dari_google_ai_studio
GOOGLE_CREDS_JSON={"installed":{"client_id":"...","client_secret":"...",...}}
GOOGLE_TOKEN_JSON=
WEBHOOK_URL=
```

### Penjelasan setiap variabel

| Variabel | Keterangan |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Token bot yang diperoleh dari BotFather di Telegram |
| `GEMINI_API_KEY` | API Key dari Google AI Studio untuk mengakses Gemini |
| `GOOGLE_CREDS_JSON` | Isi lengkap file `credentials.json` dari Google Cloud Console, ditulis dalam satu baris JSON |
| `GOOGLE_TOKEN_JSON` | Diisi otomatis setelah proses autentikasi OAuth pertama kali berhasil |
| `WEBHOOK_URL` | URL endpoint webhook publik, contoh: `https://nama-app.koyeb.app/webhook`. Kosongkan saat pengembangan lokal |

### Mendapatkan Google Credentials

1. Buka [Google Cloud Console](https://console.cloud.google.com).
2. Buat proyek baru atau gunakan proyek yang sudah ada.
3. Aktifkan **Google Calendar API** dan **Google Tasks API** di bagian Library.
4. Buat kredensial bertipe **OAuth 2.0 Client ID** dengan Application Type: **Desktop App**.
5. Unduh file JSON-nya, lalu salin seluruh isinya sebagai nilai `GOOGLE_CREDS_JSON` di file `.env`.

---

## Autentikasi Google (Pertama Kali)

Jalankan `calendar_service.py` secara langsung untuk memulai proses login:

```bash
python calendar_service.py
```

Browser akan terbuka secara otomatis dan meminta izin akses ke Google Calendar dan Google Tasks. Setelah disetujui, token akan dicetak di terminal. Salin token tersebut dan tempelkan sebagai nilai `GOOGLE_TOKEN_JSON` di file `.env`.

Langkah ini hanya perlu dilakukan sekali. Selanjutnya bot akan memperbarui token secara otomatis selama refresh token masih valid.

---

## Menjalankan Bot

```bash
python bot_main.py
```

Bot berjalan sebagai server FastAPI menggunakan Uvicorn. Saat `WEBHOOK_URL` diisi, bot otomatis mendaftarkan webhook ke Telegram saat server menyala. Jika `WEBHOOK_URL` kosong, bot tetap berjalan tetapi tidak akan menerima pesan karena tidak ada webhook yang terdaftar — gunakan mode ini hanya untuk pengujian lokal dengan tunneling (seperti ngrok).

Server akan berjalan di port yang ditentukan oleh environment variable `PORT`, atau port `8000` jika tidak ada.

---

## Deploy ke Cloud (Koyeb / Render)

1. Pastikan semua variabel di `.env` sudah diisi, termasuk `WEBHOOK_URL` yang mengarah ke domain publik aplikasi dengan path `/webhook`, contoh: `https://nama-app.koyeb.app/webhook`.
2. Deploy kode ke platform cloud pilihan.
3. Set semua variabel environment di dashboard platform tersebut.
4. Saat server pertama kali menyala, webhook akan otomatis terdaftar ke Telegram.

Endpoint yang tersedia setelah deploy:

| Path | Method | Keterangan |
|---|---|---|
| `/webhook` | POST | Pintu masuk pesan dari Telegram |
| `/` | GET | Health check, mengembalikan status server |

---

## Cara Penggunaan

Kirim salah satu dari berikut ke bot:

**Teks biasa — tambah event:**
```
Besok jam 7 malam ada rapat himpunan di ruang A201
```

**Teks biasa — perbarui event:**
```
Rapat himpunan besok dipindah ke jam 8 malam
```

**Teks biasa — batalkan event:**
```
Rapat himpunan besok dibatalkan
```

**Teks biasa — tambah tugas/deadline:**
```
Kumpulkan laporan PKM paling lambat Jumat jam 23.59
```

**File PDF** berisi undangan, jadwal, atau informasi acara.

Untuk tindakan ubah dan hapus, bot akan menampilkan tombol konfirmasi sebelum mengeksekusi perubahan.

---

## Catatan Teknis

- Waktu server dijadikan acuan saat memproses kata-kata relatif seperti "besok" atau "lusa".
- Jika waktu selesai tidak disebutkan, bot secara otomatis menambahkan 1 jam dari waktu mulai.
- Teks yang dideteksi sebagai tugas atau deadline dicatat ke Google Tasks, bukan Google Calendar.
- Pencarian event lama untuk operasi ubah dan hapus menggunakan nama acara atau `referensi_lama` yang diekstrak oleh Gemini, lalu mengambil hasil teratas yang paling relevan.
- PDF yang bersifat scan gambar tidak dapat diproses karena bot hanya mengekstrak teks digital, bukan OCR.
- File PDF sementara yang diunduh akan langsung dihapus setelah teks berhasil diekstrak.

---

## Dependensi Utama

| Paket | Fungsi |
|---|---|
| `python-telegram-bot` | Menangani komunikasi dengan Telegram Bot API |
| `fastapi` + `uvicorn` | Server web untuk menerima webhook dari Telegram |
| `google-genai` | Menghubungi Gemini AI (model: gemini-2.5-flash) untuk mengurai teks jadwal |
| `google-api-python-client` | Berinteraksi dengan Google Calendar API dan Google Tasks API |
| `google-auth-oauthlib` | Menangani proses autentikasi OAuth 2.0 |
| `PyPDF2` | Mengekstrak teks dari file PDF |
| `pydantic` | Mendefinisikan skema output terstruktur dari Gemini |
| `python-dotenv` | Membaca konfigurasi dari file `.env` |
