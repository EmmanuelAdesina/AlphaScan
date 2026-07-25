"""
AlphaScan configuration.
Loads all API keys and settings from environment variables.
No classes. No abstractions. Just config.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ── Required API Credentials ──────────────────────────────────────
CENSYS_PAT = os.getenv("CENSYS_PAT", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")
ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY", "")

# ── Application Settings ──────────────────────────────────────────
DEBUG = os.getenv("DEBUG", "false").lower() in ("1", "true", "yes")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
QUIET_MODE = os.getenv("QUIET_MODE", "false").lower() in ("1", "true", "yes")

# ── Scan Settings ─────────────────────────────────────────────────
SCAN_INTERVAL = int(os.getenv("SCAN_INTERVAL", "300"))
MAX_KEYS_PER_REPORT = int(os.getenv("MAX_KEYS_PER_REPORT", "50"))

# ── Censys query rotation ─────────────────────────────────────────
CENSYS_QUERIES = [
    'services.http.response.body:"AKIA"',
    'services.http.response.body:"ghp_"',
    'services.http.response.body:"sk_live_"',
    'services.http.response.body:"sk_test_"',
    'services.http.response.body:"sk-"',
    'services.http.response.body:"-----BEGIN RSA PRIVATE KEY"',
    'services.http.response.body:"-----BEGIN OPENSSH PRIVATE KEY"',
    'services.http.response.body:"-----BEGIN EC PRIVATE KEY"',
    'services.http.response.body:"-----BEGIN DSA PRIVATE KEY"',
    'services.http.response.body:"AIza"',
    'services.http.response.body:"mongodb://"',
    'services.http.response.body:"postgresql://"',
    'services.http.response.body:"mysql://"',
    'services.http.response.body:"0x[a-fA-F0-9]{64}"',
    'services.http.response.body:"glpat-"',
    'services.http.response.body:"SG."',
    'services.http.response.body:"BEGIN PRIVATE KEY"',
    'services.http.response.body:"api_key" AND "http.api.key"',
    'services.http.response.body:"secret_key"',
    'services.http.response.body:"access_token"',
]
CENSYS_QUERY_INDEX = int(os.getenv("CENSYS_QUERY_INDEX", "0"))
CENSYS_PAGES_PER_QUERY = int(os.getenv("CENSYS_PAGES_PER_QUERY", "2"))

# ── GitHub search query ───────────────────────────────────────────
GITHUB_SEARCH_QUERY = os.getenv(
    "GITHUB_SEARCH_QUERY",
    'filename:.env OR filename:config.py OR filename:settings.py '
    'extension:json "api_key" -is:fork',
)

# ── Deduplication ─────────────────────────────────────────────────
DEDUPLICATE_BY_IP = os.getenv("DEDUPLICATE_BY_IP", "true").lower() in ("1", "true", "yes")
DEDUPLICATE_BY_URL = os.getenv("DEDUPLICATE_BY_URL", "true").lower() in ("1", "true", "yes")
DEDUPLICATE_BY_CONTENT_HASH = os.getenv("DEDUPLICATE_BY_CONTENT_HASH", "true").lower() in ("1", "true", "yes")


def get_censys_query() -> str:
    """Return the next Censys query in rotation."""
    idx = CENSYS_QUERY_INDEX % len(CENSYS_QUERIES)
    return CENSYS_QUERIES[idx]


def advance_censys_query() -> None:
    """Advance the global query index for next scan cycle."""
    global CENSYS_QUERY_INDEX
    CENSYS_QUERY_INDEX = (CENSYS_QUERY_INDEX + 1) % len(CENSYS_QUERIES)


def check_config():
    """Return dict of which services are configured."""
    return {
        "censys": bool(CENSYS_PAT),
        "github": bool(GITHUB_TOKEN),
        "mistral": bool(MISTRAL_API_KEY),
        "discord": bool(DISCORD_WEBHOOK_URL),
        "etherscan": bool(ETHERSCAN_API_KEY),
    }