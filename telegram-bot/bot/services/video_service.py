import os
import uuid
import logging
import psutil
import asyncio
from typing import Dict, Any, Optional
from pathlib import Path
from telegram import Bot, InlineKeyboardMarkup

from ..downloader import download_video_with_info, DownloadError
from ..video_compress import compress_video
from ..services.monitoring import metrics
from ..config.config import config
from ..utils import ensure_downloads_dir, cleanup_file, generate_temp_filename

logger = logging.getLogger(__name__)

class VideoService:
    def __init__(self, downloads_dir: str = None):
        self.downloads_dir = Path(downloads_dir or config.downloads_dir)
        self.processing_tasks: Dict[str, asyncio.Task] = {}
        self.lock = asyncio.Lock()
        ensure_downloads_dir()

    async def download_and_process_video(self, url: str) -> Dict[str, Any]:
        """Video yuklab olish va qayta ishlash"""
        async with self.lock:  # Bir vaqtda faqat bitta yuklab olish
            try:
                # Xotira tekshiruvi
                if not await self._check_memory():
                    return {
                        'success': False,
                        'error': "❌ Serverda xotira yetarli emas. Iltimos, keyinroq urinib ko'ring."
                    }

                # Disk joy tekshiruvi
                if not await self._check_disk_space():
                    return {
                        'success': False,
                        'error': "❌ Serverda bo'sh joy yetarli emas. Iltimos, keyinroq urinib ko'ring."
                    }

                # Unique ID yaratish
                task_id = uuid.uuid4().hex
                
                try:
                    # Video yuklab olish
                    video_path, info = await download_video_with_info(url, str(self.downloads_dir))
                    if not video_path or not os.path.exists(video_path):
                        return {
                            'success': False,
                            'error': "❌ Video yuklab olinmadi"
                        }

                    file_size = os.path.getsize(video_path)
                    
                    # Railway xotira cheklovini tekshirish
                    if file_size > config.max_video_size_mb * 1024 * 1024:
                        cleanup_file(video_path)
                        return {
                            'success': False,
                            'error': f"❌ Video hajmi juda katta ({config.max_video_size_mb}MB dan oshmasligi kerak)"
                        }

                    # Video ma'lumotlarini olish
                    title = info.get('title', 'Video')
                    uploader = info.get('uploader', 'Unknown')
                    duration = info.get('duration', 0)

                    # Video siqish kerak bo'lsa
                    if file_size > config.target_video_size_mb * 1024 * 1024:
                        compressed_path = generate_temp_filename(prefix="compressed_", suffix=".mp4")
                        compressed_result = await compress_video(
                            video_path,
                            compressed_path,
                            target_size_mb=config.target_video_size_mb
                        )
                        
                        if compressed_result:
                            cleanup_file(video_path)
                            video_path = compressed_result
                            file_size = os.path.getsize(video_path)

                    metrics.track_successful_download(url)

                    # Natijani qaytarish
                    return {
                        'success': True,
                        'video_path': video_path,
                        'file_size': file_size,
                        'title': title,
                        'uploader': uploader,
                        'duration': duration,
                        'task_id': task_id,
                        'info': info
                    }

                except DownloadError as e:
                    logger.error(f"Video yuklab olishda xatolik: {e}")
                    metrics.track_error("DownloadError")
                    return {
                        'success': False,
                        'error': str(e)
                    }

            except Exception as e:
                logger.error(f"Video qayta ishlashda xatolik: {e}")
                metrics.track_error(type(e).__name__)
                return {
                    'success': False,
                    'error': f"❌ Xatolik yuz berdi: {str(e)}"
                }

    async def _check_memory(self) -> bool:
        """Xotira yetarliligini tekshirish"""
        try:
            memory = psutil.virtual_memory()
            return memory.percent < config.max_memory_percent
        except Exception as e:
            logger.error(f"Xotirani tekshirishda xatolik: {e}")
            metrics.track_error(type(e).__name__)
            return False

    async def _check_disk_space(self) -> bool:
        """Railway xotirasini tekshirish"""
        try:
            disk_usage = psutil.disk_usage(self.downloads_dir)
            return disk_usage.percent < config.max_disk_percent
        except Exception as e:
            logger.error(f"Disk xotirasini tekshirishda xatolik: {e}")
            metrics.track_error(type(e).__name__)
            return False

    async def cancel_processing(self, task_id: str):
        """Videoni qayta ishlashni bekor qilish"""
        if task_id in self.processing_tasks:
            task = self.processing_tasks[task_id]
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            del self.processing_tasks[task_id]

    async def cleanup(self):
        """Barcha ishlov berish vazifalarini tozalash"""
        async with self.lock:
            for task_id in list(self.processing_tasks.keys()):
                await self.cancel_processing(task_id)

    @staticmethod
    def cleanup_files(*file_paths: str) -> None:
        """Vaqtinchalik fayllarni tozalash"""
        for file_path in file_paths:
            cleanup_file(file_path)

    async def compress_and_send_video(
        self,
        video_path: str,
        chat_id: int,
        bot: Bot,
        caption: str,
        reply_markup: Optional[InlineKeyboardMarkup] = None
    ) -> bool:
        """Compress video and send it to chat"""
        try:
            # Generate path for compressed video
            compressed_path = generate_temp_filename(prefix="compressed_", suffix=".mp4")
            
            # Try compressing the video
            compressed_result = await compress_video(
                video_path,
                compressed_path,
                target_size_mb=config.target_video_size_mb,
                max_height=config.max_video_height
            )
            
            if not compressed_result or not os.path.exists(compressed_result):
                logger.error("Video compression failed")
                return False

            # Send compressed video
            try:
                with open(compressed_result, 'rb') as video_file:
                    await bot.send_video(
                        chat_id=chat_id,
                        video=video_file,
                        caption=caption,
                        reply_markup=reply_markup,
                        supports_streaming=True
                    )
                return True
                
            except Exception as e:
                logger.error(f"Error sending compressed video: {e}")
                return False
                
            finally:
                # Clean up compressed video
                cleanup_file(compressed_result)
                
        except Exception as e:
            logger.error(f"Error in compress_and_send_video: {e}")
            metrics.track_error(type(e).__name__)
            return False