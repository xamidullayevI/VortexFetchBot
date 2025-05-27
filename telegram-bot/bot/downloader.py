import os
import logging
import asyncio
from typing import Tuple, Dict, Any, Optional
import yt_dlp
from pathlib import Path

logger = logging.getLogger(__name__)

class RailwayYoutubeLogger:
    """Railway muhiti uchun maxsus logger"""
    def debug(self, msg):
        if msg.startswith('[download]'):
            logger.info(msg)
        else:
            logger.debug(msg)

    def info(self, msg):
        logger.info(msg)

    def warning(self, msg):
        logger.warning(msg)

    def error(self, msg):
        logger.error(msg)

def get_download_options(download_path: str) -> Dict[str, Any]:
    """Youtube-dl parametrlarini sozlash"""
    return {
        'format': 'best[filesize<500M]/mp4',  # Railway uchun fayl hajmi cheklovi
        'outtmpl': os.path.join(download_path, '%(id)s.%(ext)s'),
        'quiet': True,
        'no_warnings': True,
        'logger': RailwayYoutubeLogger(),
        # Railway uchun xatoliklar bilan ishlash
        'retries': 3,
        'fragment_retries': 3,
        'skip_unavailable_fragments': True,
        'ignoreerrors': False,
        # Railway uchun tarmoq sozlamalari
        'socket_timeout': 30,
        'extractor_retries': 3,
        # Railway uchun resurs cheklovlari
        'noprogress': True,
        'max_filesize': 450 * 1024 * 1024,  # 450MB
        # Ko'p resurs talab qiladigan qo'shimcha ma'lumotlarni o'chirish
        'writeinfojson': False,
        'writedescription': False,
        'writethumbnail': False,
        # Video sifati
        'prefer_ffmpeg': True,
        'merge_output_format': 'mp4',
        # Railway uchun HTTP sozlamalari
        'http_chunk_size': 10485760,  # 10MB
        'buffersize': 1024,
        # Railway tarmog'i uchun
        'external_downloader_args': {
            'ffmpeg': ['-timeout', '30000000']  # 30 sekund timeout
        }
    }

def download_video_with_info(url: str, download_path: str) -> Tuple[Optional[str], Dict[str, Any]]:
    """
    Video yuklab olish va ma'lumotlarini qaytarish
    
    Args:
        url: Video havolasi
        download_path: Yuklab olish papkasi
        
    Returns:
        Tuple[str, dict]: Video fayl manzili va ma'lumotlar
    """
    try:
        with yt_dlp.YoutubeDL(get_download_options(download_path)) as ydl:
            try:
                # Video ma'lumotlarini olish
                info = ydl.extract_info(url, download=True)
                if not info:
                    logger.error(f"Video ma'lumotlarini olib bo'lmadi: {url}")
                    return None, {}

                # Fayl manzilini olish
                if 'entries' in info:
                    # Playlist bo'lsa birinchi videoni olish
                    info = info['entries'][0]

                filename = ydl.prepare_filename(info)
                if not os.path.exists(filename):
                    # Ba'zan kengaytma noto'g'ri bo'lishi mumkin
                    base, _ = os.path.splitext(filename)
                    for ext in ['mp4', 'webm', 'mkv']:
                        alt_filename = f"{base}.{ext}"
                        if os.path.exists(alt_filename):
                            filename = alt_filename
                            break

                file_size = os.path.getsize(filename)
                if file_size > 450 * 1024 * 1024:  # 450MB
                    logger.warning(f"Video hajmi juda katta: {file_size / (1024*1024):.1f}MB")
                    if os.path.exists(filename):
                        os.remove(filename)
                    return None, {}

                return filename, info

            except Exception as e:
                logger.error(f"Video yuklab olishda xatolik: {str(e)}")
                return None, {}

    except Exception as e:
        logger.error(f"YoutubeDL xatoligi: {str(e)}")
        return None, {}
