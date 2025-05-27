import os
import logging
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

class CleanupService:
    def __init__(self, downloads_dir: str = "downloads", max_age_hours: int = 1):  # Railway uchun 1 soatga o'zgartirildi
        self.downloads_dir = Path(downloads_dir)
        self.max_age_hours = max_age_hours
        self.running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self):
        """Tozalash xizmatini ishga tushirish"""
        if self.running:
            return
            
        self.running = True
        self._task = asyncio.create_task(self._cleanup_loop())
        logger.info("Fayl tozalash xizmati ishga tushirildi")

    async def stop(self):
        """Tozalash xizmatini to'xtatish"""
        if not self.running:
            return
            
        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Fayl tozalash xizmati to'xtatildi")

    async def _cleanup_loop(self):
        """Vaqti-vaqti bilan fayllarni tozalash"""
        while self.running:
            try:
                await self._cleanup_old_files()
            except Exception as e:
                logger.error(f"Fayllarni tozalashda xatolik: {e}")
            
            # Railway uchun har 15 daqiqada tekshirish
            await asyncio.sleep(15 * 60)

    async def _cleanup_old_files(self):
        """Eski fayllarni tozalash"""
        if not self.downloads_dir.exists():
            return

        now = datetime.now()
        max_age = timedelta(hours=self.max_age_hours)
        count = 0
        size = 0

        for file_path in self.downloads_dir.iterdir():
            if not file_path.is_file():
                continue

            try:
                mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                # Railway uchun: 100MB dan katta fayllarni darhol o'chirish
                if now - mtime > max_age or file_path.stat().st_size > 100 * 1024 * 1024:
                    size += file_path.stat().st_size
                    file_path.unlink()
                    count += 1
            except Exception as e:
                logger.error(f"Faylni o'chirishda xatolik {file_path}: {e}")

        if count > 0:
            logger.info(
                f"Tozalandi: {count} ta fayl ({size / 1024 / 1024:.1f} MB)"
            )