import re
import os
import logging
import asyncio
from typing import Optional, Any, Dict
from pathlib import Path
from functools import wraps
from datetime import datetime

from bot.downloader import download_video_with_info, DownloadError

logger = logging.getLogger(__name__)

def ensure_downloads_dir() -> Path:
    """Downloads papkasini tekshirish va yaratish"""
    downloads_dir = Path("downloads")
    downloads_dir.mkdir(exist_ok=True)
    return downloads_dir

def cleanup_file(file_path: str) -> None:
    """Faylni xavfsiz o'chirish"""
    try:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        logger.error(f"Faylni o'chirishda xatolik: {e}")

def generate_temp_filename(prefix: str = "", suffix: str = "") -> str:
    """Vaqtinchalik fayl nomi yaratish"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    random_str = os.urandom(4).hex()
    return f"{prefix}_{timestamp}_{random_str}{suffix}"

def format_size(size_bytes: int) -> str:
    """Fayl hajmini insoniy formatda qaytarish"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} GB"

def format_duration(seconds: float) -> str:
    """Video davomiyligini formatlash"""
    minutes, seconds = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    if hours > 0:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"

def async_error_handler(func):
    """Asinxron funksiyalar uchun xatoliklarni qayta ishlash dekorator"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Xatolik {func.__name__}: {str(e)}", exc_info=True)
            return None
    return wrapper

def safe_get(obj: Dict[str, Any], *keys: str, default: Any = None) -> Any:
    """Dictionary'dan xavfsiz qiymat olish"""
    try:
        for key in keys:
            obj = obj[key]
        return obj
    except (KeyError, TypeError, IndexError):
        return default

def is_video_url(text: str) -> bool:
    url_regex = re.compile(r"https?://[\w./?=&%-]+", re.IGNORECASE)
    return bool(url_regex.search(text))

# Yangi universal_download: faqat yt-dlp asosida
def universal_download(url, download_dir="downloads"):
    try:
        result = download_video_with_info(url, download_dir)
        if not isinstance(result, tuple) or len(result) != 2:
            print(f"[ERROR] download_video_with_info returned unexpected value: {result}")
            return {
                "error": True,
                "error_message": "download_video_with_info noto'g'ri qiymat qaytardi (2 ta qiymat kutildi)",
                "raw_result": result
            }
        video_path, info = result
        audio_url = None
        # Agar info dictda audio link bo‘lsa, uni ham qaytar
        if info and 'requested_formats' in info:
            for fmt in info['requested_formats']:
                if fmt.get('acodec') != 'none' and fmt.get('url'):
                    audio_url = fmt['url']
                    break
        return {
            "download_url": video_path,
            "audio_url": audio_url,
            "media_type": info.get('ext') if info else None,
            "thumb": info.get('thumbnail') if info else None,
            "info": info,
            "method": "ytdlp",
            "error": False
        }
    except DownloadError as e:
        print(f"[ERROR] yt-dlp xatolik: {e}")
        return {
            "error": True,
            "error_message": f"yt-dlp xatolik yoki media topilmadi: {e}"
        }
