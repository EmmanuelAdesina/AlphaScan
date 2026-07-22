"""
Application settings for AlphaScan v0.5.
Loads configuration from environment variables with sensible defaults.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _get_bool(key: str, default: bool = False) -> bool:
    """Parse a boolean environment variable."""
    val = os.getenv(key, str(default)).lower()
    return val in ("true", "1", "yes", "on")


def _get_int(key: str, default: int) -> int:
    """Parse an integer environment variable."""
    try:
        return int(os.getenv(key, str(default)))
    except (ValueError, TypeError):
        return default


def _get_float(key: str, default: float) -> float:
    """Parse a float environment variable."""
    try:
        return float(os.getenv(key, str(default)))
    except (ValueError, TypeError):
        return default


# ── Required API Credentials ──────────────────────────────────────────────
CENSYS_API_ID: str = os.getenv("CENSYS_API_ID", "")
CENSYS_API_SECRET: str = os.getenv("CENSYS_API_SECRET", "")
GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
DISCORD_WEBHOOK_URL: str = os.getenv("DISCORD_WEBHOOK_URL", "")

# ── Operational Settings ──────────────────────────────────────────────────
SCAN_INTERVAL: int = _get_int("SCAN_INTERVAL", 300)
MAX_KEYS_PER_REPORT: int = _get_int("MAX_KEYS_PER_REPORT", 50)
DEBUG: bool = _get_bool("DEBUG", False)
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()

# ── Paths ─────────────────────────────────────────────────────────────────
DATA_DIR: Path = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

KEYS_HISTORY_FILE: Path = DATA_DIR / "keys_history.json"
METRICS_FILE: Path = DATA_DIR / "metrics.json"
KNOWLEDGE_DB_FILE: Path = DATA_DIR / "knowledge.db"
VERIFIED_KEYS_DIR: Path = DATA_DIR / "verified_keys"
VERIFIED_KEYS_DIR.mkdir(parents=True, exist_ok=True)
DECISIONS_LOG_FILE: Path = DATA_DIR / "decisions.log"

# ── Scanner Configuration ──────────────────────────────────────────────────
CENSYS_QUERY: str = os.getenv(
    "CENSYS_QUERY",
    '"http.api.key" OR "api_key" OR "secret_key" OR "access_token" '
    'OR "private_key" OR "BEGIN PRIVATE KEY" OR "BEGIN OPENSSH"',
)
GITHUB_SEARCH_QUERY: str = os.getenv(
    "GITHUB_SEARCH_QUERY",
    'filename:.env OR filename:config.py OR filename:settings.py '
    'extension:json "api_key" -is:fork',
)

# ── Security ──────────────────────────────────────────────────────────────
# Only log first N characters of keys
KEY_LOG_PREVIEW_LENGTH: int = 6
# Rate limiting
API_RATE_LIMIT: str = os.getenv("API_RATE_LIMIT", "100/minute")

# ── v0.5 Autonomous Mode ───────────────────────────────────────────────────
AUTONOMOUS_MODE: bool = _get_bool("AUTONOMOUS_MODE", True)
AUTO_PUSH_GITHUB: bool = _get_bool("AUTO_PUSH_GITHUB", True)
ALLOW_AUTO_RESTART: bool = _get_bool("ALLOW_AUTO_RESTART", True)
AUTO_PIVOT_THRESHOLD: float = _get_float("AUTO_PIVOT_THRESHOLD", 0.15)
MAX_DECISION_LOG: int = _get_int("MAX_DECISION_LOG", 1000)

# ── v0.5 Detection Toggles ─────────────────────────────────────────────────
ENABLE_SSH_DETECTION: bool = _get_bool("ENABLE_SSH_DETECTION", True)
ENABLE_CRYPTO_DETECTION: bool = _get_bool("ENABLE_CRYPTO_DETECTION", True)
ENABLE_API_DETECTION: bool = _get_bool("ENABLE_API_DETECTION", True)

# ── v0.5 Verification ──────────────────────────────────────────────────────
VERIFICATION_TIMEOUT: int = _get_int("VERIFICATION_TIMEOUT", 5)
ENABLE_ETHERSCAN_CHECK: bool = _get_bool("ENABLE_ETHERSCAN_CHECK", True)
ETHERSCAN_API_KEY: str = os.getenv("ETHERSCAN_API_KEY", "")


def get_config_summary() -> dict:
    """Return a summary of current configuration (safe for logging)."""
    return {
        "scan_interval": SCAN_INTERVAL,
        "max_keys_per_report": MAX_KEYS_PER_REPORT,
        "debug": DEBUG,
        "log_level": LOG_LEVEL,
        "censys_configured": bool(CENSYS_API_ID and CENSYS_API_SECRET),
        "github_configured": bool(GITHUB_TOKEN),
        "groq_configured": bool(GROQ_API_KEY),
        "discord_configured": bool(DISCORD_WEBHOOK_URL),
        "data_dir": str(DATA_DIR),
        "autonomous_mode": AUTONOMOUS_MODE,
        "auto_push_github": AUTO_PUSH_GITHUB,
        "allow_auto_restart": ALLOW_AUTO_RESTART,
        "auto_pivot_threshold": AUTO_PIVOT_THRESHOLD,
        "enable_ssh_detection": ENABLE_SSH_DETECTION,
        "enable_crypto_detection": ENABLE_CRYPTO_DETECTION,
        "enable_api_detection": ENABLE_API_DETECTION,
        "verification_timeout": VERIFICATION_TIMEOUT,
        "etherscan_configured": bool(ETHERSCAN_API_KEY),
    }
