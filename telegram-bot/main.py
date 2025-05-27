import os
import logging
import asyncio
import logging.config
from pathlib import Path
from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters

from bot.handlers import (
    start, help_command, stats_command,
    handle_message, extract_audio, find_original
)
from bot.services.monitoring import metrics
from bot.services.cleanup_service import CleanupService
from bot.services.health_service import HealthService
from bot.services.railway_service import RailwayService

# Logging konfiguratsiyasi
logging_conf_path = Path(__file__).parent / "bot" / "config" / "logging.conf"
if logging_conf_path.exists():
    logging.config.fileConfig(logging_conf_path)
else:
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )

logger = logging.getLogger(__name__)

# Environment o'zgaruvchilarini yuklash
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_IDS = os.getenv("ADMIN_IDS", "").split(",")
MAX_FILE_AGE = int(os.getenv("MAX_FILE_AGE_HOURS", "1"))  # Railway uchun 1 soat
PORT = int(os.getenv("PORT", "8080"))  # Railway uchun port

if not TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN .env faylida topilmadi")

def setup_downloads_folder():
    """Downloads papkasini yaratish"""
    downloads_dir = Path("downloads")
    downloads_dir.mkdir(exist_ok=True)
    return downloads_dir

async def main():
    try:
        # Downloads papkasini tayyorlash
        downloads_dir = setup_downloads_folder()

        # Railway xizmatlarini sozlash
        railway_service = RailwayService(str(downloads_dir))
        await railway_service.start()

        # Tozalash xizmatini sozlash
        cleanup_service = CleanupService(
            downloads_dir=str(downloads_dir),
            max_age_hours=MAX_FILE_AGE
        )
        await cleanup_service.start()

        # Health check xizmatini sozlash
        health_service = HealthService(port=PORT)
        await health_service.start()

        # Bot applicationini sozlash
        from telegram.request import HTTPXRequest
        request = HTTPXRequest(read_timeout=300, connect_timeout=60)
        application = (
            Application.builder()
            .token(TOKEN)
            .request(request)
            .build()
        )

        # Handlerlarni qo'shish
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("stats", stats_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        application.add_handler(CallbackQueryHandler(extract_audio, pattern=r"^get_audio:"))
        application.add_handler(CallbackQueryHandler(find_original, pattern=r"^find_original:"))

        # Error handler
        async def error_handler(update, context):
            logger.error(f"Update {update} caused error {context.error}")
            metrics.track_error(type(context.error).__name__)
            if update and update.effective_message:
                await update.effective_message.reply_text(
                    "❌ Bot ishlashida xatolik yuz berdi. Iltimos, keyinroq qayta urinib ko'ring."
                )

        application.add_error_handler(error_handler)

        # Botni ishga tushirish
        logger.info("Bot ishga tushirilmoqda...")
        await application.initialize()
        await application.start()
        
        try:
            await application.run_polling()
        finally:
            # Bot to'xtaganda xizmatlarni to'xtatish
            await cleanup_service.stop()
            await health_service.stop()
            await railway_service.stop()

    except Exception as e:
        logger.error(f"Botni ishga tushirishda xatolik: {e}")
        metrics.track_error(type(e).__name__)
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot to'xtatildi")
    except Exception as e:
        logger.error(f"Kutilmagan xatolik: {e}")
        metrics.track_error(type(e).__name__)
