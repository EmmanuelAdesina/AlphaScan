"""
Tests for AlphaScan confidence scoring engine.

Verifies:
  - Confidence factor scoring (regex, variable name, file, provider, entropy, prefix, etc.)
  - Overall confidence computation
  - Category classification from scores
  - Reason string generation (evidence trail)
  - Shannon entropy calculation
"""
import pytest

from confidence import (
    calculate_entropy,
    compute_confidence,
    ConfidenceResult,
    _confidence_category,
    _score_regex_confidence,
    _score_variable_name,
    _score_file_relevance,
    _score_known_prefix,
    _score_entropy,
    _score_length,
)


class TestEntropy:
    def test_empty_string(self):
        assert calculate_entropy("") == 0.0

    def test_low_entropy(self):
        # Repeating pattern has low entropy
        entropy = calculate_entropy("aaaa")
        assert entropy < 1.0

    def test_medium_entropy(self):
        entropy = calculate_entropy("abc123")
        assert 2.0 <= entropy <= 4.0

    def test_high_entropy(self):
        # Random-looking string has high entropy
        entropy = calculate_entropy("aB3xY7kL9pQ2mN5vR8")
        assert entropy >= 3.5

    def test_very_high_entropy(self):
        entropy = calculate_entropy("ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789abcdef")
        assert entropy >= 4.0


class TestRegexConfidence:
    def test_no_match(self):
        factor = _score_regex_confidence("unknown_secret", False)
        assert factor.score == 0
        assert "No regex pattern" in factor.reason

    def test_github_match(self):
        factor = _score_regex_confidence("github_classic_pat", True)
        assert factor.score >= 20  # GitHub gets high specificity score
        assert "github" in factor.reason.lower()

    def test_generic_match(self):
        factor = _score_regex_confidence("generic_base64_secret", True)
        assert factor.score == 10  # lower specificity


class TestVariableName:
    def test_no_variable(self):
        factor = _score_variable_name("", "github_classic_pat")
        assert factor.score == 0

    def test_matching_variable(self):
        factor = _score_variable_name("GITHUB_TOKEN", "github_classic_pat")
        assert factor.score >= 10  # strong match

    def test_partial_match(self):
        factor = _score_variable_name("API_KEY", "github_classic_pat")
        assert factor.score >= 0


class TestFileRelevance:
    def test_no_file(self):
        factor = _score_file_relevance("", "github_classic_pat")
        assert factor.score == 0

    def test_env_file(self):
        factor = _score_file_relevance(".env", "github_classic_pat")
        assert factor.score == 10  # max score for env file
        assert "high-risk" in factor.reason

    def test_test_file(self):
        # "test_fixture.py" contains "test" and "fixture" but not "config"
        factor = _score_file_relevance("test_fixture_mock.py", "github_classic_pat")
        assert factor.score <= 3.0  # test files get low relevance

    def test_config_file(self):
        factor = _score_file_relevance("config/settings.py", "github_classic_pat")
        assert factor.score >= 5.0  # config files get moderate relevance


class TestKnownPrefix:
    def test_github_prefix(self):
        factor = _score_known_prefix("ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
        assert factor.score >= 8
        assert "ghp_" in factor.reason

    def test_aws_prefix(self):
        factor = _score_known_prefix("AKIAIOSFODNN7EXAMPLE")
        assert factor.score >= 8
        assert "AKIA" in factor.reason

    def test_no_prefix(self):
        factor = _score_known_prefix("random_string_without_prefix")
        assert factor.score == 0


class TestComputeConfidence:
    def test_high_confidence_github(self):
        result = compute_confidence(
            raw_value="ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789abcdef",
            secret_family="github_classic_pat",
            pattern_matched=True,
            variable_name="GITHUB_TOKEN",
            filename=".env",
            repository="org/repo",
        )
        assert result.total_score >= 60
        assert result.category in ("high", "critical")
        assert len(result.factors) > 0
        assert result.reason != ""

    def test_low_confidence_unknown(self):
        result = compute_confidence(
            raw_value="short",
            secret_family="unknown_secret",
            pattern_matched=False,
        )
        assert result.total_score < 30
        assert result.category in ("low", "unlikely")

    def test_reason_contains_evidence(self):
        result = compute_confidence(
            raw_value="ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789abcdef",
            secret_family="github_classic_pat",
            pattern_matched=True,
        )
        # Reason should explain WHY the score was assigned
        assert "pts" in result.reason  # has point breakdown
        assert "Confidence" in result.reason  # has total

    def test_confidence_capped_at_100(self):
        result = compute_confidence(
            raw_value="ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789abcdef",
            secret_family="github_classic_pat",
            pattern_matched=True,
            variable_name="GITHUB_TOKEN",
            filename=".env",
            repository="org/repo",
            occurrences=5,
            ai_confidence=95.0,
        )
        assert result.total_score <= 100.0

    def test_factors_detail(self):
        result = compute_confidence(
            raw_value="AKIAIOSFODNN7EXAMPLE",
            secret_family="aws_access_key",
            pattern_matched=True,
        )
        # Should have multiple factors
        assert len(result.factors) >= 5
        # Each factor should have name, score, max_score, reason
        for factor in result.factors:
            assert factor.name != ""
            assert factor.max_score > 0
            assert factor.reason != ""
