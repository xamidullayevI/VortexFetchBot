import os
import time
import hmac
import base64
import hashlib
import requests
from dotenv import load_dotenv

load_dotenv()

def extract_audio_from_video(video_path: str, audio_path: str = None) -> str:
    """
    Videodan audio (mp3) ajratib beradi. Agar audio_path berilmasa, avtomatik nom beradi.
    """
    if audio_path is None:
        audio_path = video_path + ".mp3"
    subprocess.run([
        'ffmpeg', '-y', '-i', video_path, '-vn', '-acodec', 'mp3', audio_path
    ], check=True)
    return audio_path


def get_music_info(audio_file):
    host = os.getenv("ACRCLOUD_HOST")
    access_key = os.getenv("ACRCLOUD_ACCESS_KEY")
    access_secret = os.getenv("ACRCLOUD_ACCESS_SECRET")

    http_method = "POST"
    http_uri = "/v1/identify"
    data_type = "audio"
    signature_version = "1"
    timestamp = time.time()

    string_to_sign = '\n'.join([
        http_method,
        http_uri,
        access_key,
        data_type,
        signature_version,
        str(timestamp)
    ])

    sign = base64.b64encode(
        hmac.new(access_secret.encode('ascii'), string_to_sign.encode('ascii'),
                 digestmod=hashlib.sha1).digest()
    ).decode('ascii')

    with open(audio_file, 'rb') as f:
        files = {'sample': f}
        data = {
            'access_key': access_key,
            'data_type': data_type,
            'signature_version': signature_version,
            'signature': sign,
            'timestamp': str(timestamp),
        }
        
        r = requests.post(f'https://{host}{http_uri}', files=files, data=data)
        r.raise_for_status()
        result = r.json()
        
        if 'status' in result and result['status']['code'] == 0:
            music_info = result['metadata']['music'][0]
            return {
                'title': music_info.get('title', 'Unknown'),
                'artist': music_info.get('artists', [{'name': 'Unknown'}])[0]['name'],
                'album': music_info.get('album', {}).get('name', 'Unknown'),
                'release_date': music_info.get('release_date', 'Unknown'),
                'external_metadata': music_info.get('external_metadata', {})
            }
    return None


def get_music_info_from_video(video_path: str) -> dict:
    """
    Videodan audio ajratib, ACRCloud orqali original musiqani aniqlaydi.
    """
    # Bu joyga o'zingizning project credential'laringizni joylashtiring:
    host = "identify-ap-southeast-1.acrcloud.com"
    access_key = "256a370f00f84d9f8d50829df46c2b7d"
    access_secret = "c2VuUy9vYkZyqvgays3FqQdJrLsQk2yAbIjkmE8"

    audio_path = extract_audio_from_video(video_path)
    result = recognize_audio_acrcloud(audio_path, host, access_key, access_secret)
    # Agar kerak bo'lsa, vaqtinchalik audio faylni o'chirib yuborish mumkin
    if os.path.exists(audio_path):
        os.remove(audio_path)
    return result
