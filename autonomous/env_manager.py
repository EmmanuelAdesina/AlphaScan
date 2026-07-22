"""
Environment Manager for AlphaScan v0.5.

Automatically detects missing API keys, requests them via Discord,
and updates the .env file when keys are provided.
"""
import os
import re
import logging
from typing import Dict, List, Optional, Union
from pathlib import Path
from config.settings import BASE_DIR

logger = logging.getLogger(__name__)

# Required environment variables and their descriptions
REQUIRED_KEYS = {
    "CENSYS_API_ID": "Censys API ID (for Censys scanner)",
    "CENSYS_API_SECRET": "Censys API Secret (for Censys scanner)",
    "GITHUB_TOKEN": "GitHub Personal Access Token (for GitHub scanner)",
    "GROQ_API_KEY": "Groq AI API Key (for AI-powered key extraction)",
    "DISCORD_WEBHOOK_URL": "Discord Webhook URL (for notifications)",
    "ETHERSCAN_API_KEY": "Etherscan API Key (for ETH balance checks, optional)",
}


class EnvManager:
    """
    Manages environment variables and API keys autonomously.

    - Detects missing keys
    - Requests keys via Discord
    - Updates .env file
    - Reloads environment without restart
    """

    def __init__(self, env_file: Optional[Union[Path, str]] = None, notifier=None):
        self._env_file = Path(env_file) if env_file else (BASE_DIR / ".env")
        self._notifier = notifier
        self._pending_requests: Dict[str, str] = {}
        self._loaded_keys: Dict[str, str] = {}

    def detect_key_needs(self) -> List[str]:
        """Detect which required API keys are missing from the environment."""
        missing = []
        for key_name in REQUIRED_KEYS:
            value = os.getenv(key_name, "")
            if not value or value.startswith("your_"):
                missing.append(key_name)
        return missing

    def request_key_via_discord(self, service_name: str, key_name: str) -> str:
        """Send a request to Discord for a missing API key."""
        request_id = f"req_{key_name}_{os.getpid()}"
        self._pending_requests[key_name] = request_id

        message = (
            f"🔑 **API Key Request**\n"
            f"- Service: {service_name}\n"
            f"- Variable: `{key_name}`\n"
            f"- Description: {REQUIRED_KEYS.get(key_name, 'Unknown')}\n"
            f"\n"
            f"Please provide the key by running:\n"
            f"`!provide-key {key_name} <value>`\n"
            f"\n"
            f"This is needed to enable {service_name} scanning."
        )

        if self._notifier:
            self._notifier.send_info(message)
        else:
            logger.info(f"Key request (no notifier): {message}")

        return request_id

    def listen_for_key_response(self, command: str) -> Optional[Dict]:
        """Process a Discord command to provide a key."""
        if not command.startswith("!provide-key"):
            return None

        parts = command.split(None, 2)
        if len(parts) < 3:
            return {"success": False, "error": "Usage: !provide-key <KEY_NAME> <value>"}

        key_name = parts[1].upper()
        key_value = parts[2].strip()

        if key_name not in REQUIRED_KEYS:
            return {"success": False, "error": f"Unknown key: {key_name}"}

        success, msg = self.update_env_file(key_name, key_value)

        if success:
            self.reload_environment()
            self._pending_requests.pop(key_name, None)

            if self._notifier:
                self._notifier.send_info(
                    f"✅ Key `{key_name}` updated successfully. Environment reloaded."
                )

            return {"success": True, "key_name": key_name, "message": msg}

        return {"success": False, "error": msg}

    def update_env_file(self, key_name: str, key_value: str) -> tuple:
        """Update the .env file with a new key value."""
        try:
            if self._env_file.exists():
                with open(self._env_file, "r") as f:
                    lines = f.readlines()
            else:
                lines = []

            found = False
            new_lines = []
            for line in lines:
                if line.strip().startswith(f"{key_name}="):
                    new_lines.append(f"{key_name}={key_value}\n")
                    found = True
                else:
                    new_lines.append(line)

            if not found:
                new_lines.append(f"{key_name}={key_value}\n")

            with open(self._env_file, "w") as f:
                f.writelines(new_lines)

            return True, f"Updated {key_name} in .env file"

        except Exception as e:
            return False, f"Failed to update .env: {e}"

    def reload_environment(self) -> bool:
        """Reload environment variables from .env file without restart."""
        try:
            from dotenv import load_dotenv
            load_dotenv(self._env_file, override=True)

            for key_name in REQUIRED_KEYS:
                value = os.getenv(key_name, "")
                if value:
                    self._loaded_keys[key_name] = value

            return True
        except Exception as e:
            logger.error(f"Failed to reload environment: {e}")
            return False

    def get_missing_keys_report(self) -> str:
        """Generate a report of missing keys."""
        missing = self.detect_key_needs()
        if not missing:
            return "✅ All required API keys are configured."

        lines = ["⚠️ **Missing API Keys:**"]
        for key_name in missing:
            lines.append(f"  - `{key_name}`: {REQUIRED_KEYS.get(key_name, 'Unknown')}")

        lines.append("\nRequest keys via Discord or add them to .env manually.")
        return "\n".join(lines)

    def get_pending_requests(self) -> Dict[str, str]:
        """Get pending key requests."""
        return dict(self._pending_requests)
