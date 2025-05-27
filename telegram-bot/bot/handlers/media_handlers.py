import os
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from ..services.video_service import VideoService
from ..services.rate_limiter import RateLimiter
from ..downloader import DownloadError

URL_REGEX = re.compile(r"https?://[\w./?=&%-]+", re.IGNORECASE)

# Rate limiter yaratish
rate_limiter = RateLimiter(
    max_requests=30,     # Har bir foydalanuvchi uchun minutiga 30 ta so'rov
    time_window=60,      # 1 daqiqa vaqt oralig'i
    max_file_size_mb=450 # Railway uchun maksimal fayl hajmi
)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    urls = URL_REGEX.findall(text)
    if not urls:
        await update.message.reply_text("❗ Video havolasi topilmadi. Iltimos, to'g'ri havola yuboring.")
        return

    # Rate limitni tekshirish
    user_id = update.effective_user.id
    if not rate_limiter.can_process(user_id):
        await update.message.reply_text(
            "⚠️ Siz juda ko'p so'rov yubordingiz. "
            "Iltimos, bir necha daqiqadan keyin qayta urinib ko'ring."
        )
        return

    url = urls[0]
    msg = await update.message.reply_text("⏳ Fayl yuklanmoqda. Iltimos, kuting...")

    try:
        result = await VideoService().download_and_process_video(url)

        if not result['success']:
            await msg.edit_text(result['error'])
            return

        buttons = [
            [InlineKeyboardButton("🎵 Audio yuklab olish", callback_data=f"get_audio:{result['unique_id']}")]
        ]

        if result.get('audio_url'):
            buttons.append([InlineKeyboardButton("🎵 Original qo'shiqni topish", callback_data=f"find_original:{result['unique_id']}")])

        # Video yuborish
        file_path = result['video_path']
        with open(file_path, 'rb') as file:
            if result.get('is_external'):
                await msg.edit_text(
                    f"🔗 Video hajmi katta. Yuklab olish havolasi: {result['download_url']}",
                    reply_markup=InlineKeyboardMarkup(buttons)
                )
            else:
                file_size = os.path.getsize(file_path)
                if file_size > VideoService.MAX_TELEGRAM_SIZE:
                    await update.message.reply_document(
                        file,
                        caption=result['caption'],
                        filename=os.path.basename(file_path),
                        reply_markup=InlineKeyboardMarkup(buttons)
                    )
                else:
                    await update.message.reply_video(
                        file,
                        caption=result['caption'],
                        reply_markup=InlineKeyboardMarkup(buttons)
                    )
                await msg.delete()
                
    except DownloadError as e:
        await msg.edit_text(f"❌ Videoni yuklab olishda xatolik: {str(e)}")
        # Xatolik bo'lsa rate limitni oshirmaslik
        rate_limiter.user_limits[user_id].count -= 1
    except Exception as e:
        await msg.edit_text(f"❌ Xatolik yuz berdi: {str(e)}")
        # Xatolik bo'lsa rate limitni oshirmaslik
        rate_limiter.user_limits[user_id].count -= 1
    finally:
        VideoService.cleanup_files(result.get('video_path', ''))