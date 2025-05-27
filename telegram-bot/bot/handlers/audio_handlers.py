import os
import logging
from typing import Dict, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from ..acrcloud_recognizer import extract_audio_from_video, get_music_info
from ..utils import ensure_downloads_dir, cleanup_file, generate_temp_filename, format_duration
from ..services.rate_limiter import RateLimiter
from ..services.monitoring import metrics

logger = logging.getLogger(__name__)

# Audio rate limiter - alohida cheklovlar bilan
audio_rate_limiter = RateLimiter(
    max_requests=20,      # Har bir foydalanuvchi uchun minutiga 20 ta audio so'rov
    time_window=60,       # 1 daqiqa vaqt oralig'i
    max_file_size_mb=100  # Audio uchun maksimal fayl hajmi
)

async def extract_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Video fayldan audio ajratib olish"""
    if not update.callback_query:
        return
    
    query = update.callback_query
    video_path = query.data.replace("get_audio:", "")
    
    if not os.path.exists(video_path):
        await query.message.reply_text(
            "❌ Video fayli topilmadi. Iltimos, qayta yuklang."
        )
        await query.answer()
        return
    
    # Rate limitni tekshirish
    user_id = update.effective_user.id
    if not audio_rate_limiter.can_process(user_id):
        await query.edit_message_text(
            "⚠️ Siz juda ko'p audio so'rov yubordingiz. "
            "Iltimos, bir necha daqiqadan keyin qayta urinib ko'ring."
        )
        return
    
    try:
        await query.edit_message_reply_markup(reply_markup=None)
        status = await query.message.reply_text("⏳ Audio ajratilmoqda...")
        
        audio_path = extract_audio_from_video(video_path)
        
        if not audio_path or not os.path.exists(audio_path):
            await status.edit_text("❌ Audio ajratishda xatolik yuz berdi.")
            return
        
        # Fayl hajmini tekshirish
        audio_size = os.path.getsize(audio_path)
        if audio_size > 50 * 1024 * 1024:  # 50MB - Telegram limit
            await status.edit_text(
                "❌ Audio hajmi juda katta. Kichikroq video tanlang."
            )
            cleanup_file(audio_path)
            return
            
        # Audio faylni yuborish
        with open(audio_path, 'rb') as audio_file:
            await query.message.reply_audio(
                audio_file,
                caption="🎵 Musiqa formatida yuklab olindi",
                filename=os.path.basename(audio_path)
            )
        
        await status.delete()
        metrics.track_successful_audio_extraction()
        
    except Exception as e:
        logger.error(f"Audio ajratishda xatolik: {e}")
        await status.edit_text("❌ Audio ajratishda xatolik yuz berdi")
        # Xatolik bo'lsa rate limitni oshirmaslik
        audio_rate_limiter.user_limits[user_id].count -= 1
    finally:
        cleanup_file(audio_path)
        await query.answer()

async def find_original(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Original qo'shiqni aniqlash"""
    if not update.callback_query:
        return
    
    query = update.callback_query
    video_path = query.data.replace("find_original:", "")
    
    if not os.path.exists(video_path):
        await query.message.reply_text(
            "❌ Video fayli topilmadi. Iltimos, qayta yuklang."
        )
        await query.answer()
        return
    
    # Rate limitni tekshirish
    user_id = update.effective_user.id
    if not audio_rate_limiter.can_process(user_id):
        await query.edit_message_text(
            "⚠️ Siz juda ko'p qo'shiq aniqlash so'rovlarini yubordingiz. "
            "Iltimos, bir necha daqiqadan keyin qayta urinib ko'ring."
        )
        return
    
    try:
        await query.edit_message_reply_markup(reply_markup=None)
        status = await query.message.reply_text("🔍 Qo'shiq aniqlanmoqda...")
        
        audio_path = extract_audio_from_video(video_path)
        if not audio_path:
            await status.edit_text("❌ Audio ajratishda xatolik yuz berdi.")
            return
        
        result = get_music_info(audio_path)
        
        if result:
            # Natijani chiroyli formatda ko'rsatish
            message = (
                "*🎵 Qo'shiq haqida ma'lumot:*\n\n"
                f"*Nomi:* {result['title']}\n"
                f"*Ijrochi:* {result['artist']}\n"
                f"*Albom:* {result['album']}\n"
                f"*Chiqarilgan sana:* {result['release_date']}"
            )
            
            # Spotify yoki Apple Music havolalari bo'lsa qo'shish
            external_links = []
            if 'external_metadata' in result:
                metadata = result['external_metadata']
                if 'spotify' in metadata:
                    external_links.append(
                        InlineKeyboardButton(
                            "Spotify'da tinglash", 
                            url=f"https://open.spotify.com/track/{metadata['spotify']['track']['id']}"
                        )
                    )
                if 'apple_music' in metadata:
                    external_links.append(
                        InlineKeyboardButton(
                            "Apple Music'da tinglash",
                            url=metadata['apple_music']['url']
                        )
                    )
            
            keyboard = None
            if external_links:
                keyboard = InlineKeyboardMarkup([external_links])
            
            await status.edit_text(
                message,
                parse_mode='Markdown',
                reply_markup=keyboard
            )
            metrics.track_successful_music_recognition()
        else:
            await status.edit_text("❌ Kechirasiz, qo'shiq aniqlanmadi")
            
    except Exception as e:
        logger.error(f"Qo'shiqni aniqlashda xatolik: {e}")
        await status.edit_text("❌ Qo'shiqni aniqlashda xatolik yuz berdi")
        # Xatolik bo'lsa rate limitni oshirmaslik
        audio_rate_limiter.user_limits[user_id].count -= 1
    finally:
        cleanup_file(audio_path)
        await query.answer()