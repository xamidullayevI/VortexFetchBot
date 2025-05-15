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
        video_path = download_video(url, DOWNLOAD_DIR)
        with open(video_path, "rb") as video_file:
            await update.message.reply_video(video_file)
        os.remove(video_path)
        await msg.delete()
    except DownloadError as e:
        await msg.edit_text(f"❌ Error while downloading: {e}")
    except Exception as e:
        await msg.edit_text("❌ An unexpected error occurred.")
