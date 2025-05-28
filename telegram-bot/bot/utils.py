import re
import os
import logging
import asyncio
from typing import Optional, Any, Dict, Tuple
from pathlib import Path
from functools import wraps
from datetime import datetime

from .config.config import config

logger = logging.getLogger(__name__)

def extract_url(text: str) -> Optional[str]:
    """Extract URL from text message"""
    url_pattern = r'https?://[^\s<>"\']+'
    match = re.search(url_pattern, text)
    return match.group(0) if match else None

def ensure_downloads_dir() -> None:
    """Ensure downloads directory exists"""
    os.makedirs(config.downloads_dir, exist_ok=True)

def cleanup_file(file_path: str) -> None:
    """Safely remove a file if it exists"""
    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception as e:
            logger.error(f"Error removing file {file_path}: {e}")

def format_size(size_in_bytes: int) -> str:
    """Format file size in human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_in_bytes < 1024:
            if unit == 'B':
                return f"{size_in_bytes} {unit}"
            return f"{size_in_bytes:.1f} {unit}"
        size_in_bytes /= 1024
    return f"{size_in_bytes:.1f} TB"

def format_duration(seconds: float) -> str:
    """Format duration in HH:MM:SS format"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = int(seconds % 60)
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"

async def run_command(cmd: list) -> Tuple[int, bytes, bytes]:
    """Run a command asynchronously and return returncode, stdout, stderr"""
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    return process.returncode, stdout, stderr

def async_error_handler(func):
    """Asinxron funksiyalar uchun xatoliklarni qayta ishlash dekorator"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Xatolik {func.__name__}: {str(e)}", exc_info=True)
            return None
    return wrapper

def safe_get(obj: Dict[str, Any], *keys: str, default: Any = None) -> Any:
    """Dictionary'dan xavfsiz qiymat olish"""
    try:
        for key in keys:
            obj = obj[key]
        return obj
    except (KeyError, TypeError, IndexError):
        return default

def is_video_url(text: str) -> bool:
    url_regex = re.compile(r"https?://[\w./?=&%-]+", re.IGNORECASE)
    return bool(url_regex.search(text))

def is_valid_url(url: str) -> bool:
    """Check if URL is valid"""
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return url_pattern.match(url) is not None

def sanitize_filename(filename: str) -> str:
    """Remove invalid characters from filename"""
    # Remove invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    # Remove control characters
    filename = "".join(char for char in filename if ord(char) >= 32)
    return filename.strip()

def get_safe_path(base_dir: str, filename: str) -> str:
    """Get safe file path, preventing directory traversal"""
    safe_filename = sanitize_filename(filename)
    return os.path.join(base_dir, safe_filename)

async def check_url_access(url: str) -> bool:
    """Check if URL is accessible"""
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.head(url, allow_redirects=True, timeout=10) as response:
                return response.status == 200
    except Exception as e:
        logger.error(f"Error checking URL access: {e}")
        return False

def get_supported_sites() -> list:
    """Get list of supported video platforms"""
    return [
        'YouTube',
        'Instagram',
        'TikTok',
        'Facebook',
        'Twitter',
        'Vimeo',
        'Dailymotion',
        'VK',
        'Twitch',
        'SoundCloud'
    ]

def validate_url(url: str) -> bool:
    """Check if URL is from a supported platform"""
    supported_domains = [
        'youtube.com', 'youtu.be',
        'instagram.com',
        'tiktok.com',
        'facebook.com', 'fb.com', 'fb.watch',
        'twitter.com', 't.co',
        'vimeo.com',
        'dailymotion.com',
        'vk.com',
        'twitch.tv',
        'soundcloud.com'
    ]
    try:
        from urllib.parse import urlparse
        domain = urlparse(url).netloc.lower()
        return any(site in domain for site in supported_domains)
    except:
        return False
