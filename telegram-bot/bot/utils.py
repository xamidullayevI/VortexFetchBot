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
        # LOG: FastSaver javobini logga yozamiz
        print(f"[LOG] FastSaver API javobi: {data}")
        if response.status_code == 200 and data.get("success"):
            download_url = data.get("download_url")
            # Agar audio_url bor bo‘lsa, uni ham qaytaramiz
            audio_url = data.get("audio_url") or data.get("music_url")
            return download_url, audio_url
        else:
            return None, None
    except Exception as e:
        print(f"[LOG] FastSaver API xatolik: {e}")
        return None, None


# Fallback uchun yt-dlp funksiyasi (mavjud bo'lsa, chaqiriladi)
def download_with_ytdlp(url):
    # Bu funksiya sizda allaqachon bo'lishi mumkin, yoki downloader.py da bo'lishi mumkin
    # Agar yo'q bo'lsa, shu yerga qo'shish mumkin
    print("[LOG] yt-dlp orqali yuklash ishladi")
    return None, None  # yoki haqiqiy link va audio qaytarilsa shu yerga yozing

# Universal yuklab olish funksiyasi
def universal_download(url):
    download_url, audio_url = download_with_fastsaver(url)
    if download_url:
        print("[LOG] Video FastSaver API orqali yuklandi")
        return download_url, 'fastsaver', audio_url
    else:
        download_url, audio_url = download_with_ytdlp(url)
        print("[LOG] Video yt-dlp orqali yuklandi")
        return download_url, 'ytdlp', audio_url

def is_video_url(text: str) -> bool:
    url_regex = re.compile(r"https?://[\w./?=&%-]+", re.IGNORECASE)
    return bool(url_regex.search(text))
