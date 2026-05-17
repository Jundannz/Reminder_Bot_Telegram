import os
import json
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from llm_extractor import extract_event_info

load_dotenv()

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pesan_pembuka = (
        "Halo! Aku bot pengingat jadwalmu.\n"
        "Kirimkan teks atau undangan atau jadwal acara/rapat, "
        "dan aku akan mengekstrak informasinya."
    )
    await update.message.reply_text(pesan_pembuka)

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    teks_masuk = update.message.text
    pesan_tunggu = await update.message.reply_text("Sedang memproses jadwalmu...")
    
    try:
        # panggil fungsi llm
        hasil_json = extract_event_info(teks_masuk)
        teks_balasan = f"<b>Data berhasil diekstrak:</b>\n<pre>{json.dumps(hasil_json, indent=2, ensure_ascii=False)}</pre>"
        await pesan_tunggu.edit_text(teks_balasan, parse_mode='HTML')
        
    except Exception as e:
        await pesan_tunggu.edit_text(f"Waduh, terjadi kesalahan saat memproses jadwalmu: {str(e)}")

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