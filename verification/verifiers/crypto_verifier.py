"""
Crypto Key Verifier - Individual verifier for cryptocurrency keys.
Implements passive verification: format validation, BIP39 wordlist check,
wallet address derivation, Etherscan balance check (read-only).
"""
import logging
from typing import Dict, Optional
from verification.crypto_intelligence import CryptoIntelligence

logger = logging.getLogger(__name__)


class CryptoVerifier:
    """
    Verifies cryptocurrency keys using passive methods only.
    Never accesses or moves funds.
    """

    def __init__(self):
        self._intelligence = CryptoIntelligence()

    def verify(self, key_data: Dict) -> Dict:
        """
        Verify a crypto key entry.

        Args:
            key_data: Dict with crypto key information.

        Returns:
            Dict with verification results.
        """
        key_type = key_data.get("type", "")
        value = key_data.get("value", "")

        # Layer 1: Format Validation
        format_valid = self._validate_format(key_type, value)

        # Layer 2: Entropy Analysis
        from config.patterns import calculate_entropy, get_entropy_category
        entropy = calculate_entropy(value)
        entropy_category = get_entropy_category(entropy)

        # Layer 3: Context Analysis
        context = key_data.get("context", "")
        context_lower = context.lower() if context else ""
        is_defi_admin = any(kw in context_lower for kw in ["deployer", "owner", "admin", "multisig"])
        is_production = any(kw in context_lower for kw in ["prod", "production", "live"])

        # Type-specific verification
        type_specific = self._type_specific_verification(key_type, value)

        # Determine verification status
        verified = format_valid and type_specific.get("passed", False)

        return {
            "verified": verified,
            "method": "passive_crypto_verification",
            "layers": {
                "layer_1_format": {
                    "passed": format_valid,
                    "details": type_specific.get("format_details", "Format validation"),
                },
                "layer_2_entropy": {
                    "passed": entropy > 1.5,
                    "entropy": round(entropy, 4),
                    "category": entropy_category,
                },
                "layer_3_context": {
                    "passed": True,
                    "is_defi_admin": is_defi_admin,
                    "is_production": is_production,
                    "context_keywords": self._extract_context_keywords(context_lower),
                },
            },
            "type_specific": type_specific,
            "risk_level": self._determine_risk_level(key_type, verified, is_defi_admin),
            "note": "Passive verification only - no funds accessed",
        }

    def _validate_format(self, key_type: str, value: str) -> bool:
        """Validate format based on key type."""
        if key_type in ("eth_private_key", "eth_private_key_raw"):
            return self._intelligence._validate_eth_key(value)
        elif key_type == "btc_wif":
            return self._intelligence._validate_btc_wif(value)
        elif key_type == "seed_phrase":
            words = value.lower().split()
            from verification.crypto_intelligence import BIP39_WORDLIST
            return len(words) >= 12 and all(w in BIP39_WORDLIST for w in words)
        elif key_type in ("binance_key", "coinbase_key", "kraken_key"):
            return len(value) >= 16
        elif key_type in ("alchemy_key", "infura_key"):
            return len(value) >= 32
        else:
            return len(value) > 0

    def _type_specific_verification(self, key_type: str, value: str) -> Dict:
        """Perform type-specific verification."""
        if key_type in ("eth_private_key", "eth_private_key_raw"):
            # Derive wallet address
            address = self._intelligence._derive_eth_address(value)
            # Check balance via Etherscan (read-only)
            balance_info = self._intelligence._check_eth_balance(address)
            return {
                "passed": True,
                "wallet_address": address,
                "balance_check": balance_info,
                "format_details": "Valid 64-character hex private key",
            }

        elif key_type == "seed_phrase":
            words = value.lower().split()
            from verification.crypto_intelligence import BIP39_WORDLIST
            all_valid = all(w in BIP39_WORDLIST for w in words)
            return {
                "passed": all_valid and 12 <= len(words) <= 24,
                "word_count": len(words),
                "all_words_valid": all_valid,
                "format_details": f"BIP39 seed phrase with {len(words)} words",
            }

        elif key_type == "btc_wif":
            return {
                "passed": True,
                "format_details": "Valid Bitcoin WIF format",
            }

        elif key_type in ("binance_key", "coinbase_key", "kraken_key"):
            return {
                "passed": len(value) >= 16,
                "format_details": f"Exchange key format ({key_type})",
            }

        elif key_type in ("alchemy_key", "infura_key"):
            return {
                "passed": len(value) >= 32,
                "format_details": f"RPC provider key format ({key_type})",
            }

        return {"passed": len(value) > 0, "format_details": "Basic format check"}

    def _extract_context_keywords(self, context_lower: str) -> list:
        """Extract relevant context keywords."""
        keywords = []
        for kw in ["deployer", "owner", "admin", "multisig", "prod", "production",
                    "live", "dev", "test", "staging", "service", "database"]:
            if kw in context_lower:
                keywords.append(kw)
        return keywords

    def _determine_risk_level(self, key_type: str, verified: bool, is_defi_admin: bool) -> str:
        """Determine risk level based on key type and verification status."""
        if not verified:
            return "low"

        if key_type in ("eth_private_key", "eth_private_key_raw", "btc_wif", "solana_private_key"):
            if is_defi_admin:
                return "critical"
            return "critical"
        elif key_type == "seed_phrase":
            return "critical"
        elif key_type in ("binance_key", "coinbase_key", "kraken_key"):
            return "high"
        elif key_type in ("alchemy_key", "infura_key"):
            return "medium"
        return "medium"
