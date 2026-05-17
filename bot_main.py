import os
import json
import PyPDF2
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
    
async def process_and_reply(update: Update, text_content: str, status_message):
    try:
        # ekstrak informasi acara jadi dictionary menggunakan llm
        event_data = extract_event_info(text_content)
        
        # kirim data ke google calendar
        link_kalender = create_calendar_event(event_data)
        
        # susun konfirmasi akhir
        lokasi = event_data.get('lokasi') if event_data.get('lokasi') else "Tidak disebutkan"
        
        teks_balasan = (
            "<b>Jadwal Berhasil Ditambahkan!</b>\n\n"
            f"Nama Acara: {event_data['nama_acara']}\n"
            f"Waktu Mulai: {event_data['waktu']}\n"
            f"Lokasi: {lokasi}\n"
            f"Deskripsi: {event_data['deskripsi']}\n\n"
            f"Silakan cek di sini: {link_kalender}"
        )
        
        await status_message.edit_text(teks_balasan, parse_mode='HTML', disable_web_page_preview=True)
        
    except Exception as e:
        await status_message.edit_text(f"Gagal memproses jadwal. Error: {str(e)}")

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pesan_tunggu = await update.message.reply_text("Sedang memproses jadwalmu...")
    await process_and_reply(update, update.message.text, pesan_tunggu)
    
async def handle_pdf_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    dokumen = update.message.document
    
    # verifikasi tipe file PDF
    if dokumen.mime_type != 'application/pdf':
        await update.message.reply_text("Format file tidak didukung. Mohon kirim file PDF")
        return
    
    pesan_tunggu = await update.message.reply_text("Sedang memproses PDF...")
    
    try:
        # unduh file PDF ke memori
        file_obj = await context.bot.get_file(dokumen.file_id)
        nama_file_temp = f"temp_{dokumen.file_id}.pdf"
        await file_obj.download_to_drive(nama_file_temp)
        
        # ekstrak teks dari PDF
        teks_ekstraksi = ""
        with open(nama_file_temp, 'rb') as pdf_file:
            reader = PyPDF2.PdfReader(pdf_file)
            for page in reader.pages:
                teks_halaman = page.extract_text()
                if teks_halaman:
                    teks_ekstraksi += teks_halaman + "\n"
        
        os.remove(nama_file_temp)  # hapus file sementara
        
        if not teks_ekstraksi.strip():
            await pesan_tunggu.edit_text("Tidak dapat mengekstrak teks dari PDF. Pastikan PDF berisi teks yang dapat diproses.")
            return
        
        await pesan_tunggu.edit_text("Teks berhasil diekstrak. Sedang memproses jadwal...")
        
        # lempar teks hasil ekstraksi ke fungsi pemrosesan yang sama dengan pesan teks biasa
        await process_and_reply(update, teks_ekstraksi, pesan_tunggu)
        
    except Exception as e:
        await pesan_tunggu.edit_text(f"Gagal memproses PDF. Error: {str(e)}")
        
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
    # handler khusus untuk dokumen PDF
    app.add_handler(MessageHandler(filters.Document.PDF, handle_pdf_document))
    
    print("Bot Telegram sudah menyala. Tekan Ctrl+C untuk mematikan.")
    
    app.run_polling()