import os
import logging
import asyncio
import psutil
from pathlib import Path
from typing import Optional
from ..services.monitoring import metrics
from ..config.config import config

logger = logging.getLogger(__name__)

class RailwayService:
    def __init__(self, downloads_dir: str):
        self.downloads_dir = Path(downloads_dir)
        self.is_running = False
        self._monitor_task: Optional[asyncio.Task] = None
        self.max_disk_percent = config.max_disk_percent
        self.max_memory_percent = config.max_memory_percent

    async def start(self):
        """Start Railway service monitoring"""
        self.is_running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("Railway service monitoring started")

    async def stop(self):
        """Stop Railway service monitoring"""
        self.is_running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("Railway service monitoring stopped")

    async def _monitor_loop(self):
        """Monitor system resources and clean up if necessary"""
        while self.is_running:
            try:
                await self._check_system_resources()
                await asyncio.sleep(config.cleanup_interval)
            except Exception as e:
                logger.error(f"Error in Railway monitoring loop: {e}")
                metrics.track_error(type(e).__name__)
                await asyncio.sleep(60)

    async def _check_system_resources(self):
        """Check system resources and take action if needed"""
        try:
            # Check disk usage
            disk_usage = psutil.disk_usage(self.downloads_dir)
            if disk_usage.percent > self.max_disk_percent:
                logger.warning(f"High disk usage: {disk_usage.percent}%")
                await self._clean_downloads()

            # Check memory usage
            memory = psutil.virtual_memory()
            if memory.percent > self.max_memory_percent:
                logger.warning(f"High memory usage: {memory.percent}%")
                # Force garbage collection
                import gc
                gc.collect()

        except Exception as e:
            logger.error(f"Error checking system resources: {e}")
            metrics.track_error(type(e).__name__)

    async def _clean_downloads(self):
        """Clean up downloads directory when disk usage is high"""
        try:
            if not self.downloads_dir.exists():
                return

            # Get list of files sorted by modification time
            files = []
            for file_path in self.downloads_dir.iterdir():
                if file_path.is_file():
                    files.append((file_path, os.path.getmtime(file_path)))
            
            # Sort files by modification time (oldest first)
            files.sort(key=lambda x: x[1])

            # Remove oldest files until disk usage is below threshold
            for file_path, _ in files:
                try:
                    os.remove(file_path)
                    logger.info(f"Removed old file: {file_path}")
                    
                    # Check if we've freed up enough space
                    if psutil.disk_usage(self.downloads_dir).percent < self.max_disk_percent:
                        break
                except Exception as e:
                    logger.error(f"Error removing file {file_path}: {e}")

        except Exception as e:
            logger.error(f"Error cleaning downloads directory: {e}")
            metrics.track_error(type(e).__name__)