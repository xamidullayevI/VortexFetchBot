from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from bot.downloader import download_video, DownloadError, download_video_with_info
from bot.acrcloud_recognizer import get_music_info
from bot.utils import universal_download
from bot.video_compress import compress_video
from bs4 import BeautifulSoup
from io import BytesIO
from pathlib import Path
import os
import re
import subprocess
import requests
import uuid

DOWNLOAD_DIR = "downloads"

URL_REGEX = re.compile(r"https?://[\w./?=&%-]+", re.IGNORECASE)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Hello to VortexFetchBot!\nJust send me a video link from YouTube, Instagram, TikTok, or other social platforms, and I will fetch the video for you."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "ℹ️ *How to use VortexFetchBot:*\n1. Send a video link from any major social network.\n2. Wait a moment while I fetch and send you the video.\n3. Use the audio button to extract audio from videos.\n\n_If you encounter any issues, make sure the link is correct and the video is public._",
        parse_mode="Markdown"
    )

async def extract_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if not query.data.startswith("get_audio:"):
        return
    
    unique_id = query.data.split(":")[1]
    await query.message.reply_text("⏳ Audio ajratilmoqda, iltimos kuting...")
    
    try:
        video_path = os.path.join(DOWNLOAD_DIR, f"video_{unique_id}.mp4")
        audio_path = os.path.join(DOWNLOAD_DIR, f"audio_{unique_id}.mp3")
        
        if not os.path.exists(video_path):
            part_path = video_path + ".part"
            if os.path.exists(part_path):
                await query.message.reply_text("❗ Video hali to'liq yuklab olinmagan. Iltimos, biroz kuting.")
                return
                
            original_message = query.message
            if original_message.video:
                video_file = await original_message.video.get_file()
                await video_file.download_to_drive(video_path)
            else:
                await query.message.reply_text("❌ Video topilmadi.")
                return
        
        try:
            subprocess.run(
                ["ffmpeg", "-i", video_path, "-q:a", "0", "-map", "a", audio_path],
                check=True
            )
            
            # ACRCloud orqali qo'shiqni aniqlash
            music_info = get_music_info(audio_path)
            
            if music_info:
                caption = (
                    f"🎵 Original qo'shiq:\n"
                    f"📌 Nomi: {music_info['title']}\n"
                    f"👤 Ijrochi: {music_info['artist']}\n"
                    f"💿 Albom: {music_info['album']}\n"
                    f"📅 Chiqarilgan sana: {music_info['release_date']}"
                )
            else:
                caption = "🎵 Videoning audio versiyasi"
            
            with open(audio_path, "rb") as audio_file:
                await query.message.reply_audio(
                    audio_file,
                    title=f"Audio - {Path(video_path).stem}",
                    caption=caption,
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🎵 Original qo'shiqni topish", callback_data=f"find_original:{unique_id}")
                    ]]) if music_info else None
                )
        except Exception as e:
            await query.message.reply_text(f"❌ Xatolik yuz berdi: {e}")
    finally:
        for f in [video_path, audio_path]:
            try:
                if os.path.exists(f):
                    os.remove(f)
            except Exception:
                pass

async def find_original(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if not query.data.startswith("find_original:"):
        return
    
    unique_id = query.data.split(":")[1]
    audio_path = os.path.join(DOWNLOAD_DIR, f"audio_{unique_id}.mp3")
    
    if not os.path.exists(audio_path):
        await query.message.reply_text("❌ Audio fayl topilmadi.")
        return
    
    try:
        music_info = get_music_info(audio_path)
        if not music_info:
            await query.message.reply_text("❌ Qo'shiq haqida ma'lumot topilmadi.")
            return
            
        external_metadata = music_info.get('external_metadata', {})
        spotify = external_metadata.get('spotify', {})
        youtube = external_metadata.get('youtube', {})
        deezer = external_metadata.get('deezer', {})
        
        links = []
        if spotify:
            track_id = spotify.get('track', {}).get('id')
            if track_id:
                links.append(InlineKeyboardButton("🎵 Spotify", url=f"https://open.spotify.com/track/{track_id}"))
        
        if youtube:
            vid = youtube.get('vid')
            if vid:
                links.append(InlineKeyboardButton("🎥 YouTube", url=f"https://www.youtube.com/watch?v={vid}"))
        
        if deezer:
            track_id = deezer.get('track', {}).get('id')
            if track_id:
                links.append(InlineKeyboardButton("🎵 Deezer", url=f"https://www.deezer.com/track/{track_id}"))
        
        if links:
            await query.message.reply_text(
                "🔍 Original qo'shiqni tinglash uchun platformani tanlang:",
                reply_markup=InlineKeyboardMarkup([links])
            )
        else:
            await query.message.reply_text("❌ Qo'shiqning original versiyasi uchun havolalar topilmadi.")
            
    except Exception as e:
        await query.message.reply_text(f"❌ Xatolik yuz berdi: {e}")
    finally:
        try:
            if os.path.exists(audio_path):
                os.remove(audio_path)
        except Exception:
            pass

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    urls = URL_REGEX.findall(text)
    if not urls:
        await update.message.reply_text("❗ No valid video link detected. Please send a correct video URL.")
        return

    url = urls[0]
    msg = await update.message.reply_text("⏳ Fayl yuklanmoqda. Iltimos, kuting...")

    try:
        unique_id = str(uuid.uuid4())
        video_path = os.path.join(DOWNLOAD_DIR, f"video_{unique_id}.mp4")
        compressed_path = os.path.join(DOWNLOAD_DIR, f"video_{unique_id}_compressed.mp4")

        result = universal_download(url)
        if not result or result.get('error'):
            error_message = result.get('error_message', '❗ Media topilmadi yoki yuklab bo‘lmadi.') if result else '❗ Media topilmadi yoki yuklab bo‘lmadi.'
            await msg.edit_text(error_message)
            return

        download_url = result.get('download_url')
        if not download_url:
            await msg.edit_text('❗ Media topilmadi yoki yuklab bo‘lmadi. (download_url yo‘q)')
            return

        audio_url = result.get('audio_url')
        media_type = result.get('media_type')
        thumb = result.get('thumb')
        info = result.get('info')
        method = result.get('method')

        print(f"[LOG] Yuklash usuli: {method}, audio_url: {audio_url}, media_type: {media_type}")

        # Tugmalar
        extra_buttons = [
            [InlineKeyboardButton(text="🎵 Audio yuklab olish", callback_data=f"get_audio:{unique_id}")]
        ]
        if audio_url:
            extra_buttons.append(
                [InlineKeyboardButton(text="🎵 Orginal qo‘shiqni yuklash", url=audio_url)]
            )

        video_path, video_info = download_video(url, DOWNLOAD_DIR)

        file_size = os.path.getsize(video_path)
        max_telegram_size = 2 * 1024 * 1024 * 1024  # 2GB

        def get_network_name(url):
            domains = {
                'instagram.com': 'Instagram',
                'youtube.com': 'YouTube',
                'youtu.be': 'YouTube',
                'tiktok.com': 'TikTok',
                'facebook.com': 'Facebook',
                'twitter.com': 'Twitter',
                'x.com': 'Twitter',
                'vk.com': 'VK',
                'reddit.com': 'Reddit',
                'vimeo.com': 'Vimeo',
                'dailymotion.com': 'Dailymotion',
                'likee.video': 'Likee',
                'pinterest.com': 'Pinterest'
            }
            for domain, name in domains.items():
                if domain in url:
                    return name
            return 'Video'

        network_name = get_network_name(url)
        video_title = video_info.get('title') or os.path.splitext(os.path.basename(video_path))[0]
        caption = f"{network_name}: {video_title}"
        ext = os.path.splitext(video_path)[1].lower()
        image_exts = ['.jpg', '.jpeg', '.png', '.webp', '.gif']
        reply_markup = InlineKeyboardMarkup(extra_buttons)

        if file_size <= max_telegram_size:
            with open(video_path, "rb") as file:
                if ext in image_exts:
                    await update.message.reply_photo(file, caption=caption, reply_markup=reply_markup)
                else:
                    await update.message.reply_video(file, caption=caption, reply_markup=reply_markup)
            await msg.delete()
        else:
            await msg.edit_text("⚠️ Fayl 2 GB dan katta! Video siqilmoqda, kuting...")
            from bot.video_compress import compress_video
            compress_video(video_path, compressed_path, target_size_mb=2000)

            compressed_size = os.path.getsize(compressed_path)
            if compressed_size > max_telegram_size:
                await msg.edit_text("❌ Siqilgan video ham 2 GB dan katta. Telegram orqali yuborib bo‘lmaydi. Faylni tashqi hostingga yuklab, link yuborilmoqda...")
                try:
                    with open(compressed_path, 'rb') as f:
                        resp = requests.put('https://transfer.sh/video.mp4', data=f)
                    if resp.status_code == 200:
                        await msg.edit_text(f"🔗 Faylni bu link orqali yuklab olishingiz mumkin: {resp.text.strip()}")
                    else:
                        await msg.edit_text("❌ Faylni tashqi hostingga yuklab bo‘lmadi. Iltimos, kichikroq video yuboring.")
                except Exception as e:
                    await msg.edit_text(f"❌ Faylni tashqi hostingga yuklashda xatolik: {e}")
                return

            await msg.edit_text("⏳ Video siqildi. Endi Telegramga yuklanmoqda...")
            with open(compressed_path, "rb") as file:
                await update.message.reply_document(file, caption=caption, reply_markup=reply_markup)
            await msg.delete()

    except Exception as e:
        await msg.edit_text(f"❌ Xatolik yuz berdi: {e}")
