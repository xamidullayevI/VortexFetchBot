import re
import os



def is_video_url(text: str) -> bool:
    url_regex = re.compile(r"https?://[\w./?=&%-]+", re.IGNORECASE)
    return bool(url_regex.search(text))

# Yangi universal_download: faqat yt-dlp asosida
from bot.downloader import download_video_with_info, DownloadError

def universal_download(url, download_dir="downloads"):
    try:
        video_path, info = download_video_with_info(url, download_dir)
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
