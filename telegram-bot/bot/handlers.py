from telegram import Update
from telegram.ext import ContextTypes
from bot.downloader import download_video, DownloadError
import os
import re

DOWNLOAD_DIR = "downloads"

URL_REGEX = re.compile(r"https?://[\w./?=&%-]+", re.IGNORECASE)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to VortexFetchBot!\nJust send me a video link from YouTube, Instagram, TikTok, or other social platforms, and I will fetch the video for you."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "ℹ️ *How to use VortexFetchBot:*\n1. Send a video link from any major social network.\n2. Wait a moment while I fetch and send you the video.\n\n_If you encounter any issues, make sure the link is correct and the video is public._",
        parse_mode="Markdown"
    )

import requests

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    urls = URL_REGEX.findall(text)
    if not urls:
        await update.message.reply_text(
            "❗ No valid video link detected. Please send a correct video URL."
        )
        return
    url = urls[0]
    msg = await update.message.reply_text("⏳ Fetching your video, please wait...")
    try:
        last_percent = {'value': 0}
        async def update_progress(percent):
            try:
                await msg.edit_text(f"⏳ Video yuklanmoqda: {percent}%")
            except Exception:
                pass
        def progress_hook(d):
            if d['status'] == 'downloading':
                percent_str = d.get('_percent_str', '0.0%').replace('%','').strip()
                try:
                    percent = int(float(percent_str))
                except ValueError:
                    percent = 0
                if percent >= last_percent['value'] + 5:
                    # asyncio.create_task bilan chaqirish uchun
                    import asyncio
                    asyncio.create_task(update_progress(percent))
                    last_percent['value'] = percent
        video_path = download_video(url, DOWNLOAD_DIR, progress_callback=progress_hook)
        file_size = os.path.getsize(video_path)
        max_telegram_size = 50 * 1024 * 1024  # 50 MB
        if file_size <= max_telegram_size:
            with open(video_path, "rb") as video_file:
                await update.message.reply_video(video_file)
            os.remove(video_path)
            await msg.delete()
        else:
            # Faylni transfer.sh ga yuklash
            with open(video_path, 'rb') as f:
                response = requests.put(
                    f'https://transfer.sh/{os.path.basename(video_path)}',
                    data=f
                )
            os.remove(video_path)
            if response.status_code == 200:
                download_link = response.text.strip()
                await msg.edit_text(
                    f"📥 Video fayli 50 MB dan katta bo'lgani uchun Telegram orqali yuborilmadi.\n\nYuklab olish uchun link: {download_link}"
                )
            else:
                await msg.edit_text("❌ Video yuklashda xatolik yuz berdi (transfer.sh)")
    except DownloadError as e:
        await msg.edit_text(f"❌ Error while downloading: {e}")
    except Exception as e:
        await msg.edit_text(f"❌ An unexpected error occurred: {e}")
