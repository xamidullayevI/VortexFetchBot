import os
import json
import logging
import asyncio
import subprocess
from typing import Optional, Dict, Any
from pathlib import Path

from .services.monitoring import metrics
from .config.config import config
from .utils import run_command

logger = logging.getLogger(__name__)

async def get_video_info(video_path: str) -> Optional[Dict[str, Any]]:
    """Get video information using ffprobe"""
    try:
        cmd = [
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            video_path
        ]
        
        returncode, stdout, stderr = await run_command(cmd)
        
        if returncode != 0:
            logger.error(f"FFprobe error: {stderr.decode()}")
            return None
            
        return json.loads(stdout.decode())
        
    except Exception as e:
        logger.error(f"Error getting video info: {e}")
        metrics.track_error(type(e).__name__)
        return None

def calculate_target_bitrate(
    duration: float,
    target_size_mb: int,
    audio_bitrate: int = 128000
) -> int:
    """Calculate target video bitrate based on desired file size"""
    target_size_bits = target_size_mb * 8 * 1024 * 1024
    audio_size = (audio_bitrate * duration) / 8
    video_size = target_size_bits - audio_size
    video_bitrate = int(video_size / duration)
    return max(video_bitrate, 100000)  # Minimum 100Kbps

async def compress_video(
    input_path: str,
    output_path: str,
    target_size_mb: int = None,
    max_height: int = 720
) -> Optional[str]:
    """Compress video to target size while maintaining quality"""
    try:
        if not os.path.exists(input_path):
            logger.error(f"Input video not found: {input_path}")
            return None

        # Use config target size if not specified
        target_size_mb = target_size_mb or config.target_video_size_mb
            
        # Get video information
        video_info = await get_video_info(input_path)
        if not video_info:
            return None
            
        # Get video duration and original size
        duration = float(video_info['format']['duration'])
        original_size = os.path.getsize(input_path)
        
        # If already smaller than target, return original
        if original_size <= target_size_mb * 1024 * 1024:
            logger.info("Video already within size limit")
            return input_path
            
        # Find video stream
        video_stream = None
        for stream in video_info['streams']:
            if stream['codec_type'] == 'video':
                video_stream = stream
                break
                
        if not video_stream:
            logger.error("No video stream found")
            return None
            
        # Calculate target bitrate
        target_bitrate = calculate_target_bitrate(
            duration=duration,
            target_size_mb=target_size_mb
        )
        
        # Calculate scaling
        width = int(video_stream.get('width', 1920))
        height = int(video_stream.get('height', 1080))
        
        if height > max_height:
            scale_factor = max_height / height
            width = int(width * scale_factor)
            height = max_height
            
        # Ensure even dimensions
        width = width - (width % 2)
        height = height - (height % 2)
        
        # Construct ffmpeg command
        cmd = [
            'ffmpeg',
            '-i', input_path,
            '-c:v', 'libx264',
            '-preset', 'medium',
            '-b:v', f'{target_bitrate}',
            '-maxrate', f'{int(target_bitrate * 1.5)}',
            '-bufsize', f'{int(target_bitrate * 2)}',
            '-vf', f'scale={width}:{height}',
            '-c:a', 'aac',
            '-b:a', '128k',
            '-ar', '44100',
            '-movflags', '+faststart',
            '-y',
            output_path
        ]
        
        # Run compression
        returncode, stdout, stderr = await run_command(cmd)
        
        if returncode != 0:
            logger.error(f"FFmpeg error: {stderr.decode()}")
            metrics.track_error("FFmpegError")
            return None
            
        if os.path.exists(output_path):
            new_size = os.path.getsize(output_path)
            compression_ratio = (original_size - new_size) / original_size * 100
            logger.info(f"Video compressed: {compression_ratio:.1f}% size reduction")
            return output_path
            
    except Exception as e:
        logger.error(f"Error compressing video: {e}")
        metrics.track_error(type(e).__name__)
        if os.path.exists(output_path):
            try:
                os.remove(output_path)
            except:
                pass
                
    return None

async def extract_audio_from_video(video_path: str) -> str:
    """Extract audio from video file using ffmpeg"""
    try:
        video_path = Path(video_path)
        if not video_path.exists():
            logger.error(f"Video file not found: {video_path}")
            return None
            
        # Create audio output path
        audio_path = video_path.with_suffix('.mp3')
        
        # Construct ffmpeg command
        cmd = [
            'ffmpeg',
            '-i', str(video_path),
            '-vn',  # Disable video
            '-acodec', 'libmp3lame',
            '-ab', '192k',
            '-ar', '44100',
            '-y',  # Overwrite output file
            str(audio_path)
        ]
        
        # Run ffmpeg command
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            logger.error(f"FFmpeg error: {stderr.decode()}")
            metrics.track_error("FFmpegError")
            return None
            
        if not audio_path.exists():
            logger.error("Audio file was not created")
            return None
            
        return str(audio_path)
        
    except Exception as e:
        logger.error(f"Error extracting audio: {e}")
        metrics.track_error(type(e).__name__)
        return None
