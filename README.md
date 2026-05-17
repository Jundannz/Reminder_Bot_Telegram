# Telegram Calendar Bot

Bot Telegram yang membaca teks jadwal atau file PDF, lalu secara otomatis mencatatnya ke Google Calendar menggunakan Gemini AI sebagai pemroses bahasa alami.

---

## Cara Kerja

1. Pengguna mengirim pesan teks atau file PDF ke bot Telegram.
2. Bot mengekstrak isi teks (jika PDF) lalu mengirimkannya ke Gemini AI.
3. Gemini mengurai informasi seperti nama acara, waktu, lokasi, dan deskripsi.
4. Hasilnya dikirim ke Google Calendar API untuk membuat event baru.
5. Bot membalas dengan ringkasan event dan tautan langsung ke Google Calendar.

---

## Struktur Proyek

```
.
├── bot_main.py          # Entry point bot, menangani pesan Telegram
├── llm_extractor.py     # Menghubungi Gemini AI untuk mengurai jadwal
├── calendar_service.py  # Menghubungi Google Calendar API untuk membuat event
├── requirements.txt     # Daftar dependensi Python
└── .env                 # Konfigurasi kunci API (tidak di-commit ke Git)
```

---

## Prasyarat

- Python 3.10 atau lebih baru
- Akun Google dengan Google Calendar API aktif
- API Key Gemini dari Google AI Studio
- Bot Telegram yang sudah dibuat melalui BotFather

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
```

### Penjelasan setiap variabel

| Variabel | Keterangan |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Token bot yang diperoleh dari BotFather di Telegram |
| `GEMINI_API_KEY` | API Key dari Google AI Studio untuk mengakses Gemini |
| `GOOGLE_CREDS_JSON` | Isi lengkap file `credentials.json` dari Google Cloud Console, ditulis dalam satu baris JSON |
| `GOOGLE_TOKEN_JSON` | Diisi otomatis setelah proses autentikasi OAuth pertama kali berhasil |

### Mendapatkan Google Credentials

1. Buka [Google Cloud Console](https://console.cloud.google.com).
2. Buat proyek baru atau gunakan proyek yang sudah ada.
3. Aktifkan **Google Calendar API** di bagian Library.
4. Buat kredensial bertipe **OAuth 2.0 Client ID** dengan Application Type: **Desktop App**.
5. Unduh file JSON-nya, lalu salin seluruh isinya sebagai nilai `GOOGLE_CREDS_JSON` di file `.env`.

---

## Autentikasi Google (Pertama Kali)

Jalankan `calendar_service.py` secara langsung untuk memulai proses login:

```bash
python calendar_service.py
```

Browser akan terbuka secara otomatis dan meminta izin akses ke Google Calendar. Setelah disetujui, token akan dicetak di terminal. Salin token tersebut dan tempelkan sebagai nilai `GOOGLE_TOKEN_JSON` di file `.env`.

Langkah ini hanya perlu dilakukan sekali. Selanjutnya bot akan memperbarui token secara otomatis selama refresh token masih valid.

---

## Menjalankan Bot

```bash
python bot_main.py
```

Jika berhasil, terminal akan menampilkan:

```
Bot Telegram sudah menyala. Tekan Ctrl+C untuk mematikan.
```

---

## Cara Penggunaan

Kirim salah satu dari berikut ke bot:

- **Pesan teks biasa**, contoh:
  ```
  Besok jam 7 malam ada rapat himpunan di ruang A201
  ```

- **File PDF** berisi undangan, jadwal, atau informasi acara.

Bot akan membalas dengan konfirmasi berisi nama acara, waktu, lokasi, deskripsi, dan tautan langsung ke event di Google Calendar.

---

## Catatan Teknis

- Waktu server dijadikan acuan saat memproses kata-kata relatif seperti "besok" atau "lusa".
- Jika waktu selesai tidak disebutkan dalam teks, bot secara otomatis menambahkan 1 jam dari waktu mulai.
- PDF yang bersifat scan gambar (bukan teks digital) tidak dapat diproses karena bot hanya mengekstrak teks tertulis, bukan OCR.
- File PDF sementara yang diunduh akan langsung dihapus setelah teks berhasil diekstrak.

---

## Dependensi Utama

| Paket | Fungsi |
|---|---|
| `python-telegram-bot` | Menangani komunikasi dengan Telegram Bot API |
| `google-genai` | Menghubungi Gemini AI untuk mengurai teks jadwal |
| `google-api-python-client` | Berinteraksi dengan Google Calendar API |
| `google-auth-oauthlib` | Menangani proses autentikasi OAuth 2.0 |
| `PyPDF2` | Mengekstrak teks dari file PDF |
| `pydantic` | Mendefinisikan skema output terstruktur dari Gemini |
| `python-dotenv` | Membaca konfigurasi dari file `.env` |
