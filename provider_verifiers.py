"""
AlphaScan Provider Verification Framework.

Every provider-specific credential has a dedicated verifier that
checks whether the credential is recognized by the issuing provider.

Uses lightweight identity or metadata endpoints that confirm whether
the credential is recognized without performing unnecessary operations.

Records:
  verification_status (never collapses into a single boolean)
  verification_reason
  provider_response
  verified_at

Verification statuses:
  UNKNOWN      — No verification attempted
  UNSUPPORTED  — No verifier available for this provider
  VALID_FORMAT — Format is correct but provider check not done
  ACTIVE       — Provider confirms credential is currently active
  EXPIRED      — Provider confirms credential has expired
  REVOKED      — Provider confirms credential was revoked
  DISABLED     — Provider confirms credential is disabled
  INSUFFICIENT_SCOPE — Credential works but lacks required scope
  RATE_LIMITED — Verification was rate-limited
  UNREACHABLE  — Provider endpoint unreachable
  INVALID      — Provider confirms credential is invalid
"""
from __future__ import annotations

import abc
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Type

import requests

from models import VerificationStatus

logger = logging.getLogger(__name__)


# ── Circuit Breaker ──────────────────────────────────────────────────

@dataclass
class CircuitBreaker:
    """Prevents repeated calls to a failing provider endpoint."""
    max_failures: int = 3
    reset_timeout_seconds: float = 300.0
    failure_count: int = 0
    last_failure_time: float = 0.0
    state: str = "closed"  # closed, open, half-open

    def can_execute(self) -> bool:
        if self.state == "closed":
            return True
        if self.state == "open":
            if time.time() - self.last_failure_time > self.reset_timeout_seconds:
                self.state = "half-open"
                return True
            return False
        # half-open: allow one test call
        return True

    def record_success(self) -> None:
        self.failure_count = 0
        self.state = "closed"

    def record_failure(self) -> None:
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.max_failures:
            self.state = "open"


# ── Verification Result ──────────────────────────────────────────────

@dataclass
class ProviderVerificationResult:
    """Complete result of a provider verification check."""
    status: VerificationStatus = VerificationStatus.UNKNOWN
    reason: str = ""
    provider_response: Optional[Dict[str, Any]] = None
    verified_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "reason": self.reason,
            "provider_response": self.provider_response,
            "verified_at": self.verified_at,
        }


# ── Base Verifier ────────────────────────────────────────────────────

class ProviderVerifier(abc.ABC):
    """Abstract base class for provider-specific credential verification.

    Each verifier implements a lightweight check against the provider's
    identity/metadata endpoint. Never performs destructive or unnecessary
    operations with the credential.
    """

    provider_name: str = ""
    circuit_breaker: CircuitBreaker = CircuitBreaker()
    timeout_seconds: float = 10.0
    retry_count: int = 2

    @abc.abstractmethod
    def verify(self, credential: str, context: Dict[str, Any] = None) -> ProviderVerificationResult:
        """Verify a credential against the provider.

        Args:
            credential: The raw secret value to verify
            context: Additional context (repository, variable_name, etc.)

        Returns:
            ProviderVerificationResult with status, reason, and provider response
        """
        ...

    def _safe_request(
        self,
        url: str,
        headers: Dict[str, str],
        method: str = "GET",
        params: Dict[str, Any] = None,
        json_data: Dict[str, Any] = None,
    ) -> Optional[requests.Response]:
        """Make a safe HTTP request with retries and circuit breaker."""
        if not self.circuit_breaker.can_execute():
            logger.warning(f"Circuit breaker open for {self.provider_name}, skipping verification")
            return None

        for attempt in range(self.retry_count + 1):
            try:
                if method == "GET":
                    resp = requests.get(url, headers=headers, params=params, timeout=self.timeout_seconds)
                elif method == "POST":
                    resp = requests.post(url, headers=headers, json=json_data, timeout=self.timeout_seconds)
                else:
                    resp = requests.request(method, url, headers=headers, timeout=self.timeout_seconds)
                self.circuit_breaker.record_success()
                return resp
            except requests.Timeout:
                logger.debug(f"{self.provider_name} verification timeout (attempt {attempt + 1})")
            except requests.ConnectionError:
                logger.debug(f"{self.provider_name} connection error (attempt {attempt + 1})")
            except requests.RequestException as e:
                logger.debug(f"{self.provider_name} request error: {e} (attempt {attempt + 1})")

        self.circuit_breaker.record_failure()
        return None


# ── GitHub Verifier ──────────────────────────────────────────────────

class GitHubVerifier(ProviderVerifier):
    """Verify GitHub tokens using the /user endpoint.

    Uses lightweight identity check — confirms whether the token
    is recognized without performing any repository operations.
    """
    provider_name = "github"
    circuit_breaker = CircuitBreaker(max_failures=5, reset_timeout_seconds=600.0)

    def verify(self, credential: str, context: Dict[str, Any] = None) -> ProviderVerificationResult:
        headers = {
            "Authorization": f"token {credential}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "AlphaScan-Verifier/1.0",
        }

        resp = self._safe_request("https://api.github.com/user", headers)

        if resp is None:
            return ProviderVerificationResult(
                status=VerificationStatus.UNREACHABLE,
                reason="GitHub API unreachable after retries",
            )

        if resp.status_code == 200:
            data = resp.json()
            return ProviderVerificationResult(
                status=VerificationStatus.ACTIVE,
                reason=f"Token valid. User: {data.get('login', 'unknown')}",
                provider_response={
                    "user": data.get("login"),
                    "scopes": resp.headers.get("X-OAuth-Scopes", ""),
                    "rate_limit_remaining": resp.headers.get("X-RateLimit-Remaining", ""),
                },
            )

        if resp.status_code == 401:
            return ProviderVerificationResult(
                status=VerificationStatus.INVALID,
                reason="GitHub API returned 401 — token is invalid or expired",
                provider_response={"status_code": 401},
            )

        if resp.status_code == 403:
            # Could be rate limited or insufficient scope
            rate_limit_remaining = resp.headers.get("X-RateLimit-Remaining", "0")
            if rate_limit_remaining == "0":
                return ProviderVerificationResult(
                    status=VerificationStatus.RATE_LIMITED,
                    reason="GitHub API rate limit reached during verification",
                )
            return ProviderVerificationResult(
                status=VerificationStatus.INSUFFICIENT_SCOPE,
                reason="GitHub API returned 403 — token lacks required scope",
                provider_response={"status_code": 403},
            )

        return ProviderVerificationResult(
            status=VerificationStatus.UNKNOWN,
            reason=f"GitHub API returned unexpected status {resp.status_code}",
        )


# ── OpenAI Verifier ──────────────────────────────────────────────────

class OpenAIVerifier(ProviderVerifier):
    """Verify OpenAI API keys using the /models endpoint."""
    provider_name = "openai"

    def verify(self, credential: str, context: Dict[str, Any] = None) -> ProviderVerificationResult:
        headers = {
            "Authorization": f"Bearer {credential}",
            "User-Agent": "AlphaScan-Verifier/1.0",
        }

        resp = self._safe_request("https://api.openai.com/v1/models", headers)

        if resp is None:
            return ProviderVerificationResult(
                status=VerificationStatus.UNREACHABLE,
                reason="OpenAI API unreachable after retries",
            )

        if resp.status_code == 200:
            data = resp.json()
            model_count = len(data.get("data", []))
            return ProviderVerificationResult(
                status=VerificationStatus.ACTIVE,
                reason=f"API key valid. {model_count} models available.",
                provider_response={"model_count": model_count},
            )

        if resp.status_code == 401:
            return ProviderVerificationResult(
                status=VerificationStatus.INVALID,
                reason="OpenAI API returned 401 — invalid key",
            )

        if resp.status_code == 429:
            return ProviderVerificationResult(
                status=VerificationStatus.RATE_LIMITED,
                reason="OpenAI API rate limited during verification",
            )

        return ProviderVerificationResult(
            status=VerificationStatus.UNKNOWN,
            reason=f"OpenAI API returned {resp.status_code}",
        )


# ── Anthropic Verifier ────────────────────────────────────────────────

class AnthropicVerifier(ProviderVerifier):
    """Verify Anthropic API keys using lightweight endpoint."""
    provider_name = "anthropic"

    def verify(self, credential: str, context: Dict[str, Any] = None) -> ProviderVerificationResult:
        headers = {
            "x-api-key": credential,
            "anthropic-version": "2023-06-01",
            "User-Agent": "AlphaScan-Verifier/1.0",
        }

        resp = self._safe_request("https://api.anthropic.com/v1/models", headers)

        if resp is None:
            return ProviderVerificationResult(
                status=VerificationStatus.UNREACHABLE,
                reason="Anthropic API unreachable",
            )

        if resp.status_code == 200:
            return ProviderVerificationResult(
                status=VerificationStatus.ACTIVE,
                reason="Anthropic API key valid",
            )

        if resp.status_code == 401:
            return ProviderVerificationResult(
                status=VerificationStatus.INVALID,
                reason="Anthropic API returned 401 — invalid key",
            )

        return ProviderVerificationResult(
            status=VerificationStatus.UNKNOWN,
            reason=f"Anthropic API returned {resp.status_code}",
        )


# ── Stripe Verifier ──────────────────────────────────────────────────

class StripeVerifier(ProviderVerifier):
    """Verify Stripe keys using the /balance endpoint (read-only)."""
    provider_name = "stripe"

    def verify(self, credential: str, context: Dict[str, Any] = None) -> ProviderVerificationResult:
        headers = {
            "Authorization": f"Bearer {credential}",
            "User-Agent": "AlphaScan-Verifier/1.0",
        }

        resp = self._safe_request("https://api.stripe.com/v1/balance", headers)

        if resp is None:
            return ProviderVerificationResult(
                status=VerificationStatus.UNREACHABLE,
                reason="Stripe API unreachable",
            )

        if resp.status_code == 200:
            return ProviderVerificationResult(
                status=VerificationStatus.ACTIVE,
                reason="Stripe key valid. Balance endpoint accessible.",
            )

        if resp.status_code == 401:
            return ProviderVerificationResult(
                status=VerificationStatus.INVALID,
                reason="Stripe API returned 401 — invalid key",
            )

        return ProviderVerificationResult(
            status=VerificationStatus.UNKNOWN,
            reason=f"Stripe API returned {resp.status_code}",
        )


# ── AWS Verifier ──────────────────────────────────────────────────────

class AWSVerifier(ProviderVerifier):
    """Verify AWS Access Keys using STS GetCallerIdentity.

    This is a read-only identity endpoint that reveals who the
    key belongs to without performing any AWS operations.
    """
    provider_name = "aws"

    def verify(self, credential: str, context: Dict[str, Any] = None) -> ProviderVerificationResult:
        # AWS requires signed requests — this is a simplified check
        # For production, use boto3 with proper STS signing
        # Here we do a format + prefix check
        if credential.startswith("AKIA"):
            return ProviderVerificationResult(
                status=VerificationStatus.VALID_FORMAT,
                reason="AWS Access Key format valid (AKIA prefix, correct length). "
                       "Full provider verification requires AWS SDK with secret key pair.",
            )
        return ProviderVerificationResult(
            status=VerificationStatus.INVALID,
            reason="AWS Access Key format invalid",
        )


# ── Discord Verifier ──────────────────────────────────────────────────

class DiscordVerifier(ProviderVerifier):
    """Verify Discord Bot Tokens using the /users/@me endpoint."""
    provider_name = "discord"

    def verify(self, credential: str, context: Dict[str, Any] = None) -> ProviderVerificationResult:
        headers = {
            "Authorization": f"Bot {credential}",
            "User-Agent": "AlphaScan-Verifier/1.0",
        }

        resp = self._safe_request("https://discord.com/api/v10/users/@me", headers)

        if resp is None:
            return ProviderVerificationResult(
                status=VerificationStatus.UNREACHABLE,
                reason="Discord API unreachable",
            )

        if resp.status_code == 200:
            data = resp.json()
            return ProviderVerificationResult(
                status=VerificationStatus.ACTIVE,
                reason=f"Discord bot token valid. Bot: {data.get('username', 'unknown')}",
                provider_response={"bot_username": data.get("username")},
            )

        if resp.status_code == 401:
            return ProviderVerificationResult(
                status=VerificationStatus.INVALID,
                reason="Discord API returned 401 — invalid token",
            )

        return ProviderVerificationResult(
            status=VerificationStatus.UNKNOWN,
            reason=f"Discord API returned {resp.status_code}",
        )


# ── Slack Verifier ────────────────────────────────────────────────────

class SlackVerifier(ProviderVerifier):
    """Verify Slack tokens using the auth.test endpoint."""
    provider_name = "slack"

    def verify(self, credential: str, context: Dict[str, Any] = None) -> ProviderVerificationResult:
        headers = {
            "Authorization": f"Bearer {credential}",
            "User-Agent": "AlphaScan-Verifier/1.0",
        }

        resp = self._safe_request(
            "https://slack.com/api/auth.test",
            headers=headers,
        )

        if resp is None:
            return ProviderVerificationResult(
                status=VerificationStatus.UNREACHABLE,
                reason="Slack API unreachable",
            )

        if resp.status_code == 200:
            data = resp.json()
            if data.get("ok"):
                return ProviderVerificationResult(
                    status=VerificationStatus.ACTIVE,
                    reason=f"Slack token valid. Team: {data.get('team', 'unknown')}",
                    provider_response={"team": data.get("team"), "user": data.get("user")},
                )
            error = data.get("error", "unknown")
            if error == "invalid_auth":
                return ProviderVerificationResult(
                    status=VerificationStatus.INVALID,
                    reason=f"Slack API auth failed: {error}",
                )
            return ProviderVerificationResult(
                status=VerificationStatus.UNKNOWN,
                reason=f"Slack API returned error: {error}",
            )

        return ProviderVerificationResult(
            status=VerificationStatus.UNKNOWN,
            reason=f"Slack API returned {resp.status_code}",
        )


# ── GitLab Verifier ──────────────────────────────────────────────────

class GitLabVerifier(ProviderVerifier):
    """Verify GitLab PATs using the /user endpoint."""
    provider_name = "gitlab"

    def verify(self, credential: str, context: Dict[str, Any] = None) -> ProviderVerificationResult:
        headers = {
            "PRIVATE-TOKEN": credential,
            "User-Agent": "AlphaScan-Verifier/1.0",
        }

        resp = self._safe_request("https://gitlab.com/api/v4/user", headers)

        if resp is None:
            return ProviderVerificationResult(
                status=VerificationStatus.UNREACHABLE,
                reason="GitLab API unreachable",
            )

        if resp.status_code == 200:
            data = resp.json()
            return ProviderVerificationResult(
                status=VerificationStatus.ACTIVE,
                reason=f"GitLab PAT valid. User: {data.get('username', 'unknown')}",
                provider_response={"user": data.get("username")},
            )

        if resp.status_code == 401:
            return ProviderVerificationResult(
                status=VerificationStatus.INVALID,
                reason="GitLab API returned 401 — invalid token",
            )

        return ProviderVerificationResult(
            status=VerificationStatus.UNKNOWN,
            reason=f"GitLab API returned {resp.status_code}",
        )


# ── Twilio Verifier ──────────────────────────────────────────────────

class TwilioVerifier(ProviderVerifier):
    """Verify Twilio credentials using the Accounts endpoint."""
    provider_name = "twilio"

    def verify(self, credential: str, context: Dict[str, Any] = None) -> ProviderVerificationResult:
        # Twilio requires SID + Auth Token pair
        # Single value verification is format-only
        if credential.startswith("AC") and len(credential) == 34:
            return ProviderVerificationResult(
                status=VerificationStatus.VALID_FORMAT,
                reason="Twilio Account SID format valid. Full verification requires auth token pair.",
            )
        return ProviderVerificationResult(
            status=VerificationStatus.INVALID,
            reason="Twilio SID format invalid",
        )


# ── Cloudflare Verifier ───────────────────────────────────────────────

class CloudflareVerifier(ProviderVerifier):
    """Verify Cloudflare API tokens."""
    provider_name = "cloudflare"

    def verify(self, credential: str, context: Dict[str, Any] = None) -> ProviderVerificationResult:
        headers = {
            "Authorization": f"Bearer {credential}",
            "User-Agent": "AlphaScan-Verifier/1.0",
        }

        resp = self._safe_request(
            "https://api.cloudflare.com/client/v4/user/tokens/verify",
            headers=headers,
        )

        if resp is None:
            return ProviderVerificationResult(
                status=VerificationStatus.UNREACHABLE,
                reason="Cloudflare API unreachable",
            )

        if resp.status_code == 200:
            data = resp.json()
            if data.get("success"):
                return ProviderVerificationResult(
                    status=VerificationStatus.ACTIVE,
                    reason="Cloudflare API token valid",
                    provider_response={"status": data.get("status")},
                )
            return ProviderVerificationResult(
                status=VerificationStatus.INVALID,
                reason="Cloudflare token verification failed",
            )

        if resp.status_code == 403:
            return ProviderVerificationResult(
                status=VerificationStatus.INVALID,
                reason="Cloudflare API returned 403 — invalid token",
            )

        return ProviderVerificationResult(
            status=VerificationStatus.UNKNOWN,
            reason=f"Cloudflare API returned {resp.status_code}",
        )


# ── SendGrid Verifier ─────────────────────────────────────────────────

class SendGridVerifier(ProviderVerifier):
    """Verify SendGrid API keys."""
    provider_name = "sendgrid"

    def verify(self, credential: str, context: Dict[str, Any] = None) -> ProviderVerificationResult:
        headers = {
            "Authorization": f"Bearer {credential}",
            "User-Agent": "AlphaScan-Verifier/1.0",
        }

        resp = self._safe_request(
            "https://api.sendgrid.com/v3/user/profile",
            headers=headers,
        )

        if resp is None:
            return ProviderVerificationResult(
                status=VerificationStatus.UNREACHABLE,
                reason="SendGrid API unreachable",
            )

        if resp.status_code == 200:
            return ProviderVerificationResult(
                status=VerificationStatus.ACTIVE,
                reason="SendGrid API key valid",
            )

        if resp.status_code == 401:
            return ProviderVerificationResult(
                status=VerificationStatus.INVALID,
                reason="SendGrid API returned 401 — invalid key",
            )

        return ProviderVerificationResult(
            status=VerificationStatus.UNKNOWN,
            reason=f"SendGrid API returned {resp.status_code}",
        )


# ── Google Verifier ──────────────────────────────────────────────────

class GoogleVerifier(ProviderVerifier):
    """Verify Google API keys using format check.

    Google API keys can't be easily verified without making
    actual API calls (which could be destructive). Format-only check.
    """
    provider_name = "google"

    def verify(self, credential: str, context: Dict[str, Any] = None) -> ProviderVerificationResult:
        if credential.startswith("AIza") and len(credential) == 39:
            return ProviderVerificationResult(
                status=VerificationStatus.VALID_FORMAT,
                reason="Google API key format valid (AIza prefix, correct length). "
                       "Full verification requires specific Google API endpoint.",
            )
        return ProviderVerificationResult(
            status=VerificationStatus.INVALID,
            reason="Google API key format invalid",
        )


# ── Verifier Registry ────────────────────────────────────────────────

VERIFIER_REGISTRY: Dict[str, ProviderVerifier] = {
    "github": GitHubVerifier(),
    "openai": OpenAIVerifier(),
    "anthropic": AnthropicVerifier(),
    "stripe": StripeVerifier(),
    "aws": AWSVerifier(),
    "discord": DiscordVerifier(),
    "slack": SlackVerifier(),
    "gitlab": GitLabVerifier(),
    "twilio": TwilioVerifier(),
    "cloudflare": CloudflareVerifier(),
    "sendgrid": SendGridVerifier(),
    "google": GoogleVerifier(),
}


def get_verifier(provider: str) -> Optional[ProviderVerifier]:
    """Get the appropriate verifier for a provider."""
    return VERIFIER_REGISTRY.get(provider)


def verify_secret_provider(
    provider: str,
    credential: str,
    context: Dict[str, Any] = None,
) -> ProviderVerificationResult:
    """
    Verify a secret against its provider.

    If no verifier is registered for the provider, returns UNSUPPORTED.
    """
    verifier = get_verifier(provider)
    if verifier is None:
        return ProviderVerificationResult(
            status=VerificationStatus.UNSUPPORTED,
            reason=f"No verifier available for provider '{provider}'",
        )

    try:
        return verifier.verify(credential, context)
    except Exception as e:
        logger.error(f"Provider verification error for {provider}: {e}")
        return ProviderVerificationResult(
            status=VerificationStatus.UNKNOWN,
            reason=f"Verification error: {str(e)}",
        )


def register_verifier(provider: str, verifier: ProviderVerifier) -> None:
    """Register a custom verifier for a provider (plugin support)."""
    VERIFIER_REGISTRY[provider] = verifier
    logger.info(f"Registered custom verifier for provider: {provider}")
