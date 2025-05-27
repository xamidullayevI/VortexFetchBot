import time
import logging
from typing import Dict, Set
from collections import defaultdict
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

@dataclass
class RateLimit:
    """Rate limit ma'lumotlari"""
    last_reset: float = field(default_factory=time.time)
    count: int = 0

class RateLimiter:
    def __init__(
        self,
        max_requests: int = 30,      # Har bir foydalanuvchi uchun maksimal so'rovlar soni
        time_window: int = 60,       # Vaqt oralig'i (sekundlarda)
        max_file_size_mb: int = 450  # Maksimal fayl hajmi (MB)
    ):
        self.max_requests = max_requests
        self.time_window = time_window
        self.max_file_size = max_file_size_mb * 1024 * 1024
        self.user_limits: Dict[int, RateLimit] = defaultdict(RateLimit)
        self.blocked_users: Set[int] = set()

    def can_process(self, user_id: int, file_size: int = 0) -> bool:
        """
        Foydalanuvchi so'rovini qayta ishlash mumkinligini tekshirish
        
        Args:
            user_id: Foydalanuvchi ID'si
            file_size: Fayl hajmi (baytlarda)
            
        Returns:
            bool: So'rovni qayta ishlash mumkinligi
        """
        # Bloklangan foydalanuvchilarni tekshirish
        if user_id in self.blocked_users:
            return False

        # Fayl hajmini tekshirish
        if file_size > self.max_file_size:
            logger.warning(f"User {user_id} tried to process file larger than {self.max_file_size} bytes")
            return False

        current_time = time.time()
        user_limit = self.user_limits[user_id]

        # Vaqt oralig'i tugagan bo'lsa, hisoblagichni qayta boshlash
        if current_time - user_limit.last_reset >= self.time_window:
            user_limit.last_reset = current_time
            user_limit.count = 0

        # So'rovlar sonini tekshirish
        if user_limit.count >= self.max_requests:
            logger.warning(f"Rate limit exceeded for user {user_id}")
            return False

        user_limit.count += 1
        return True

    def block_user(self, user_id: int):
        """Foydalanuvchini bloklash"""
        self.blocked_users.add(user_id)
        logger.info(f"User {user_id} blocked")

    def unblock_user(self, user_id: int):
        """Foydalanuvchi blokini olib tashlash"""
        self.blocked_users.discard(user_id)
        logger.info(f"User {user_id} unblocked")

    def reset_limits(self):
        """Barcha cheklovlarni qayta o'rnatish"""
        self.user_limits.clear()
        self.blocked_users.clear()
        logger.info("Rate limits reset")