"""
Key ranking system for AlphaScan v0.5.

Classifies all discovered secrets with a 0-10 ranking:
  0 = SSH Private Keys (THE ULTIMATE PRIZE)
  1 = Crypto Exchange Keys (Withdrawal)
  2 = Wallet Private Keys / Seed Phrases
  3 = Hot Wallet Server Keys
  4 = DeFi Protocol Admin Keys
  5 = RPC Provider Keys
  6 = Smart Contract Deployment Keys
  7 = Cloud Provider Keys
  8 = Payment Processor Keys
  9 = AI Provider Keys
  10 = Dev Platform Keys
"""
import logging
from typing import Dict, Optional, List
from config.patterns import (
    RANK_SSH, RANK_CRYPTO_EXCHANGE, RANK_CRYPTO_PRIVATE, RANK_HOT_WALLET,
    RANK_DEFI_ADMIN, RANK_RPC, RANK_SMART_CONTRACT, RANK_CLOUD,
    RANK_PAYMENT, RANK_AI, RANK_DEV,
)

logger = logging.getLogger(__name__)

# Human-readable rank names
RANK_NAMES: Dict[int, str] = {
    RANK_SSH: "SSH Private Keys",
    RANK_CRYPTO_EXCHANGE: "Crypto Exchange Keys",
    RANK_CRYPTO_PRIVATE: "Wallet Private Keys / Seed Phrases",
    RANK_HOT_WALLET: "Hot Wallet Server Keys",
    RANK_DEFI_ADMIN: "DeFi Protocol Admin Keys",
    RANK_RPC: "RPC Provider Keys",
    RANK_SMART_CONTRACT: "Smart Contract Deployment Keys",
    RANK_CLOUD: "Cloud Provider Keys",
    RANK_PAYMENT: "Payment Processor Keys",
    RANK_AI: "AI Provider Keys",
    RANK_DEV: "Dev Platform Keys",
}

# Discord color codes for each rank
RANK_COLORS: Dict[int, int] = {
    RANK_SSH: 0xFF0000,          # Red - Critical
    RANK_CRYPTO_EXCHANGE: 0xFF4500,  # OrangeRed
    RANK_CRYPTO_PRIVATE: 0xFF8C00,   # DarkOrange
    RANK_HOT_WALLET: 0xFFA500,      # Orange
    RANK_DEFI_ADMIN: 0xFFD700,      # Gold
    RANK_RPC: 0x9932CC,             # DarkOrchid
    RANK_SMART_CONTRACT: 0xBA55D3,  # MediumOrchid
    RANK_CLOUD: 0x1E90FF,           # DodgerBlue
    RANK_PAYMENT: 0x32CD32,         # LimeGreen
    RANK_AI: 0x00CED1,              # DarkTurquoise
    RANK_DEV: 0x5865F2,             # Discord Blue
}

# Rank group labels for summary reports
RANK_GROUPS: Dict[str, List[int]] = {
    "critical": [RANK_SSH],
    "high": [RANK_CRYPTO_EXCHANGE, RANK_CRYPTO_PRIVATE, RANK_HOT_WALLET],
    "medium": [RANK_DEFI_ADMIN, RANK_RPC, RANK_SMART_CONTRACT],
    "standard": [RANK_CLOUD, RANK_PAYMENT, RANK_AI, RANK_DEV],
}


class KeyRanker:
    """
    Assigns and adjusts ranks for discovered keys based on:
    - Base rank from pattern classification
    - Context analysis (production vs test, permissions)
    - Encryption status
    - Key type specifics
    """

    # Context keywords that boost rank (lower rank = higher value)
    RANK_BOOST_KEYWORDS = {
        "root": 0, "admin": 0, "sudo": 0, "privileged": 0,
        "prod": -1, "production": -1, "live": -1,
    }

    # Context keywords that penalize rank (higher rank = lower value)
    RANK_PENALTY_KEYWORDS = {
        "dev": 1, "test": 1, "staging": 1, "development": 1,
    }

    # Service account keywords
    SERVICE_KEYWORDS = {
        "service": 1, "automation": 1, "ci/cd": 1, "deploy": 1,
        "database": 2, "db": 2, "mysql": 2,
    }

    def __init__(self):
        self._rank_adjustments: List[Dict] = []

    def get_rank_name(self, rank: int) -> str:
        """Get human-readable name for a rank."""
        return RANK_NAMES.get(rank, "Unknown")

    def get_rank_color(self, rank: int) -> int:
        """Get Discord color code for a rank."""
        return RANK_COLORS.get(rank, 0x5865F2)

    def get_rank_group(self, rank: int) -> str:
        """Get the group label for a rank (critical, high, medium, standard)."""
        for group, ranks in RANK_GROUPS.items():
            if rank in ranks:
                return group
        return "standard"

    def adjust_rank(self, base_rank: int, context: str = "",
                    encrypted: bool = False, key_type: str = "") -> int:
        """
        Adjust a key's rank based on context analysis.

        Args:
            base_rank: The base rank from pattern classification.
            context: Surrounding text context for the key.
            encrypted: Whether the key is encrypted.
            key_type: The type of key (e.g., 'ssh_rsa', 'eth_private_key').

        Returns:
            Adjusted rank (clamped to 0-10).
        """
        adjusted_rank = base_rank
        context_lower = context.lower() if context else ""

        # Apply context-based rank adjustments
        for keyword, boost in self.RANK_BOOST_KEYWORDS.items():
            if keyword in context_lower:
                adjusted_rank += boost

        for keyword, penalty in self.RANK_PENALTY_KEYWORDS.items():
            if keyword in context_lower:
                adjusted_rank += penalty

        # Encrypted keys get rank penalty
        if encrypted:
            adjusted_rank += 2

        # SSH key context analysis
        if key_type.startswith("ssh_"):
            if "root" in context_lower or "admin" in context_lower:
                adjusted_rank = min(adjusted_rank, RANK_SSH)
            elif any(kw in context_lower for kw in self.SERVICE_KEYWORDS):
                adjusted_rank = max(adjusted_rank, RANK_SSH + 1)

        # Crypto key context analysis
        if key_type.startswith("eth_") or key_type.startswith("btc_"):
            if any(kw in context_lower for kw in ["deployer", "owner", "admin", "multisig"]):
                adjusted_rank = min(adjusted_rank, RANK_DEFI_ADMIN)

        # Clamp to valid range
        adjusted_rank = max(0, min(10, adjusted_rank))

        # Record adjustment for audit trail
        self._rank_adjustments.append({
            "base_rank": base_rank,
            "adjusted_rank": adjusted_rank,
            "context": context[:100] if context else "",
            "encrypted": encrypted,
            "key_type": key_type,
        })

        return adjusted_rank

    def get_rank_summary(self, keys: List[Dict]) -> Dict:
        """
        Generate a summary of keys by rank group.

        Returns:
            Dict with counts for each rank group and total.
        """
        summary = {
            "total": len(keys),
            "rank_0": 0,
            "rank_1_3": 0,
            "rank_4_6": 0,
            "rank_7_10": 0,
            "by_rank": {},
        }

        for key in keys:
            rank = key.get("rank", RANK_DEV)
            summary["by_rank"][rank] = summary["by_rank"].get(rank, 0) + 1

            if rank == RANK_SSH:
                summary["rank_0"] += 1
            elif rank <= 3:
                summary["rank_1_3"] += 1
            elif rank <= 6:
                summary["rank_4_6"] += 1
            else:
                summary["rank_7_10"] += 1

        return summary

    def get_rank_adjustments(self) -> List[Dict]:
        """Get the history of rank adjustments."""
        return self._rank_adjustments
