import re
import os
import requests

def download_with_fastsaver(url):
    api_key = os.getenv("FASTSAVER_API_KEY")
    api_url = "https://fastsaverapi.com/api/download"
    params = {"url": url, "apikey": api_key}
    try:
        response = requests.get(api_url, params=params, timeout=20)
        data = response.json()
        if response.status_code == 200 and data.get("success"):
            return data["download_url"]
        else:
            return None
    except Exception as e:
        return None

# Fallback uchun yt-dlp funksiyasi (mavjud bo'lsa, chaqiriladi)
def download_with_ytdlp(url):
    # Bu funksiya sizda allaqachon bo'lishi mumkin, yoki downloader.py da bo'lishi mumkin
    # Agar yo'q bo'lsa, shu yerga qo'shish mumkin
    pass

# Universal yuklab olish funksiyasi
def universal_download(url):
    result = download_with_fastsaver(url)
    if result:
        return result, 'fastsaver'
    else:
        result = download_with_ytdlp(url)
        return result, 'ytdlp'

def is_video_url(text: str) -> bool:
    url_regex = re.compile(r"https?://[\w./?=&%-]+", re.IGNORECASE)
    return bool(url_regex.search(text))
