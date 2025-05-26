import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from pathlib import Path
from ..acrcloud_recognizer import get_music_info
import subprocess

DOWNLOAD_DIR = "downloads"

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
            # Yuqori sifatli audio extract (44100 Hz, 192k bitrate)
            subprocess.run([
                "ffmpeg", "-i", video_path, "-vn", "-ar", "44100", "-ab", "192k", "-acodec", "mp3", audio_path
            ], check=True)

            music_info = get_music_info(audio_path)
            print("ACRCLOUD RESULT:", music_info)  # LOG natija

            if music_info:
                caption = (
                    f"🎵 Original qo'shiq:\n"
                    f"📌 Nomi: {music_info['title']}\n"
                    f"👤 Ijrochi: {music_info['artist']}\n"
                    f"💿 Albom: {music_info['album']}\n"
                    f"📅 Chiqarilgan sana: {music_info['release_date']}"
                )
            else:
                caption = "🎵 Videoning audio versiyasi\n❗ Original qo'shiq aniqlanmadi."

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