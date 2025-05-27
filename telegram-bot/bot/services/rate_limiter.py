import time
import logging
import asyncio
from typing import Dict, Set, Optional
from collections import defaultdict
from dataclasses import dataclass, field
from ..config.config import config

logger = logging.getLogger(__name__)

@dataclass
class UserLimit:
    count: int = 0
    last_reset: float = field(default_factory=time.time)
    total_size: int = 0
    unblock_task: Optional[asyncio.Task] = None

class RateLimiter:
    def __init__(
        self,
        max_requests: int = None,
        time_window: int = 60,
        max_file_size_mb: int = None,
        max_total_size_mb: int = 1024  # 1GB default total size per window
    ):
        self.max_requests = max_requests or config.max_requests_per_minute
        self.time_window = time_window
        self.max_file_size = (max_file_size_mb or config.max_video_size_mb) * 1024 * 1024
        self.max_total_size = max_total_size_mb * 1024 * 1024
        self.user_limits: Dict[int, UserLimit] = {}
        self.blocked_users: Set[int] = set()

    def can_process(self, user_id: int, file_size: int = 0) -> bool:
        """
        Check if user can process a request
        
        Args:
            user_id: User's Telegram ID
            file_size: Size of file in bytes
            
        Returns:
            bool: Whether request can be processed
        """
        # Check blocked users
        if user_id in self.blocked_users:
            logger.warning(f"Blocked user {user_id} attempted request")
            return False

        # Check file size limit
        if file_size > self.max_file_size:
            logger.warning(
                f"User {user_id} attempted to process file larger than "
                f"{self.max_file_size/1024/1024:.1f}MB"
            )
            return False

        current_time = time.time()

        # Get or create user limit
        if user_id not in self.user_limits:
            self.user_limits[user_id] = UserLimit()
        
        user_limit = self.user_limits[user_id]

        # Reset counters if time window expired
        if current_time - user_limit.last_reset >= self.time_window:
            user_limit.count = 0
            user_limit.total_size = 0
            user_limit.last_reset = current_time

        # Check request count limit
        if user_limit.count >= self.max_requests:
            logger.warning(f"Rate limit exceeded for user {user_id}")
            return False

        # Check total size limit
        if user_limit.total_size + file_size > self.max_total_size:
            logger.warning(
                f"Total size limit exceeded for user {user_id}: "
                f"{(user_limit.total_size + file_size)/1024/1024:.1f}MB"
            )
            return False

        # Update counters
        user_limit.count += 1
        user_limit.total_size += file_size
        return True

    async def block_user(self, user_id: int, duration: int = None):
        """
        Block a user
        
        Args:
            user_id: User's Telegram ID
            duration: Block duration in seconds (None for permanent)
        """
        self.blocked_users.add(user_id)
        logger.info(f"User {user_id} blocked{f' for {duration}s' if duration else ''}")
        
        # Cancel any existing unblock task
        if user_id in self.user_limits and self.user_limits[user_id].unblock_task:
            self.user_limits[user_id].unblock_task.cancel()
        
        if duration:
            # Create new unblock task
            async def unblock_later():
                try:
                    await asyncio.sleep(duration)
                    await self.unblock_user(user_id)
                except asyncio.CancelledError:
                    pass
                
            task = asyncio.create_task(unblock_later())
            if user_id not in self.user_limits:
                self.user_limits[user_id] = UserLimit()
            self.user_limits[user_id].unblock_task = task

    async def unblock_user(self, user_id: int):
        """Unblock a user"""
        self.blocked_users.discard(user_id)
        if user_id in self.user_limits:
            if self.user_limits[user_id].unblock_task:
                self.user_limits[user_id].unblock_task.cancel()
            del self.user_limits[user_id]
        logger.info(f"User {user_id} unblocked")

    def reset_user(self, user_id: int):
        """Reset limits for a specific user"""
        if user_id in self.user_limits:
            if self.user_limits[user_id].unblock_task:
                self.user_limits[user_id].unblock_task.cancel()
            del self.user_limits[user_id]
        self.blocked_users.discard(user_id)
        logger.info(f"Limits reset for user {user_id}")

    def reset_all(self):
        """Reset all limits and unblock all users"""
        for user_limit in self.user_limits.values():
            if user_limit.unblock_task:
                user_limit.unblock_task.cancel()
        self.user_limits.clear()
        self.blocked_users.clear()
        logger.info("All rate limits reset")

    def get_user_stats(self, user_id: int) -> Optional[Dict]:
        """Get current limits for a user"""
        if user_id not in self.user_limits:
            return None
            
        limit = self.user_limits[user_id]
        current_time = time.time()
        time_left = max(0, self.time_window - (current_time - limit.last_reset))
        
        return {
            'requests': limit.count,
            'max_requests': self.max_requests,
            'total_size_mb': limit.total_size / 1024 / 1024,
            'max_size_mb': self.max_total_size / 1024 / 1024,
            'time_left': time_left,
            'is_blocked': user_id in self.blocked_users
        }