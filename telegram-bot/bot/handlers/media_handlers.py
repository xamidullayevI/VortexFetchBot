import os
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from ..services.video_service import VideoService

URL_REGEX = re.compile(r"https?://[\w./?=&%-]+", re.IGNORECASE)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    urls = URL_REGEX.findall(text)
    if not urls:
        await update.message.reply_text("❗ Video havolasi topilmadi. Iltimos, to'g'ri havola yuboring.")
        return

    url = urls[0]
    msg = await update.message.reply_text("⏳ Fayl yuklanmoqda. Iltimos, kuting...")

    # Video servisidan foydalanish
    result = await VideoService.download_and_process_video(url)

    try:
        if not result['success']:
            await msg.edit_text(result['error'])
            return

        # Tugmalarni tayyorlash
        extra_buttons = [
            [InlineKeyboardButton(text="🎵 Audio yuklab olish", callback_data=f"get_audio:{result['unique_id']}")]
        ]
        if result.get('audio_url'):
            extra_buttons.append(
                [InlineKeyboardButton(text="🎵 Original qo'shiqni yuklash", url=result['audio_url'])]
            )
        reply_markup = InlineKeyboardMarkup(extra_buttons)

        # Agar tashqi hostingga yuklangan bo'lsa
        if result.get('is_external'):
            await msg.edit_text(
                f"🔗 Faylni bu havola orqali yuklab olishingiz mumkin: {result['download_url']}",
                reply_markup=reply_markup
            )
            return

        # Faylni yuborish
        video_path = result['video_path']
        ext = os.path.splitext(video_path)[1].lower()
        image_exts = ['.jpg', '.jpeg', '.png', '.webp', '.gif']

        with open(video_path, "rb") as file:
            if ext in image_exts:
                await update.message.reply_photo(
                    file,
                    caption=result['caption'],
                    reply_markup=reply_markup
                )
            else:
                if result.get('file_size', 0) > VideoService.MAX_TELEGRAM_SIZE:
                    await update.message.reply_document(
                        file,
                        caption=result['caption'],
                        reply_markup=reply_markup
                    )
                else:
                    await update.message.reply_video(
                        file,
                        caption=result['caption'],
                        reply_markup=reply_markup
                    )
        await msg.delete()

    except Exception as e:
        await msg.edit_text(f"❌ Xatolik yuz berdi: {str(e)}")
    finally:
        # Vaqtinchalik fayllarni tozalash
        if 'video_path' in result:
            VideoService.cleanup_files(result['video_path'])