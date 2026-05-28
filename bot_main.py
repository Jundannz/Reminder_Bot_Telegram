import os
import json
import PyPDF2
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from llm_extractor import extract_event_info
from calendar_service import create_calendar_event, search_calendar_events, update_calendar_event, delete_calendar_event, create_google_task, search_google_tasks, update_google_task, delete_google_task
from fastapi import FastAPI, Request, Response
from contextlib import asynccontextmanager
import uvicorn

load_dotenv()

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pesan_pembuka = (
        "Halo! Kirim teks jadwal atau undangan apa saja di sini. "
        "Aku akan otomatis mencatatnya ke Google Calendar milikmu."
    )
    await update.message.reply_text(pesan_pembuka)
    
async def process_and_reply(update: Update, text_content: str, status_message, context: ContextTypes.DEFAULT_TYPE, image_path: str = None):
    try:
        events = extract_event_info(text_content, image_path)
        
        create_events = [e for e in events if e['intent'] == 'create']
        update_events = [e for e in events if e['intent'] == 'update']
        delete_events = [e for e in events if e['intent'] == 'delete']
        task_events = [e for e in events if e['intent'] == 'create_task']
        update_task_events = [e for e in events if e['intent'] == 'update_task']
        delete_task_events = [e for e in events if e['intent'] == 'delete_task']

        # 1. Proses Create Event & Task
        teks_balasan_create = ""
        
        # Eksekusi Event Kalender
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
            
        # Eksekusi Task/Deadline
        for task_data in task_events:
            create_google_task(task_data)
            tanggal_deadline = task_data['waktu'].split('T')[0]
            teks_balasan_create += (
                f"<b>Tugas Baru</b>\n"
                f"Nama: {task_data['nama_acara']}\n"
                f"Deadline: {tanggal_deadline}\n"
                f"Deskripsi: {task_data['deskripsi']}\n\n"
            )
            
        if teks_balasan_create:
            await status_message.edit_text(teks_balasan_create, parse_mode='HTML', disable_web_page_preview=True)
        else:
            await status_message.edit_text("Memeriksa jadwal yang perlu diperbarui/dihapus...")

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
            
        # 4. Proses Update & Delete Task
        if (update_task_events or delete_task_events) and 'pending_updates' not in context.user_data:
            context.user_data['pending_updates'] = {}

        for task_data in update_task_events:
            query = task_data.get('referensi_lama') or task_data['nama_acara']
            kandidat = search_google_tasks(query)
            
            if not kandidat:
                await update.message.reply_text(f"Tidak ditemukan tugas lama untuk direvisi: <b>{query}</b>", parse_mode='HTML')
                continue
            
            target = kandidat[0]
            context.user_data['pending_updates'][target['id']] = task_data
            
            keyboard = InlineKeyboardMarkup([[ 
                InlineKeyboardButton("Ya, ubah deadline", callback_data=f"confirm_update_task:{target['id']}"),
                InlineKeyboardButton("Batal", callback_data=f"cancel_update_task:{target['id']}")
            ]])
            
            pesan_konfirmasi = (
                f"Ditemukan tugas: <b>{target['title']}</b>\n"
                f"Deadline lama: {target.get('due', 'N/A').split('T')[0]}\n\n"
                f"Akan diubah menjadi:\n"
                f"Judul: {task_data['nama_acara']}\n"
                f"Deadline baru: {task_data['waktu'].split('T')[0]}\n\n"
                f"Lanjutkan?"
            )
            await update.message.reply_text(pesan_konfirmasi, parse_mode='HTML', reply_markup=keyboard)

        for task_data in delete_task_events:
            query = task_data.get('referensi_lama') or task_data['nama_acara']
            kandidat = search_google_tasks(query)
            
            if not kandidat:
                await update.message.reply_text(f"Tidak ditemukan tugas untuk dihapus: <b>{query}</b>", parse_mode='HTML')
                continue
            
            target = kandidat[0]
            context.user_data['pending_updates'][target['id']] = task_data
            
            keyboard = InlineKeyboardMarkup([[ 
                InlineKeyboardButton("Ya, Hapus Tugas", callback_data=f"confirm_delete_task:{target['id']}"),
                InlineKeyboardButton("Batal", callback_data=f"cancel_delete_task:{target['id']}")
            ]])
            
            pesan_konfirmasi = (
                f"<b>KONFIRMASI HAPUS TUGAS</b>\n\n"
                f"Ditemukan tugas: <b>{target['title']}</b>\n\n"
                f"Apakah kamu yakin ingin menghapus tugas ini?"
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
            await query.edit_message_text(f"<b>Jadwal diperbarui!</b>\nLink: {link}", parse_mode='HTML')
            del context.user_data['pending_updates'][event_id]

        elif action == "confirm_delete":
            delete_calendar_event(event_id)
            await query.edit_message_text(f"Acara <b>{event_data['nama_acara']}</b> dihapus.", parse_mode='HTML')
            del context.user_data['pending_updates'][event_id]
            
        elif action == "confirm_update_task":
            update_google_task(event_id, event_data)
            await query.edit_message_text(f"<b>Tugas diperbarui!</b>\nDeadline baru: {event_data['waktu'].split('T')[0]}", parse_mode='HTML')
            del context.user_data['pending_updates'][event_id]

        elif action == "confirm_delete_task":
            delete_google_task(event_id)
            await query.edit_message_text(f"Tugas <b>{event_data['nama_acara']}</b> dihapus.", parse_mode='HTML')
            del context.user_data['pending_updates'][event_id]
            
        elif action.startswith("cancel_"):
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

async def handle_photo_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ambil elemen terakhir [-1] untuk mendapatkan resolusi tertinggi dari Telegram
    photo_file = await update.message.photo[-1].get_file()
    nama_file_temp = f"temp_{photo_file.file_id}.jpg"
    await photo_file.download_to_drive(nama_file_temp)
    
    # ambil caption foto jika ada, jika kosong berikan instruksi asali
    caption = update.message.caption or "Tolong ekstrak jadwal dari gambar ini."
    pesan_tunggu = await update.message.reply_text("Sedang membaca jadwal dari gambar...")
    
    try:
        await process_and_reply(update, caption, pesan_tunggu, context, image_path=nama_file_temp)
    finally:
        # gunakan blok finally agar file foto dihapus dari peladen entah prosesnya berhasil atau gagal
        if os.path.exists(nama_file_temp):
            os.remove(nama_file_temp)

token = os.getenv("TELEGRAM_BOT_TOKEN")
if not token:
    raise ValueError("Error: TELEGRAM_BOT_TOKEN tidak ditemukan di environment")

# Inisialisasi PTB Application secara global
ptb_app = ApplicationBuilder().token(token).build()

# Daftarkan semua handler
ptb_app.add_handler(CommandHandler("start", start_command))
ptb_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
ptb_app.add_handler(MessageHandler(filters.Document.PDF, handle_pdf_document))
ptb_app.add_handler(MessageHandler(filters.PHOTO, handle_photo_message))
ptb_app.add_handler(CallbackQueryHandler(handle_update_callback, pattern="^(confirm|cancel)_(update|delete|update_task|delete_task):"))

# Webhook URL (Nanti diisi dengan domain yang diberikan oleh Koyeb/Render)
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")

@asynccontextmanager
async def lifespan(_: FastAPI):
    # Dijalankan saat server FastAPI menyala
    if WEBHOOK_URL:
        await ptb_app.bot.set_webhook(url=WEBHOOK_URL)
        print(f"Webhook berhasil diatur ke: {WEBHOOK_URL}")
    else:
        print("Peringatan: WEBHOOK_URL belum diatur. Bot mungkin tidak akan menerima pesan.")
        
    async with ptb_app:
        await ptb_app.start()
        yield # Server berjalan di titik ini
        await ptb_app.stop()

# Inisialisasi FastAPI
app = FastAPI(lifespan=lifespan)

@app.post("/webhook")
async def process_webhook(request: Request):
    # Endpoint ini adalah pintu masuk pesan dari server Telegram
    try:
        req_json = await request.json()
        update = Update.de_json(req_json, ptb_app.bot)
        await ptb_app.process_update(update)
        return Response(status_code=200)
    except Exception as e:
        print(f"Error memproses webhook: {e}")
        return Response(status_code=500)

@app.get("/")
async def health_check():
    # Endpoint root biarkan hanya untuk cek status server (Health Check)
    return {"status": "ok", "message": "Telegram Calendar Bot is running via Webhook"}

if __name__ == "__main__":
    # Konfigurasi port dinamis sesuai platform cloud (default 8000 untuk lokal)
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("bot_main:app", host="0.0.0.0", port=port)