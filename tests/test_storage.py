"""
Tests for AlphaScan storage module.

Verifies:
  - SQLite-backed storage creation and initialization
  - Secret insert and retrieval
  - Batch insert performance
  - Paginated listing with total count
  - Filtering by source, repository, type, confidence, date, etc.
  - Streaming queries (memory-safe for 100k+ findings)
  - Metrics storage and retrieval
  - Export index tracking
  - In-memory database support for testing
"""
import pytest

from storage import Storage, _build_where, reset_storage, _confidence_category
from models import Secret, ValidationLevel, VerificationStatus


@pytest.fixture
def memory_storage():
    """Create an in-memory SQLite storage for testing."""
    storage = Storage(":memory:")
    yield storage
    storage.close()


@pytest.fixture
def sample_secrets():
    """Create sample secrets for testing."""
    return [
        Secret(
            id="s1",
            source="github",
            finding_target="https://github.com/org/repo1",
            repository="org/repo1",
            file=".env",
            secret_family="github_classic_pat",
            secret_type="GitHub Classic PAT",
            provider="github",
            confidence_score=85.0,
            raw_value="ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
            validation_level=ValidationLevel.PROVIDER,
            verification_status=VerificationStatus.ACTIVE,
            discovered_at="2024-01-15T10:30:00",
            metadata={"entropy": 4.5},
        ),
        Secret(
            id="s2",
            source="censys",
            finding_target="1.2.3.4:443",
            repository="org/repo2",
            file="config/settings.py",
            secret_family="aws_access_key",
            secret_type="AWS Access Key",
            provider="aws",
            confidence_score=70.0,
            raw_value="AKIAIOSFODNN7EXAMPLE",
            validation_level=ValidationLevel.HEURISTIC,
            verification_status=VerificationStatus.VALID_FORMAT,
            discovered_at="2024-01-15T14:00:00",
            metadata={"entropy": 3.8},
        ),
        Secret(
            id="s3",
            source="pastebin",
            finding_target="https://pastebin.com/raw/abc123",
            repository="",
            file="paste.txt",
            secret_family="openai_api",
            secret_type="OpenAI API Key",
            provider="openai",
            confidence_score=45.0,
            raw_value="sk-proj-abcdefghijklmnopqrstuvwxyz",
            validation_level=ValidationLevel.FORMAT,
            verification_status=VerificationStatus.UNKNOWN,
            discovered_at="2024-01-14T08:00:00",
            metadata={"entropy": 4.2},
        ),
    ]


class TestStorageInit:
    def test_memory_db_creation(self, memory_storage):
        assert memory_storage is not None

    def test_count_empty(self, memory_storage):
        assert memory_storage.count_secrets() == 0


class TestSecretInsert:
    def test_insert_single(self, memory_storage, sample_secrets):
        memory_storage.insert_secret(sample_secrets[0])
        assert memory_storage.count_secrets() == 1

    def test_insert_and_retrieve(self, memory_storage, sample_secrets):
        secret = sample_secrets[0]
        memory_storage.insert_secret(secret)
        retrieved = memory_storage.get_secret(secret.id)
        assert retrieved is not None
        assert retrieved.source == secret.source
        assert retrieved.secret_type == secret.secret_type
        assert retrieved.confidence_score == secret.confidence_score
        assert retrieved.raw_value == secret.raw_value

    def test_get_nonexistent(self, memory_storage):
        result = memory_storage.get_secret("nonexistent_id")
        assert result is None


class TestBatchInsert:
    def test_batch_insert(self, memory_storage, sample_secrets):
        memory_storage.insert_secrets_batch(sample_secrets)
        assert memory_storage.count_secrets() == 3

    def test_batch_insert_large(self, memory_storage):
        """Test inserting a large batch to verify performance."""
        secrets = []
        for i in range(500):
            secrets.append(Secret(
                id=f"batch-{i}",
                source="github",
                repository=f"org/repo{i}",
                file=".env",
                secret_type="GitHub Classic PAT",
                secret_family="github_classic_pat",
                provider="github",
                confidence_score=80.0,
                raw_value=f"ghp_{i}_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
                discovered_at=f"2024-01-15T10:{i % 60}:00",
                metadata={"entropy": 4.5},
            ))
        memory_storage.insert_secrets_batch(secrets)
        assert memory_storage.count_secrets() == 500


class TestListSecrets:
    def test_list_all(self, memory_storage, sample_secrets):
        memory_storage.insert_secrets_batch(sample_secrets)
        secrets, total = memory_storage.list_secrets(offset=0, limit=10)
        assert len(secrets) == 3
        assert total == 3

    def test_list_paginated(self, memory_storage, sample_secrets):
        memory_storage.insert_secrets_batch(sample_secrets)
        secrets, total = memory_storage.list_secrets(offset=0, limit=2)
        assert len(secrets) == 2
        assert total == 3

    def test_list_offset(self, memory_storage, sample_secrets):
        memory_storage.insert_secrets_batch(sample_secrets)
        secrets, total = memory_storage.list_secrets(offset=2, limit=10)
        assert len(secrets) == 1
        assert total == 3


class TestFiltering:
    def test_filter_by_source(self, memory_storage, sample_secrets):
        memory_storage.insert_secrets_batch(sample_secrets)
        secrets, total = memory_storage.list_secrets(filters={"source": "github"})
        assert total == 1
        assert secrets[0].source == "github"

    def test_filter_by_repository(self, memory_storage, sample_secrets):
        memory_storage.insert_secrets_batch(sample_secrets)
        secrets, total = memory_storage.list_secrets(filters={"repository": "repo1"})
        assert total == 1

    def test_filter_by_secret_type(self, memory_storage, sample_secrets):
        memory_storage.insert_secrets_batch(sample_secrets)
        secrets, total = memory_storage.list_secrets(filters={"secret_type": "AWS Access Key"})
        assert total == 1

    def test_filter_by_confidence_min(self, memory_storage, sample_secrets):
        memory_storage.insert_secrets_batch(sample_secrets)
        secrets, total = memory_storage.list_secrets(filters={"confidence_min": 70})
        assert total == 2

    def test_filter_by_confidence_max(self, memory_storage, sample_secrets):
        memory_storage.insert_secrets_batch(sample_secrets)
        secrets, total = memory_storage.list_secrets(filters={"confidence_max": 50})
        assert total == 1

    def test_filter_by_validation_level(self, memory_storage, sample_secrets):
        memory_storage.insert_secrets_batch(sample_secrets)
        secrets, total = memory_storage.list_secrets(filters={"validation_level": "provider"})
        assert total == 1

    def test_filter_by_verified_boolean(self, memory_storage, sample_secrets):
        memory_storage.insert_secrets_batch(sample_secrets)
        secrets, total = memory_storage.list_secrets(filters={"verified": True})
        assert total == 2  # active + valid_format

    def test_filter_by_date(self, memory_storage, sample_secrets):
        memory_storage.insert_secrets_batch(sample_secrets)
        secrets, total = memory_storage.list_secrets(filters={"date": "2024-01-15"})
        assert total == 2

    def test_filter_by_provider(self, memory_storage, sample_secrets):
        memory_storage.insert_secrets_batch(sample_secrets)
        secrets, total = memory_storage.list_secrets(filters={"provider": "github"})
        assert total == 1

    def test_combined_filters(self, memory_storage, sample_secrets):
        memory_storage.insert_secrets_batch(sample_secrets)
        secrets, total = memory_storage.list_secrets(
            filters={"source": "github", "confidence_min": 80}
        )
        assert total == 1


class TestStreaming:
    def test_stream_all(self, memory_storage, sample_secrets):
        memory_storage.insert_secrets_batch(sample_secrets)
        streamed = list(memory_storage.stream_secrets())
        assert len(streamed) == 3

    def test_stream_as_dicts(self, memory_storage, sample_secrets):
        memory_storage.insert_secrets_batch(sample_secrets)
        dicts = list(memory_storage.stream_secrets_as_dicts(batch_size=2))
        assert len(dicts) == 3
        for d in dicts:
            assert "id" in d
            assert "source" in d
            assert "raw_value" not in d  # default is masked only

    def test_stream_as_dicts_with_raw(self, memory_storage, sample_secrets):
        memory_storage.insert_secrets_batch(sample_secrets)
        dicts = list(memory_storage.stream_secrets_as_dicts(include_raw=True, batch_size=2))
        assert len(dicts) == 3
        for d in dicts:
            assert "raw_value" in d


class TestMetricsStorage:
    def test_insert_metrics(self, memory_storage):
        metrics_id = memory_storage.insert_metrics({
            "total_findings": 100,
            "high_confidence": 20,
        })
        assert metrics_id is not None

    def test_get_latest_metrics(self, memory_storage):
        memory_storage.insert_metrics({"total": 100})
        memory_storage.insert_metrics({"total": 200})
        result = memory_storage.get_latest_metrics()
        assert result is not None
        assert result["total"] == 200


class TestExportIndex:
    def test_insert_export_index(self, memory_storage):
        export_id = memory_storage.insert_export_index(
            export_date="2024-01-15",
            export_dir="exports/2024-01-15",
            findings_count=50,
        )
        assert export_id is not None

    def test_get_export_history(self, memory_storage):
        memory_storage.insert_export_index("2024-01-15", "exports/2024-01-15", 50)
        memory_storage.insert_export_index("2024-01-14", "exports/2024-01-14", 30)
        history = memory_storage.get_export_history()
        assert len(history) == 2


class TestBuildWhere:
    def test_empty_filters(self):
        where, params = _build_where({})
        assert where == ""
        assert params == []

    def test_source_filter(self):
        where, params = _build_where({"source": "github"})
        assert "source = ?" in where
        assert params == ["github"]

    def test_confidence_range(self):
        where, params = _build_where({"confidence_min": 50, "confidence_max": 90})
        assert "confidence_score >= ?" in where
        assert "confidence_score <= ?" in where
        assert params == [50.0, 90.0]

    def test_date_filter(self):
        where, params = _build_where({"date": "2024-01-15"})
        assert "discovered_at >= ?" in where
        assert "2024-01-15T00:00:00" in params

    def test_verified_true(self):
        where, params = _build_where({"verified": True})
        assert "verification_status IN" in where

    def test_verified_false(self):
        where, params = _build_where({"verified": False})
        assert "verification_status IN" in where


class TestConfidenceCategory:
    def test_category_mapping(self):
        assert _confidence_category(95) == "critical"
        assert _confidence_category(75) == "high"
        assert _confidence_category(50) == "medium"
        assert _confidence_category(25) == "low"
        assert _confidence_category(10) == "unlikely"
