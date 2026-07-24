"""
System Health Monitor for Discord Bot
Provides real-time system health information.
"""
import asyncio
import logging
import psutil
from typing import Dict, Any

logger = logging.getLogger(__name__)


class HealthMonitor:
    """Monitor system health and status."""

    def __init__(self, engine=None):
        self.engine = engine

    async def get_health(self) -> Dict[str, Any]:
        """Get complete system health information."""
        try:
            health = {
                "cpu": await self._get_cpu_usage(),
                "ram": await self._get_ram_usage(),
                "running_scanners": await self._get_running_scanners(),
                "queued_jobs": await self._get_queued_jobs(),
                "successful_scans": await self._get_successful_scans(),
                "failed_scans": await self._get_failed_scans(),
                "total_keys": await self._get_total_keys(),
                "verified_keys": await self._get_verified_keys(),
                "database_status": await self._get_database_status(),
                "discord_status": await self._get_discord_status(),
                "webhook_status": await self._get_webhook_status(),
                "llm_status": await self._get_llm_status(),
            }
            return health
        except Exception as e:
            logger.error(f"Error getting health: {e}")
            return {}

    async def _get_cpu_usage(self) -> str:
        """Get CPU usage percentage."""
        try:
            usage = await asyncio.to_thread(psutil.cpu_percent, interval=1)
            status = "🟢" if usage < 50 else "🟡" if usage < 80 else "🔴"
            return f"{status} {usage:.1f}%"
        except Exception as e:
            logger.warning(f"Error getting CPU usage: {e}")
            return "❓ Unknown"

    async def _get_ram_usage(self) -> str:
        """Get RAM usage percentage."""
        try:
            usage = psutil.virtual_memory().percent
            status = "🟢" if usage < 50 else "🟡" if usage < 80 else "🔴"
            return f"{status} {usage:.1f}%"
        except Exception as e:
            logger.warning(f"Error getting RAM usage: {e}")
            return "❓ Unknown"

    async def _get_running_scanners(self) -> int:
        """Get number of running scanners."""
        try:
            if self.engine and hasattr(self.engine, 'scanner_manager'):
                return len(self.engine.scanner_manager.get_enabled_scanners())
            return 0
        except Exception as e:
            logger.warning(f"Error getting running scanners: {e}")
            return 0

    async def _get_queued_jobs(self) -> int:
        """Get number of queued jobs."""
        try:
            if self.engine and hasattr(self.engine, 'state'):
                # Check if there are pending operations
                return 0  # Placeholder
            return 0
        except Exception as e:
            logger.warning(f"Error getting queued jobs: {e}")
            return 0

    async def _get_successful_scans(self) -> int:
        """Get number of successful scans."""
        try:
            if self.engine:
                status = self.engine.get_status()
                return status.get("total_scans", 0)
            return 0
        except Exception as e:
            logger.warning(f"Error getting successful scans: {e}")
            return 0

    async def _get_failed_scans(self) -> int:
        """Get number of failed scans."""
        try:
            if self.engine and hasattr(self.engine, 'state'):
                # Count failed scans from knowledge base
                if hasattr(self.engine, 'kb') and self.engine.kb:
                    return 0  # Would need to implement failure tracking
            return 0
        except Exception as e:
            logger.warning(f"Error getting failed scans: {e}")
            return 0

    async def _get_total_keys(self) -> int:
        """Get total number of keys found."""
        try:
            if self.engine:
                status = self.engine.get_status()
                return status.get("total_keys_found", 0)
            return 0
        except Exception as e:
            logger.warning(f"Error getting total keys: {e}")
            return 0

    async def _get_verified_keys(self) -> int:
        """Get number of verified keys."""
        try:
            if self.engine:
                keys = self.engine.get_keys()
                return len(keys)
            return 0
        except Exception as e:
            logger.warning(f"Error getting verified keys: {e}")
            return 0

    async def _get_database_status(self) -> str:
        """Get database status."""
        try:
            if self.engine and hasattr(self.engine, 'kb') and self.engine.kb:
                return "✅ Online"
            return "❌ Offline"
        except Exception as e:
            logger.warning(f"Error getting database status: {e}")
            return "❓ Unknown"

    async def _get_discord_status(self) -> str:
        """Get Discord bot status."""
        try:
            # This would be updated by the bot itself
            return "✅ Connected"
        except Exception as e:
            logger.warning(f"Error getting Discord status: {e}")
            return "❌ Disconnected"

    async def _get_webhook_status(self) -> str:
        """Get Discord webhook status."""
        try:
            from config.settings import DISCORD_WEBHOOK_URL

            if DISCORD_WEBHOOK_URL:
                return "✅ Configured"
            return "⚠️ Not configured"
        except Exception as e:
            logger.warning(f"Error getting webhook status: {e}")
            return "❓ Unknown"

    async def _get_llm_status(self) -> str:
        """Get LLM provider status."""
        try:
            if self.engine and hasattr(self.engine, 'parser'):
                if hasattr(self.engine.parser, 'llm_manager'):
                    provider = self.engine.parser.llm_manager.get_active_provider()
                    return f"✅ {provider}" if provider else "❓ Unknown"
            return "❓ Unknown"
        except Exception as e:
            logger.warning(f"Error getting LLM status: {e}")
            return "❓ Unknown"
