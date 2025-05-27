from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from ..utils import extract_url
from ..downloader import download_video
from ..services.monitoring import metrics

async def handle_media_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle messages containing media URLs"""
    if not update.effective_message or not update.effective_message.text:
        return
    
    url = extract_url(update.effective_message.text)
    if not url:
        await update.effective_message.reply_text(
            "❌ Video havolasi topilmadi. Iltimos, to'g'ri havola yuboring."
        )
        return

    try:
        # Track download attempt
        metrics.track_download_attempt(url)
        
        status_message = await update.effective_message.reply_text(
            "⏳ Video yuklab olinmoqda..."
        )

        video_info = await download_video(url)
        
        if not video_info or not video_info.get('file_path'):
            await status_message.edit_text(
                "❌ Videoni yuklab olishda xatolik yuz berdi. Iltimos, keyinroq urinib ko'ring."
            )
            return

        # Create inline keyboard for additional options
        keyboard = [
            [
                InlineKeyboardButton(
                    "🎵 Audio formatda yuklash",
                    callback_data=f"get_audio:{video_info['file_path']}"
                )
            ],
            [
                InlineKeyboardButton(
                    "🎧 Musiqani topish",
                    callback_data=f"find_original:{video_info['file_path']}"
                )
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Send the video
        with open(video_info['file_path'], 'rb') as video_file:
            await context.bot.send_video(
                chat_id=update.effective_chat.id,
                video=video_file,
                caption=f"📹 {video_info.get('title', 'Video')}",
                reply_markup=reply_markup
            )
        
        # Track successful download
        metrics.track_successful_download(url)
        
        await status_message.delete()

    except Exception as e:
        # Track error
        metrics.track_error(type(e).__name__)
        
        await status_message.edit_text(
            f"❌ Xatolik yuz berdi: {str(e)}\n\n"
            "Iltimos, havolani tekshiring va qayta urinib ko'ring."
        )