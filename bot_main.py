import os
import json
import PyPDF2
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from llm_extractor import extract_event_info
from calendar_service import create_calendar_event, search_calendar_events, update_calendar_event, delete_calendar_event

load_dotenv()

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pesan_pembuka = (
        "Halo! Kirim teks jadwal atau undangan apa saja di sini. "
        "Aku akan otomatis mencatatnya ke Google Calendar milikmu."
    )
    await update.message.reply_text(pesan_pembuka)
    
async def process_and_reply(update: Update, text_content: str, status_message, context: ContextTypes.DEFAULT_TYPE):
    try:
        events = extract_event_info(text_content)
        
        create_events = [e for e in events if e['intent'] == 'create']
        update_events = [e for e in events if e['intent'] == 'update']
        delete_events = [e for e in events if e['intent'] == 'delete']
        
        # 1. Proses Create
        teks_balasan_create = ""
        for event_data in create_events:
            link = create_calendar_event(event_data)
            lokasi = event_data.get('lokasi') or "Tidak disebutkan"
            teks_balasan_create += (
                f"<b>Jadwal Baru Ditambahkan</b>\n"
                f"Nama: {event_data['nama_acara']}\n"
                f"Waktu: {event_data['waktu']}\n"
                f"Lokasi: {lokasi}\n"
                f"Link: {link}\n\n"
            )
            
        # tampilkan hasil create, atau ubah status jika hanya ada update
        if teks_balasan_create:
            await status_message.edit_text(teks_balasan_create, parse_mode='HTML', disable_web_page_preview=True)
        else:
            await status_message.edit_text("Memeriksa jadwal yang perlu diperbarui...")

        # 2. Proses Update
        if update_events and 'pending_updates' not in context.user_data:
            context.user_data['pending_updates'] = {}

        for event_data in update_events:
            query = event_data.get('referensi_lama') or event_data['nama_acara']
            kandidat = search_calendar_events(query)
            
            if not kandidat:
                await update.message.reply_text(f"Tidak ditemukan jadwal lama untuk: <b>{query}</b>", parse_mode='HTML')
                continue
            
            target = kandidat[0]
            context.user_data['pending_updates'][target['id']] = event_data
            
            keyboard = InlineKeyboardMarkup([[ 
                InlineKeyboardButton("Ya, update", callback_data=f"confirm_update:{target['id']}"),
                InlineKeyboardButton("Batal", callback_data=f"cancel_update:{target['id']}")
            ]])
            
            pesan_konfirmasi = (
                f"Ditemukan event: <b>{target['summary']}</b>\n"
                f"Waktu sekarang: {target['start'].get('dateTime', 'N/A')}\n\n"
                f"Akan diubah menjadi:\n"
                f"Nama: {event_data['nama_acara']}\n"
                f"Waktu baru: {event_data['waktu']}\n\n"
                f"Lanjutkan?"
            )
            
            # Kirim pesan terpisah untuk setiap jadwal yang perlu konfirmasi
            await update.message.reply_text(pesan_konfirmasi, parse_mode='HTML', reply_markup=keyboard)
        
        # 3. Proses Delete
        for event_data in delete_events:
            query = event_data.get('referensi_lama') or event_data['nama_acara']
            kandidat = search_calendar_events(query)
            
            if not kandidat:
                await update.message.reply_text(f"Tidak ditemukan jadwal untuk dibatalkan: <b>{query}</b>", parse_mode='HTML')
                continue
            
            target = kandidat[0]
            if 'pending_updates' not in context.user_data:
                context.user_data['pending_updates'] = {}
            context.user_data['pending_updates'][target['id']] = event_data
            
            keyboard = InlineKeyboardMarkup([[ 
                InlineKeyboardButton("Ya, Hapus", callback_data=f"confirm_delete:{target['id']}"),
                InlineKeyboardButton("Batal", callback_data=f"cancel_delete:{target['id']}")
            ]])
            
            pesan_konfirmasi = (
                f"<b>KONFIRMASI PEMBATALAN</b>\n\n"
                f"Ditemukan event: <b>{target['summary']}</b>\n"
                f"Waktu: {target['start'].get('dateTime', 'N/A')}\n\n"
                f"Apakah kamu yakin ingin <b>MENGHAPUS</b> jadwal ini dari kalender?"
            )
            await update.message.reply_text(pesan_konfirmasi, parse_mode='HTML', reply_markup=keyboard)
            
    except Exception as e:
        await update.message.reply_text(f"Gagal memproses. Error: {str(e)}")

async def handle_update_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    action, event_id = query.data.split(":", 1)
    event_data = context.user_data.get('pending_updates', {}).get(event_id)
    
    if action in ["confirm_update", "confirm_delete"] and not event_data:
        await query.edit_message_text("Session expired. Kirim ulang permintaanmu.")
        return

    try:
        if action == "confirm_update":
            link = update_calendar_event(event_id, event_data)
            await query.edit_message_text(
                f"<b>Jadwal berhasil diperbarui!</b>\nNama: {event_data['nama_acara']}\nWaktu baru: {event_data['waktu']}\nLink: {link}",
                parse_mode='HTML', disable_web_page_preview=True
            )
            del context.user_data['pending_updates'][event_id]

        elif action == "confirm_delete":
            delete_calendar_event(event_id)
            await query.edit_message_text(
                f"<b>Jadwal Dihapus!</b>\nAcara <b>{event_data['nama_acara']}</b> telah dihapus dari kalender.",
                parse_mode='HTML'
            )
            del context.user_data['pending_updates'][event_id]
            
        elif action in ["cancel_update", "cancel_delete"]:
            context.user_data.get('pending_updates', {}).pop(event_id, None)
            await query.edit_message_text("Aksi dibatalkan.")
            
    except Exception as e:
        await query.edit_message_text(f"Gagal memproses aksi. Error: {str(e)}")

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pesan_tunggu = await update.message.reply_text("Sedang memproses jadwalmu...")
    await process_and_reply(update, update.message.text, pesan_tunggu, context)
    
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
        await process_and_reply(update, teks_ekstraksi, pesan_tunggu, context)
        
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
    app.add_handler(CallbackQueryHandler(handle_update_callback, pattern="^(confirm|cancel)_(update|delete):"))
    
    print("Bot Telegram sudah menyala. Tekan Ctrl+C untuk mematikan.")
    
    app.run_polling()