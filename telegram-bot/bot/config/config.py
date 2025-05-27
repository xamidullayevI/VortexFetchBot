import os
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass

@dataclass
class BotConfig:
    # Bot settings
    token: str
    admin_ids: List[int]
    max_file_age: int
    port: int
    downloads_dir: Path

    # Railway settings
    max_disk_percent: int = 80
    max_memory_percent: int = 85
    cleanup_interval: int = 300  # 5 minutes

    # Video settings
    max_video_size_mb: int = 450  # Railway limit
    target_video_size_mb: int = 45  # Telegram limit
    
    # Rate limiting
    max_requests_per_minute: int = 30
    max_audio_requests_per_minute: int = 20

    @classmethod
    def load(cls) -> 'BotConfig':
        """Load configuration from environment variables"""
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not token:
            raise ValueError("TELEGRAM_BOT_TOKEN not found in environment variables")

        # Parse admin IDs
        admin_ids_str = os.getenv("ADMIN_IDS", "")
        admin_ids = [int(id_str) for id_str in admin_ids_str.split(",") if id_str.strip()]

        # Set up downloads directory
        downloads_dir = Path("downloads")
        downloads_dir.mkdir(exist_ok=True)

        return cls(
            token=token,
            admin_ids=admin_ids,
            max_file_age=int(os.getenv("MAX_FILE_AGE_HOURS", "1")),
            port=int(os.getenv("PORT", "8080")),
            downloads_dir=downloads_dir,
            max_disk_percent=int(os.getenv("MAX_DISK_PERCENT", "80")),
            max_memory_percent=int(os.getenv("MAX_MEMORY_PERCENT", "85")),
            cleanup_interval=int(os.getenv("CLEANUP_INTERVAL_SECONDS", "300")),
            max_video_size_mb=int(os.getenv("MAX_VIDEO_SIZE_MB", "450")),
            target_video_size_mb=int(os.getenv("TARGET_VIDEO_SIZE_MB", "45")),
            max_requests_per_minute=int(os.getenv("MAX_REQUESTS_PER_MINUTE", "30")),
            max_audio_requests_per_minute=int(os.getenv("MAX_AUDIO_REQUESTS_PER_MINUTE", "20"))
        )

# Global config instance
config = BotConfig.load()