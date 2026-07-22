"""
AlphaScan v0.5 - Verification System.

Provides comprehensive secret verification with:
- SSH private key detection and analysis
- Crypto key detection and wallet balance checks
- API key detection and format validation
- Three-layer verification pipeline (format, entropy, context)
- Clean classified Discord reports
"""
from verification.verifier import SecretVerifier
from verification.key_rank import KeyRanker, RANK_NAMES, RANK_COLORS
from verification.ssh_intelligence import SSHIntelligence
from verification.crypto_intelligence import CryptoIntelligence
from verification.api_intelligence import APIIntelligence
from verification.discord_reporter import DiscordReporter

__all__ = [
    "SecretVerifier",
    "KeyRanker",
    "RANK_NAMES",
    "RANK_COLORS",
    "SSHIntelligence",
    "CryptoIntelligence",
    "APIIntelligence",
    "DiscordReporter",
]
