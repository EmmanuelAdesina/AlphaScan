"""AlphaScan configuration validator."""
import logging
import os
from typing import Dict, List

from config import CENSYS_PAT, GITHUB_TOKEN, MISTRAL_API_KEY, DISCORD_WEBHOOK_URL, ETHERSCAN_API_KEY

logger = logging.getLogger(__name__)


class ConfigValidator:
    """Validates configuration and reports errors/warnings."""

    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.info: List[str] = []

    def validate_all(self) -> Dict:
        """Run all validation checks."""
        self.errors.clear()
        self.warnings.clear()
        self.info.clear()

        self._check_dotenv()
        self._check_api_keys()
        self._check_settings()

        return {
            "errors": self.errors,
            "warnings": self.warnings,
            "info": self.info,
        }

    def _check_dotenv(self):
        """Check if .env file exists."""
        if not os.path.exists(".env"):
            self.warnings.append(".env file not found. Using environment variables or defaults.")

    def _check_api_keys(self):
        """Check API key configuration."""
        checks = {
            "Censys": CENSYS_PAT,
            "GitHub": GITHUB_TOKEN,
            "Mistral": MISTRAL_API_KEY,
            "Discord": DISCORD_WEBHOOK_URL,
        }

        for name, key in checks.items():
            if not key:
                self.warnings.append(f"{name} API key not configured (scanner disabled)")

        if not ETHERSCAN_API_KEY:
            self.info.append("Etherscan API key not configured (wallet balance checks disabled)")

    def _check_settings(self):
        """Check scan settings."""
        scan_interval = int(os.getenv("SCAN_INTERVAL", "300"))
        if scan_interval < 60:
            self.warnings.append(f"SCAN_INTERVAL={scan_interval}s is very aggressive (recommended: >= 300s)")

        max_keys = int(os.getenv("MAX_KEYS_PER_REPORT", "50"))
        if max_keys > 100:
            self.warnings.append(f"MAX_KEYS_PER_REPORT={max_keys} may hit Discord rate limits")

    def log_report(self):
        """Log validation report."""
        if self.errors:
            for error in self.errors:
                logger.error(f"Config error: {error}")
        if self.warnings:
            for warning in self.warnings:
                logger.warning(f"Config warning: {warning}")
        if self.info:
            for info in self.info:
                logger.info(f"Config info: {info}")

        if not self.errors and not self.warnings:
            logger.info("Configuration OK")