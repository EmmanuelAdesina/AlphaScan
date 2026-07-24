"""
API Key Verifier for AlphaScan v0.5.

Performs lightweight pre-scan validation of every configured API key by
sending a minimal test request to each provider.  Critical keys (GitHub,
Censys, Etherscan) must all pass or the scan is aborted.  Optional keys
(NVIDIA, Discord) only emit a warning when missing/invalid.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from config.settings import (
    CENSYS_API_ID,
    CENSYS_API_SECRET,
    GITHUB_TOKEN,
    GROQ_API_KEY,
    NVIDIA_API_KEY,
    NVIDIA_BASE_URL,
    ETHERSCAN_API_KEY,
    DISCORD_WEBHOOK_URL,
    QUIET_MODE,
)

logger = logging.getLogger(__name__)


# ── Critical vs Optional classification ─────────────────────────────────────
CRITICAL_KEYS = {"github", "censys", "etherscan"}
OPTIONAL_KEYS = {"groq", "nvidia", "discord"}


@dataclass
class KeyVerificationResult:
    """Result of verifying a single API key."""
    api_name: str
    valid: bool
    critical: bool
    message: str
    details: str = ""

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.api_name}: valid={self.valid} msg={self.message}"


@dataclass
class VerificationReport:
    """Aggregate report for all verified keys."""
    results: List[KeyVerificationResult] = field(default_factory=list)
    all_critical_passed: bool = True
    aborted: bool = False
    abort_reason: str = ""

    @property
    def passed(self) -> List[KeyVerificationResult]:
        return [r for r in self.results if r.valid]

    @property
    def failed(self) -> List[KeyVerificationResult]:
        return [r for r in self.results if not r.valid]

    @property
    def skipped(self) -> List[KeyVerificationResult]:
        return [r for r in self.results if not r.valid and "not set" in r.message.lower()]


def _print_status(emoji: str, message: str) -> None:
    """Print a status line unless in QUIET_MODE."""
    if not QUIET_MODE:
        print(f"{emoji} {message}")


def verify_api_key(
    api_name: str,
    api_key: str,
    test_endpoint: str,
    *,
    headers: Optional[Dict[str, str]] = None,
    auth: Optional[Tuple[str, str]] = None,
    params: Optional[Dict[str, str]] = None,
    critical: bool = False,
    expected_status: int = 200,
) -> KeyVerificationResult:
    """
    Verify a single API key by sending a lightweight test request.

    Args:
        api_name: Human-readable name (e.g. "GitHub").
        api_key: The key/secret value to test.
        test_endpoint: URL to hit for verification.
        headers: Optional request headers (e.g. Authorization).
        auth: Optional (user, password) tuple for Basic auth.
        params: Optional query parameters.
        critical: Whether this key is critical (abort if invalid).
        expected_status: HTTP status code considered successful.

    Returns:
        KeyVerificationResult with validity and message.
    """
    # Empty / placeholder key → treat as "not set"
    if not api_key or api_key.startswith("your_") or api_key == "":
        msg = f"{api_name} not set" + (" (optional, skipping)" if not critical else " (CRITICAL)")
        _print_status("⚠️", msg)
        return KeyVerificationResult(
            api_name=api_name,
            valid=False,
            critical=critical,
            message=msg,
        )

    # Lazy import to avoid hard dependency at module load time
    try:
        from utils.http_client import get_http_client
    except Exception:  # pragma: no cover
        import requests
        try:
            resp = requests.get(test_endpoint, headers=headers, auth=auth, params=params, timeout=10)
            return _evaluate_response(api_name, resp, critical, expected_status)
        except Exception as e:
            msg = f"{api_name} verification failed: {e}"
            _print_status("❌", msg)
            return KeyVerificationResult(api_name, valid=False, critical=critical, message=msg, details=str(e))

    client = get_http_client()
    resp = client.get(test_endpoint, headers=headers, params=params, timeout=10)

    if resp is None:
        msg = f"{api_name} verification failed (no response / network error)"
        _print_status("❌", msg)
        return KeyVerificationResult(api_name, valid=False, critical=critical, message=msg)

    return _evaluate_response(api_name, resp, critical, expected_status)


def _evaluate_response(api_name: str, resp, critical: bool, expected_status: int) -> KeyVerificationResult:
    """Evaluate an HTTP response and return a verification result."""
    status = getattr(resp, "status_code", 0)

    # 200/401/403 tell us the key *format* was accepted by the API; 401/403
    # means the key is invalid/expired.
    if status == expected_status or status == 200:
        details = _extract_rate_limit(api_name, resp)
        msg = f"{api_name} valid"
        if details:
            msg += f" ({details})"
        _print_status("✅", msg)
        return KeyVerificationResult(
            api_name=api_name,
            valid=True,
            critical=critical,
            message=msg,
            details=details,
        )

    if status in (401, 403):
        msg = f"{api_name} invalid (HTTP {status} - unauthorized)"
        _print_status("❌", msg)
        return KeyVerificationResult(api_name, valid=False, critical=critical, message=msg)

    msg = f"{api_name} verification failed (HTTP {status})"
    _print_status("❌", msg)
    return KeyVerificationResult(api_name, valid=False, critical=critical, message=msg)


def _extract_rate_limit(api_name: str, resp) -> str:
    """Extract useful info like rate-limit from response headers/body."""
    try:
        headers = getattr(resp, "headers", {}) or {}
        # GitHub rate limit header
        if "X-RateLimit-Remaining" in headers:
            return f"rate limit: {headers['X-RateLimit-Remaining']}"
        # Generic remaining header
        for h in ("X-RateLimit-Limit", "RateLimit-Limit"):
            if h in headers:
                return f"rate limit: {headers[h]}"
    except Exception:
        pass
    return ""


# ── Provider-specific verifiers ────────────────────────────────────────────

def _verify_github() -> KeyVerificationResult:
    """Verify GitHub token via GET /user."""
    return verify_api_key(
        api_name="GitHub token",
        api_key=GITHUB_TOKEN,
        test_endpoint="https://api.github.com/user",
        headers={"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github+json"},
        critical=True,
    )


def _verify_censys() -> KeyVerificationResult:
    """Verify Censys credentials via GET /api/v1/account."""
    # Censys uses HTTP Basic auth with api_id:api_secret
    combined = f"{CENSYS_API_ID}:{CENSYS_API_SECRET}"
    return verify_api_key(
        api_name="Censys credentials",
        api_key=combined,
        test_endpoint="https://search.censys.io/api/v1/account",
        auth=(CENSYS_API_ID, CENSYS_API_SECRET),
        critical=True,
    )


def _verify_etherscan() -> KeyVerificationResult:
    """Verify Etherscan API key via a lightweight status request."""
    return verify_api_key(
        api_name="Etherscan API key",
        api_key=ETHERSCAN_API_KEY,
        test_endpoint="https://api.etherscan.io/api",
        params={
            "module": "stats",
            "action": "ethsupply",
            "apikey": ETHERSCAN_API_KEY,
        },
        critical=True,
    )


def _verify_groq() -> KeyVerificationResult:
    """Verify Groq API key via GET /openai/v1/models."""
    return verify_api_key(
        api_name="Groq API key",
        api_key=GROQ_API_KEY,
        test_endpoint="https://api.groq.com/openai/v1/models",
        headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
        critical=False,
    )


def _verify_nvidia() -> KeyVerificationResult:
    """Verify NVIDIA NIM API key via GET /v1/models (optional)."""
    return verify_api_key(
        api_name="NVIDIA_API_KEY",
        api_key=NVIDIA_API_KEY,
        test_endpoint=f"{NVIDIA_BASE_URL.rstrip('/')}/models",
        headers={"Authorization": f"Bearer {NVIDIA_API_KEY}"},
        critical=False,
    )


def _verify_discord() -> KeyVerificationResult:
    """Verify Discord webhook (optional - just check it's set)."""
    if not DISCORD_WEBHOOK_URL:
        _print_status("⚠️", "DISCORD_WEBHOOK_URL not set (optional, skipping)")
        return KeyVerificationResult(
            api_name="Discord webhook",
            valid=False,
            critical=False,
            message="DISCORD_WEBHOOK_URL not set (optional, skipping)",
        )
    _print_status("✅", "Discord webhook configured")
    return KeyVerificationResult(
        api_name="Discord webhook",
        valid=True,
        critical=False,
        message="Discord webhook configured",
    )


def verify_all_api_keys() -> VerificationReport:
    """
    Verify every configured API key before scanning begins.

    Prints a clear ✅/❌ status for each key.  Aborts (sets report.aborted)
    if any critical key (GitHub, Censys, Etherscan) is invalid.

    Returns:
        VerificationReport with all results and abort status.
    """
    if not QUIET_MODE:
        print("🔐 Verifying API keys...")

    report = VerificationReport()

    # Critical keys first
    report.results.append(_verify_github())
    report.results.append(_verify_censys())
    report.results.append(_verify_etherscan())

    # Optional keys
    report.results.append(_verify_groq())
    report.results.append(_verify_nvidia())
    report.results.append(_verify_discord())

    # Check critical failures
    critical_failures = [
        r for r in report.results if r.critical and not r.valid
    ]
    if critical_failures:
        report.all_critical_passed = False
        report.aborted = True
        failed_names = ", ".join(r.api_name for r in critical_failures)
        report.abort_reason = (
            f"Critical API key(s) invalid or missing: {failed_names}. "
            f"Aborting scan. Please fix the configuration in .env and retry."
        )
        if not QUIET_MODE:
            print(f"\n❌ {report.abort_reason}")
    else:
        if not QUIET_MODE:
            print("Starting scan...")

    return report


def should_abort_scan(report: VerificationReport) -> bool:
    """Return True if the scan should be aborted based on verification report."""
    return report.aborted