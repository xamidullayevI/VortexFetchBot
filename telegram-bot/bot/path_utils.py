"""Path utility functions for the bot"""
import os
import uuid
from pathlib import Path
from .config.config import config

def generate_temp_filename(prefix: str = "", suffix: str = "") -> str:
    """Generate temporary filename in downloads directory"""
    filename = f"{prefix}{uuid.uuid4().hex}{suffix}"
    return str(Path(config.downloads_dir) / filename)