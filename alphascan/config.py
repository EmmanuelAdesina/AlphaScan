"""
AlphaScan configuration.
Loads all API keys and settings from environment variables.
No classes. No abstractions. Just config.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ── Required API Credentials ──────────────────────────────────────
CENSYS_API_ID = os.getenv("CENSYS_API_ID", "")
CENSYS_API_SECRET = os.getenv("CENSYS_API_SECRET", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")
ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY", "")

# ── Scan Settings ─────────────────────────────────────────────────
SCAN_INTERVAL = int(os.getenv("SCAN_INTERVAL", "300"))
MAX_KEYS_PER_REPORT = int(os.getenv("MAX_KEYS_PER_REPORT", "50"))

# ── Censys query ──────────────────────────────────────────────────
CENSYS_QUERY = os.getenv(
    "CENSYS_QUERY",
    '"http.api.key" OR "api_key" OR "secret_key" OR "access_token" '
    'OR "private_key" OR "BEGIN PRIVATE KEY" OR "BEGIN OPENSSH"',
)

# ── GitHub search query ───────────────────────────────────────────
GITHUB_SEARCH_QUERY = os.getenv(
    "GITHUB_SEARCH_QUERY",
    'filename:.env OR filename:config.py OR filename:settings.py '
    'extension:json "api_key" -is:fork',
)


def check_config():
    """Return dict of which services are configured."""
    return {
        "censys": bool(CENSYS_API_ID and CENSYS_API_SECRET),
        "github": bool(GITHUB_TOKEN),
        "groq": bool(GROQ_API_KEY),
        "discord": bool(DISCORD_WEBHOOK_URL),
        "etherscan": bool(ETHERSCAN_API_KEY),
    }