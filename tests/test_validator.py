"""
Tests for key classification and validation modules.
"""
import pytest
from utils.key_validator import KeyValidator
from config.patterns import KeyClassifier, PATTERNS, classifier


class TestKeyClassifier:
    """Tests for key classification patterns."""

    def test_openai_key_classification(self):
        """Test OpenAI key classification."""
        result = classifier.classify("sk-proj-abc123def456ghi789jkl012mno345pqr")
        assert result is not None
        assert result["type"] == "openai"
        assert "sk-" in result["value"]

    def test_claude_key_classification(self):
        """Test Claude/Anthropic key classification."""
        result = classifier.classify("sk-ant-api03-abc123def456ghi789jkl012mno345")
        assert result is not None
        assert result["type"] == "claude"

    def test_aws_key_classification(self):
        """Test AWS key classification."""
        result = classifier.classify("AKIAIOSFODNN7EXAMPLE")
        assert result is not None
        assert result["type"] == "aws"

    def test_google_key_classification(self):
        """Test Google API key classification."""
        result = classifier.classify("AIzaSyB1234567890abcdefghijklmnopqrstuv")
        assert result is not None
        assert result["type"] == "google"

    def test_github_key_classification(self):
        """Test GitHub token classification."""
        result = classifier.classify("ghp_abcdefghijklmnopqrstuvwxyz0123456789AB")
        assert result is not None
        assert result["type"] == "github"

    def test_stripe_live_key_classification(self):
        """Test Stripe live key classification."""
        result = classifier.classify("sk_test_example")
        assert result is not None
        assert result["type"] == "stripe_live"

    def test_stripe_test_key_classification(self):
        """Test Stripe test key classification."""
        result = classifier.classify("sk_test_abcdefghijklmnopqrstuvwxyz123456")
        assert result is not None
        assert result["type"] == "stripe_test"

    def test_discord_key_classification(self):
        """Test Discord token classification."""
        result = classifier.classify("DISCORD_TOKEN_PLACEHOLDER")
        assert result is not None
        assert result["type"] == "discord"

    def test_slack_key_classification(self):
        """Test Slack token classification."""
        result = classifier.classify("SLACK_TOKEN_PLACEHOLDER")
        assert result is not None
        assert result["type"] == "slack"

    def test_mongodb_classification(self):
        """Test MongoDB connection string classification."""
        result = classifier.classify("mongodb+srv://user:pass@cluster.mongodb.net/db")
        assert result is not None
        assert result["type"] == "mongodb"

    def test_postgresql_classification(self):
        """Test PostgreSQL connection string classification."""
        result = classifier.classify("postgresql://user:pass@host:5432/db")
        assert result is not None
        assert result["type"] == "postgresql"

    def test_mysql_classification(self):
        """Test MySQL connection string classification."""
        result = classifier.classify("mysql://user:pass@host:3306/db")
        assert result is not None
        assert result["type"] == "mysql"

    def test_no_match(self):
        """Test that non-key strings return None."""
        result = classifier.classify("this is just a regular string")
        assert result is None

    def test_empty_string(self):
        """Test that empty strings return None."""
        result = classifier.classify("")
        assert result is None

    def test_batch_classification(self):
        """Test batch classification."""
        texts = [
            "sk-proj-abc123def456ghi789jkl012mno345pqr",
            "AKIAIOSFODNN7EXAMPLE",
            "not a key",
        ]
        results = classifier.classify_batch(texts)
        assert len(results) == 2  # Only 2 should match

    def test_masking(self):
        """Test that keys are properly masked."""
        result = classifier.classify("sk-proj-abc123def456ghi789jkl012mno345pqr")
        assert result is not None
        assert "..." in result["masked_value"]
        # Full key should not be in masked value
        assert result["value"] != result["masked_value"]

    def test_add_pattern(self):
        """Test dynamically adding a new pattern."""
        new_classifier = KeyClassifier()
        success = new_classifier.add_pattern(
            "test_type", r"test_[a-zA-Z0-9]{10,}", "Test pattern", "test_"
        )
        assert success is True
        result = new_classifier.classify("test_abcdefghijklmnopqrstuvwxyz")
        assert result is not None
        assert result["type"] == "test_type"

    def test_get_pattern_names(self):
        """Test getting all pattern names."""
        names = classifier.get_pattern_names()
        assert "openai" in names
        assert "aws" in names
        assert "github" in names

    def test_get_all_patterns(self):
        """Test getting all patterns as dicts."""
        patterns = classifier.get_all_patterns()
        assert len(patterns) > 0
        assert all("name" in p for p in patterns)
        assert all("pattern" in p for p in patterns)


class TestKeyValidator:
    """Tests for key validation."""

    def test_valid_openai_key(self):
        """Test validation of a valid OpenAI key."""
        validator = KeyValidator()
        key_data = {"type": "openai", "value": "sk-proj-abc123def456ghi789jkl012mno345pqr"}
        assert validator.validate(key_data) is True

    def test_invalid_short_key(self):
        """Test validation of a too-short key."""
        validator = KeyValidator()
        key_data = {"type": "openai", "value": "sk-short"}
        assert validator.validate(key_data) is False

    def test_invalid_prefix(self):
        """Test validation of a key with wrong prefix."""
        validator = KeyValidator()
        key_data = {"type": "openai", "value": "ghp-abc123def456ghi789jkl012mno345pqr"}
        assert validator.validate(key_data) is False

    def test_valid_aws_key(self):
        """Test validation of a valid AWS key."""
        validator = KeyValidator()
        key_data = {"type": "aws", "value": "AKIAIOSFODNN7EXAMPLE"}
        assert validator.validate(key_data) is True

    def test_valid_github_key(self):
        """Test validation of a valid GitHub key."""
        validator = KeyValidator()
        key_data = {"type": "github", "value": "ghp_abcdefghijklmnopqrstuvwxyz0123456789AB"}
        assert validator.validate(key_data) is True

    def test_empty_value(self):
        """Test validation of an empty key value."""
        validator = KeyValidator()
        key_data = {"type": "openai", "value": ""}
        assert validator.validate(key_data) is False

    def test_generic_key(self):
        """Test validation of a generic key type."""
        validator = KeyValidator()
        key_data = {"type": "generic", "value": "abcdefghijklmnopqrstuvwxyz1234567890"}
        assert validator.validate(key_data) is True

    def test_short_generic_key(self):
        """Test validation of a short generic key."""
        validator = KeyValidator()
        key_data = {"type": "generic", "value": "short"}
        assert validator.validate(key_data) is False

    def test_validate_batch(self):
        """Test batch validation."""
        validator = KeyValidator()
        keys = [
            {"type": "openai", "value": "sk-proj-abc123def456ghi789jkl012mno345pqr"},
            {"type": "openai", "value": "short"},
            {"type": "aws", "value": "AKIAIOSFODNN7EXAMPLE"},
        ]
        valid, invalid = validator.validate_batch(keys)
        assert len(valid) == 2
        assert len(invalid) == 1

    def test_mask_key(self):
        """Test key masking."""
        validator = KeyValidator()
        masked = validator.mask_key("sk-proj-abc123def456ghi789jkl012mno345pqr")
        assert "*" in masked
        assert len(masked) < len("sk-proj-abc123def456ghi789jkl012mno345pqr")

    def test_is_duplicate(self):
        """Test duplicate detection."""
        validator = KeyValidator()
        existing = [
            {"value": "key1"},
            {"value": "key2"},
        ]
        assert validator.is_duplicate("key1", existing) is True
        assert validator.is_duplicate("key3", existing) is False
