"""
Core Secret Verifier for AlphaScan v0.5.

Implements the three-layer verification pipeline:
  Layer 1: Format Validation (structure, length, pattern)
  Layer 2: Entropy Analysis (randomness measurement)
  Layer 3: Context Analysis (LLM-based production/test, permissions)

Routes keys to the appropriate specialized verifier (SSH, Crypto, API).
"""
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from verification.ssh_intelligence import SSHIntelligence
from verification.crypto_intelligence import CryptoIntelligence
from verification.api_intelligence import APIIntelligence
from verification.key_rank import KeyRanker
from verification.verifiers.ssh_verifier import SSHVerifier
from verification.verifiers.crypto_verifier import CryptoVerifier
from verification.verifiers.api_verifier import APIVerifier
from config.patterns import calculate_entropy, get_entropy_category, RANK_SSH, RANK_DEV
from config.settings import MIN_VERIFICATION_CONFIDENCE

logger = logging.getLogger(__name__)


class SecretVerifier:
    """
    Main verification orchestrator for AlphaScan v0.5.

    Routes discovered secrets to the appropriate specialized verifier,
    applies the three-layer verification pipeline, and produces
    verified, ranked, and classified results.
    """

    # Key type prefixes for routing to verifiers
    SSH_TYPES = {"ssh_openssh", "ssh_rsa", "ssh_dsa", "ssh_ec", "ssh_encrypted",
                 "ssh_public_rsa", "ssh_public_ecdsa", "ssh_public_ed25519"}
    CRYPTO_TYPES = {"eth_private_key", "eth_private_key_raw", "btc_wif",
                    "solana_private_key", "seed_phrase", "binance_key",
                    "coinbase_key", "kraken_key", "alchemy_key", "infura_key",
                    "defi_admin_key", "deployer_key"}
    API_TYPES = {"claude", "openai", "aws", "google", "azure", "github", "gitlab",
                 "stripe_live", "stripe_test", "paypal", "twilio", "sendgrid",
                 "mailgun", "discord", "slack", "mongodb", "postgresql", "mysql",
                 "supabase", "firebase", "google_oauth", "generic_apikey",
                 "generic_bearer"}

    def __init__(self):
        self._ssh_intel = SSHIntelligence()
        self._crypto_intel = CryptoIntelligence()
        self._api_intel = APIIntelligence()
        self._ranker = KeyRanker()
        self._ssh_verifier = SSHVerifier()
        self._crypto_verifier = CryptoVerifier()
        self._api_verifier = APIVerifier()

        # Statistics
        self._stats = {
            "total_verified": 0,
            "total_rejected": 0,
            "by_type": {},
            "by_rank": {},
        }

    def verify(self, key_data: Dict) -> Dict:
        """
        Verify a single key entry through the three-layer pipeline.

        Args:
            key_data: Dict with at least 'type' and 'value' keys.
                      May also include 'context', 'encrypted', etc.

        Returns:
            Dict with verification results including:
            - verified: bool
            - rank: int (0-10)
            - verification: detailed results
            - risk_level: str
        """
        key_type = key_data.get("type", "")
        value = key_data.get("value", "")
        context = key_data.get("context", "")

        # Determine which verifier to use
        verifier, intel = self._get_verifier_and_intel(key_type)

        if verifier is None:
            # Unknown key type - use generic verification
            verification_result = self._generic_verify(key_data)
        else:
            # Run the specialized verifier
            verification_result = verifier.verify(key_data)

        # Estimate confidence for the verification result
        confidence = self._estimate_confidence(verification_result)
        verification_result["confidence"] = confidence

        if confidence < MIN_VERIFICATION_CONFIDENCE:
            verification_result["verified"] = False
            verification_result["note"] = (
                f"{verification_result.get('note', '')} "
                f"(rejected by confidence threshold {MIN_VERIFICATION_CONFIDENCE})"
            ).strip()

        # Apply rank adjustment based on context
        base_rank = key_data.get("rank", RANK_DEV)
        encrypted = key_data.get("encrypted", False)
        adjusted_rank = self._ranker.adjust_rank(
            base_rank=base_rank,
            context=context,
            encrypted=encrypted,
            key_type=key_type,
        )

        # Update statistics
        if verification_result["verified"]:
            self._stats["total_verified"] += 1
            self._stats["by_type"][key_type] = self._stats["by_type"].get(key_type, 0) + 1
            self._stats["by_rank"][adjusted_rank] = self._stats["by_rank"].get(adjusted_rank, 0) + 1
        else:
            self._stats["total_rejected"] += 1

        # Build final result
        result = dict(key_data)  # Copy original data
        result["verified"] = verification_result["verified"]
        result["rank"] = adjusted_rank
        result["confidence"] = confidence
        result["verification"] = verification_result
        result["risk_level"] = verification_result.get("risk_level", "unknown")
        result["verified_at"] = datetime.utcnow().isoformat()

        return result

    def _estimate_confidence(self, verification_result: Dict) -> float:
        """Estimate a confidence score for a verification result."""
        layers = verification_result.get("layers", {})
        format_passed = layers.get("layer_1_format", {}).get("passed", False)
        entropy_passed = layers.get("layer_2_entropy", {}).get("passed", False)
        context_passed = layers.get("layer_3_context", {}).get("passed", False)

        score = 0.0
        score += 0.50 if format_passed else 0.0
        score += 0.35 if entropy_passed else 0.0
        score += 0.15 if context_passed else 0.0
        return round(min(1.0, score), 2)

    def verify_batch(self, keys: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """
        Verify a batch of keys.

        Returns:
            Tuple of (verified_keys, rejected_keys).
        """
        verified = []
        rejected = []

        for key in keys:
            result = self.verify(key)
            if result["verified"]:
                verified.append(result)
            else:
                rejected.append(result)

        return verified, rejected

    def detect_and_verify(self, text: str) -> List[Dict]:
        """
        Detect and verify all secrets in a text string.

        Uses all three intelligence modules to detect secrets,
        then verifies each one.

        Args:
            text: Text to scan for secrets.

        Returns:
            List of verified secret dicts.
        """
        results = []

        # Detect SSH keys
        if text:
            ssh_keys = self._ssh_intel.detect(text)
            for key in ssh_keys:
                key["context"] = text[:500]
                result = self.verify(key)
                if result["verified"]:
                    results.append(result)

            # Detect crypto keys
            crypto_keys = self._crypto_intel.detect(text)
            for key in crypto_keys:
                key["context"] = text[:500]
                result = self.verify(key)
                if result["verified"]:
                    results.append(result)

            # Detect API keys
            api_keys = self._api_intel.detect(text)
            for key in api_keys:
                key["context"] = text[:500]
                result = self.verify(key)
                if result["verified"]:
                    results.append(result)

        return results

    def _get_verifier_and_intel(self, key_type: str) -> tuple:
        """Get the appropriate verifier and intelligence module for a key type."""
        if key_type in self.SSH_TYPES:
            return self._ssh_verifier, self._ssh_intel
        elif key_type in self.CRYPTO_TYPES:
            return self._crypto_verifier, self._crypto_intel
        elif key_type in self.API_TYPES:
            return self._api_verifier, self._api_intel
        return None, None

    def _generic_verify(self, key_data: Dict) -> Dict:
        """Generic verification for unknown key types."""
        value = key_data.get("value", "")

        # Layer 1: Format validation
        format_valid = len(value) >= 16

        # Layer 2: Entropy analysis
        entropy = calculate_entropy(value)
        entropy_category = get_entropy_category(entropy)

        # Layer 3: Context analysis
        context = key_data.get("context", "")
        context_lower = context.lower() if context else ""
        is_production = any(kw in context_lower for kw in ["prod", "production", "live"])

        verified = format_valid and entropy > 0

        result = dict(key_data)
        result["verified"] = verified
        result["rank"] = key_data.get("rank", RANK_DEV)
        result["verification"] = {
            "verified": verified,
            "method": "generic_verification",
            "layers": {
                "layer_1_format": {"passed": format_valid, "details": "Basic format check"},
                "layer_2_entropy": {"passed": entropy > 0, "entropy": round(entropy, 4), "category": entropy_category},
                "layer_3_context": {"passed": True, "is_production": is_production},
            },
            "risk_level": "medium" if verified else "low",
            "note": "Generic verification - limited checks",
        }
        result["risk_level"] = result["verification"]["risk_level"]
        result["verified_at"] = datetime.utcnow().isoformat()

        return result

    def get_stats(self) -> Dict:
        """Get verification statistics."""
        return dict(self._stats)

    def reset_stats(self) -> None:
        """Reset verification statistics."""
        self._stats = {
            "total_verified": 0,
            "total_rejected": 0,
            "by_type": {},
            "by_rank": {},
        }
