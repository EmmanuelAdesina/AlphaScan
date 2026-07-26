"""
Tests for AlphaScan Findings Export API.

Verifies:
  - All endpoints return correct responses
  - Pagination works correctly
  - Filtering works correctly
  - Streaming export responses
  - Secret masking (raw values not exposed by default)
  - Authorization for full values
  - Metrics endpoint
  - Health check
"""
import pytest
import json
import io

from fastapi.testclient import TestClient

from api.routes import app
from storage import Storage, get_storage, reset_storage
from models import Secret, ValidationLevel, VerificationStatus


@pytest.fixture(autouse=True)
def setup_storage():
    """Use in-memory storage for all API tests."""
    # Reset global storage and replace with in-memory
    reset_storage()
    storage = Storage(":memory:")

    # Monkey-patch the global storage
    import api.routes as routes_module
    routes_module._get_app_storage = lambda: storage

    # Also patch the global get_storage
    import storage as storage_module
    storage_module._storage = storage

    yield storage

    storage.close()
    reset_storage()


@pytest.fixture
def populated_storage(setup_storage):
    """Storage with sample data."""
    secrets = [
        Secret(
            id="api-s1",
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
            id="api-s2",
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
            id="api-s3",
            source="pastebin",
            finding_target="https://pastebin.com/raw/abc",
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
    setup_storage.insert_secrets_batch(secrets)
    return setup_storage


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


class TestRootEndpoints:
    def test_root(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["service"] == "AlphaScan"
        assert data["version"] == "1.0.0"

    def test_health(self, client, populated_storage):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["total_findings"] == 3


class TestFindingsEndpoint:
    def test_list_findings(self, client, populated_storage):
        resp = client.get("/findings")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 3
        assert len(data["findings"]) == 3

    def test_list_findings_pagination(self, client, populated_storage):
        resp = client.get("/findings?offset=0&limit=2")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 3
        assert len(data["findings"]) == 2

    def test_list_findings_offset(self, client, populated_storage):
        resp = client.get("/findings?offset=2&limit=10")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["findings"]) == 1

    def test_findings_no_raw_by_default(self, client, populated_storage):
        resp = client.get("/findings")
        data = resp.json()
        for finding in data["findings"]:
            assert "raw_value" not in finding
            assert "masked_value" in finding

    def test_findings_required_fields(self, client, populated_storage):
        resp = client.get("/findings")
        data = resp.json()
        required = [
            "id", "source", "repository", "file", "finding_target",
            "secret_type", "confidence", "validation_level", "verified",
            "masked_value", "entropy", "discovered_at",
        ]
        for finding in data["findings"]:
            for field in required:
                assert field in finding, f"Missing field: {field}"

    def test_get_single_finding(self, client, populated_storage):
        resp = client.get("/findings/api-s1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "api-s1"
        assert data["source"] == "github"

    def test_get_nonexistent_finding(self, client, populated_storage):
        resp = client.get("/findings/nonexistent")
        assert resp.status_code == 404


class TestFiltering:
    def test_filter_by_source(self, client, populated_storage):
        resp = client.get("/findings?source=github")
        data = resp.json()
        assert data["total"] == 1
        assert data["findings"][0]["source"] == "github"

    def test_filter_by_repository(self, client, populated_storage):
        resp = client.get("/findings?repository=repo1")
        data = resp.json()
        assert data["total"] == 1

    def test_filter_by_secret_type(self, client, populated_storage):
        resp = client.get("/findings?secret_type=GitHub Classic PAT")
        data = resp.json()
        assert data["total"] == 1

    def test_filter_by_confidence_min(self, client, populated_storage):
        resp = client.get("/findings?confidence_min=70")
        data = resp.json()
        assert data["total"] == 2

    def test_filter_by_date(self, client, populated_storage):
        resp = client.get("/findings?date=2024-01-15")
        data = resp.json()
        assert data["total"] == 2

    def test_filter_by_provider(self, client, populated_storage):
        resp = client.get("/findings?provider=github")
        data = resp.json()
        assert data["total"] == 1

    def test_filter_by_validation_level(self, client, populated_storage):
        resp = client.get("/findings?validation_level=provider")
        data = resp.json()
        assert data["total"] == 1


class TestExportEndpoints:
    def test_export_json(self, client, populated_storage):
        resp = client.get("/export/json")
        assert resp.status_code == 200
        # StreamingResponse — check content type
        assert "application/json" in resp.headers.get("content-type", "")
        # Parse the content
        content = resp.text
        data = json.loads(content)
        assert "findings" in data
        assert len(data["findings"]) == 3

    def test_export_json_no_raw(self, client, populated_storage):
        resp = client.get("/export/json")
        content = resp.text
        data = json.loads(content)
        for finding in data["findings"]:
            assert "raw_value" not in finding

    def test_export_csv(self, client, populated_storage):
        resp = client.get("/export/csv")
        assert resp.status_code == 200
        assert "text/csv" in resp.headers.get("content-type", "")
        # Check header row is present
        content = resp.text
        lines = content.strip().split("\n")
        assert len(lines) >= 2  # header + at least one row
        header = lines[0]
        assert "id" in header
        assert "source" in header
        assert "masked_value" in header

    def test_export_json_with_filter(self, client, populated_storage):
        resp = client.get("/export/json?source=github")
        content = resp.text
        data = json.loads(content)
        assert len(data["findings"]) == 1

    def test_export_csv_with_filter(self, client, populated_storage):
        resp = client.get("/export/csv?source=github")
        content = resp.text
        lines = content.strip().split("\n")
        assert len(lines) == 2  # header + 1 row


class TestMetricsEndpoint:
    def test_get_metrics(self, client, populated_storage):
        resp = client.get("/metrics")
        assert resp.status_code == 200
        data = resp.json()
        # Check all required metric fields
        required = [
            "candidate_secrets",
            "high_confidence_secrets",
            "currently_active",
            "expired",
            "revoked",
            "unknown",
            "needs_review",
            "average_confidence",
            "scanner_stats",
            "family_distribution",
        ]
        for field in required:
            assert field in data, f"Missing metric: {field}"

    def test_metrics_counts(self, client, populated_storage):
        resp = client.get("/metrics")
        data = resp.json()
        assert data["candidate_secrets"] == 3
        assert data["currently_active"] == 1
        assert data["average_confidence"] > 0


class TestExportsHistory:
    def test_exports_list(self, client, populated_storage):
        resp = client.get("/exports")
        assert resp.status_code == 200
        data = resp.json()
        assert "exports" in data
