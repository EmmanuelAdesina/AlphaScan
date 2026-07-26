"""
Tests for AlphaScan provider verification framework.

Verifies:
  - Circuit breaker behavior
  - Verification result creation
  - Verifier registry
  - Format-only verification (AWS, Google)
  - Provider verifier base class
  - Custom verifier registration
"""
import pytest

from provider_verifiers import (
    CircuitBreaker,
    ProviderVerificationResult,
    ProviderVerifier,
    GitHubVerifier,
    AWSVerifier,
    GoogleVerifier,
    TwilioVerifier,
    VERIFIER_REGISTRY,
    verify_secret_provider,
    register_verifier,
)
from models import VerificationStatus


class TestCircuitBreaker:
    def test_initial_state_closed(self):
        cb = CircuitBreaker()
        assert cb.state == "closed"
        assert cb.can_execute() is True

    def test_record_success(self):
        cb = CircuitBreaker()
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        assert cb.failure_count == 0
        assert cb.state == "closed"

    def test_open_after_max_failures(self):
        cb = CircuitBreaker(max_failures=3)
        cb.record_failure()
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "open"
        assert cb.can_execute() is False

    def test_half_open_after_timeout(self):
        cb = CircuitBreaker(max_failures=1, reset_timeout_seconds=0.01)
        cb.record_failure()
        assert cb.state == "open"
        import time
        time.sleep(0.02)
        assert cb.can_execute() is True
        assert cb.state == "half-open"


class TestVerificationResult:
    def test_default_result(self):
        result = ProviderVerificationResult()
        assert result.status == VerificationStatus.UNKNOWN
        assert result.reason == ""
        assert result.verified_at is not None

    def test_to_dict(self):
        result = ProviderVerificationResult(
            status=VerificationStatus.ACTIVE,
            reason="Token valid",
            provider_response={"user": "test"},
        )
        d = result.to_dict()
        assert d["status"] == "active"
        assert d["reason"] == "Token valid"
        assert d["provider_response"]["user"] == "test"


class TestVerifierRegistry:
    def test_registry_has_providers(self):
        assert "github" in VERIFIER_REGISTRY
        assert "openai" in VERIFIER_REGISTRY
        assert "anthropic" in VERIFIER_REGISTRY
        assert "stripe" in VERIFIER_REGISTRY
        assert "aws" in VERIFIER_REGISTRY
        assert "discord" in VERIFIER_REGISTRY
        assert "slack" in VERIFIER_REGISTRY
        assert "gitlab" in VERIFIER_REGISTRY
        assert "twilio" in VERIFIER_REGISTRY
        assert "cloudflare" in VERIFIER_REGISTRY
        assert "sendgrid" in VERIFIER_REGISTRY
        assert "google" in VERIFIER_REGISTRY

    def test_verifier_types(self):
        for provider, verifier in VERIFIER_REGISTRY.items():
            assert isinstance(verifier, ProviderVerifier)
            assert verifier.provider_name == provider


class TestAWSVerifier:
    def test_valid_format(self):
        verifier = AWSVerifier()
        result = verifier.verify("AKIAIOSFODNN7EXAMPLE")
        assert result.status == VerificationStatus.VALID_FORMAT
        assert "AKIA prefix" in result.reason

    def test_invalid_format(self):
        verifier = AWSVerifier()
        result = verifier.verify("invalid_key_format")
        assert result.status == VerificationStatus.INVALID


class TestGoogleVerifier:
    def test_valid_format(self):
        verifier = GoogleVerifier()
        key = "AIzaSy" + "A" * 33  # 39 chars total
        result = verifier.verify(key)
        assert result.status == VerificationStatus.VALID_FORMAT

    def test_invalid_format(self):
        verifier = GoogleVerifier()
        result = verifier.verify("invalid_google_key")
        assert result.status == VerificationStatus.INVALID


class TestTwilioVerifier:
    def test_valid_sid_format(self):
        verifier = TwilioVerifier()
        sid = "AC" + "a" * 32  # 34 chars total
        result = verifier.verify(sid)
        assert result.status == VerificationStatus.VALID_FORMAT

    def test_invalid_format(self):
        verifier = TwilioVerifier()
        result = verifier.verify("invalid_twilio")
        assert result.status == VerificationStatus.INVALID


class TestVerifySecretProvider:
    def test_unsupported_provider(self):
        result = verify_secret_provider("nonexistent_provider", "some_value")
        assert result.status == VerificationStatus.UNSUPPORTED
        assert "No verifier" in result.reason

    def test_aws_provider(self):
        result = verify_secret_provider("aws", "AKIAIOSFODNN7EXAMPLE")
        assert result.status == VerificationStatus.VALID_FORMAT

    def test_exception_handling(self):
        """Verify that exceptions are caught and return UNKNOWN status."""
        # Passing an empty credential should not crash
        result = verify_secret_provider("aws", "")
        assert result.status in (VerificationStatus.INVALID, VerificationStatus.UNKNOWN)


class TestCustomVerifier:
    def test_register_custom_verifier(self):
        class CustomVerifier(ProviderVerifier):
            provider_name = "custom_provider"

            def verify(self, credential, context=None):
                return ProviderVerificationResult(
                    status=VerificationStatus.VALID_FORMAT,
                    reason="Custom verification",
                )

        register_verifier("custom_provider", CustomVerifier())
        assert "custom_provider" in VERIFIER_REGISTRY
        result = verify_secret_provider("custom_provider", "test")
        assert result.status == VerificationStatus.VALID_FORMAT
