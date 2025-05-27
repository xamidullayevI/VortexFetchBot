import logging
import time
import psutil
from functools import wraps
from typing import Any, Callable, Dict
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class MetricsCollector:
    """Bot ishlashini kuzatish uchun metrikalar to'plovchi"""
    download_times: Dict[str, float] = field(default_factory=dict)
    process_times: Dict[str, float] = field(default_factory=dict)
    error_counts: Dict[str, int] = field(default_factory=dict)
    total_downloads: int = 0
    total_errors: int = 0
    start_time: datetime = field(default_factory=datetime.now)

    def track_download(self, url: str, duration: float) -> None:
        """Video yuklab olish vaqtini kuzatish"""
        self.download_times[url] = duration
        self.total_downloads += 1

    def track_error(self, error_type: str) -> None:
        """Xatoliklarni kuzatish"""
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
        self.total_errors += 1

    def get_statistics(self) -> Dict[str, Any]:
        """Bot ishlashi haqida statistika"""
        uptime = (datetime.now() - self.start_time).total_seconds()
        avg_download_time = (
            sum(self.download_times.values()) / len(self.download_times)
            if self.download_times else 0
        )

        # Railway tizim ma'lumotlari
        try:
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            cpu_percent = psutil.cpu_percent(interval=0.1)

            system_stats = {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_used_mb': memory.used / (1024 * 1024),
                'memory_total_mb': memory.total / (1024 * 1024),
                'disk_percent': disk.percent,
                'disk_used_mb': disk.used / (1024 * 1024),
                'disk_total_mb': disk.total / (1024 * 1024)
            }
        except Exception as e:
            logger.error(f"Tizim ma'lumotlarini olishda xatolik: {e}")
            system_stats = {}
        
        return {
            "total_downloads": self.total_downloads,
            "total_errors": self.total_errors,
            "uptime_seconds": uptime,
            "average_download_time": avg_download_time,
            "error_distribution": dict(self.error_counts),
            "system": system_stats
        }

# Global metrikalar obyekti
metrics = MetricsCollector()

def monitor_performance(func: Callable) -> Callable:
    """Funksiya bajarilish vaqtini o'lchash uchun dekorator"""
    @wraps(func)
    async def wrapper(*args, **kwargs) -> Any:
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            duration = time.time() - start_time
            
            # URL bo'lsa, yuklab olish vaqtini saqlash
            if len(args) > 0 and isinstance(args[1], str) and "://" in args[1]:
                metrics.track_download(args[1], duration)
                
            return result
        except Exception as e:
            metrics.track_error(type(e).__name__)
            raise
            
    return wrapper

def get_bot_statistics() -> Dict[str, Any]:
    """Bot ishlashi haqida umumiy statistika"""
    return metrics.get_statistics()