import logging
import asyncio
from aiohttp import web
from typing import Optional
from ..services.monitoring import metrics

logger = logging.getLogger(__name__)

class HealthService:
    def __init__(self, port: int = 8080):
        self.port = port
        self.app = web.Application()
        self.app.router.add_get("/health", self.health_check)
        self.app.router.add_get("/metrics", self.get_metrics)
        self.runner: Optional[web.AppRunner] = None
        self.site: Optional[web.TCPSite] = None

    async def start(self):
        """Start the health check service"""
        try:
            self.runner = web.AppRunner(self.app)
            await self.runner.setup()
            self.site = web.TCPSite(self.runner, '0.0.0.0', self.port)
            await self.site.start()
            logger.info(f"Health service started on port {self.port}")
        except Exception as e:
            logger.error(f"Failed to start health service: {e}")
            metrics.track_error(type(e).__name__)
            raise

    async def stop(self):
        """Stop the health check service"""
        try:
            if self.site:
                await self.site.stop()
            if self.runner:
                await self.runner.cleanup()
            logger.info("Health service stopped")
        except Exception as e:
            logger.error(f"Error stopping health service: {e}")
            metrics.track_error(type(e).__name__)

    async def health_check(self, request: web.Request) -> web.Response:
        """Handle health check requests"""
        try:
            # Basic health check - if we can respond, we're healthy
            return web.json_response({
                "status": "healthy",
                "timestamp": asyncio.get_event_loop().time()
            })
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            metrics.track_error(type(e).__name__)
            return web.json_response({
                "status": "unhealthy",
                "error": str(e)
            }, status=500)

    async def get_metrics(self, request: web.Request) -> web.Response:
        """Return bot metrics"""
        try:
            stats = metrics.get_stats()
            return web.json_response({
                "status": "success",
                "metrics": stats
            })
        except Exception as e:
            logger.error(f"Error getting metrics: {e}")
            metrics.track_error(type(e).__name__)
            return web.json_response({
                "status": "error",
                "error": str(e)
            }, status=500)