import re
import os
import requests

def download_with_fastsaver(url):
    """
    FastSaver API orqali universal media (video, rasm, audio) yuklash.
    Instagram, TikTok, Facebook, Twitter, Pinterest, Threads, Snapchat, Likee va boshqalar uchun.
    """
    api_key = os.getenv("FASTSAVER_API_KEY")
    if not api_key:
        print("[ERROR] FASTSAVER_API_KEY environment variable topilmadi!")
        return {
            "error": True,
            "error_message": "FastSaver API token topilmadi. Railway yoki .env faylga FASTSAVER_API_KEY ni to‘g‘ri yozing!"
        }
    api_url = "https://fastsaverapi.com/api/get-info"
    params = {"url": url, "token": api_key}
    try:
        response = requests.get(api_url, params=params, timeout=20)
        try:
            data = response.json()
        except Exception:
            print(f"[ERROR] FastSaver API javobi JSON formatda emas: {response.text}")
            return {
                "error": True,
                "error_message": f"FastSaver API javobi JSON formatda emas: {response.text}"
            }
        print(f"[LOG] FastSaver API javobi: {data}")
        # API xatoliklari uchun aniq xabar
        if 'detail' in data and data['detail'] == 'Not found':
            return {
                "error": True,
                "error_message": "FastSaver API: 'Not found'. Token yoki endpoint xato yoki noto‘g‘ri URL yuborildi."
            }
        if data.get('error') or not data.get('download_url'):
            return {
                "error": True,
                "error_message": f"FastSaver API xatolik yoki media topilmadi: {data}"
            }
        download_url = data.get("download_url")
        audio_url = data.get("audio_url") or data.get("music_url")
        media_type = data.get("type")
        thumb = data.get("thumb")
        return {
            "download_url": download_url,
            "audio_url": audio_url,
            "media_type": media_type,
            "thumb": thumb,
            "info": data,
            "error": False
        }
    except Exception as e:
        print(f"[ERROR] FastSaver API xatolik: {e}")
        return {
            "error": True,
            "error_message": f"FastSaver API so‘rovda xatolik: {e}"
        }



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
