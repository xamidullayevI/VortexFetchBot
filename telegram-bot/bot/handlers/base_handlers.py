from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from ..services.monitoring import get_bot_statistics
import os
import psutil

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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Foydalanuvchi /start buyrug'ini yuborgan vaqtda ishga tushadi"""
    user = update.effective_user
    await update.message.reply_text(
        f"Salom, {user.first_name}! " + WELCOME_MESSAGE,
        parse_mode=ParseMode.MARKDOWN
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Foydalanuvchi /help buyrug'ini yuborgan vaqtda ishga tushadi"""
    await update.message.reply_text(
        HELP_MESSAGE,
        parse_mode=ParseMode.MARKDOWN
    )

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Bot statistikasini ko'rsatish (faqat adminlar uchun)"""
    admin_ids = os.getenv("ADMIN_IDS", "").split(",")
    if not admin_ids or str(update.effective_user.id) not in admin_ids:
        await update.message.reply_text("❌ Bu buyruq faqat bot adminlari uchun")
        return
        
    stats = get_bot_statistics()
    uptime_hours = stats["uptime_seconds"] / 3600
    system_stats = stats.get("system", {})
    
    # Railway tizim ma'lumotlari
    downloads_size = sum(
        os.path.getsize(os.path.join("downloads", f))
        for f in os.listdir("downloads")
        if os.path.isfile(os.path.join("downloads", f))
    ) / (1024 * 1024)  # MB ga o'tkazish
    
    message = (
        "*📊 Bot Statistikasi*\n\n"
        f"🕒 Ishlab turgan vaqt: {uptime_hours:.1f} soat\n"
        f"📥 Jami yuklab olishlar: {stats['total_downloads']}\n"
        f"⚠️ Jami xatoliklar: {stats['total_errors']}\n"
        f"⏱ O'rtacha yuklab olish vaqti: {stats['average_download_time']:.1f} sekund\n\n"
        "*🖥 Tizim Holati:*\n"
        f"• CPU: {system_stats.get('cpu_percent', 0)}%\n"
        f"• RAM: {system_stats.get('memory_percent', 0)}%\n"
        f"• Disk: {system_stats.get('disk_percent', 0)}%\n"
        f"• Downloads papka hajmi: {downloads_size:.1f}MB\n\n"
        "*⚠️ Xatoliklar Taqsimoti:*\n"
    )
    
    for error_type, count in stats["error_distribution"].items():
        message += f"• {error_type}: {count}\n"
    
    await update.message.reply_text(
        message,
        parse_mode=ParseMode.MARKDOWN
    )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Bot xatoliklarini qayta ishlash"""
    error_message = f"❌ Xatolik yuz berdi: {str(context.error)}"
    if update and update.effective_message:
        await update.effective_message.reply_text(
            error_message + "\n\nIltimos, keyinroq qayta urinib ko'ring."
        )