import os
import json
import logging
import asyncio
from aiohttp import web
from typing import Optional
from datetime import datetime
from ..services.monitoring import metrics
from ..config.config import config

logger = logging.getLogger(__name__)

class HealthService:
    def __init__(self, port: int = None):
        self.port = port or int(os.getenv('PORT', config.port))
        self.start_time = datetime.now()
        self._app = web.Application()
        self._app.router.add_get("/", self.root_handler)  # Add root handler for Railway
        self._app.router.add_get("/health", self.health_check)
        self._app.router.add_get("/metrics", self.metrics_endpoint)
        self._runner: Optional[web.AppRunner] = None
        self._site: Optional[web.TCPSite] = None

    async def start(self):
        """Start the health check service"""
        try:
            self._runner = web.AppRunner(self._app)
            await self._runner.setup()
            self._site = web.TCPSite(
                self._runner,
                host="0.0.0.0",
                port=self.port
            )
            await self._site.start()
            logger.info(f"Health check service started on port {self.port}")
        except Exception as e:
            logger.error(f"Failed to start health check service: {e}")
            metrics.track_error(type(e).__name__)

    async def stop(self):
        """Stop the health check service"""
        try:
            if self._site:
                await self._site.stop()
            if self._runner:
                await self._runner.cleanup()
            logger.info("Health check service stopped")
        except Exception as e:
            logger.error(f"Error stopping health check service: {e}")
            metrics.track_error(type(e).__name__)

    async def root_handler(self, request: web.Request) -> web.Response:
        """Handle root endpoint for Railway"""
        return web.Response(text="Bot is running", content_type="text/plain")

    async def health_check(self, request: web.Request) -> web.Response:
        """Handle /health endpoint"""
        try:
            import psutil

            # Get system stats
            process = psutil.Process()
            memory_info = process.memory_info()
            cpu_percent = process.cpu_percent()
            memory_percent = process.memory_percent()
            
            # Get disk usage for downloads directory
            disk = psutil.disk_usage(str(config.downloads_dir))

            # Prepare health check response
            health_data = {
                "status": "healthy",
                "uptime": str(datetime.now() - self.start_time),
                "system": {
                    "cpu_percent": cpu_percent,
                    "memory_used_mb": memory_info.rss / 1024 / 1024,
                    "memory_percent": memory_percent,
                    "disk_free_mb": disk.free / 1024 / 1024,
                    "disk_percent": disk.percent
                }
            }

            # Check resource thresholds
            warnings = []
            if cpu_percent > 80:
                warnings.append("High CPU usage")
            if memory_percent > config.max_memory_percent:
                warnings.append("High memory usage")
            if disk.percent > config.max_disk_percent:
                warnings.append("Low disk space")

            if warnings:
                health_data["status"] = "warning"
                health_data["warnings"] = warnings

            return web.json_response(health_data)

        except Exception as e:
            logger.error(f"Health check error: {e}")
            metrics.track_error(type(e).__name__)
            return web.json_response({
                "status": "error",
                "error": str(e)
            }, status=500)

    async def metrics_endpoint(self, request: web.Request) -> web.Response:
        """Handle /metrics endpoint"""
        try:
            # Get bot metrics
            bot_stats = metrics.get_statistics()
            
            # Format metrics in Prometheus format
            prometheus_metrics = []
            
            # Add download metrics
            prometheus_metrics.extend([
                '# TYPE bot_downloads_total counter',
                f'bot_downloads_total {bot_stats["total_downloads"]}',
                '# TYPE bot_downloads_success counter',
                f'bot_downloads_success {bot_stats["successful_downloads"]}',
                '# TYPE bot_downloads_errors counter',
                f'bot_downloads_errors {bot_stats["total_errors"]}'
            ])
            
            # Add audio processing metrics
            prometheus_metrics.extend([
                '# TYPE bot_audio_extractions counter',
                f'bot_audio_extractions {bot_stats["audio_extractions"]}',
                '# TYPE bot_music_recognitions counter',
                f'bot_music_recognitions {bot_stats["music_recognitions"]}'
            ])
            
            # Add system metrics
            system_stats = bot_stats.get("system", {})
            if system_stats:
                prometheus_metrics.extend([
                    '# TYPE bot_cpu_percent gauge',
                    f'bot_cpu_percent {system_stats.get("cpu_percent", 0)}',
                    '# TYPE bot_memory_percent gauge',
                    f'bot_memory_percent {system_stats.get("memory_percent", 0)}',
                    '# TYPE bot_disk_percent gauge',
                    f'bot_disk_percent {system_stats.get("disk_percent", 0)}'
                ])
            
            return web.Response(
                text="\n".join(prometheus_metrics),
                content_type="text/plain"
            )
            
        except Exception as e:
            logger.error(f"Metrics endpoint error: {e}")
            metrics.track_error(type(e).__name__)
            return web.Response(
                text="# Error collecting metrics",
                content_type="text/plain",
                status=500
            )