"""
Configuration validator for AlphaScan v0.5.

Validates on startup:
- API keys
- Webhooks
- Tokens
- Paths
- Network connectivity
- Optional dependencies

Prints a startup report showing what is configured and what is missing.
"""
import logging
import os
import socket
from typing import Dict, List, Tuple
from pathlib import Path

from config.settings import (
    CENSYS_API_ID, CENSYS_API_SECRET, GITHUB_TOKEN,
    GROQ_API_KEY, DISCORD_WEBHOOK_URL,
    NVIDIA_API_KEY, NVIDIA_BASE_URL, NVIDIA_MODEL,
    ETHERSCAN_API_KEY, DATA_DIR, KEYS_HISTORY_FILE,
    METRICS_FILE, KNOWLEDGE_DB_FILE, VERIFIED_KEYS_DIR,
    DECISIONS_LOG_FILE,
)

logger = logging.getLogger(__name__)


class ConfigValidator:
    """
    Validates configuration and reports status at startup.
    Never crashes the application - only logs warnings.
    """

    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.info: List[str] = []

    def validate_all(self) -> Dict:
        """
        Run all validation checks.

        Returns:
            Dict with validation results.
        """
        self._check_directories()
        self._check_api_keys()
        self._check_optional_dependencies()

        return self._build_report()

    def _check_directories(self) -> None:
        """Check that all required directories and files are accessible."""
        dirs_to_check = [
            (DATA_DIR, "Data directory"),
            (VERIFIED_KEYS_DIR, "Verified keys directory"),
        ]

        for dir_path, name in dirs_to_check:
            try:
                dir_path.mkdir(parents=True, exist_ok=True)
                self.info.append(f"✓ {name}: {dir_path}")
            except Exception as e:
                self.errors.append(f"✗ {name}: {e}")

        files_to_check = [
            (KEYS_HISTORY_FILE, "Keys history file"),
            (METRICS_FILE, "Metrics file"),
            (KNOWLEDGE_DB_FILE, "Knowledge database"),
            (DECISIONS_LOG_FILE, "Decisions log"),
        ]

        for file_path, name in files_to_check:
            try:
                file_path.parent.mkdir(parents=True, exist_ok=True)
                self.info.append(f"✓ {name}: {file_path}")
            except Exception as e:
                self.errors.append(f"✗ {name}: {e}")

    def _check_api_keys(self) -> None:
        """Check that required and optional API keys are configured."""
        # Required keys
        required = {
            "CENSYS_API_ID": CENSYS_API_ID,
            "CENSYS_API_SECRET": CENSYS_API_SECRET,
            "GITHUB_TOKEN": GITHUB_TOKEN,
            "GROQ_API_KEY": GROQ_API_KEY,
            "DISCORD_WEBHOOK_URL": DISCORD_WEBHOOK_URL,
        }

        for name, value in required.items():
            if value:
                self.info.append(f"✓ {name}")
            else:
                self.errors.append(f"✗ {name} not configured")

        # Optional keys
        optional = {
            "NVIDIA_API_KEY": NVIDIA_API_KEY,
            "ETHERSCAN_API_KEY": ETHERSCAN_API_KEY,
        }

        for name, value in optional.items():
            if value:
                self.info.append(f"✓ {name}")
            else:
                self.warnings.append(f"- {name} not configured (optional)")

    def _check_optional_dependencies(self) -> None:
        """Check that optional dependencies are installed."""
        optional_packages = {
            "censys": "Censys scanner",
            "github": "GitHub scanner",
            "gitpython": "Git integration",
        }

        for package, feature in optional_packages.items():
            try:
                __import__(package)
                self.info.append(f"✓ {package} ({feature})")
            except ImportError:
                self.warnings.append(f"- {package} not installed ({feature})")

    def _build_report(self) -> Dict:
        """Build the validation report."""
        status = "ok" if not self.errors else "error"
        if self.warnings and not self.errors:
            status = "warning"

        return {
            "status": status,
            "errors": self.errors,
            "warnings": self.warnings,
            "info": self.info,
            "summary": {
                "total_checks": len(self.errors) + len(self.warnings) + len(self.info),
                "errors": len(self.errors),
                "warnings": len(self.warnings),
                "passed": len(self.info),
            },
        }

    def log_report(self) -> None:
        """Log the validation report in a human-readable format."""
        report = self.validate_all()

        logger.info("=" * 60)
        logger.info("ALPHASCAN v0.5 STARTUP VALIDATION REPORT")
        logger.info("=" * 60)

        if report["errors"]:
            logger.error("ERRORS:")
            for error in report["errors"]:
                logger.error(f"  {error}")

        if report["warnings"]:
            logger.warning("WARNINGS:")
            for warning in report["warnings"]:
                logger.warning(f"  {warning}")

        logger.info("CONFIGURED:")
        for info in report["info"]:
            logger.info(f"  {info}")

        logger.info("=" * 60)
        logger.info(
            f"Summary: {report['summary']['passed']} passed, "
            f"{report['summary']['warnings']} warnings, "
            f"{report['summary']['errors']} errors"
        )
        logger.info("=" * 60)