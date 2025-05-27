import os
import uuid
import logging
import psutil
from typing import Dict, Any, Optional
from pathlib import Path

from ..downloader import download_video_with_info, DownloadError
from ..video_compress import compress_video
from ..utils import (
    ensure_downloads_dir,
    cleanup_file,
    format_size,
    format_duration,
    generate_temp_filename
)

logger = logging.getLogger(__name__)

class VideoService:
    MAX_TELEGRAM_SIZE = 49 * 1024 * 1024  # 49MB
    COMPRESS_TARGET_SIZE = 45 * 1024 * 1024  # 45MB
    RAILWAY_MAX_SIZE = 450 * 1024 * 1024  # 450MB - Railway disk limit
    MEMORY_THRESHOLD = 80  # 80% memory usage threshold

    def __init__(self):
        self.downloads_dir = ensure_downloads_dir()

    async def download_and_process_video(self, url: str) -> Dict[str, Any]:
        """Video yuklab olish va qayta ishlash"""
        try:
            # Xotira tekshiruvi
            if not self._check_memory():
                return {
                    'success': False,
                    'error': "❌ Serverda xotira yetarli emas. Iltimos, keyinroq urinib ko'ring."
                }

            # Disk joy tekshiruvi
            if not self._check_disk_space():
                return {
                    'success': False,
                    'error': "❌ Serverda bo'sh joy yetarli emas. Iltimos, keyinroq urinib ko'ring."
                }

            # Unique ID yaratish
            unique_id = uuid.uuid4().hex
            
            try:
                # Video yuklab olish
                video_path, info = download_video_with_info(url, str(self.downloads_dir))
                if not video_path or not os.path.exists(video_path):
                    return {
                        'success': False,
                        'error': "❌ Video yuklab olinmadi"
                    }

                file_size = os.path.getsize(video_path)
                
                # Railway xotira cheklovini tekshirish
                if file_size > self.RAILWAY_MAX_SIZE:
                    cleanup_file(video_path)
                    return {
                        'success': False,
                        'error': "❌ Video hajmi juda katta (450MB dan oshmasligi kerak)"
                    }

                # Video ma'lumotlarini olish
                duration = info.get('duration', 0)
                title = info.get('title', 'Video')
                uploader = info.get('uploader', 'Unknown')

                # Caption tayyorlash
                caption = (
                    f"📹 *{title}*\n"
                    f"👤 *Kanal:* {uploader}\n"
                    f"⏱ *Davomiyligi:* {format_duration(duration)}\n"
                    f"📦 *Hajmi:* {format_size(file_size)}"
                )

                # Agar video hajmi katta bo'lsa yoki xotira tanqis bo'lsa, siqish
                if file_size > self.COMPRESS_TARGET_SIZE or self._is_memory_critical():
                    needs_compression = True
                else:
                    needs_compression = file_size > self.MAX_TELEGRAM_SIZE

                # Video siqish kerak bo'lsa
                if needs_compression:
                    compressed_path = generate_temp_filename(prefix="compressed_", suffix=".mp4")
                    target_size = min(45, max(20, self._get_optimal_target_size()))
                    
                    compressed_result = compress_video(
                        video_path,
                        compressed_path,
                        target_size_mb=target_size
                    )
                    
                    if compressed_result:
                        cleanup_file(video_path)
                        video_path = compressed_result

                # Natijani qaytarish
                return {
                    'success': True,
                    'video_path': video_path,
                    'caption': caption,
                    'unique_id': unique_id,
                    'audio_url': info.get('url'),
                    'info': info
                }

            except DownloadError as e:
                logger.error(f"Video yuklab olishda xatolik: {e}")
                return {
                    'success': False,
                    'error': str(e)
                }

        except Exception as e:
            logger.error(f"Video qayta ishlashda xatolik: {e}")
            return {
                'success': False,
                'error': f"❌ Xatolik yuz berdi: {str(e)}"
            }

    def _check_memory(self) -> bool:
        """Xotira yetarliligini tekshirish"""
        try:
            memory = psutil.virtual_memory()
            return memory.percent < self.MEMORY_THRESHOLD
        except Exception as e:
            logger.error(f"Xotirani tekshirishda xatolik: {e}")
            return True

    def _is_memory_critical(self) -> bool:
        """Xotira holati kritik ekanligini tekshirish"""
        try:
            memory = psutil.virtual_memory()
            return memory.percent > 90
        except Exception:
            return False

    def _get_optimal_target_size(self) -> int:
        """Optimal siqish hajmini hisoblash"""
        try:
            memory = psutil.virtual_memory()
            # Xotira bandligi qancha yuqori bo'lsa, shuncha ko'p siqish
            if memory.percent > 85:
                return 20  # 20MB gacha siqish
            elif memory.percent > 75:
                return 30  # 30MB gacha siqish
            else:
                return 45  # 45MB gacha siqish
        except Exception:
            return 45  # Xatolik bo'lsa default qiymat

    def _check_disk_space(self) -> bool:
        """Railway xotirasini tekshirish"""
        try:
            total_size = 0
            for path in Path(self.downloads_dir).glob('**/*'):
                if path.is_file():
                    total_size += path.stat().st_size
            
            return total_size < (self.RAILWAY_MAX_SIZE * 0.9)  # 90% dan kam bo'lishi kerak
        except Exception as e:
            logger.error(f"Xotirani tekshirishda xatolik: {e}")
            return False

    @staticmethod
    def cleanup_files(*file_paths: str) -> None:
        """Vaqtinchalik fayllarni tozalash"""
        for file_path in file_paths:
            cleanup_file(file_path)