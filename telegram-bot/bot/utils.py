import re
import os
import logging
import asyncio
from typing import Optional, Any, Dict
from pathlib import Path
from functools import wraps
from datetime import datetime
import uuid

from bot.downloader import download_video_with_info, DownloadError

logger = logging.getLogger(__name__)

def extract_url(text: str) -> Optional[str]:
    """Extract URL from text message"""
    url_pattern = r'https?://[^\s<>"\']+'
    match = re.search(url_pattern, text)
    return match.group(0) if match else None

def ensure_downloads_dir() -> Path:
    """Ensure downloads directory exists"""
    downloads_dir = Path("downloads")
    downloads_dir.mkdir(exist_ok=True)
    return downloads_dir

def cleanup_file(filepath: str) -> None:
    """Safely delete a file"""
    try:
        if filepath and os.path.exists(filepath):
            os.remove(filepath)
            logger.debug(f"Deleted file: {filepath}")
    except Exception as e:
        logger.error(f"Error cleaning up file {filepath}: {e}")

def generate_temp_filename(prefix: str = "", suffix: str = "") -> str:
    """Generate temporary filename in downloads directory"""
    downloads_dir = ensure_downloads_dir()
    return str(downloads_dir / f"{prefix}{uuid.uuid4()}{suffix}")

def format_size(size_bytes: int) -> str:
    """Format file size to human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f}{unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f}GB"

def format_duration(seconds: float) -> str:
    """Format duration in seconds to mm:ss or hh:mm:ss format"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"

async def run_command(cmd: list) -> tuple:
    """Run shell command asynchronously"""
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

# Yangi universal_download: faqat yt-dlp asosida
def universal_download(url, download_dir="downloads"):
    try:
        result = download_video_with_info(url, download_dir)
        if not isinstance(result, tuple) or len(result) != 2:
            print(f"[ERROR] download_video_with_info returned unexpected value: {result}")
            return {
                "error": True,
                "error_message": "download_video_with_info noto'g'ri qiymat qaytardi (2 ta qiymat kutildi)",
                "raw_result": result
            }
        video_path, info = result
        audio_url = None
        # Agar info dictda audio link bo‘lsa, uni ham qaytar
        if info and 'requested_formats' in info:
            for fmt in info['requested_formats']:
                if fmt.get('acodec') != 'none' and fmt.get('url'):
                    audio_url = fmt['url']
                    break
        return {
            "download_url": video_path,
            "audio_url": audio_url,
            "media_type": info.get('ext') if info else None,
            "thumb": info.get('thumbnail') if info else None,
            "info": info,
            "method": "ytdlp",
            "error": False
        }
    except DownloadError as e:
        print(f"[ERROR] yt-dlp xatolik: {e}")
        return {
            "error": True,
            "error_message": f"yt-dlp xatolik yoki media topilmadi: {e}"
        }

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
