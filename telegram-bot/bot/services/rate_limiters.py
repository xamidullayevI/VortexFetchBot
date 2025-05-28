"""Rate limiter instances shared across the bot"""
from .rate_limiter import RateLimiter
from ..config.config import config

# Global rate limiter for overall bot usage
rate_limiter = RateLimiter()

# Audio processing rate limiter
audio_rate_limiter = RateLimiter(
    max_requests=config.max_audio_requests_per_minute,
    time_window=60,
    max_file_size_mb=100
)