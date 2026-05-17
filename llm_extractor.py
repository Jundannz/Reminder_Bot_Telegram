import os
import json
from datetime import datetime
from google import genai
from google.genai import types # Dibutuhkan untuk memanggil GenerateContentConfig
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load env
load_dotenv()

# Client baru sesuai standar SDK terbaru
client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

# 1. Pastikan skema memiliki deskripsi yang jelas untuk memandu model
class EventDetails(BaseModel):
    nama_acara: str = Field(description="Nama atau judul agenda acara")
    waktu: str = Field(description="Waktu mulai acara dalam format ISO 8601 (contoh: 2026-05-20T19:00:00+07:00)")
    waktu_selesai: str | None = Field(default=None, description="Waktu selesai acara format ISO 8601, berikan null jika tidak ada informasi jelas")
    lokasi: str | None = Field(default=None, description="Tempat atau ruangan acara, berikan null jika tidak disebutkan")
    deskripsi: str = Field(description="Ringkasan singkat, catatan, atau instruksi tambahan dari teks")

def extract_event_info(raw_text: str):
    # Dapatkan waktu saat ini sebagai jangkar referensi tanggal relatif
    current_time = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    system_instruction = f"""
    Kamu adalah asisten ekstraksi jadwal profesional.
    Waktu server saat ini adalah: {current_time} (Gunakan ini untuk menghitung kata ganti waktu seperti 'besok', 'lusa', atau 'jam 7 malam').
    Tugasmu adalah mengekstrak entitas dari teks user ke dalam skema JSON yang ditentukan. Jangan berikan teks prolog atau epilog.
    """

    # 2. pemanggilan yang benar menggunakan konfigurasi objek terstruktur
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=raw_text,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type="application/json",
            response_schema=EventDetails,
            temperature=0.1
        )
    )

    return json.loads(response.text)

# Testing
if __name__ == "__main__":
    teks_ujian = "Besok jam 7 malam ada rapat himpunan di ruang A201"
    print(f"Mengonstruksi teks: '{teks_ujian}'")
    
    hasil = extract_event_info(teks_ujian)
    print(json.dumps(hasil, indent=2, ensure_ascii=False))