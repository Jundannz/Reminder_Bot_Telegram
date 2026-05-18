import os
import json
from datetime import datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv

load_dotenv()

# scopes memberikan izin penuh untuk membaca dan menulis di google calendar
SCOPES = ['https://www.googleapis.com/auth/calendar']

def get_calendar_service():
    creds = None
    
    # baca string JSON dari .env
    token_json_str = os.getenv("GOOGLE_TOKEN_JSON")
    creds_json_str = os.getenv("GOOGLE_CREDS_JSON")
    
    # pakai token jika ada di env
    if token_json_str:
        try:
            token_info = json.loads(token_json_str)
            creds = Credentials.from_authorized_user_info(token_info, SCOPES)
        except json.JSONDecodeError:
            print("Error: GOOGLE_TOKEN_JSON tidak valid.")
        
    # jika tidak ada token valid, coba proses kredensial
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # fallback jika token tidak valid
            if not creds_json_str:
                raise Exception("Error: GOOGLE_CREDS_JSON tidak ditemukan di .env")
        
            client_config = json.loads(creds_json_str)
            flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
            creds = flow.run_local_server(port=0)
            
            # token baru dicetak di terminal agar bisa disalin ke .env jika diperlukan
            print("Token baru berhasil dibuat. Salin teks di bawah ini ke GOOGLE_TOKEN_JSON jika token lama rusak:")
            print(creds.to_json())
            
    return build('calendar', 'v3', credentials=creds)

def create_calendar_event(event_data: dict) -> str:
    try:
        service = get_calendar_service()
        
        # atur waktu selesai otomatis (tambah 1 jam jika tidak diberikan oleh llm)
        waktu_mulai = event_data['waktu']
        waktu_selesai = event_data.get('waktu_selesai')
        
        if not waktu_selesai:
            # skenario jika waktu_selesai bernilai null, parsing dan tambahkan 1 jam
            dt = datetime.fromisoformat(waktu_mulai)
            from datetime import timedelta
            waktu_selesai = (dt + timedelta(hours=1)).isoformat()
        
        # konstruksi body event sesuai spesifikasi g oogle calendar API
        event_body = {
            'summary': event_data['nama_acara'],
            'location': event_data.get('lokasi', ''),
            'description': event_data.get('deskripsi', ''),
            'start': {
                'dateTime': waktu_mulai,
                'timeZone': 'Asia/Jakarta',
            },
            'end': {
                'dateTime': waktu_selesai,
                'timeZone': 'Asia/Jakarta',
            },
        }
        
        #eksekusi insert event ke calendar utama
        event = service.events().insert(calendarId='primary', body=event_body).execute()
        return event.get('htmlLink')
        
    except HttpError as error:
        raise Exception(f"Terjadi error saat membuat event di Google Calendar: {error}")

def search_calendar_events(query: str, max_results: int = 5) -> list:
    service = get_calendar_service()
    now = datetime.utcnow().isoformat() + 'Z'
    
    result = service.events().list(
        calendarId='primary',
        q=query,
        timeMin=now,
        maxResults=max_results,
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    
    return result.get('items', [])

def update_calendar_event(event_id: str, event_data: dict) -> str:
    service = get_calendar_service()
    
    waktu_mulai = event_data['waktu']
    waktu_selesai = event_data.get('waktu_selesai')
    
    if not waktu_selesai:
        from datetime import timedelta
        dt = datetime.fromisoformat(waktu_mulai)
        waktu_selesai = (dt + timedelta(hours=1)).isoformat()
    
    patch_body = {
        'summary': event_data['nama_acara'],
        'location': event_data.get('lokasi', ''),
        'description': event_data.get('deskripsi', ''),
        'start': {'dateTime': waktu_mulai, 'timeZone': 'Asia/Jakarta'},
        'end': {'dateTime': waktu_selesai, 'timeZone': 'Asia/Jakarta'},
    }
    
    event = service.events().patch(
        calendarId='primary',
        eventId=event_id,
        body=patch_body
    ).execute()
    
    return event.get('htmlLink')

def delete_calendar_event(event_id: str):
    service = get_calendar_service()
    service.events().delete(
        calendarId='primary',
        eventId=event_id
    ).execute()

#uji coba
if __name__ == "__main__":
    data_uji = {
        "nama_acara": "Rapat Pengurus Harian",
        "waktu": "2026-05-18T19:00:00+07:00",
        "waktu_selesai": None,
        "lokasi": "Ruang Pertemuan Rektorat",
        "deskripsi": "Membahas persiapan teknis acara utama"
    }
    
    print("Menjalankan uji coba integrasi Google Calendar...")
    print("Browser akan otomatis terbuka untuk meminta izin akses Google Account.")
    
    link_kalender = create_calendar_event(data_uji)
    print(f"Sukses! Event berhasil dibuat. Link akses: {link_kalender}")