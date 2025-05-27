import os
import logging
from typing import Dict, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from ..acrcloud_recognizer import extract_audio_from_video, get_music_info
from ..utils import ensure_downloads_dir, cleanup_file, generate_temp_filename, format_duration
from ..services.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)

# Audio rate limiter - alohida cheklovlar bilan
audio_rate_limiter = RateLimiter(
    max_requests=20,      # Har bir foydalanuvchi uchun minutiga 20 ta audio so'rov
    time_window=60,       # 1 daqiqa vaqt oralig'i
    max_file_size_mb=100  # Audio uchun maksimal fayl hajmi
)

async def extract_audio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Video fayldan audio ajratib olish"""
    query = update.callback_query
    await query.answer()
    
    # Rate limitni tekshirish
    user_id = update.effective_user.id
    if not audio_rate_limiter.can_process(user_id):
        await query.edit_message_text(
            "⚠️ Siz juda ko'p audio so'rov yubordingiz. "
            "Iltimos, bir necha daqiqadan keyin qayta urinib ko'ring."
        )
        return
    
    try:
        # video_id ni olish
        video_id = query.data.split(':')[1]
        video_path = os.path.join(ensure_downloads_dir(), f"video_{video_id}")
        
        if not os.path.exists(video_path):
            await query.edit_message_text("❌ Kechirasiz, video fayl topilmadi. Qaytadan urinib ko'ring.")
            return

        # Fayl hajmini tekshirish
        video_size = os.path.getsize(video_path)
        if video_size > 100 * 1024 * 1024:  # 100MB
            await query.edit_message_text("❌ Video hajmi juda katta. Kichikroq video tanlang.")
            return
            
        status_message = await query.message.reply_text("⏳ Audio ajratilmoqda...")
        
        try:
            # Audio ajratish
            audio_path = extract_audio_from_video(video_path)
            
            # Audio hajmini tekshirish
            audio_size = os.path.getsize(audio_path)
            if audio_size > 50 * 1024 * 1024:  # 50MB - Telegram limit
                await status_message.edit_text(
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
            
            await status_message.delete()
            
        except Exception as e:
            logger.error(f"Audio ajratishda xatolik: {e}")
            await status_message.edit_text("❌ Audio ajratishda xatolik yuz berdi")
            # Xatolik bo'lsa rate limitni oshirmaslik
            audio_rate_limiter.user_limits[user_id].count -= 1
        finally:
            cleanup_file(audio_path)
            
    except Exception as e:
        logger.error(f"Umumiy xatolik: {e}")
        await query.message.reply_text("❌ Kutilmagan xatolik yuz berdi")
        audio_rate_limiter.user_limits[user_id].count -= 1

async def find_original(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Original qo'shiqni aniqlash"""
    query = update.callback_query
    await query.answer()
    
    # Rate limitni tekshirish
    user_id = update.effective_user.id
    if not audio_rate_limiter.can_process(user_id):
        await query.edit_message_text(
            "⚠️ Siz juda ko'p qo'shiq aniqlash so'rovlarini yubordingiz. "
            "Iltimos, bir necha daqiqadan keyin qayta urinib ko'ring."
        )
        return
    
    try:
        video_id = query.data.split(':')[1]
        video_path = os.path.join(ensure_downloads_dir(), f"video_{video_id}")
        
        if not os.path.exists(video_path):
            await query.edit_message_text("❌ Kechirasiz, video fayl topilmadi")
            return
            
        status_message = await query.message.reply_text("🔍 Qo'shiq aniqlanmoqda...")
        
        try:
            # Vaqtinchalik audio fayl yaratish
            temp_audio = generate_temp_filename(prefix="search", suffix=".mp3")
            extract_audio_from_video(video_path, temp_audio)
            
            # ACRCloud orqali qo'shiqni aniqlash
            result = get_music_info(temp_audio)
            
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
                
                await status_message.edit_text(
                    message,
                    parse_mode='Markdown',
                    reply_markup=keyboard
                )
            else:
                await status_message.edit_text("❌ Kechirasiz, qo'shiq aniqlanmadi")
                
        except Exception as e:
            logger.error(f"Qo'shiqni aniqlashda xatolik: {e}")
            await status_message.edit_text("❌ Qo'shiqni aniqlashda xatolik yuz berdi")
            # Xatolik bo'lsa rate limitni oshirmaslik
            audio_rate_limiter.user_limits[user_id].count -= 1
        finally:
            cleanup_file(temp_audio)
            
    except Exception as e:
        logger.error(f"Umumiy xatolik: {e}")
        await query.message.reply_text("❌ Kutilmagan xatolik yuz berdi")
        audio_rate_limiter.user_limits[user_id].count -= 1