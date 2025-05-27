from telegram import Update
from telegram.ext import ContextTypes
from ..services.monitoring import metrics
from ..config.config import config
from ..services.rate_limiter import RateLimiter, audio_rate_limiter
import logging

logger = logging.getLogger(__name__)

# Global rate limiter
rate_limiter = RateLimiter()

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
        await update.effective_message.reply_text(HELP_MESSAGE, parse_mode='Markdown')

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /stats command (admin only)"""
    if not update.effective_chat or not update.effective_user:
        return
        
    user_id = update.effective_user.id
    
    # Check if user is admin
    if user_id not in config.admin_ids:
        await update.effective_message.reply_text(
            "⚠️ Bu buyruq faqat adminlar uchun."
        )
        return
        
    metrics.track_command("stats")
    stats = metrics.get_statistics()
    
    stats_text = f"""📊 *Bot statistikasi:*

🔄 Jami yuklanishlar: {stats['total_downloads']}
✅ Muvaffaqiyatli: {stats['successful_downloads']}
❌ Xatoliklar: {stats['total_errors']}
⚡️ So'nggi 24 soat: {stats['last_24h']}
🎵 Audio ajratildi: {stats['audio_extractions']}
🎼 Musiqa aniqlandi: {stats['music_recognitions']}

💾 *Tizim holati:*
CPU: {stats['system'].get('cpu_percent', 'N/A')}%
RAM: {stats['system'].get('memory_percent', 'N/A')}%
Disk: {stats['system'].get('disk_percent', 'N/A')}%"""
        
    await update.effective_message.reply_text(stats_text, parse_mode='Markdown')

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /admin command - Admin only commands"""
    if not update.effective_chat or not update.effective_message:
        return
        
    user_id = update.effective_user.id
    if user_id not in config.admin_ids:
        await update.effective_message.reply_text(
            "❌ Bu buyruq faqat adminlar uchun."
        )
        return

    if not context.args or len(context.args) < 1:
        await update.effective_message.reply_text(
            "📝 Admin buyruqlar:\n\n"
            "/admin block <user_id> [duration] - Foydalanuvchini bloklash\n"
            "/admin unblock <user_id> - Blokdan chiqarish\n"
            "/admin reset <user_id> - Cheklovlarni qayta o'rnatish\n"
            "/admin stats [user_id] - Statistikani ko'rish"
        )
        return

    command = context.args[0].lower()
    
    if command == "stats":
        if len(context.args) > 1:
            try:
                target_id = int(context.args[1])
                stats = audio_rate_limiter.get_user_stats(target_id)
                if stats:
                    await update.effective_message.reply_text(
                        f"📊 Foydalanuvchi {target_id} statistikasi:\n\n"
                        f"So'rovlar: {stats['requests']}/{stats['max_requests']}\n"
                        f"Umumiy hajm: {stats['total_size_mb']:.1f}MB/{stats['max_size_mb']}MB\n"
                        f"Vaqt qoldi: {stats['time_left']:.0f}s\n"
                        f"Bloklangan: {'Ha' if stats['is_blocked'] else 'Yo`q'}"
                    )
                else:
                    await update.effective_message.reply_text(
                        f"❓ Foydalanuvchi {target_id} topilmadi"
                    )
            except ValueError:
                await update.effective_message.reply_text("❌ Noto'g'ri foydalanuvchi ID")
        else:
            stats = metrics.get_statistics()
            await update.effective_message.reply_text(
                "📊 Bot statistikasi:\n\n"
                f"Jami so'rovlar: {stats['total_downloads']}\n"
                f"Muvaffaqiyatli: {stats['successful_downloads']}\n"
                f"Xatoliklar: {stats['total_errors']}\n"
                f"Audio ajratildi: {stats['audio_extractions']}\n"
                f"Musiqa aniqlandi: {stats['music_recognitions']}\n\n"
                f"Tizim holati:\n"
                f"CPU: {stats['system'].get('cpu_percent', 'N/A')}%\n"
                f"RAM: {stats['system'].get('memory_percent', 'N/A')}%\n"
                f"Disk: {stats['system'].get('disk_percent', 'N/A')}%"
            )
    
    elif command == "block":
        if len(context.args) < 2:
            await update.effective_message.reply_text(
                "❌ Foydalanuvchi ID'sini kiriting"
            )
            return
            
        try:
            target_id = int(context.args[1])
            duration = int(context.args[2]) if len(context.args) > 2 else None
            
            await audio_rate_limiter.block_user(target_id, duration)
            if duration:
                await update.effective_message.reply_text(
                    f"✅ Foydalanuvchi {target_id} {duration} sekundga bloklandi"
                )
            else:
                await update.effective_message.reply_text(
                    f"✅ Foydalanuvchi {target_id} doimiy bloklandi"
                )
                
        except ValueError:
            await update.effective_message.reply_text("❌ Noto'g'ri ID yoki vaqt")
    
    elif command == "unblock":
        if len(context.args) < 2:
            await update.effective_message.reply_text(
                "❌ Foydalanuvchi ID'sini kiriting"
            )
            return
            
        try:
            target_id = int(context.args[1])
            await audio_rate_limiter.unblock_user(target_id)
            await update.effective_message.reply_text(
                f"✅ Foydalanuvchi {target_id} blokdan chiqarildi"
            )
        except ValueError:
            await update.effective_message.reply_text("❌ Noto'g'ri ID")
    
    elif command == "reset":
        if len(context.args) < 2:
            await update.effective_message.reply_text(
                "❌ Foydalanuvchi ID'sini kiriting"
            )
            return
            
        try:
            target_id = int(context.args[1])
            audio_rate_limiter.reset_user(target_id)
            await update.effective_message.reply_text(
                f"✅ Foydalanuvchi {target_id} chekovlari qayta o'rnatildi"
            )
        except ValueError:
            await update.effective_message.reply_text("❌ Noto'g'ri ID")
    
    else:
        await update.effective_message.reply_text(
            "❌ Noto'g'ri buyruq. /admin buyrug'i orqali mavjud buyruqlarni ko'ring"
        )