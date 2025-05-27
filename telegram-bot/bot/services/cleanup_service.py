import os
import time
import asyncio
import logging
from pathlib import Path
from typing import Optional
from ..utils import cleanup_file
from ..config.config import config
from ..services.monitoring import metrics

logger = logging.getLogger(__name__)

class CleanupService:
    def __init__(
        self,
        downloads_dir: str = None,
        max_age_hours: int = None,
        cleanup_interval: int = None
    ):
        self.downloads_dir = Path(downloads_dir or config.downloads_dir)
        self.max_age_hours = max_age_hours or config.max_file_age
        self.cleanup_interval = cleanup_interval or config.cleanup_interval
        self._task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self):
        """Start the cleanup service"""
        if self._running:
            return
            
        self._running = True
        self._task = asyncio.create_task(self._run_cleanup_loop())
        logger.info(
            f"Cleanup service started with {self.max_age_hours}h max age, "
            f"{self.cleanup_interval}s interval"
        )

    async def stop(self):
        """Stop the cleanup service"""
        if not self._running:
            return
            
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Cleanup service stopped")

    async def _run_cleanup_loop(self):
        """Main cleanup loop"""
        while self._running:
            try:
                await self._cleanup_old_files()
                await self._check_disk_usage()
                await asyncio.sleep(self.cleanup_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                metrics.track_error(type(e).__name__)
                await asyncio.sleep(60)  # Wait a minute before retrying

    async def _cleanup_old_files(self):
        """Clean up files older than max_age_hours"""
        try:
            current_time = time.time()
            max_age_seconds = self.max_age_hours * 3600
            cleaned_count = 0
            cleaned_size = 0

            if not self.downloads_dir.exists():
                return

            for file in self.downloads_dir.iterdir():
                if not file.is_file():
                    continue

                try:
                    file_age = current_time - file.stat().st_mtime
                    if file_age > max_age_seconds:
                        file_size = file.stat().st_size
                        cleanup_file(str(file))
                        cleaned_count += 1
                        cleaned_size += file_size
                except Exception as e:
                    logger.error(f"Error cleaning up file {file}: {e}")

            if cleaned_count > 0:
                logger.info(
                    f"Cleaned up {cleaned_count} files "
                    f"({cleaned_size/1024/1024:.1f}MB)"
                )

        except Exception as e:
            logger.error(f"Error in _cleanup_old_files: {e}")
            metrics.track_error(type(e).__name__)

    async def _check_disk_usage(self):
        """Check disk usage and clean up more files if needed"""
        try:
            import psutil
            disk_usage = psutil.disk_usage(str(self.downloads_dir))
            
            if disk_usage.percent >= config.max_disk_percent:
                logger.warning(
                    f"Disk usage at {disk_usage.percent}%, "
                    "performing emergency cleanup"
                )
                
                # Get list of files sorted by modification time
                files = []
                for file in self.downloads_dir.iterdir():
                    if file.is_file():
                        try:
                            files.append((
                                file,
                                file.stat().st_mtime,
                                file.stat().st_size
                            ))
                        except Exception:
                            continue
                
                # Sort by modification time (oldest first)
                files.sort(key=lambda x: x[1])
                
                # Delete files until disk usage is below threshold
                cleaned_count = 0
                cleaned_size = 0
                target_percent = config.max_disk_percent - 10  # Aim for 10% less
                
                for file, _, size in files:
                    if disk_usage.percent <= target_percent:
                        break
                        
                    try:
                        cleanup_file(str(file))
                        cleaned_count += 1
                        cleaned_size += size
                        disk_usage = psutil.disk_usage(str(self.downloads_dir))
                    except Exception as e:
                        logger.error(f"Error in emergency cleanup of {file}: {e}")
                
                if cleaned_count > 0:
                    logger.info(
                        f"Emergency cleanup: removed {cleaned_count} files "
                        f"({cleaned_size/1024/1024:.1f}MB)"
                    )

        except Exception as e:
            logger.error(f"Error in _check_disk_usage: {e}")
            metrics.track_error(type(e).__name__)

    async def force_cleanup(self):
        """Force immediate cleanup"""
        await self._cleanup_old_files()
        await self._check_disk_usage()