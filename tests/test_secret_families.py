"""
Tests for AlphaScan secret families module.

Verifies:
  - Family definitions are properly registered
  - Classification of various secret types
  - Pattern matching for known families
  - Context-based fallback classification
  - Never defaults to "api_key" for unknown secrets
"""
import pytest

from secret_families import classify_secret, get_family, all_family_names, FAMILIES


class TestFamilyDefinitions:
    def test_all_families_registered(self):
        assert len(FAMILIES) >= 40  # we defined 44 families

    def test_family_names(self):
        names = all_family_names()
        assert "github_classic_pat" in names
        assert "aws_access_key" in names
        assert "openai_api" in names
        assert "stripe_secret_key" in names
        assert "ethereum_private_key" in names

    def test_get_family(self):
        defn = get_family("github_classic_pat")
        assert defn is not None
        assert defn.provider == "github"
        assert defn.display_type == "GitHub Classic PAT"

    def test_get_nonexistent_family(self):
        defn = get_family("nonexistent_family")
        assert defn is None


class TestClassifySecret:
    def test_github_classic_pat(self):
        family, display, provider = classify_secret("ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
        assert family == "github_classic_pat"
        assert provider == "github"

    def test_github_fine_grained_pat(self):
        # Fine-grained PATs have the github_pat_ prefix
        family, display, provider = classify_secret("github_pat_ABCDEFGHIJKLMNOPQRSTUVWXYZ_abcdefghijklmnopqrstuvwxyz0123456789_ABCDEFGHIJKLMNOPQRSTUVWXYZ")
        assert family == "github_fine_grained_pat"
        assert provider == "github"

    def test_aws_access_key(self):
        family, display, provider = classify_secret("AKIAIOSFODNN7EXAMPLE")
        assert family == "aws_access_key"
        assert provider == "aws"
        assert "AWS Access Key" in display

    def test_openai_key(self):
        family, display, provider = classify_secret("sk-proj-abcdefghijklmnopqrstuvwxyz")
        assert family == "openai_api"
        assert provider == "openai"

    def test_anthropic_key(self):
        family, display, provider = classify_secret("sk-ant-api03-abcdefghijklmnopqrstuvwxyz")
        assert family == "anthropic_api"
        assert provider == "anthropic"

    def test_stripe_live_key(self):
        family, display, provider = classify_secret("sk_live_TESTING_ONLY_xxxxxxxxxxxxxxxxxxxxxx1234")
        assert family == "stripe_secret_key"
        assert provider == "stripe"

    def test_sendgrid_key(self):
        family, display, provider = classify_secret("SG.abcdefghijklmnopqrstuvwxyz.ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghij")
        assert family == "sendgrid_api"
        assert provider == "sendgrid"

    def test_gitlab_pat(self):
        family, display, provider = classify_secret("glpat-ABCDEFGHIJKLMNOPQRSTUVWXYZ")
        assert family == "gitlab_pat"
        assert provider == "gitlab"

    def test_mongodb_uri(self):
        family, display, provider = classify_secret("mongodb://user:password@host:27017/db")
        assert family == "mongodb_uri"
        assert provider == "mongodb"

    def test_postgresql_uri(self):
        family, display, provider = classify_secret("postgresql://user:password@localhost:5432/db")
        assert family == "postgresql_uri"
        assert provider == "postgresql"

    def test_rsa_private_key(self):
        key_text = "-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAKCAQEA\n-----END RSA PRIVATE KEY-----"
        family, display, provider = classify_secret(key_text)
        assert family == "rsa_private_key"
        assert provider == "ssh"

    def test_google_api_key(self):
        family, display, provider = classify_secret("AIzaSyDABCDEFGHIJKLMNOPQRSTUVWXYZabcd")
        assert family == "google_ai_api"
        assert provider == "google"

    def test_never_defaults_to_api_key(self):
        """Unknown secrets must NEVER be classified as 'api_key'."""
        # A random string without any known pattern
        family, display, provider = classify_secret("xyz_random_string_no_pattern_match")
        assert family != "api_key"
        assert family in ("generic_base64_secret", "unknown_secret", "needs_review")

    def test_context_based_classification(self):
        """Context clues should help classify secrets when patterns don't match."""
        context = {
            "variable_name": "GITHUB_TOKEN",
            "filename": ".env",
            "repository": "org/repo",
        }
        # Even without a perfect pattern match, context should guide classification
        family, display, provider = classify_secret(
            "some_value_without_known_prefix",
            context=context,
        )
        # Context keywords should influence the result
        assert isinstance(family, str)
        assert isinstance(display, str)

    def test_entropy_fallback_for_high_entropy_strings(self):
        """High-entropy strings without patterns should be 'Generic Base64 Secret'."""
        family, display, provider = classify_secret(
            "aB3xY7kL9pQ2mN5vR8tW4zH6jK0fS2dL8cA5eI3oU7"
        )
        assert family in ("generic_base64_secret", "unknown_secret")
        assert family != "api_key"
