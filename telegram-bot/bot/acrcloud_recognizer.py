import os
import time
import hmac
import base64
import hashlib
import logging
import asyncio
import aiohttp
from typing import Dict, Optional, Any
from pathlib import Path

from .utils import run_command
from .services.monitoring import metrics
from .config.config import config

logger = logging.getLogger(__name__)

async def extract_audio_from_video(video_path: str, output_path: Optional[str] = None) -> Optional[str]:
    """Extract audio from video file"""
    try:
        if not os.path.exists(video_path):
            logger.error(f"Video file not found: {video_path}")
            return None

        if output_path is None:
            output_path = str(Path(video_path).with_suffix('.mp3'))

        cmd = [
            'ffmpeg',
            '-i', video_path,
            '-vn',  # Disable video
            '-acodec', 'libmp3lame',
            '-ab', '192k',
            '-ar', '44100',
            '-y',  # Overwrite output file
            output_path
        ]

        returncode, stdout, stderr = await run_command(cmd)

        if returncode != 0:
            logger.error(f"FFmpeg error: {stderr.decode()}")
            return None

        if not os.path.exists(output_path):
            logger.error("Audio file was not created")
            return None

        return output_path

    except Exception as e:
        logger.error(f"Error extracting audio: {e}")
        metrics.track_error(type(e).__name__)
        return None

async def get_music_info(audio_file: str) -> Optional[Dict[str, Any]]:
    """
    Recognize music using ACRCloud HTTP API
    Returns dict with music info or None if not found/error
    """
    try:
        # Check ACRCloud credentials
        host = os.getenv("ACRCLOUD_HOST")
        access_key = os.getenv("ACRCLOUD_ACCESS_KEY")
        access_secret = os.getenv("ACRCLOUD_ACCESS_SECRET")

        if not all([host, access_key, access_secret]):
            logger.error("ACRCloud credentials not configured")
            return None

        http_method = "POST"
        http_uri = "/v1/identify"
        data_type = "audio"
        signature_version = "1"
        timestamp = str(int(time.time()))

        string_to_sign = "\n".join([
            http_method,
            http_uri,
            access_key,
            data_type,
            signature_version,
            timestamp
        ])

        sign = base64.b64encode(
            hmac.new(
                access_secret.encode('ascii'),
                string_to_sign.encode('ascii'),
                digestmod=hashlib.sha1
            ).digest()
        ).decode('ascii')

        # Read audio file
        with open(audio_file, 'rb') as f:
            sample_bytes = f.read(10 * 1024 * 1024)  # Read up to 10MB

        # Prepare form data
        data = aiohttp.FormData()
        data.add_field('access_key', access_key)
        data.add_field('data_type', data_type)
        data.add_field('signature', sign)
        data.add_field('signature_version', signature_version)
        data.add_field('timestamp', timestamp)
        data.add_field('sample', sample_bytes, filename='sample.mp3')

        async with aiohttp.ClientSession() as session:
            url = f'https://{host}{http_uri}'
            async with session.post(url, data=data, timeout=30) as response:
                if response.status != 200:
                    logger.error(f"ACRCloud API error: {response.status}")
                    return None

                result = await response.json()

                if (result.get('status', {}).get('code') == 0 and
                    'metadata' in result and
                    'music' in result['metadata'] and
                    result['metadata']['music']):
                    
                    music = result['metadata']['music'][0]
                    
                    # Format response
                    response_data = {
                        'title': music.get('title', 'Unknown'),
                        'artist': music.get('artists', [{'name': 'Unknown'}])[0]['name'],
                        'album': music.get('album', {}).get('name', 'Unknown'),
                        'release_date': music.get('release_date', 'Unknown'),
                        'score': music.get('score', 0),
                        'external_metadata': music.get('external_metadata', {})
                    }

                    # Add duration if available
                    duration = music.get('duration_ms')
                    if duration:
                        response_data['duration'] = duration / 1000  # Convert to seconds

                    metrics.track_successful_music_recognition()
                    return response_data

        return None

    except Exception as e:
        logger.error(f"Error in music recognition: {e}")
        metrics.track_error(type(e).__name__)
        return None

async def get_music_info_from_video(video_path: str) -> Optional[Dict[str, Any]]:
    """Extract audio from video and recognize music"""
    try:
        # Extract audio to temporary file
        audio_path = await extract_audio_from_video(video_path)
        if not audio_path:
            return None

        try:
            # Recognize music
            result = await get_music_info(audio_path)
            return result
        finally:
            # Clean up temporary audio file
            if os.path.exists(audio_path):
                try:
                    os.remove(audio_path)
                except Exception as e:
                    logger.error(f"Error removing temporary audio file: {e}")

    except Exception as e:
        logger.error(f"Error in get_music_info_from_video: {e}")
        metrics.track_error(type(e).__name__)
        return None
