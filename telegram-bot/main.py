import os
import logging
import logging.config
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters

# Import handlers
from bot.handlers.base_handlers import start_command, help_command, stats_command, admin_command
from bot.handlers.media_handlers import handle_media_message
from bot.handlers.audio_handlers import extract_audio, find_original

# Import services
from bot.services.monitoring import metrics
from bot.services.cleanup_service import CleanupService
from bot.services.health_service import HealthService
from bot.services.railway_service import RailwayService
from bot.config.config import config

# Load environment variables
load_dotenv()

# Configure logging
logging_conf_path = Path(__file__).parent / "bot" / "config" / "logging.conf"
if logging_conf_path.exists():
    logging.config.fileConfig(logging_conf_path)
else:
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )

logger = logging.getLogger(__name__)

async def main():
    """Start the bot"""
    try:
        # Initialize Railway service
        railway_service = RailwayService(str(config.downloads_dir))
        await railway_service.start()

        # Initialize cleanup service
        cleanup_service = CleanupService(
            downloads_dir=str(config.downloads_dir),
            max_age_hours=config.max_file_age
        )
        await cleanup_service.start()

        # Initialize health check service
        health_service = HealthService(port=config.port)
        await health_service.start()

        # Configure bot with higher timeouts for Railway
        from telegram.request import HTTPXRequest
        request = HTTPXRequest(
            read_timeout=300,
            write_timeout=300,
            connect_timeout=60,
            pool_timeout=120
        )
        
        # Initialize bot application
        application = (
            Application.builder()
            .token(config.token)
            .request(request)
            .build()
        )

        # Add handlers
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("stats", stats_command))
        application.add_handler(CommandHandler("admin", admin_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_media_message))
        application.add_handler(CallbackQueryHandler(extract_audio, pattern=r"^get_audio:"))
        application.add_handler(CallbackQueryHandler(find_original, pattern=r"^find_original:"))

        # Error handler
        async def error_handler(update, context):
            logger.error(f"Update {update} caused error {context.error}")
            metrics.track_error(type(context.error).__name__)
            
            error_message = "❌ Bot ishlashida xatolik yuz berdi."
            
            if str(context.error).startswith("HTTP"):
                error_message = "❌ Telegram serveriga ulanishda xatolik. Iltimos, keyinroq urinib ko'ring."
            elif "Timed out" in str(context.error):
                error_message = "⌛️ So'rov vaqti tugadi. Video hajmi juda katta bo'lishi mumkin."
            elif "FILE_PARTS_INVALID" in str(context.error):
                error_message = "❌ Fayl hajmi juda katta (50MB dan oshmasligi kerak)."
            elif "FILE_REFERENCE_EXPIRED" in str(context.error):
                error_message = "❌ Fayl muddati tugagan. Iltimos, qaytadan yuklang."
            
            if update and update.effective_message:
                await update.effective_message.reply_text(
                    f"{error_message}\n\n"
                    "Qayta urinib ko'ring yoki /help buyrug'i orqali yordam oling."
                )

        application.add_error_handler(error_handler)

        # Start bot
        logger.info("Starting bot...")
        await application.initialize()
        await application.start()
        
        # Run bot until stopped
        logger.info("Bot is running...")
        await application.run_polling(
            drop_pending_updates=True,
            allowed_updates=[
                "message",
                "callback_query",
                "my_chat_member"
            ]
        )

    except Exception as e:
        logger.error(f"Bot initialization error: {e}")
        metrics.track_error(type(e).__name__)
        raise

    finally:
        # Cleanup on shutdown
        logger.info("Shutting down...")
        await cleanup_service.stop()
        await health_service.stop()
        await railway_service.stop()
        try:
            await application.stop()
        except:
            pass

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        metrics.track_error(type(e).__name__)
