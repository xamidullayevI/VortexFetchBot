import os
import time
import hmac
import base64
import hashlib
import requests
import subprocess
import logging
import asyncio
import acrcloud.acrcloud_extr_tool
from dotenv import load_dotenv
from typing import Dict, Optional
from .services.monitoring import metrics

load_dotenv()

logger = logging.getLogger(__name__)

# ACRCloud credentials from environment variables
ACR_HOST = os.getenv('ACRCLOUD_HOST')
ACR_ACCESS_KEY = os.getenv('ACRCLOUD_ACCESS_KEY')
ACR_ACCESS_SECRET = os.getenv('ACRCLOUD_ACCESS_SECRET')

def extract_audio_from_video(video_path: str, audio_path: str = None) -> str:
    """
    Videodan audio (mp3) ajratib beradi. Agar audio_path berilmasa, avtomatik nom beradi.
    """
    if audio_path is None:
        audio_path = video_path + ".mp3"
    subprocess.run([
        'ffmpeg', '-y', '-i', video_path, '-vn', '-acodec', 'mp3', audio_path
    ], check=True)
    return audio_path


def get_music_info(audio_file):
    host = os.getenv("ACRCLOUD_HOST")
    access_key = os.getenv("ACRCLOUD_ACCESS_KEY")
    access_secret = os.getenv("ACRCLOUD_ACCESS_SECRET")

    if not all([host, access_key, access_secret]):
        return None

    http_method = "POST"
    http_uri = "/v1/identify"
    data_type = "audio"
    signature_version = "1"
    timestamp = time.time()

    string_to_sign = '\n'.join([
        http_method,
        http_uri,
        access_key,
        data_type,
        signature_version,
        str(timestamp)
    ])

    sign = base64.b64encode(
        hmac.new(access_secret.encode('ascii'), string_to_sign.encode('ascii'),
                 digestmod=hashlib.sha1).digest()
    ).decode('ascii')

    with open(audio_file, 'rb') as f:
        files = {'sample': f}
        data = {
            'access_key': access_key,
            'data_type': data_type,
            'signature_version': signature_version,
            'signature': sign,
            'timestamp': str(timestamp),
        }
        
        r = requests.post(f'https://{host}{http_uri}', files=files, data=data)
        r.raise_for_status()
        result = r.json()
        
        if 'status' in result and result['status']['code'] == 0 and 'metadata' in result and 'music' in result['metadata'] and result['metadata']['music']:
            music_info = result['metadata']['music'][0]
            return {
                'title': music_info.get('title', 'Unknown'),
                'artist': music_info.get('artists', [{'name': 'Unknown'}])[0]['name'],
                'album': music_info.get('album', {}).get('name', 'Unknown'),
                'release_date': music_info.get('release_date', 'Unknown'),
                'external_metadata': music_info.get('external_metadata', {})
            }
    return None


async def recognize_music(audio_path: str) -> Optional[Dict]:
    """
    Recognize music using ACRCloud service
    Returns dict with music info or None if not found/error
    """
    try:
        if not all([ACR_HOST, ACR_ACCESS_KEY, ACR_ACCESS_SECRET]):
            logger.error("ACRCloud credentials not configured")
            return None

        config = {
            'host': ACR_HOST,
            'access_key': ACR_ACCESS_KEY,
            'access_secret': ACR_ACCESS_SECRET,
            'debug': False,
            'timeout': 10
        }

        # Create recognizer
        client = acrcloud.acrcloud_extr_tool.ExtrTool(config)

        # Run recognition in executor to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            client.recognize_by_file,
            audio_path,
            0,  # Start time offset
            10   # Duration to analyze (seconds)
        )

        if not result or 'status' not in result or result['status']['code'] != 0:
            logger.info("No music found or error in recognition")
            return None

        music = result.get('metadata', {}).get('music', [])
        if not music:
            logger.info("No music metadata found")
            return None

        # Get first match
        track = music[0]
        
        # Format response
        response = {
            'title': track.get('title', 'Unknown Title'),
            'artist': track.get('artists', [{'name': 'Unknown Artist'}])[0]['name'],
            'album': track.get('album', {}).get('name', 'Unknown Album'),
            'release_date': track.get('release_date', 'Unknown Date'),
            'score': track.get('score', 0)
        }

        # Add streaming links if available
        external_metadata = track.get('external_metadata', {})
        
        if 'spotify' in external_metadata:
            spotify = external_metadata['spotify']
            response['spotify'] = f"https://open.spotify.com/track/{spotify['track']['id']}"
            
        if 'apple_music' in external_metadata:
            response['apple_music'] = external_metadata['apple_music'].get('url')

        metrics.track_successful_music_recognition()
        return response

    except Exception as e:
        logger.error(f"Error in music recognition: {e}")
        metrics.track_error(type(e).__name__)
        return None


def get_music_info_from_video(video_path: str) -> dict:
    """
    Videodan audio ajratib, ACRCloud orqali original musiqani aniqlaydi.
    """
    audio_path = extract_audio_from_video(video_path)
    result = get_music_info(audio_path)
    # Vaqtinchalik audio faylni tozalash
    if os.path.exists(audio_path):
        os.remove(audio_path)
    return result
