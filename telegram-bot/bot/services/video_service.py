import os
import uuid
import requests
from typing import Dict, Optional, Tuple
from ..downloader import download_video, DownloadError
from ..utils import universal_download
from ..video_compress import compress_video

class VideoService:
    DOWNLOAD_DIR = "downloads"
    MAX_TELEGRAM_SIZE = 2 * 1024 * 1024 * 1024  # 2GB

    @staticmethod
    def get_network_name(url: str) -> str:
        domains = {
            'instagram.com': 'Instagram',
            'youtube.com': 'YouTube',
            'youtu.be': 'YouTube',
            'tiktok.com': 'TikTok',
            'facebook.com': 'Facebook',
            'twitter.com': 'Twitter',
            'x.com': 'Twitter',
            'vk.com': 'VK',
            'reddit.com': 'Reddit',
            'vimeo.com': 'Vimeo',
            'dailymotion.com': 'Dailymotion',
            'likee.video': 'Likee',
            'pinterest.com': 'Pinterest'
        }
        return next((name for domain, name in domains.items() if domain in url), 'Video')

    @classmethod
    async def download_and_process_video(cls, url: str) -> Dict:
        """Video yuklab olish va qayta ishlash uchun asosiy metod"""
        try:
            unique_id = str(uuid.uuid4())
            video_path = os.path.join(cls.DOWNLOAD_DIR, f"video_{unique_id}.mp4")
            compressed_path = os.path.join(cls.DOWNLOAD_DIR, f"video_{unique_id}_compressed.mp4")

            # Universal yuklab olish
            result = universal_download(url)
            if not result or result.get('error'):
                error_message = result.get('error_message', '❗ Media topilmadi yoki yuklab bo\'lmadi.') if result else '❗ Media topilmadi yoki yuklab bo\'lmadi.'
                return {'success': False, 'error': error_message}

            video_path = result.get('download_url')
            video_info = result.get('info')
            if not video_path:
                return {'success': False, 'error': '❗ Media topilmadi yoki yuklab bo\'lmadi. (download_url yo\'q)'}

            try:
                file_size = os.path.getsize(video_path)
            except Exception as e:
                return {'success': False, 'error': f"❌ Fayl topilmadi yoki o'qib bo'lmadi: {str(e)}"}

            network_name = cls.get_network_name(url)
            video_title = video_info.get('title') if video_info else os.path.splitext(os.path.basename(video_path))[0]

            # Fayl hajmi tekshiruvi
            if file_size > cls.MAX_TELEGRAM_SIZE:
                compressed_result = await cls.handle_large_file(video_path, compressed_path)
                if not compressed_result['success']:
                    return compressed_result
                video_path = compressed_path

            return {
                'success': True,
                'video_path': video_path,
                'caption': f"{network_name}: {video_title}",
                'file_size': file_size,
                'unique_id': unique_id,
                'audio_url': result.get('audio_url'),
                'media_type': result.get('media_type'),
                'thumb': result.get('thumb'),
                'info': result.get('info')
            }

        except Exception as e:
            return {'success': False, 'error': f"❌ Xatolik yuz berdi: {str(e)}"}

    @classmethod
    async def handle_large_file(cls, video_path: str, compressed_path: str) -> Dict:
        """Katta hajmli fayllarni qayta ishlash"""
        try:
            compress_video(video_path, compressed_path, target_size_mb=2000)
            compressed_size = os.path.getsize(compressed_path)

            if compressed_size > cls.MAX_TELEGRAM_SIZE:
                return await cls.upload_to_external_host(compressed_path)

            return {'success': True, 'video_path': compressed_path}

        except Exception as e:
            return {'success': False, 'error': f"❌ Videoni siqishda xatolik: {str(e)}"}

    @staticmethod
    async def upload_to_external_host(file_path: str) -> Dict:
        """Faylni tashqi hostingga yuklash"""
        try:
            with open(file_path, 'rb') as f:
                resp = requests.put('https://transfer.sh/video.mp4', data=f)
            if resp.status_code == 200:
                return {
                    'success': True,
                    'is_external': True,
                    'download_url': resp.text.strip()
                }
            return {'success': False, 'error': "❌ Faylni tashqi hostingga yuklab bo'lmadi."}
        except Exception as e:
            return {'success': False, 'error': f"❌ Faylni tashqi hostingga yuklashda xatolik: {str(e)}"}

    @staticmethod
    def cleanup_files(*file_paths: str) -> None:
        """Vaqtinchalik fayllarni tozalash"""
        for file_path in file_paths:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception:
                pass