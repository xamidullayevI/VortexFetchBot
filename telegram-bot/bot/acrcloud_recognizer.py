import time
import hashlib
import hmac
import base64
import requests
import os
import subprocess

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


def recognize_audio_acrcloud(audio_file_path: str,
                             host: str,
                             access_key: str,
                             access_secret: str) -> dict:
    """
    ACRCloud API orqali audio fayldan original musiqani aniqlash.
    """
    http_method = "POST"
    http_uri = "/v1/identify"
    data_type = "audio"
    signature_version = "1"
    timestamp = str(int(time.time()))

    string_to_sign = "\n".join([http_method, http_uri, access_key, data_type, signature_version, timestamp])
    sign = base64.b64encode(
        hmac.new(access_secret.encode('utf-8'), string_to_sign.encode('utf-8'), digestmod=hashlib.sha1).digest()
    ).decode('utf-8')

    files = {'sample': open(audio_file_path, 'rb')}
    data = {
        'access_key': access_key,
        'data_type': data_type,
        'signature_version': signature_version,
        'signature': sign,
        'timestamp': timestamp,
    }
    url = f"https://{host}/v1/identify"
    response = requests.post(url, files=files, data=data, timeout=10)
    return response.json()


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
