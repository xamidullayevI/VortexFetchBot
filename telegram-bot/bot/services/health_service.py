import logging
import asyncio
from aiohttp import web
from typing import Optional
from .monitoring import get_bot_statistics

logger = logging.getLogger(__name__)

class HealthService:
    def __init__(self, port: int = 8080):
        self.port = port
        self.app = web.Application()
        self.runner: Optional[web.AppRunner] = None
        self._setup_routes()
        
    def _setup_routes(self):
        self.app.router.add_get("/", self.health_check)
        self.app.router.add_get("/health", self.health_check)
        
    async def health_check(self, request: web.Request) -> web.Response:
        """Health check endpointi"""
        try:
            stats = get_bot_statistics()
            system_stats = stats.get("system", {})
            
            health_data = {
                "status": "healthy",
                "uptime_seconds": stats["uptime_seconds"],
                "total_downloads": stats["total_downloads"],
                "memory_usage": f"{system_stats.get('memory_percent', 0)}%",
                "disk_usage": f"{system_stats.get('disk_percent', 0)}%"
            }
            
            return web.json_response(health_data)
        except Exception as e:
            logger.error(f"Health check xatoligi: {e}")
            return web.json_response(
                {"status": "unhealthy", "error": str(e)},
                status=500
            )
    
    async def start(self):
        """Health check serverini ishga tushirish"""
        try:
            self.runner = web.AppRunner(self.app)
            await self.runner.setup()
            
            site = web.TCPSite(self.runner, '0.0.0.0', self.port)
            await site.start()
            
            logger.info(f"Health check serveri ishga tushirildi: http://0.0.0.0:{self.port}")
        except Exception as e:
            logger.error(f"Health check serverini ishga tushirishda xatolik: {e}")
            raise
    
    async def stop(self):
        """Health check serverini to'xtatish"""
        if self.runner:
            try:
                await self.runner.cleanup()
            except Exception as e:
                logger.error(f"Health check serverini to'xtatishda xatolik: {e}")
                raise