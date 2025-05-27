import os
import logging
import asyncio
from typing import Optional, Tuple, Dict, Any
import yt_dlp
from .services.monitoring import metrics
from .utils import generate_temp_filename

logger = logging.getLogger(__name__)

class DownloadError(Exception):
    """Custom exception for download errors"""
    pass

def create_ydl_opts(output_path: str) -> dict:
    """Create yt-dlp options"""
    return {
        'format': 'best[ext=mp4]/best',
        'outtmpl': output_path,
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'noprogress': True,
        'noplaylist': True,
        'max_filesize': 450 * 1024 * 1024,  # 450MB - Railway limit
    }

async def download_video_with_info(url: str, output_dir: str = "downloads") -> Tuple[str, Dict[str, Any]]:
    """Download video and return path with video info"""
    try:
        os.makedirs(output_dir, exist_ok=True)
        output_path = generate_temp_filename(suffix=".%(ext)s")
        ydl_opts = create_ydl_opts(output_path)
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = await asyncio.get_event_loop().run_in_executor(
                    None, 
                    lambda: ydl.extract_info(url, download=True)
                )
                
            if not info:
                raise DownloadError("Could not extract video info")
            
            # Find downloaded file
            for file in os.listdir(output_dir):
                if file.startswith(os.path.basename(output_path.split('.')[0])):
                    video_path = os.path.join(output_dir, file)
                    if os.path.exists(video_path):
                        return video_path, info
                        
            raise DownloadError("Downloaded file not found")
            
        except yt_dlp.utils.DownloadError as e:
            raise DownloadError(f"yt-dlp error: {str(e)}")
            
    except Exception as e:
        logger.error(f"Download error for {url}: {str(e)}")
        metrics.track_error(type(e).__name__)
        raise DownloadError(str(e))

async def download_video(url: str) -> Optional[str]:
    """Simple video download function"""
    try:
        video_path, _ = await download_video_with_info(url)
        return video_path
    except Exception as e:
        logger.error(f"Simple download error for {url}: {str(e)}")
        return None
