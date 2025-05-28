"""Railway-optimized Telegram bot package"""
from . import handlers
from . import services
from . import config
from . import utils
from . import path_utils
from . import acrcloud_recognizer
from . import video_compress
from . import downloader

__version__ = "1.0.0"
__author__ = "Your Name"

# Export commonly used modules
__all__ = [
    'handlers',
    'services',
    'config',
    'utils',
    'path_utils',
    'acrcloud_recognizer',
    'video_compress',
    'downloader'
]

