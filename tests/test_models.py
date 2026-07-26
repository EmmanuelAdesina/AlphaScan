"""
Tests for AlphaScan models module.

Verifies:
  - Secret model creation, serialization, masking
  - ValidationLevel enum and descriptions
  - VerificationStatus enum and badges
  - ConfidenceCategory scoring
  - Secret.from_finding conversion (backward compatibility)
  - Finding model backward compatibility
  - Legacy type mapping
"""
import pytest

from models import (
    ConfidenceCategory,
    Finding,
    HistoryEntry,
    Secret,
    ValidationLevel,
    VerificationStatus,
    _map_legacy_type,
)


# ── ValidationLevel ──────────────────────────────────────────────

class TestValidationLevel:
    def test_enum_values(self):
        assert ValidationLevel.NONE.value == "none"
        assert ValidationLevel.FORMAT.value == "format"
        assert ValidationLevel.STRUCTURE.value == "structure"
        assert ValidationLevel.HEURISTIC.value == "heuristic"
        assert ValidationLevel.PROVIDER.value == "provider"
        assert ValidationLevel.ACTIVE.value == "active"

    def test_rank_order(self):
        assert ValidationLevel.NONE.rank < ValidationLevel.FORMAT.rank
        assert ValidationLevel.FORMAT.rank < ValidationLevel.STRUCTURE.rank
        assert ValidationLevel.STRUCTURE.rank < ValidationLevel.HEURISTIC.rank
        assert ValidationLevel.HEURISTIC.rank < ValidationLevel.PROVIDER.rank
        assert ValidationLevel.PROVIDER.rank < ValidationLevel.ACTIVE.rank

    def test_descriptions(self):
        assert "No validation" in ValidationLevel.NONE.description
        assert "Format validated" in ValidationLevel.FORMAT.description
        assert "Provider validated" in ValidationLevel.PROVIDER.description
        assert "Active validated" in ValidationLevel.ACTIVE.description

    def test_from_string(self):
        assert ValidationLevel("format") == ValidationLevel.FORMAT
        assert ValidationLevel("active") == ValidationLevel.ACTIVE


# ── VerificationStatus ───────────────────────────────────────────

class TestVerificationStatus:
    def test_enum_values(self):
        assert VerificationStatus.UNKNOWN.value == "unknown"
        assert VerificationStatus.ACTIVE.value == "active"
        assert VerificationStatus.EXPIRED.value == "expired"
        assert VerificationStatus.REVOKED.value == "revoked"
        assert VerificationStatus.INVALID.value == "invalid"
        assert VerificationStatus.DISABLED.value == "disabled"
        assert VerificationStatus.UNSUPPORTED.value == "unsupported"
        assert VerificationStatus.VALID_FORMAT.value == "valid_format"
        assert VerificationStatus.INSUFFICIENT_SCOPE.value == "insufficient_scope"
        assert VerificationStatus.RATE_LIMITED.value == "rate_limited"
        assert VerificationStatus.UNREACHABLE.value == "unreachable"

    def test_badges(self):
        assert "✅" in VerificationStatus.ACTIVE.badge
        assert "❌" in VerificationStatus.INVALID.badge
        assert "❓" in VerificationStatus.UNKNOWN.badge
        assert "⏰" in VerificationStatus.EXPIRED.badge
        assert "🔒" in VerificationStatus.REVOKED.badge
        assert "⛔" in VerificationStatus.DISABLED.badge

    def test_display_priority(self):
        assert VerificationStatus.ACTIVE.display_priority == 0
        assert VerificationStatus.UNKNOWN.display_priority == 10

    def test_all_statuses_have_badges(self):
        for status in VerificationStatus:
            assert status.badge is not None
            assert len(status.badge) > 0


# ── ConfidenceCategory ───────────────────────────────────────────

class TestConfidenceCategory:
    def test_from_score_ranges(self):
        assert ConfidenceCategory.from_score(98) == ConfidenceCategory.CRITICAL
        assert ConfidenceCategory.from_score(100) == ConfidenceCategory.CRITICAL
        assert ConfidenceCategory.from_score(90) == ConfidenceCategory.CRITICAL
        assert ConfidenceCategory.from_score(70) == ConfidenceCategory.HIGH
        assert ConfidenceCategory.from_score(89) == ConfidenceCategory.HIGH
        assert ConfidenceCategory.from_score(40) == ConfidenceCategory.MEDIUM
        assert ConfidenceCategory.from_score(69) == ConfidenceCategory.MEDIUM
        assert ConfidenceCategory.from_score(20) == ConfidenceCategory.LOW
        assert ConfidenceCategory.from_score(39) == ConfidenceCategory.LOW
        assert ConfidenceCategory.from_score(0) == ConfidenceCategory.UNLIKELY
        assert ConfidenceCategory.from_score(19) == ConfidenceCategory.UNLIKELY


# ── Secret Model ──────────────────────────────────────────────────

class TestSecret:
    def test_default_creation(self):
        secret = Secret()
        assert secret.id
        assert secret.source == ""
        assert secret.confidence_score == 0.0
        assert secret.validation_level == ValidationLevel.NONE
        assert secret.verification_status == VerificationStatus.UNKNOWN

    def test_creation_with_fields(self):
        secret = Secret(
            source="github",
            finding_target="https://github.com/org/repo",
            repository="org/repo",
            file=".env",
            secret_type="GitHub Classic PAT",
            secret_family="github_classic_pat",
            provider="github",
            confidence_score=85.0,
            raw_value="ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
            validation_level=ValidationLevel.PROVIDER,
            verification_status=VerificationStatus.ACTIVE,
        )
        assert secret.source == "github"
        assert secret.confidence_score == 85.0
        assert secret.raw_value == "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        assert secret.masked_value != secret.raw_value
        assert "ghp_" in secret.masked_value

    def test_masked_value_auto_generation(self):
        secret = Secret(raw_value="ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
        assert secret.masked_value != ""
        assert secret.masked_value != secret.raw_value

    def test_mask_empty(self):
        secret = Secret(raw_value="")
        # raw_value is empty (falsy), so __post_init__ won't auto-mask
        # We need to explicitly check empty case
        assert secret.raw_value == ""
        # Test the static _mask method directly
        assert Secret._mask("", "") == "[empty]"

    def test_mask_short_value(self):
        secret = Secret(raw_value="abc12345")
        assert "..." in secret.masked_value

    def test_compute_stable_id_deterministic(self):
        s1 = Secret(source="github", secret_type="GitHub Classic PAT", raw_value="ghp_abc123")
        s2 = Secret(source="github", secret_type="GitHub Classic PAT", raw_value="ghp_abc123")
        assert s1.compute_stable_id() == s2.compute_stable_id()

    def test_compute_stable_id_different(self):
        s1 = Secret(source="github", secret_type="GitHub Classic PAT", raw_value="ghp_abc123")
        s2 = Secret(source="github", secret_type="GitHub Classic PAT", raw_value="ghp_xyz789")
        assert s1.compute_stable_id() != s2.compute_stable_id()

    def test_to_dict_without_raw(self):
        secret = Secret(raw_value="ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", source="github")
        d = secret.to_dict(include_raw=False)
        assert "raw_value" not in d
        assert "masked_value" in d

    def test_to_dict_with_raw(self):
        secret = Secret(raw_value="ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", source="github")
        d = secret.to_dict(include_raw=True)
        assert "raw_value" in d
        assert d["raw_value"] == "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"

    def test_to_export_dict_has_required_fields(self):
        secret = Secret(
            id="test-123",
            source="github",
            repository="org/repo",
            file=".env",
            finding_target="https://github.com/org/repo",
            secret_type="GitHub Classic PAT",
            confidence_score=85.0,
            validation_level=ValidationLevel.PROVIDER,
            verification_status=VerificationStatus.ACTIVE,
            raw_value="ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
            metadata={"entropy": 4.5},
        )
        d = secret.to_export_dict()
        required = [
            "id", "source", "repository", "file", "finding_target",
            "secret_type", "confidence", "validation_level", "verified",
            "masked_value", "entropy", "discovered_at",
        ]
        for field in required:
            assert field in d, f"Missing required field: {field}"
        assert "raw_value" not in d

    def test_from_dict_round_trip(self):
        secret = Secret(
            source="github",
            secret_type="GitHub Classic PAT",
            confidence_score=85.0,
            raw_value="ghp_abc",
            validation_level=ValidationLevel.PROVIDER,
            verification_status=VerificationStatus.ACTIVE,
        )
        d = secret.to_dict(include_raw=True)
        restored = Secret.from_dict(d)
        assert restored.source == secret.source
        assert restored.secret_type == secret.secret_type
        assert restored.confidence_score == secret.confidence_score
        assert restored.raw_value == secret.raw_value

    def test_from_finding_conversion(self):
        finding = Finding(
            source="github",
            target="https://github.com/org/repo",
            content="GITHUB_TOKEN=ghp_abc123def456ghi789jkl012mno345",
            metadata={"repo": "org/repo", "path": ".env"},
            extracted_secrets=[
                {"type": "github", "value": "ghp_abc123def456ghi789jkl012mno345", "rank": 10},
            ],
            validation_results=[
                {"valid": True, "format_valid": True},
            ],
        )
        secret = Secret.from_finding(finding)
        assert secret.source == "github"
        assert secret.finding_target == "https://github.com/org/repo"
        assert secret.repository == "org/repo"
        assert secret.raw_value == "ghp_abc123def456ghi789jkl012mno345"
        assert secret.confidence_score > 0

    def test_history_entry_serialization(self):
        entry = HistoryEntry(
            timestamp="2024-01-01T00:00:00Z",
            event="detected",
            details={"source": "github"},
        )
        d = entry.to_dict()
        assert d["timestamp"] == "2024-01-01T00:00:00Z"
        assert d["event"] == "detected"
        assert d["details"]["source"] == "github"


# ── Finding (backward compatibility) ────────────────────────────────

class TestFinding:
    def test_creation(self):
        finding = Finding(
            source="github",
            target="https://github.com/org/repo",
            content="API_KEY=abc123",
        )
        assert finding.source == "github"
        assert finding.content_hash is not None

    def test_to_dict(self):
        finding = Finding(source="censys", target="1.2.3.4", content="secret data")
        d = finding.to_dict()
        assert d["source"] == "censys"
        assert d["content_hash"] is not None

    def test_from_dict(self):
        data = {
            "source": "github",
            "target": "https://github.com/org/repo",
            "content": "API_KEY=abc123",
        }
        finding = Finding.from_dict(data)
        assert finding.source == "github"


# ── Legacy type mapping ──────────────────────────────────────────

class TestLegacyTypeMapping:
    def test_known_types(self):
        result = _map_legacy_type("github")
        assert result["family"] == "github_pat"
        assert result["provider"] == "github"
        assert result["display_type"] == "GitHub Classic PAT"

    def test_unknown_type(self):
        result = _map_legacy_type("unknown_type")
        assert result["family"] == "unknown_secret"

    def test_ssh_types(self):
        result = _map_legacy_type("ssh_rsa")
        assert result["family"] == "ssh_key"
        assert result["display_type"] == "RSA Private Key"

    def test_aws_type(self):
        result = _map_legacy_type("aws")
        assert result["family"] == "aws_key"
        assert result["provider"] == "aws"
