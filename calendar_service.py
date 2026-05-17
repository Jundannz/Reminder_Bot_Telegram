import os
from datetime import datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# scopes memberikan izin penuh untuk membaca dan menulis di google calendar
SCOPES = ['https://www.googleapis.com/auth/calendar']

def get_calendar_service():
    creds = None
    # file token.json menyimpan token akses dan dibuat otomatis saat proses autentikasi pertama kali
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        
        # simpan token untuk penggunaan selanjutnya
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    
    return build('calendar', 'v3', credentials=creds)

def create_calendar_event(event_data: dict) -> str:
    """
    Fungsi untuk memasukkan event baru ke Google Calendar berdasarkan dictionary JSON.
    Returns: URL link ke event kalender yang berhasil dibuat.
    """
    
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