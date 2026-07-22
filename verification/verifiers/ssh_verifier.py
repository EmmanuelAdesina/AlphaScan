"""
SSH Key Verifier - Individual verifier for SSH private keys.
Implements passive verification: format validation, fingerprint generation,
encryption status detection. NEVER uses the key.
"""
import re
import base64
import hashlib
import logging
from typing import Dict, Optional
from verification.ssh_intelligence import SSHIntelligence

logger = logging.getLogger(__name__)


class SSHVerifier:
    """
    Verifies SSH private keys using passive methods only.
    """

    def __init__(self):
        self._intelligence = SSHIntelligence()

    def verify(self, key_data: Dict) -> Dict:
        """
        Verify an SSH key entry.

        Args:
            key_data: Dict with SSH key information (type, value, etc.)

        Returns:
            Dict with verification results.
        """
        value = key_data.get("value", "")
        key_type = key_data.get("type", "")

        # Layer 1: Format Validation
        format_valid = self._validate_format(value, key_type)

        # Layer 2: Entropy Analysis
        entropy = self._calculate_entropy(value)

        # Layer 3: Context Analysis
        context = key_data.get("context", "")
        permissions = self._analyze_context(context)
        encrypted = key_data.get("encrypted", False)

        # Generate fingerprint
        fingerprint = self._generate_fingerprint(value)

        # Determine verification status - SSH keys are verified if they have
        # PEM headers (format) OR have sufficient entropy
        verified = format_valid or entropy > 0

        return {
            "verified": verified,
            "method": "passive_ssh_verification",
            "layers": {
                "layer_1_format": {
                    "passed": format_valid,
                    "details": "PEM format and base64 encoding validated" if format_valid else "Invalid PEM format",
                },
                "layer_2_entropy": {
                    "passed": entropy > 0,
                    "entropy": round(entropy, 4),
                    "category": self._get_entropy_category(entropy),
                },
                "layer_3_context": {
                    "passed": True,
                    "permissions": permissions,
                    "encrypted": encrypted,
                    "production": "prod" in context.lower() or "production" in context.lower(),
                },
            },
            "fingerprint": fingerprint,
            "encrypted": encrypted,
            "permissions": permissions,
            "risk_level": self._determine_risk_level(encrypted, permissions),
            "note": "Passive verification only - key was not used",
        }

    def _validate_format(self, value: str, key_type: str) -> bool:
        """Validate SSH key format."""
        # Check for PEM headers
        if "BEGIN" in value and "END" in value:
            return self._intelligence._validate_pem(value)
        # Check for public key format
        if value.startswith("ssh-rsa") or value.startswith("ssh-ed25519") or value.startswith("ecdsa"):
            return True
        return False

    def _calculate_entropy(self, value: str) -> float:
        """Calculate Shannon entropy of the key value."""
        from config.patterns import calculate_entropy
        return calculate_entropy(value)

    def _get_entropy_category(self, entropy: float) -> str:
        """Get entropy category."""
        from config.patterns import get_entropy_category
        return get_entropy_category(entropy)

    def _analyze_context(self, context: str) -> str:
        """Analyze context for permission level."""
        return self._intelligence._analyze_context(context)

    def _generate_fingerprint(self, value: str) -> str:
        """Generate MD5 fingerprint."""
        return self._intelligence._generate_fingerprint(value)

    def _determine_risk_level(self, encrypted: bool, permissions: str) -> str:
        """Determine risk level based on encryption and permissions."""
        if encrypted:
            return "high"
        if permissions in ("ROOT ACCESS", "ADMIN ACCESS"):
            return "critical"
        if permissions in ("SERVICE ACCOUNT", "AUTOMATION ACCOUNT", "CI/CD ACCOUNT", "DEPLOY ACCOUNT"):
            return "high"
        if permissions in ("DATABASE ACCOUNT",):
            return "medium"
        return "high"
