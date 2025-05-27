import os
import logging
import asyncio
import time
from pathlib import Path
from typing import Optional
from ..services.monitoring import metrics

logger = logging.getLogger(__name__)

class CleanupService:
    def __init__(self, downloads_dir: str, max_age_hours: int = 1):
        self.downloads_dir = Path(downloads_dir)
        self.max_age_seconds = max_age_hours * 3600
        self.is_running = False
        self._cleanup_task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the cleanup service"""
        self.is_running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info(f"Cleanup service started. Max file age: {self.max_age_seconds/3600:.1f} hours")

    async def stop(self):
        """Stop the cleanup service"""
        self.is_running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        logger.info("Cleanup service stopped")

    async def _cleanup_loop(self):
        """Main cleanup loop"""
        while self.is_running:
            try:
                await self._cleanup_old_files()
                # Check every 5 minutes
                await asyncio.sleep(300)
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                metrics.track_error(type(e).__name__)
                # On error, wait 1 minute before retrying
                await asyncio.sleep(60)

    async def _cleanup_old_files(self):
        """Clean up old files from downloads directory"""
        try:
            current_time = time.time()
            if not self.downloads_dir.exists():
                logger.warning(f"Downloads directory not found: {self.downloads_dir}")
                return

            files_removed = 0
            total_size_cleaned = 0

            for file_path in self.downloads_dir.glob('*'):
                if not file_path.is_file():
                    continue

                try:
                    file_age = current_time - os.path.getmtime(file_path)
                    if file_age > self.max_age_seconds:
                        file_size = os.path.getsize(file_path)
                        os.remove(file_path)
                        files_removed += 1
                        total_size_cleaned += file_size
                        logger.debug(f"Removed old file: {file_path}")
                except Exception as e:
                    logger.error(f"Error removing file {file_path}: {e}")
                    metrics.track_error(type(e).__name__)

            if files_removed > 0:
                logger.info(
                    f"Cleanup completed: {files_removed} files removed, "
                    f"{total_size_cleaned / (1024*1024):.1f}MB freed"
                )

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            metrics.track_error(type(e).__name__)