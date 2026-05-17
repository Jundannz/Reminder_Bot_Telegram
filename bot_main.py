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