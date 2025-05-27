from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from telegram.error import TelegramError
from ..utils import extract_url, format_duration, format_size
from ..downloader import download_video_with_info, DownloadError
from ..services.monitoring import metrics
from ..services.video_service import VideoService
from ..config.config import config
import logging
import asyncio
import time

logger = logging.getLogger(__name__)
video_service = VideoService()

async def update_progress_message(message, text: str, every_n_seconds: int = 3):
    """Update progress message not more often than every N seconds"""
    current_time = time.time()
    if not hasattr(message, "_last_edit_time") or current_time - message._last_edit_time >= every_n_seconds:
        try:
            await message.edit_text(text)
            message._last_edit_time = current_time
        except TelegramError:
            pass

async def handle_media_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle messages containing media URLs"""
    if not update.effective_message or not update.effective_message.text:
        return
    
    url = extract_url(update.effective_message.text)
    if not url:
        platforms = (
            "▫️ YouTube\n"
            "▫️ Instagram\n"
            "▫️ TikTok\n"
            "▫️ Facebook\n"
            "▫️ Twitter\n"
            "▫️ Va boshqa ko'plab platformalar"
        )
        await update.effective_message.reply_text(
            f"❌ Video havolasi topilmadi. Iltimos, to'g'ri havola yuboring.\n\n"
            f"🌐 Qo'llab-quvvatlanadigan platformalar:\n{platforms}",
            parse_mode=ParseMode.HTML
        )
        return

    try:
        # Track download attempt
        metrics.track_download_attempt(url)
        
        status_message = await update.effective_message.reply_text(
            "🔍 Video tekshirilmoqda..."
        )

        # Start video processing
        process_start_time = time.time()
        result = await video_service.download_and_process_video(url)
        process_duration = time.time() - process_start_time
        
        if not result['success']:
            error_msg = result.get('error', "Noma'lum xatolik yuz berdi")
            error_help = (
                "Iltimos, quyidagilarni tekshiring:\n"
                "▫️ Video mavjudligi\n"
                "▫️ Video hajmi (max: 450MB)\n"
                "▫️ Video xususiy emasligini\n"
                "▫️ Platforma qo'llab-quvvatlanishini"
            )
            await status_message.edit_text(
                f"❌ {error_msg}\n\n{error_help}",
                parse_mode=ParseMode.HTML
            )
            return

        # Format video info
        title = result['title']
        duration = result.get('duration', 0)
        file_size = result['file_size']
        duration_text = format_duration(duration) if duration else "Noma'lum"
        size_text = format_size(file_size)
        process_text = f"⚡️ Qayta ishlash vaqti: {process_duration:.1f}s"

        info_text = (
            f"📹 *{title}*\n\n"
            f"⏱ Davomiyligi: {duration_text}\n"
            f"💾 Hajmi: {size_text}\n"
            f"{process_text}"
        )

        await update_progress_message(status_message, "📤 Video yuklanmoqda...")

        # Create inline keyboard
        keyboard = [
            [
                InlineKeyboardButton(
                    "🎵 Audio formatda yuklash",
                    callback_data=f"get_audio:{result['video_path']}"
                )
            ]
        ]

        # Add music recognition button if duration is reasonable
        if duration and duration <= 300:  # 5 minutes max for music recognition
            keyboard.append([
                InlineKeyboardButton(
                    "🎼 Musiqani topish",
                    callback_data=f"find_original:{result['video_path']}"
                )
            ])

        reply_markup = InlineKeyboardMarkup(keyboard)

        # Send the video
        try:
            with open(result['video_path'], 'rb') as video_file:
                await context.bot.send_video(
                    chat_id=update.effective_chat.id,
                    video=video_file,
                    caption=info_text,
                    reply_markup=reply_markup,
                    supports_streaming=True,
                    width=result.get('width'),
                    height=result.get('height'),
                    duration=int(duration) if duration else None,
                    parse_mode=ParseMode.MARKDOWN
                )
            
            # Track successful download
            metrics.track_successful_download(url)
            
        except TelegramError as e:
            if "File too large" in str(e):
                await status_message.edit_text(
                    "❌ Video hajmi juda katta (50MB dan oshmasligi kerak).\n"
                    "Videoni siqib ko'raman..."
                )
                
                # Try compressing the video
                compressed_result = await video_service.compress_and_send_video(
                    result['video_path'],
                    update.effective_chat.id,
                    context.bot,
                    info_text,
                    reply_markup
                )
                
                if not compressed_result:
                    await status_message.edit_text(
                        "❌ Video hajmi juda katta va uni siqib bo'lmadi.\n"
                        "Iltimos, kichikroq video tanlang."
                    )
                    return
            else:
                logger.error(f"Error sending video: {e}")
                await status_message.edit_text(
                    "❌ Video yuborishda xatolik yuz berdi.\n"
                    "Iltimos, keyinroq qayta urinib ko'ring."
                )
                return
        
        finally:
            # Clean up status message
            try:
                await status_message.delete()
            except:
                pass

    except asyncio.CancelledError:
        await status_message.edit_text("❌ Video yuklab olish bekor qilindi")
        
    except Exception as e:
        # Track error
        metrics.track_error(type(e).__name__)
        error_message = "Tizim xatoligi yuz berdi"
        
        if isinstance(e, DownloadError):
            if "private" in str(e).lower():
                error_message = "Bu video xususiy yoki uni yuklab olish cheklangan"
            elif "age" in str(e).lower():
                error_message = "Bu video yoshga oid cheklovga ega"
            elif "available" in str(e).lower():
                error_message = "Video mavjud emas yoki o'chirilgan"
            else:
                error_message = str(e)
        
        await status_message.edit_text(
            f"❌ Xatolik yuz berdi: {error_message}\n\n"
            "Iltimos, havolani tekshiring va qayta urinib ko'ring.",
            parse_mode=ParseMode.HTML
        )