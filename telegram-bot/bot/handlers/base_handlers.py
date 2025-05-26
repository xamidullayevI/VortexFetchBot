from telegram import Update
from telegram.ext import ContextTypes

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 VortexFetchBot'ga xush kelibsiz!\nYouTube, Instagram, TikTok yoki boshqa ijtimoiy tarmoqlardan video havolasini yuboring, men sizga videoni yuklab beraman."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "ℹ️ *VortexFetchBot'dan foydalanish:*\n1. Istalgan ijtimoiy tarmoqdan video havolasini yuboring.\n2. Men videoni yuklab olgunimcha biroz kuting.\n3. Videodan audio ajratib olish uchun audio tugmasidan foydalaning.\n\n_Agar muammo yuzaga kelsa, havola to'g'riligini va video ochiq ekanligini tekshiring._",
        parse_mode="Markdown"
    )