import os
import logging
import psutil
import asyncio
from typing import Optional, Dict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class RailwayService:
    MEMORY_THRESHOLD = 85  # 85% memory usage threshold
    DISK_THRESHOLD = 85    # 85% disk usage threshold
    CLEANUP_INTERVAL = 300  # 5 minutes

    def __init__(self, downloads_dir: str = "downloads"):
        self.downloads_dir = downloads_dir
        self.running = False
        self._task: Optional[asyncio.Task] = None
        self._last_cleanup = datetime.now()

    async def start(self):
        """Railway resurslarini monitoring qilishni boshlash"""
        if self.running:
            return

        self.running = True
        self._task = asyncio.create_task(self._monitor_loop())
        logger.info("Railway monitoring xizmati ishga tushirildi")

    async def stop(self):
        """Railway resurslarini monitoring qilishni to'xtatish"""
        if not self.running:
            return

        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Railway monitoring xizmati to'xtatildi")

    async def _monitor_loop(self):
        """Railway resurslarini monitoring qilish"""
        while self.running:
            try:
                await self._check_resources()
            except Exception as e:
                logger.error(f"Railway resurslarini tekshirishda xatolik: {e}")

            await asyncio.sleep(self.CLEANUP_INTERVAL)

    async def _check_resources(self):
        """Tizim resurslarini tekshirish va kerak bo'lsa tozalash"""
        try:
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            if memory.percent > self.MEMORY_THRESHOLD:
                logger.warning(f"Xotira sig'imi yuqori: {memory.percent}%")
                await self._emergency_cleanup()

            if disk.percent > self.DISK_THRESHOLD:
                logger.warning(f"Disk sig'imi yuqori: {disk.percent}%")
                await self._emergency_cleanup()

        except Exception as e:
            logger.error(f"Resurslarni tekshirishda xatolik: {e}")

    async def _emergency_cleanup(self):
        """Favqulodda tozalash - eng katta/eski fayllarni o'chirish"""
        try:
            files = []
            for root, _, filenames in os.walk(self.downloads_dir):
                for filename in filenames:
                    path = os.path.join(root, filename)
                    try:
                        stats = os.stat(path)
                        files.append({
                            'path': path,
                            'size': stats.st_size,
                            'mtime': stats.st_mtime
                        })
                    except OSError:
                        continue

            # Fayllarni hajmi bo'yicha tartiblash
            files.sort(key=lambda x: (-x['size'], -x['mtime']))

            # 50% fayllarni o'chirish
            for file in files[:len(files)//2]:
                try:
                    os.remove(file['path'])
                    logger.info(f"Emergency cleanup: {file['path']} o'chirildi")
                except OSError as e:
                    logger.error(f"Faylni o'chirishda xatolik {file['path']}: {e}")

        except Exception as e:
            logger.error(f"Emergency cleanup xatoligi: {e}")

    def get_resource_usage(self) -> Dict[str, float]:
        """Railway resurs foydalanish statistikasi"""
        try:
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                'memory_percent': memory.percent,
                'memory_used_mb': memory.used / (1024 * 1024),
                'disk_percent': disk.percent,
                'disk_used_mb': disk.used / (1024 * 1024)
            }
        except Exception as e:
            logger.error(f"Resurs statistikasini olishda xatolik: {e}")
            return {}