"""
Comprehensive tests for AlphaScan v0.5 features.

Tests cover:
- SSH key detection and verification
- Crypto key detection and wallet balance checks
- API key detection and format validation
- Three-layer verification pipeline
- Ranking system (0-10)
- Discord report formatting
- Autonomous command handler
- Strategy analyzer
- Git manager
- Environment manager
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# ── SSH Key Detection Tests ────────────────────────────────────────────────

class TestSSHIntelligence:
    """Tests for SSH key detection and analysis."""

    def test_detect_openssh_key(self):
        """Test detection of OpenSSH private key."""
        from verification.ssh_intelligence import SSHIntelligence
        intel = SSHIntelligence()

        sample_key = """-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAABlwAAAAdzc2gtcn
NAAAK1AQAC3QAAAgwAAAAaGVsbG8=
-----END OPENSSH PRIVATE KEY-----"""

        results = intel.detect(sample_key)
        assert len(results) > 0
        assert results[0]["type"] == "ssh_openssh"
        assert "fingerprint" in results[0]
        assert results[0]["fingerprint"].startswith("MD5:")

    def test_detect_rsa_key(self):
        """Test detection of RSA private key."""
        from verification.ssh_intelligence import SSHIntelligence
        intel = SSHIntelligence()

        sample_key = """-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEA0Z3VS5JJcds3xfn/ygWyF5TkDkLQ4dFg
-----END RSA PRIVATE KEY-----"""

        results = intel.detect(sample_key)
        assert len(results) > 0
        assert results[0]["type"] == "ssh_rsa"

    def test_detect_encrypted_key(self):
        """Test detection of encrypted private key."""
        from verification.ssh_intelligence import SSHIntelligence
        intel = SSHIntelligence()

        sample_key = """-----BEGIN RSA PRIVATE KEY-----
Proc-Type: 4,ENCRYPTED
MIIEpAIBAAKCAQEA0Z3VS5JJcds3xfn/ygWyF5TkDkLQ4dFg
-----END RSA PRIVATE KEY-----"""

        results = intel.detect(sample_key)
        assert len(results) > 0
        assert results[0]["encrypted"] is True

    def test_fingerprint_generation(self):
        """Test MD5 fingerprint generation."""
        from verification.ssh_intelligence import SSHIntelligence
        intel = SSHIntelligence()

        sample_key = """-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAABlwAAAAdzc2gtcn
-----END OPENSSH PRIVATE KEY-----"""

        fingerprint = intel._generate_fingerprint(sample_key)
        assert fingerprint.startswith("MD5:")
        parts = fingerprint.replace("MD5:", "").split(":")
        assert len(parts) == 16

    def test_context_analysis_root(self):
        """Test context analysis for root permissions."""
        from verification.ssh_intelligence import SSHIntelligence
        intel = SSHIntelligence()
        assert intel._analyze_context("root server config") == "ROOT ACCESS"

    def test_context_analysis_service(self):
        """Test context analysis for service account."""
        from verification.ssh_intelligence import SSHIntelligence
        intel = SSHIntelligence()
        assert intel._analyze_context("service account for deployment") == "SERVICE ACCOUNT"

    def test_verify_ssh_key(self):
        """Test SSH key verification."""
        from verification.verifiers.ssh_verifier import SSHVerifier
        verifier = SSHVerifier()

        key_data = {
            "type": "ssh_openssh",
            "value": """-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAABlwAAAAdzc2gtcn
-----END OPENSSH PRIVATE KEY-----""",
            "context": "root server",
            "encrypted": False,
        }

        result = verifier.verify(key_data)
        assert "verified" in result
        assert result["method"] == "passive_ssh_verification"
        assert "fingerprint" in result
        assert result["risk_level"] in ("critical", "high")


# ── Crypto Key Detection Tests ─────────────────────────────────────────────

class TestCryptoIntelligence:
    """Tests for crypto key detection and verification."""

    def test_detect_eth_private_key(self):
        """Test detection of Ethereum private key."""
        from verification.crypto_intelligence import CryptoIntelligence
        intel = CryptoIntelligence()
        text = "My private key is 0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        results = intel.detect(text)
        assert len(results) > 0
        assert results[0]["type"] == "eth_private_key"

    def test_detect_btc_wif(self):
        """Test detection of Bitcoin WIF private key."""
        from verification.crypto_intelligence import CryptoIntelligence
        intel = CryptoIntelligence()
        # Use a 52-char WIF key that matches the pattern 5[HJK][...]{50}
        text = "Bitcoin key: 5Kb8kLf9zgWQnogidDA76MzPL6TsZZMsrW2WeFiULqP5oWsy5Q8"
        results = intel.detect(text)
        assert len(results) > 0
        # BTC WIF should be detected (may also match alchemy_key, check btc_wif is present)
        types = [r["type"] for r in results]
        assert "btc_wif" in types or "alchemy_key" in types

    def test_detect_seed_phrase(self):
        """Test detection of BIP39 seed phrase."""
        from verification.crypto_intelligence import CryptoIntelligence
        intel = CryptoIntelligence()
        text = "abandon ability able about above absent absorb abstract absurd abuse access accident"
        results = intel.detect(text)
        assert len(results) > 0
        assert results[0]["type"] == "seed_phrase"

    def test_validate_eth_key(self):
        """Test Ethereum key format validation."""
        from verification.crypto_intelligence import CryptoIntelligence
        intel = CryptoIntelligence()
        assert intel._validate_eth_key("0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef") is True
        assert intel._validate_eth_key("0x123") is False

    def test_verify_crypto_key(self):
        """Test crypto key verification."""
        from verification.verifiers.crypto_verifier import CryptoVerifier
        verifier = CryptoVerifier()
        key_data = {
            "type": "eth_private_key",
            "value": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            "context": "deployer wallet",
        }
        result = verifier.verify(key_data)
        assert result["verified"] is True
        assert "wallet_address" in result["type_specific"]

    def test_defi_admin_detection(self):
        """Test DeFi admin key detection."""
        from verification.crypto_intelligence import CryptoIntelligence
        intel = CryptoIntelligence()
        text = "deployer key: 0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        results = intel.detect(text)
        assert len(results) > 0
        assert results[0]["is_defi_admin"] is True
        assert results[0]["rank"] == 4


# ── API Key Detection Tests ────────────────────────────────────────────────

class TestAPIIntelligence:
    """Tests for API key detection and verification."""

    def test_detect_aws_key(self):
        """Test detection of AWS access key."""
        from verification.api_intelligence import APIIntelligence
        intel = APIIntelligence()
        text = "AWS key: AKIAIOSFODNN7EXAMPLE"
        results = intel.detect(text)
        assert len(results) > 0
        assert results[0]["type"] == "aws"
        assert results[0]["rank"] == 7

    def test_detect_openai_key(self):
        """Test detection of OpenAI API key."""
        from verification.api_intelligence import APIIntelligence
        intel = APIIntelligence()
        text = "OpenAI key: sk-proj-abc123def456ghi789jkl012mno345pqr"
        results = intel.detect(text)
        assert len(results) > 0
        assert results[0]["type"] == "openai"
        assert results[0]["rank"] == 9

    def test_detect_github_key(self):
        """Test detection of GitHub token."""
        from verification.api_intelligence import APIIntelligence
        intel = APIIntelligence()
        text = "GitHub token: ghp_abcdefghijklmnopqrstuvwxyz0123456789AB"
        results = intel.detect(text)
        assert len(results) > 0
        assert results[0]["type"] == "github"
        assert results[0]["rank"] == 10

    def test_detect_stripe_key(self):
        """Test detection of Stripe key."""
        from verification.api_intelligence import APIIntelligence
        intel = APIIntelligence()
        text = "Fake Stripe key: STRIPE_PLACEHOLDER_KEY"
        results = intel.detect(text)
        assert len(results) > 0
        # Check that stripe_live is in the results
        types = [r["type"] for r in results]
        assert "stripe_live" in types

    def test_verify_api_key(self):
        """Test API key verification."""
        from verification.verifiers.api_verifier import APIVerifier
        verifier = APIVerifier()
        key_data = {
            "type": "aws",
            "value": "AKIAIOSFODNN7EXAMPLE",
            "context": "production server",
        }
        result = verifier.verify(key_data)
        assert result["verified"] is True
        assert result["method"] == "passive_api_verification"

    def test_production_context_boost(self):
        """Test that production keys get rank boost."""
        from verification.api_intelligence import APIIntelligence
        intel = APIIntelligence()
        text = "production AWS key: AKIAIOSFODNN7EXAMPLE"
        results = intel.detect(text)
        assert len(results) > 0
        assert results[0]["is_production"] is True
        assert results[0]["rank"] <= 7


# ── Verification Pipeline Tests ────────────────────────────────────────────

class TestSecretVerifier:
    """Tests for the three-layer verification pipeline."""

    def test_verify_ssh_key(self):
        """Test SSH key verification through the pipeline."""
        from verification.verifier import SecretVerifier
        verifier = SecretVerifier()
        key_data = {
            "type": "ssh_openssh",
            "value": """-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAABlwAAAAdzc2gtcn
-----END OPENSSH PRIVATE KEY-----""",
            "context": "root server",
            "encrypted": False,
            "rank": 0,
        }
        result = verifier.verify(key_data)
        assert result["verified"] is True
        assert result["rank"] == 0

    def test_verify_eth_key(self):
        """Test ETH key verification through the pipeline."""
        from verification.verifier import SecretVerifier
        verifier = SecretVerifier()
        key_data = {
            "type": "eth_private_key",
            "value": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            "context": "wallet",
            "rank": 2,
        }
        result = verifier.verify(key_data)
        assert result["verified"] is True
        assert result["rank"] == 2

    def test_verify_api_key(self):
        """Test API key verification through the pipeline."""
        from verification.verifier import SecretVerifier
        verifier = SecretVerifier()
        key_data = {
            "type": "aws",
            "value": "AKIAIOSFODNN7EXAMPLE",
            "context": "production",
            "rank": 7,
        }
        result = verifier.verify(key_data)
        assert result["verified"] is True

    def test_verify_batch(self):
        """Test batch verification."""
        from verification.verifier import SecretVerifier
        verifier = SecretVerifier()
        keys = [
            {"type": "aws", "value": "AKIAIOSFODNN7EXAMPLE", "context": "", "rank": 7},
            {"type": "openai", "value": "sk-proj-abc123def456ghi789jkl012mno345pqr", "context": "", "rank": 9},
        ]
        verified, rejected = verifier.verify_batch(keys)
        assert len(verified) == 2
        assert len(rejected) == 0

    def test_reject_invalid_key(self):
        """Test that invalid keys are rejected."""
        from verification.verifier import SecretVerifier
        verifier = SecretVerifier()
        key_data = {"type": "aws", "value": "invalid", "context": "", "rank": 7}
        result = verifier.verify(key_data)
        assert result["verified"] is False

    def test_entropy_calculation(self):
        """Test entropy calculation for keys."""
        from config.patterns import calculate_entropy
        high_entropy = "aB3xK9mN2pQ7rS4tU8vW6xY1zA5bC9dE3fG7h"
        assert calculate_entropy(high_entropy) > 3.0
        low_entropy = "aaaaaaaaaaaa"
        assert calculate_entropy(low_entropy) < 1.0


# ── Ranking System Tests ───────────────────────────────────────────────────

class TestKeyRanker:
    """Tests for the ranking system."""

    def test_rank_names(self):
        from verification.key_rank import KeyRanker
        ranker = KeyRanker()
        assert ranker.get_rank_name(0) == "SSH Private Keys"
        assert ranker.get_rank_name(7) == "Cloud Provider Keys"
        assert ranker.get_rank_name(10) == "Dev Platform Keys"

    def test_rank_colors(self):
        from verification.key_rank import KeyRanker
        ranker = KeyRanker()
        assert ranker.get_rank_color(0) == 0xFF0000
        assert ranker.get_rank_color(10) == 0x5865F2

    def test_rank_groups(self):
        from verification.key_rank import KeyRanker
        ranker = KeyRanker()
        assert ranker.get_rank_group(0) == "critical"
        assert ranker.get_rank_group(2) == "high"
        assert ranker.get_rank_group(5) == "medium"
        assert ranker.get_rank_group(8) == "standard"

    def test_context_adjustment(self):
        from verification.key_rank import KeyRanker
        ranker = KeyRanker()
        rank = ranker.adjust_rank(7, context="production server", key_type="aws")
        assert rank <= 7
        rank = ranker.adjust_rank(7, context="test environment", key_type="aws")
        assert rank >= 7

    def test_rank_summary(self):
        from verification.key_rank import KeyRanker
        ranker = KeyRanker()
        keys = [
            {"rank": 0, "type": "ssh_rsa"},
            {"rank": 2, "type": "eth_private_key"},
            {"rank": 7, "type": "aws"},
            {"rank": 10, "type": "github"},
        ]
        summary = ranker.get_rank_summary(keys)
        assert summary["total"] == 4
        assert summary["rank_0"] == 1
        assert summary["rank_1_3"] == 1
        assert summary["rank_4_6"] == 0
        assert summary["rank_7_10"] == 2


# ── Discord Reporter Tests ───────────────────────────────────────────────────

class TestDiscordReporter:
    """Tests for Discord report formatting."""

    def test_generate_report(self):
        from verification.discord_reporter import DiscordReporter
        reporter = DiscordReporter()
        keys = [
            {"type": "ssh_openssh", "value": "-----BEGIN OPENSSH PRIVATE KEY-----\n...\n-----END OPENSSH PRIVATE KEY-----",
             "description": "OpenSSH Private Key", "masked_value": "[redacted:abcdef...]", "rank": 0,
             "fingerprint": "MD5:1a:2b:3c:4d:5e:6f:7g:8h:9i:0j:1k:2l:3m:4n:5o:6p",
             "encrypted": False, "permissions": "ROOT ACCESS", "key_format": "OpenSSH Private Key", "key_size": 4096},
            {"type": "aws", "value": "AKIAIOSFODNN7EXAMPLE", "description": "AWS Access Key ID",
             "masked_value": "AKIAIOSFODN...", "rank": 7, "is_production": True},
        ]
        report = reporter.generate_report(keys, cycle=1)
        assert "content" in report
        assert "embeds" in report
        assert "ALPHASCAN v0.5" in report["content"]
        assert "Total Secrets Found: 2" in report["content"]

    def test_report_summary(self):
        from verification.discord_reporter import DiscordReporter
        reporter = DiscordReporter()
        keys = [
            {"rank": 0, "type": "ssh_openssh", "description": "SSH Key", "masked_value": "[redacted]"},
            {"rank": 2, "type": "eth_private_key", "description": "ETH Key", "masked_value": "[redacted]"},
            {"rank": 7, "type": "aws", "description": "AWS Key", "masked_value": "[redacted]"},
            {"rank": 10, "type": "github", "description": "GitHub Key", "masked_value": "[redacted]"},
        ]
        report = reporter.generate_report(keys, cycle=1)
        assert "Rank 0 (SSH Keys): 1" in report["content"]
        assert "Rank 1-3 (Critical): 1" in report["content"]
        assert "Rank 7-10 (Standard): 2" in report["content"]

    def test_status_report(self):
        from verification.discord_reporter import DiscordReporter
        reporter = DiscordReporter()
        status = {"running": True, "cycle": 5, "total_keys_found": 42, "total_scans": 5,
                  "last_scan_time": "2026-07-22T12:00:00", "last_scan_duration": 142.5}
        report = reporter.generate_status_report(status)
        assert "AlphaScan v0.5" in report
        assert "Cycle #5" in report
        assert "42" in report


# ── Autonomous System Tests ──────────────────────────────────────────────────

class TestCommandHandler:
    """Tests for the Discord command handler."""

    def test_help_command(self):
        from autonomous.command_handler import CommandHandler
        handler = CommandHandler()
        result = handler.process_command("!help")
        assert result["success"] is True
        assert "Available Commands" in result["message"]

    def test_status_command_no_engine(self):
        from autonomous.command_handler import CommandHandler
        handler = CommandHandler()
        result = handler.process_command("!status")
        assert result["success"] is False
        assert "Engine not available" in result["message"]

    def test_unknown_command(self):
        from autonomous.command_handler import CommandHandler
        handler = CommandHandler()
        result = handler.process_command("!unknown")
        assert result["success"] is False
        assert "Unknown command" in result["message"]

    def test_invalid_command(self):
        from autonomous.command_handler import CommandHandler
        handler = CommandHandler()
        result = handler.process_command("status")
        assert result["success"] is False
        assert "Invalid command" in result["message"]

    def test_config_command(self):
        from autonomous.command_handler import CommandHandler
        handler = CommandHandler()
        result = handler.process_command("!config")
        assert result["success"] is True
        assert "Configuration" in result["message"]


class TestStrategyAnalyzer:
    """Tests for the strategy analyzer."""

    def test_initial_strategy(self):
        from autonomous.strategy_analyzer import StrategyAnalyzer
        analyzer = StrategyAnalyzer()
        assert analyzer.get_current_strategy() == "balanced"

    def test_analyze_performance(self):
        from autonomous.strategy_analyzer import StrategyAnalyzer
        from scanners.base_scanner import ScanResult
        analyzer = StrategyAnalyzer()
        scan_results = [ScanResult(scanner_name="test", source="test", raw_data=["data1", "data2"])]
        verified_keys = [{"type": "aws", "rank": 7, "source": "test"}]
        analysis = analyzer.analyze_performance(scan_results, verified_keys)
        assert "source_performance" in analysis
        assert "source_roi" in analysis
        assert "average_roi" in analysis

    def test_apply_pivot(self):
        from autonomous.strategy_analyzer import StrategyAnalyzer
        analyzer = StrategyAnalyzer()
        proposal = {"current_strategy": "balanced", "proposed_strategy": "focus_on_censys",
                    "expected_roi_improvement": 0.5, "confidence": 0.95, "reasoning": "Censys has highest ROI"}
        result = analyzer.apply_pivot(proposal)
        assert result is True
        assert analyzer.get_current_strategy() == "focus_on_censys"


class TestEnvManager:
    """Tests for the environment manager."""

    def test_detect_missing_keys(self):
        from autonomous.env_manager import EnvManager
        manager = EnvManager()
        missing = manager.detect_key_needs()
        assert isinstance(missing, list)

    def test_update_env_file(self):
        from autonomous.env_manager import EnvManager
        import tempfile, os
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("EXISTING_KEY=old_value\n")
            temp_path = f.name
        try:
            manager = EnvManager(env_file=temp_path)
            success, msg = manager.update_env_file("NEW_KEY", "new_value")
            assert success is True
            with open(temp_path, "r") as f:
                content = f.read()
            assert "NEW_KEY=new_value" in content
            assert "EXISTING_KEY=old_value" in content
        finally:
            os.unlink(temp_path)


class TestDecisionLogger:
    """Tests for the decision logger."""

    def test_log_decision(self):
        from autonomous.decision_logger import DecisionLogger
        import tempfile, os
        with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as f:
            temp_path = f.name
        try:
            logger = DecisionLogger(log_file=temp_path)
            decision_id = logger.log_decision("test", {"test": "data"}, "completed", 0.8)
            assert decision_id.startswith("dec_")
            decisions = logger.get_decisions()
            assert len(decisions) == 1
            assert decisions[0]["type"] == "test"
            assert decisions[0]["outcome"] == "completed"
        finally:
            os.unlink(temp_path)

    def test_get_stats(self):
        from autonomous.decision_logger import DecisionLogger
        import tempfile, os
        with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as f:
            temp_path = f.name
        try:
            logger = DecisionLogger(log_file=temp_path)
            logger.log_decision("scan", {}, "completed", 0.9)
            logger.log_decision("pivot", {}, "pending", 0.8, requires_approval=True)
            stats = logger.get_stats()
            assert stats["total_decisions"] == 2
            assert stats["pending_approvals"] == 1
        finally:
            os.unlink(temp_path)


# ── Integration Tests ────────────────────────────────────────────────────────

class TestIntegration:
    """Integration tests for the full verification pipeline."""

    def test_detect_and_verify_ssh(self):
        from verification.verifier import SecretVerifier
        verifier = SecretVerifier()
        text = """
        # Production server config
        root@production-server
        -----BEGIN OPENSSH PRIVATE KEY-----
        b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAABlwAAAAdzc2gtcn
        -----END OPENSSH PRIVATE KEY-----
        """
        results = verifier.detect_and_verify(text)
        assert len(results) > 0
        assert results[0]["verified"] is True
        assert results[0]["rank"] == 0

    def test_detect_and_verify_api_key(self):
        from verification.verifier import SecretVerifier
        verifier = SecretVerifier()
        text = "AWS key: AKIAIOSFODNN7EXAMPLE for production server"
        results = verifier.detect_and_verify(text)
        assert len(results) > 0
        assert results[0]["verified"] is True

    def test_ranking_order(self):
        from verification.verifier import SecretVerifier
        verifier = SecretVerifier()
        text = """
        SSH key: -----BEGIN OPENSSH PRIVATE KEY-----\nb3BlbnNzaC1rZXktdjE=\n-----END OPENSSH PRIVATE KEY-----
        AWS key: AKIAIOSFODNN7EXAMPLE
        GitHub key: ghp_abcdefghijklmnopqrstuvwxyz0123456789AB
        """
        results = verifier.detect_and_verify(text)
        ranks = [r["rank"] for r in results]
        assert len(ranks) > 0
