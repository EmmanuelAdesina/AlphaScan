"""
Discord notification module for APIS.
Sends status updates, key reports, and self-improvement alerts via Discord webhooks.
"""
import logging
import json
from typing import List, Dict, Optional
from datetime import datetime
from config.settings import DISCORD_WEBHOOK_URL, MAX_KEYS_PER_REPORT

logger = logging.getLogger(__name__)


class DiscordNotifier:
    """
    Sends notifications to Discord via webhook.
    Handles status updates, key reports, and self-improvement alerts.
    """

    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url or DISCORD_WEBHOOK_URL
        self._enabled = bool(self.webhook_url)

    def _send(self, content: str, embeds: Optional[List[Dict]] = None) -> bool:
        """Send a message to Discord webhook."""
        if not self._enabled:
            logger.warning("Discord webhook not configured, skipping notification")
            return False

        import requests

        payload = {"content": content}
        if embeds:
            payload["embeds"] = embeds

        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10,
            )
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Failed to send Discord notification: {e}")
            return False

    def send_status(self, cycle: int, duration: float, keys_found: int,
                    new_scanner: Optional[str] = None) -> bool:
        """Send a status update message."""
        lines = [
            "📡 **APIS Status**",
            f"- Cycle #{cycle} completed in {duration:.1f}s",
            f"- Found {keys_found} valid key(s)",
        ]
        if new_scanner:
            lines.append(f"- New scanner added: \"{new_scanner}\" (auto-generated)")
        lines.append(f"- Next scan in {_format_interval()}")

        return self._send("\n".join(lines))

    def send_key_report(self, keys: List[Dict]) -> bool:
        """Send a report of found keys, categorized by type."""
        if not keys:
            return self._send("🔑 APIS - No keys found in this cycle.")

        # Group keys by type
        by_type: Dict[str, List[Dict]] = {}
        for key in keys[:MAX_KEYS_PER_REPORT]:
            key_type = key.get("type", "generic")
            by_type.setdefault(key_type, []).append(key)

        embeds = []
        for key_type, type_keys in by_type.items():
            # Mask key values for safety
            fields = []
            for key in type_keys:
                masked = key.get("masked_value", "[redacted]")
                fields.append({
                    "name": f"{key_type.upper()} ({len(type_keys)})",
                    "value": f"`{masked}`",
                    "inline": False,
                })

            embeds.append({
                "title": f"🔑 {key_type.upper()} Keys Found",
                "fields": fields,
                "color": 0x5865F2,
            })

        summary = f"🔑 **APIS - API Keys Found**\n\n📊 Summary: {len(keys)} valid key(s)"
        return self._send(summary, embeds)

    def send_new_key_type(self, key_type: str, sample: str,
                          confidence: float = 0.0) -> bool:
        """Notify about a newly discovered key type."""
        msg = (
            f"⚠️ **New key type discovered: {key_type}**\n"
            f"- Sample: `{sample[:20]}...`\n"
            f"- Confidence: {confidence:.2f}\n"
            f"- Requesting classification guidance."
        )
        return self._send(msg)

    def send_self_improvement(self, message: str, success: bool = True) -> bool:
        """Send a self-improvement update."""
        emoji = "✅" if success else "❌"
        msg = f"💡 **System Improvement**\n{emoji} {message}"
        return self._send(msg)

    def send_error(self, error: str, context: str = "") -> bool:
        """Send an error notification."""
        msg = f"❌ **APIS Error**\n- {error}"
        if context:
            msg += f"\n- Context: {context}"
        return self._send(msg)

    def send_info(self, message: str) -> bool:
        """Send a general info message."""
        return self._send(f"ℹ️ {message}")

    def send_help_request(self, issue: str, context: str = "") -> bool:
        """Request human input for an issue the system cannot resolve."""
        msg = (
            f"🆘 **Human Input Requested**\n"
            f"- Issue: {issue}\n"
            f"- Context: {context}\n"
            f"Please provide guidance."
        )
        return self._send(msg)


def _format_interval() -> str:
    """Format the next scan interval for display."""
    from config.settings import SCAN_INTERVAL
    minutes = SCAN_INTERVAL // 60
    seconds = SCAN_INTERVAL % 60
    if minutes > 0:
        return f"{minutes}m {seconds}s"
    return f"{seconds}s"
