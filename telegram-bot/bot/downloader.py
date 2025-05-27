import os
import logging
import asyncio
from typing import Optional, Tuple, Dict, Any
from pathlib import Path
import yt_dlp
from .services.monitoring import metrics
from .utils import generate_temp_filename
from .config.config import config

logger = logging.getLogger(__name__)

class DownloadError(Exception):
    """Custom exception for download errors"""
    pass

def create_ydl_opts(output_path: str) -> dict:
    """Create yt-dlp options"""
    return {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': output_path,
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'noprogress': True,
        'noplaylist': True,
        'max_filesize': config.max_video_size_mb * 1024 * 1024,
        'merge_output_format': 'mp4',
        'postprocessors': [{
            'key': 'FFmpegVideoRemuxer',
            'preferedformat': 'mp4',
        }],
    }

async def download_video_with_info(url: str, output_dir: str = "downloads") -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    """Download video and return path with video info"""
    try:
        output_dir = Path(output_dir)
        output_dir.mkdir(exist_ok=True)
        
        output_path = generate_temp_filename(suffix=".%(ext)s")
        ydl_opts = create_ydl_opts(output_path)

        loop = asyncio.get_event_loop()
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Extract info first to validate URL and check size
                info = await loop.run_in_executor(
                    None,
                    lambda: ydl.extract_info(url, download=False)
                )
                
                if not info:
                    raise DownloadError("Could not extract video info")
                
                # Check file size if available
                filesize = info.get('filesize') or info.get('filesize_approx')
                if filesize and filesize > config.max_video_size_mb * 1024 * 1024:
                    raise DownloadError(
                        f"Video size ({filesize/(1024*1024):.1f}MB) exceeds limit "
                        f"({config.max_video_size_mb}MB)"
                    )
                
                # Download video
                info = await loop.run_in_executor(
                    None,
                    lambda: ydl.extract_info(url, download=True)
                )
                
            # Find downloaded file
            for file in output_dir.iterdir():
                if file.name.startswith(Path(output_path).stem):
                    video_path = str(file)
                    if os.path.exists(video_path):
                        metrics.track_successful_download(url)
                        return video_path, info
                        
            raise DownloadError("Downloaded file not found")
            
        except yt_dlp.utils.DownloadError as e:
            # Handle specific yt-dlp errors
            error_msg = str(e)
            if "HTTP Error 403" in error_msg:
                raise DownloadError("Video is private or requires authentication")
            elif "This video is not available" in error_msg:
                raise DownloadError("Video is not available")
            elif "Sign in to confirm your age" in error_msg:
                raise DownloadError("Age-restricted content")
            else:
                raise DownloadError(f"Download error: {error_msg}")
            
    except DownloadError:
        raise
    except Exception as e:
        logger.error(f"Download error for {url}: {str(e)}")
        metrics.track_error(type(e).__name__)
        raise DownloadError(str(e))
    
    return None, None

async def download_video(url: str) -> Optional[str]:
    """Simple video download function"""
    try:
        video_path, _ = await download_video_with_info(url)
        return video_path
    except Exception as e:
        logger.error(f"Simple download error for {url}: {str(e)}")
        metrics.track_error(type(e).__name__)
        return None
