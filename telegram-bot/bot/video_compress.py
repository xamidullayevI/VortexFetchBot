import os
import logging
import subprocess
import json
import psutil
from typing import Optional

logger = logging.getLogger(__name__)

def compress_video(
    input_path: str,
    output_path: str,
    target_size_mb: int = 45,
    max_cpu_percent: int = 80
) -> Optional[str]:
    """
    Videoni siqish
    
    Args:
        input_path: Video fayl manzili
        output_path: Siqilgan video fayl manzili
        target_size_mb: Maqsad fayl hajmi (MB)
        max_cpu_percent: Maksimal CPU foydalanish foizi
    
    Returns:
        str: Siqilgan video fayl manzili yoki None
    """
    try:
        # Input video haqida ma'lumot olish
        probe = subprocess.run(
            ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', input_path],
            capture_output=True,
            text=True
        )
        
        if probe.returncode != 0:
            logger.error(f"FFprobe xatoligi: {probe.stderr}")
            return None
            
        video_info = json.loads(probe.stdout)
        
        # Video duration va bitrate'ni olish
        duration = float(video_info['format']['duration'])
        original_size = os.path.getsize(input_path)
        
        # Maqsad bitrate'ni hisoblash (bits/s)
        target_size = target_size_mb * 1024 * 1024 * 8  # MB to bits
        target_bitrate = int(target_size / duration)
        
        # CPU va xotira holati bo'yicha siqish parametrlarini moslashtirish
        cpu_percent = psutil.cpu_percent()
        memory = psutil.virtual_memory()
        
        # Agar resurslar tanqis bo'lsa, siqishni kuchaytirish
        if cpu_percent > max_cpu_percent or memory.percent > 80:
            target_bitrate = int(target_bitrate * 0.8)  # 20% ko'proq siqish
            threads = 1  # CPU yadrolari sonini kamaytirish
        else:
            threads = min(os.cpu_count() or 2, 2)  # Railway uchun max 2 yadro
        
        # FFmpeg buyrug'ini tayyorlash
        command = [
            'ffmpeg',
            '-i', input_path,
            '-c:v', 'libx264',
            '-preset', 'medium',  # Railway uchun muvozanatli preset
            '-b:v', f'{target_bitrate}',
            '-maxrate', f'{int(target_bitrate * 1.5)}',  # Maksimal bitrate
            '-bufsize', f'{int(target_bitrate * 2)}',    # Buffer hajmi
            '-threads', str(threads),
            '-movflags', '+faststart',  # Tez boshlash uchun
            '-y',  # Mavjud faylni qayta yozish
            output_path
        ]
        
        # Video siqish
        result = subprocess.run(
            command,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            logger.error(f"FFmpeg xatoligi: {result.stderr}")
            return None
            
        # Natijani tekshirish
        if os.path.exists(output_path):
            new_size = os.path.getsize(output_path)
            compression_ratio = (original_size - new_size) / original_size * 100
            logger.info(f"Video siqildi: {compression_ratio:.1f}% hajm kamaydi")
            return output_path
            
    except Exception as e:
        logger.error(f"Video siqishda xatolik: {e}")
        if os.path.exists(output_path):
            try:
                os.remove(output_path)
            except:
                pass
    
    return None
