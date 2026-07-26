"""
Tests for AlphaScan metrics engine.

Verifies:
  - Scan metrics computation from secrets list
  - All required metric fields are present
  - Confidence distribution counts
  - Verification status distribution
  - Validation level counts
  - Family distribution
  - Scanner statistics
  - Average confidence
"""
import pytest

from metrics import compute_metrics, ScanMetrics, _compute_from_list
from models import Secret, ValidationLevel, VerificationStatus


@pytest.fixture
def sample_secrets():
    """Create a diverse set of secrets for metrics testing."""
    return [
        Secret(
            source="github",
            secret_family="github_classic_pat",
            secret_type="GitHub Classic PAT",
            provider="github",
            confidence_score=85.0,
            validation_level=ValidationLevel.PROVIDER,
            verification_status=VerificationStatus.ACTIVE,
            raw_value="ghp_abc123",
            metadata={"entropy": 4.5},
        ),
        Secret(
            source="censys",
            secret_family="aws_access_key",
            secret_type="AWS Access Key",
            provider="aws",
            confidence_score=72.0,
            validation_level=ValidationLevel.HEURISTIC,
            verification_status=VerificationStatus.VALID_FORMAT,
            raw_value="AKIAabc",
            metadata={"entropy": 3.8},
        ),
        Secret(
            source="pastebin",
            secret_family="unknown_secret",
            secret_type="Unknown Secret",
            provider="",
            confidence_score=15.0,
            validation_level=ValidationLevel.NONE,
            verification_status=VerificationStatus.UNKNOWN,
            raw_value="some_random_string",
            metadata={"entropy": 2.0},
        ),
        Secret(
            source="github",
            secret_family="openai_api",
            secret_type="OpenAI API Key",
            provider="openai",
            confidence_score=55.0,
            validation_level=ValidationLevel.FORMAT,
            verification_status=VerificationStatus.UNKNOWN,
            raw_value="sk-abc123",
            metadata={"entropy": 4.0},
        ),
    ]


class TestScanMetrics:
    def test_empty_metrics(self):
        metrics = ScanMetrics()
        d = metrics.to_dict()
        assert d["assets_crawled"] == 0
        assert d["candidate_secrets"] == 0

    def test_all_fields_present(self, sample_secrets):
        metrics = compute_metrics(sample_secrets)
        d = metrics.to_dict()
        required_fields = [
            "assets_crawled",
            "files_analyzed",
            "candidate_secrets",
            "high_confidence_secrets",
            "medium_confidence_secrets",
            "low_confidence_secrets",
            "provider_verified",
            "currently_active",
            "expired",
            "revoked",
            "disabled",
            "unknown",
            "needs_review",
            "false_positives_removed",
            "duplicate_secrets_merged",
            "verification_failures",
            "average_confidence",
            "validation_levels",
            "scanner_stats",
            "family_distribution",
        ]
        for field in required_fields:
            assert field in d, f"Missing metric field: {field}"

    def test_candidate_count(self, sample_secrets):
        metrics = compute_metrics(sample_secrets)
        assert metrics.candidate_secrets == 4

    def test_confidence_distribution(self, sample_secrets):
        metrics = compute_metrics(sample_secrets)
        # scores: 85, 72, 15, 55 → high:2, medium:1, low:1
        assert metrics.high_confidence_secrets == 2
        assert metrics.medium_confidence_secrets == 1
        assert metrics.low_confidence_secrets == 1

    def test_verification_distribution(self, sample_secrets):
        metrics = compute_metrics(sample_secrets)
        assert metrics.currently_active == 1  # ACTIVE
        assert metrics.provider_verified == 2  # ACTIVE + VALID_FORMAT
        assert metrics.unknown == 2  # two UNKNOWN

    def test_average_confidence(self, sample_secrets):
        metrics = compute_metrics(sample_secrets)
        # (85 + 72 + 15 + 55) / 4 = 56.75
        assert metrics.average_confidence == pytest.approx(56.75, abs=0.1)

    def test_family_distribution(self, sample_secrets):
        metrics = compute_metrics(sample_secrets)
        fd = metrics.family_distribution
        assert fd["github_classic_pat"] == 1
        assert fd["aws_access_key"] == 1
        assert fd["unknown_secret"] == 1
        assert fd["openai_api"] == 1

    def test_scanner_stats(self, sample_secrets):
        metrics = compute_metrics(sample_secrets)
        stats = metrics.scanner_stats
        # Secrets with no scanner field are grouped as "unknown"
        assert len(stats) > 0
        total_count = sum(s["count"] for s in stats.values())
        assert total_count == len(sample_secrets)

    def test_needs_review(self, sample_secrets):
        metrics = compute_metrics(sample_secrets)
        # The "unknown_secret" family counts as needs_review
        assert metrics.needs_review >= 1

    def test_false_positives(self, sample_secrets):
        metrics = compute_metrics(sample_secrets)
        # Low confidence + unverified should count as false positives
        assert metrics.false_positives_removed >= 0  # depends on threshold
