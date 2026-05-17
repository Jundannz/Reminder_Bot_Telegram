import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from llm_extractor import extract_event_info
from calendar_service import create_calendar_event

load_dotenv()

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pesan_pembuka = (
        "Halo! Kirim teks jadwal atau undangan apa saja di sini. "
        "Aku akan otomatis mencatatnya ke Google Calendar milikmu."
    )
    await update.message.reply_text(pesan_pembuka)

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    teks_masuk = update.message.text
    pesan_tunggu = await update.message.reply_text("Sedang memproses jadwalmu...")
    
    try:
        # ekstrak teks mentah to dictionary menggunakan LLM
        event_data = extract_event_info(teks_masuk)
        
        # kirim data ke google calendar
        link_kalender = create_calendar_event(event_data)
        
        # susun konfirmasi dengan data yang berhasil diekstrak dan link ke kalender
        lokasi = event_data.get('lokasi') if event_data.get('lokasi') else "Tidak disebutkan"
        
        teks_balasan = (
            "<b>Jadwal Berhasil Ditambahkan!</b>\n\n"
            f"Nama Acara: {event_data['nama_acara']}\n"
            f"Waktu Mulai: {event_data['waktu']}\n"
            f"Lokasi: {lokasi}\n"
            f"Deskripsi: {event_data['deskripsi']}\n\n"
            f"Silakan cek di sini: {link_kalender}"
        )
        
        # update pesan tunggu dengan konfirmasi sukses
        await pesan_tunggu.edit_text(teks_balasan, parse_mode='HTML', disable_web_page_preview=True)
        
    except Exception as e:
        # menangani errror
        await pesan_tunggu.edit_text(f"Gagal memproses jadwal. Error: {str(e)}")

if __name__ == "__main__":
    #inisialisasi bot dari api
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    
    if not token:
        print("Error: TELEGRAM_BOT_TOKEN tidak ditemukan di environment")
        exit(1)
    
    app = ApplicationBuilder().token(token).build()
    
    # daftarkan handler untuk command /start dan pesan teks biasa
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
    
    print("Bot Telegram sudah menyala. Tekan Ctrl+C untuk mematikan.")
    
    app.run_polling()