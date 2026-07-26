"""
Tests for AlphaScan deduplication engine.

Verifies:
  - Identical secrets are merged
  - Different secrets remain separate
  - Occurrence tracking (count, repositories, files)
  - History entries for duplicate sightings
  - Confidence score and validation level merging
  - Deduplication statistics
"""
import pytest

from deduplication import deduplicate_secrets, DeduplicationResult
from models import Secret, ValidationLevel, VerificationStatus, HistoryEntry


@pytest.fixture
def duplicate_secrets():
    """Create duplicate secrets (same value, different sources)."""
    return [
        Secret(
            source="github",
            finding_target="https://github.com/org/repo",
            repository="org/repo",
            file=".env",
            secret_family="github_classic_pat",
            secret_type="GitHub Classic PAT",
            provider="github",
            confidence_score=85.0,
            raw_value="ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
            validation_level=ValidationLevel.PROVIDER,
            verification_status=VerificationStatus.ACTIVE,
            discovered_at="2024-01-15T10:00:00",
        ),
        Secret(
            source="pastebin",
            finding_target="https://pastebin.com/raw/abc",
            repository="org/other-repo",
            file="config.py",
            secret_family="github_classic_pat",
            secret_type="GitHub Classic PAT",
            provider="github",
            confidence_score=75.0,
            raw_value="ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
            validation_level=ValidationLevel.HEURISTIC,
            verification_status=VerificationStatus.UNKNOWN,
            discovered_at="2024-01-15T14:00:00",
        ),
        Secret(
            source="censys",
            finding_target="1.2.3.4:443",
            repository="org/repo",
            file="settings.py",
            secret_family="github_classic_pat",
            secret_type="GitHub Classic PAT",
            provider="github",
            confidence_score=90.0,
            raw_value="ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
            validation_level=ValidationLevel.ACTIVE,
            verification_status=VerificationStatus.ACTIVE,
            discovered_at="2024-01-16T08:00:00",
        ),
    ]


@pytest.fixture
def unique_secrets():
    """Create unique secrets (different values)."""
    return [
        Secret(
            source="github",
            raw_value="ghp_ABC_VALUE_1",
            secret_type="GitHub Classic PAT",
            discovered_at="2024-01-15T10:00:00",
        ),
        Secret(
            source="censys",
            raw_value="AKIAIOSFODNN7EXAMPLE",
            secret_type="AWS Access Key",
            discovered_at="2024-01-15T14:00:00",
        ),
    ]


class TestDeduplication:
    def test_duplicate_merging(self, duplicate_secrets):
        result = deduplicate_secrets(duplicate_secrets)
        assert len(result.unique_secrets) == 1
        assert result.duplicates_found == 2
        assert result.total_input == 3

    def test_occurrence_tracking(self, duplicate_secrets):
        result = deduplicate_secrets(duplicate_secrets)
        secret = result.unique_secrets[0]
        assert secret.metadata.get("occurrences") == 3

    def test_repository_tracking(self, duplicate_secrets):
        result = deduplicate_secrets(duplicate_secrets)
        secret = result.unique_secrets[0]
        repos = secret.metadata.get("repositories", [])
        assert len(repos) >= 2  # at least 2 different repos

    def test_file_tracking(self, duplicate_secrets):
        result = deduplicate_secrets(duplicate_secrets)
        secret = result.unique_secrets[0]
        files = secret.metadata.get("files", [])
        assert len(files) >= 2  # at least 2 different files

    def test_history_entries(self, duplicate_secrets):
        result = deduplicate_secrets(duplicate_secrets)
        secret = result.unique_secrets[0]
        # Should have original discovery + 2 duplicate sightings
        assert len(secret.history) >= 2

    def test_confidence_keeps_highest(self, duplicate_secrets):
        result = deduplicate_secrets(duplicate_secrets)
        secret = result.unique_secrets[0]
        # Should keep the highest confidence (90.0)
        assert secret.confidence_score == 90.0

    def test_validation_level_keeps_highest(self, duplicate_secrets):
        result = deduplicate_secrets(duplicate_secrets)
        secret = result.unique_secrets[0]
        # Should keep the highest validation level (ACTIVE)
        assert secret.validation_level == ValidationLevel.ACTIVE

    def test_unique_secrets_not_merged(self, unique_secrets):
        result = deduplicate_secrets(unique_secrets)
        assert len(result.unique_secrets) == 2
        assert result.duplicates_found == 0

    def test_empty_input(self):
        result = deduplicate_secrets([])
        assert len(result.unique_secrets) == 0
        assert result.duplicates_found == 0

    def test_last_seen_updated(self, duplicate_secrets):
        result = deduplicate_secrets(duplicate_secrets)
        secret = result.unique_secrets[0]
        # Should reflect the most recent sighting
        assert secret.last_seen >= "2024-01-15"
