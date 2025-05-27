from telegram import Update
from telegram.ext import ContextTypes

from ..services.monitoring import metrics

HELP_MESSAGE = """🤖 *Video Yuklovchi Bot*

*Asosiy buyruqlar:*
/start - Botni ishga tushirish
/help - Yordam xabarini ko'rsatish
/stats - Bot statistikasini ko'rish (admin uchun)

*Qo'llab-quvvatlanadigan platformalar:*
• YouTube
• Instagram
• TikTok
• Facebook
• Twitter
• va boshqa ko'plab saytlar

*Qanday ishlatish kerak?*
1. Video havolasini yuboring
2. Bot videoni yuklab beradi
3. "🎵 Audio yuklab olish" tugmasini bosib, faqat ovozini olishingiz mumkin

*Muhim eslatmalar:*
• Video hajmi 450MB dan oshmasligi kerak
• Xususiy videolarni yuklab bo'lmaydi
• Yuklab olingan fayllar 1 soatdan keyin o'chiriladi

❓ *Muammo yuzaga kelsa:*
• Havolani tekshiring
• Videoning mavjudligiga ishonch hosil qiling
• Keyinroq qayta urinib ko'ring"""

WELCOME_MESSAGE = """👋 Botimizga xush kelibsiz!

🎥 Men turli platformalardan video yuklab beruvchi botman.
Video havolasini menga yuboring va men uni yuklab beraman.

❓ Yordam olish uchun /help buyrug'ini yuboring."""

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    if update.effective_chat:
        metrics.track_command("start")
        await update.effective_message.reply_text(
            "👋 Salom! Men video yuklovchi botman. Menga video havolasini yuboring."
        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    if update.effective_chat:
        metrics.track_command("help")
        help_text = """🔍 Qo'llab-quvvatlanadigan platformalar:
- YouTube
- Instagram
- TikTok
- Facebook
- Va boshqalar...

📝 Buyruqlar:
/start - Botni ishga tushirish
/help - Yordam
/stats - Bot statistikasi (admin uchun)

💡 Ishlatish:
1. Video havolasini yuboring
2. Bot videoni yuklab beradi
3. Audio formatda yuklab olish uchun "🎵 Audio formatda yuklash" tugmasini bosing"""
        
        await update.effective_message.reply_text(help_text)

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /stats command (admin only)"""
    if update.effective_chat:
        metrics.track_command("stats")
        stats = metrics.get_statistics()
        stats_text = f"""📊 Bot statistikasi:

🔄 Jami yuklanishlar: {stats['total_downloads']}
✅ Muvaffaqiyatli: {stats['successful_downloads']}
❌ Xatoliklar: {stats['total_errors']}
⚡️ So'nggi 24 soat: {stats['last_24h']}
🎵 Audio ajratildi: {stats['audio_extractions']}
🎼 Musiqa aniqlandi: {stats['music_recognitions']}

💾 Tizim holati:
CPU: {stats['system'].get('cpu_percent', 'N/A')}%
RAM: {stats['system'].get('memory_percent', 'N/A')}%
Disk: {stats['system'].get('disk_percent', 'N/A')}%"""
        
        await update.effective_message.reply_text(stats_text)