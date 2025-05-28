import os
import logging
from typing import Dict, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from ..acrcloud_recognizer import extract_audio_from_video, get_music_info
from ..utils import cleanup_file, format_duration
from ..path_utils import generate_temp_filename
from ..services.rate_limiters import audio_rate_limiter
from ..services.monitoring import metrics
from ..config.config import config

logger = logging.getLogger(__name__)

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
    file_size = os.path.getsize(video_path)
    
    if not audio_rate_limiter.can_process(user_id, file_size):
        await query.answer(
            "⚠️ Siz juda ko'p audio so'rov yubordingiz. "
            "Iltimos, bir necha daqiqadan keyin qayta urinib ko'ring.",
            show_alert=True
        )
        return
    
    try:
        await query.edit_message_reply_markup(reply_markup=None)
        status = await query.message.reply_text("⏳ Audio ajratilmoqda...")
        
        # Generate unique output path
        audio_path = generate_temp_filename(prefix="audio_", suffix=".mp3")
        audio_path = await extract_audio_from_video(video_path, audio_path)
        
        if not audio_path or not os.path.exists(audio_path):
            await status.edit_text(
                "❌ Audio ajratishda xatolik yuz berdi.\n"
                "Video formati qo'llab-quvvatlanmasligi mumkin."
            )
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
        try:
            with open(audio_path, 'rb') as audio_file:
                original_filename = os.path.basename(video_path)
                audio_filename = f"{os.path.splitext(original_filename)[0]}.mp3"
                
                await query.message.reply_audio(
                    audio=audio_file,
                    caption="🎵 Musiqa formatida yuklab olindi",
                    filename=audio_filename,
                    duration=None  # FFprobe orqali aniqlanadi
                )
            
            await status.delete()
            metrics.track_successful_audio_extraction()
            
        except Exception as e:
            logger.error(f"Audio yuborishda xatolik: {e}")
            await status.edit_text(
                "❌ Audio yuborishda xatolik yuz berdi.\n"
                "Fayl hajmi juda katta bo'lishi mumkin."
            )
        
    except Exception as e:
        logger.error(f"Audio ajratishda xatolik: {e}")
        await status.edit_text(
            "❌ Audio ajratishda xatolik yuz berdi.\n"
            "Iltimos, boshqa video bilan urinib ko'ring."
        )
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
        await query.answer(
            "⚠️ Siz juda ko'p qo'shiq aniqlash so'rovlarini yubordingiz. "
            "Iltimos, bir necha daqiqadan keyin qayta urinib ko'ring.",
            show_alert=True
        )
        return
    
    try:
        await query.edit_message_reply_markup(reply_markup=None)
        status = await query.message.reply_text(
            "🔍 Qo'shiq aniqlanmoqda...\n"
            "Bu bir necha soniya vaqt olishi mumkin."
        )
        
        # Vaqtinchalik audio fayl
        audio_path = generate_temp_filename(prefix="music_", suffix=".mp3")
        audio_path = await extract_audio_from_video(video_path, audio_path)
        
        if not audio_path:
            await status.edit_text(
                "❌ Audio ajratishda xatolik yuz berdi.\n"
                "Video formati qo'llab-quvvatlanmasligi mumkin."
            )
            return
        
        result = await get_music_info(audio_path)
        
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
            await status.edit_text(
                "❌ Kechirasiz, qo'shiq aniqlanmadi.\n"
                "Video musiqa emasligi yoki sifati pastligi sabab bo'lishi mumkin."
            )
            
    except Exception as e:
        logger.error(f"Qo'shiqni aniqlashda xatolik: {e}")
        await status.edit_text(
            "❌ Qo'shiqni aniqlashda xatolik yuz berdi.\n"
            "Iltimos, keyinroq qayta urinib ko'ring."
        )
        # Xatolik bo'lsa rate limitni oshirmaslik
        audio_rate_limiter.user_limits[user_id].count -= 1
        
    finally:
        cleanup_file(audio_path)
        await query.answer()