"""AlphaScan API key verifier."""
import logging
import time
from typing import Any, Dict, Optional

import requests

from config import CENSYS_PAT, GITHUB_TOKEN, MISTRAL_API_KEY, DISCORD_WEBHOOK_URL

logger = logging.getLogger(__name__)


class VerificationResult:
    """Stores API key verification results."""

    def __init__(self):
        self.censys_ok = False
        self.github_ok = False
        self.mistral_ok = False
        self.discord_ok = False
        self.abort_reason = ""

    @property
    def critical_failed(self) -> bool:
        """Check if any critical key failed."""
        return bool(self.abort_reason)


def verify_censys(pat: str) -> bool:
    """Verify Censys PAT is valid."""
    if not pat:
        return False
    try:
        headers = {
            "Authorization": f"Bearer {pat}",
            "Accept": "application/json",
            "User-Agent": "AlphaScan/1.0",
        }
        resp = requests.get(
            "https://api.platform.censys.io/v3/hosts/search",
            headers=headers,
            params={"q": "api_key", "per_page": 1},
            timeout=15,
        )
        return resp.status_code == 200
    except Exception as e:
        logger.debug(f"Censys verification failed: {e}")
        return False


def verify_github(token: str) -> bool:
    """Verify GitHub token is valid."""
    if not token:
        return False
    try:
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
        }
        resp = requests.get(
            "https://api.github.com/user",
            headers=headers,
            timeout=10,
        )
        return resp.status_code == 200
    except Exception as e:
        logger.debug(f"GitHub verification failed: {e}")
        return False


def verify_mistral(api_key: str) -> bool:
    """Verify Mistral API key is valid."""
    if not api_key:
        return False
    try:
        from mistralai import Mistral
        client = Mistral(api_key=api_key)
        response = client.chat.complete(
            model="mistral-small-latest",
            messages=[{"role": "user", "content": "Say OK"}],
            max_tokens=5,
        )
        return bool(response.choices)
    except Exception as e:
        logger.debug(f"Mistral verification failed: {e}")
        return False


def verify_discord(webhook_url: str) -> bool:
    """Verify Discord webhook is valid."""
    if not webhook_url:
        return False
    try:
        resp = requests.post(
            webhook_url,
            json={"content": "AlphaScan verification test"},
            timeout=10,
        )
        return resp.status_code in (200, 204)
    except Exception as e:
        logger.debug(f"Discord verification failed: {e}")
        return False


def verify_all_api_keys() -> VerificationResult:
    """Verify all configured API keys."""
    result = VerificationResult()

    result.censys_ok = verify_censys(CENSYS_PAT)
    result.github_ok = verify_github(GITHUB_TOKEN)
    result.mistral_ok = verify_mistral(MISTRAL_API_KEY)
    result.discord_ok = verify_discord(DISCORD_WEBHOOK_URL)

    if CENSYS_PAT and not result.censys_ok:
        result.abort_reason = "Censys PAT is invalid or expired. Get a new one at https://console.censys.io/api"

    if GITHUB_TOKEN and not result.github_ok:
        result.abort_reason = "GitHub token is invalid or expired."

    if MISTRAL_API_KEY and not result.mistral_ok:
        result.abort_reason = "Mistral API key is invalid."

    return result


def should_abort_scan(verification: VerificationResult) -> bool:
    """Determine if scan should be aborted based on verification."""
    return verification.critical_failed