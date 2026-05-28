import os
import json
from datetime import datetime
from PIL import Image
from google import genai
from google.genai import types # Dibutuhkan untuk memanggil GenerateContentConfig
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from typing import List, Literal

# Load env
load_dotenv()

# Client baru sesuai standar SDK terbaru
client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

# 1. Pastikan skema memiliki deskripsi yang jelas untuk memandu model
class EventDetails(BaseModel):
    intent: Literal["create", "update", "delete", "create_task", "update_task", "delete_task"] = Field(
        description="'create' untuk jadwal biasa, 'update' untuk revisi, 'delete' untuk batal, 'create_task'/'update_task'/'delete_task' untuk tugas, PR, freelance, atau deadline pekerjaan."
    )
    nama_acara: str = Field(description="Nama acara atau nama tugas/deadline")
    referensi_lama: str | None = Field(
        default=None,
        description="Hanya intisari nama acara lama yang dirujuk. JANGAN masukkan keterangan waktu seperti 'besok' atau 'jam'. Contoh: 'kumpul editing PIONIR'"
    )
    waktu: str = Field(description="Waktu mulai atau tenggat waktu dalam format ISO 8601")
    waktu_selesai: str | None = Field(default=None, description="Waktu selesai, null jika tidak disebutkan atau jika intent adalah create_task")
    lokasi: str | None = Field(default=None, description="Lokasi, null jika tidak disebutkan")
    deskripsi: str = Field(description="Ringkasan tugas atau deskripsi detail acara")

class EventList(BaseModel):
    events: List[EventDetails] = Field(description="Daftar semua agenda yang ditemukan dalam teks. Jika hanya ada satu agenda, tetap kembalikan sebagai list berisi satu item.")

def extract_event_info(raw_text: str, image_path: str = None):
    # Dapatkan waktu saat ini sebagai jangkar referensi tanggal relatif
    current_time = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    system_instruction = f"""
    Kamu adalah asisten ekstraksi jadwal profesional.
    Waktu server saat ini adalah: {current_time} (Gunakan ini untuk menghitung kata ganti waktu seperti 'besok', 'lusa', atau 'jam 7 malam').
    Tugasmu adalah mengekstrak entitas dari teks user ke dalam skema JSON yang ditentukan. Jangan berikan teks prolog atau epilog.
    """

    # Siapkan list konten. Jika ada gambar, sisipkan di urutan pertama.
    contents_list = [raw_text]
    if image_path:
        img = Image.open(image_path)
        contents_list.insert(0, img)

    # 2. pemanggilan yang benar menggunakan konfigurasi objek terstruktur
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=contents_list,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type="application/json",
            response_schema=EventList,
            temperature=0.1
        )
    )

    return json.loads(response.text)["events"]

# Testing
if __name__ == "__main__":
    teks_ujian = "Besok jam 7 malam ada rapat himpunan di ruang A201"
    print(f"Mengonstruksi teks: '{teks_ujian}'")
    
    hasil = extract_event_info(teks_ujian)
    print(json.dumps(hasil, indent=2, ensure_ascii=False))