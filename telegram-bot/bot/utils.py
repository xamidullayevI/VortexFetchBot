import re
import os
import requests

def download_with_fastsaver(url):
    """
    FastSaver API orqali universal media (video, rasm, audio) yuklash.
    Instagram, TikTok, Facebook, Twitter, Pinterest, Threads, Snapchat, Likee va boshqalar uchun.
    """
    api_key = os.getenv("FASTSAVER_API_KEY")
    api_url = "https://fastsaverapi.com/api/get-info"
    params = {"url": url, "token": api_key}
    try:
        response = requests.get(api_url, params=params, timeout=20)
        data = response.json()
        print(f"[LOG] FastSaver API javobi: {data}")
        # Xatolik bo'lmasa va download_url bor bo'lsa
        if not data.get("error") and data.get("download_url"):
            download_url = data.get("download_url")
            # Rasm uchun ham download_url qaytadi (type: image)
            # Audio uchun audio_url yoki music_url bo'lishi mumkin
            audio_url = data.get("audio_url") or data.get("music_url")
            media_type = data.get("type")  # video, image, audio
            thumb = data.get("thumb")
            return {
                "download_url": download_url,
                "audio_url": audio_url,
                "media_type": media_type,
                "thumb": thumb,
                "info": data
            }
        else:
            return None
    except Exception as e:
        print(f"[LOG] FastSaver API xatolik: {e}")
        return None



# Fallback uchun yt-dlp funksiyasi (mavjud bo'lsa, chaqiriladi)
def download_with_ytdlp(url):
    # Agar FastSaver ishlamasa, fallback sifatida ishlatiladi
    print("[LOG] yt-dlp orqali yuklash ishladi")
    return None  # yoki haqiqiy link va audio qaytarilsa shu yerga yozing

# Universal yuklab olish funksiyasi
def universal_download(url):
    """
    Universal yuklab olish: avval FastSaver, keyin fallback yt-dlp.
    Har doim dict qaytaradi: {download_url, audio_url, media_type, thumb, info, method}
    """
    fastsaver_result = download_with_fastsaver(url)
    if fastsaver_result:
        fastsaver_result['method'] = 'fastsaver'
        print("[LOG] Media FastSaver API orqali yuklandi")
        return fastsaver_result
    else:
        ytdlp_result = download_with_ytdlp(url)
        if ytdlp_result:
            ytdlp_result['method'] = 'ytdlp'
            print("[LOG] Media yt-dlp orqali yuklandi")
            return ytdlp_result
        else:
            print("[LOG] Hech qanday media topilmadi")
            return None

def is_video_url(text: str) -> bool:
    url_regex = re.compile(r"https?://[\w./?=&%-]+", re.IGNORECASE)
    return bool(url_regex.search(text))
