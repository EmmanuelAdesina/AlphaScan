"""
API Key Verifier - Individual verifier for API keys.
Implements passive verification: format validation, prefix checking, length validation.
"""
import re
import logging
from typing import Dict, Optional
from verification.api_intelligence import APIIntelligence

logger = logging.getLogger(__name__)


class APIVerifier:
    """
    Verifies API keys using format validation (passive).
    No live API calls are made.
    """

    def __init__(self):
        self._intelligence = APIIntelligence()

    def verify(self, key_data: Dict) -> Dict:
        """
        Verify an API key entry.

        Args:
            key_data: Dict with API key information.

        Returns:
            Dict with verification results.
        """
        key_type = key_data.get("type", "")
        value = key_data.get("value", "")

        # Layer 1: Format Validation
        format_result = self._validate_format(key_type, value)
        format_valid = format_result["valid"]

        # Layer 2: Entropy Analysis
        from config.patterns import calculate_entropy, get_entropy_category
        entropy = calculate_entropy(value)
        entropy_category = get_entropy_category(entropy)

        # Layer 3: Context Analysis
        context = key_data.get("context", "")
        context_lower = context.lower() if context else ""
        is_production = any(kw in context_lower for kw in ["prod", "production", "live"])
        is_test = any(kw in context_lower for kw in ["test", "dev", "staging", "sandbox"])

        # Determine verification status
        verified = format_valid and entropy > 0

        return {
            "verified": verified,
            "method": "passive_api_verification",
            "layers": {
                "layer_1_format": {
                    "passed": format_valid,
                    "details": format_result["details"],
                    "prefix_check": format_result.get("prefix_check", True),
                    "length_check": format_result.get("length_check", True),
                },
                "layer_2_entropy": {
                    "passed": entropy > 1.5,
                    "entropy": round(entropy, 4),
                    "category": entropy_category,
                },
                "layer_3_context": {
                    "passed": True,
                    "is_production": is_production,
                    "is_test": is_test,
                },
            },
            "risk_level": self._determine_risk_level(key_type, verified, is_production),
            "note": "Format validation only - no live API calls made",
        }

    def _validate_format(self, key_type: str, value: str) -> Dict:
        """Validate format based on key type."""
        result = {"valid": False, "details": "", "prefix_check": True, "length_check": True}

        if key_type == "aws":
            result["valid"] = bool(re.match(r"AKIA[0-9A-Z]{16}", value))
            result["prefix_check"] = value.startswith("AKIA")
            result["length_check"] = len(value) == 20
            result["details"] = "AWS Access Key ID format" if result["valid"] else "Invalid AWS key format"

        elif key_type in ("gcp", "google_ai"):
            result["valid"] = bool(re.match(r"AIza[0-9A-Za-z_-]{35}", value))
            result["prefix_check"] = value.startswith("AIza")
            result["length_check"] = len(value) >= 39
            result["details"] = "Google API key format" if result["valid"] else "Invalid Google key format"

        elif key_type == "azure":
            result["valid"] = len(value) == 32 and value.isalnum()
            result["length_check"] = len(value) == 32
            result["details"] = "Azure API key format" if result["valid"] else "Invalid Azure key format"

        elif key_type == "stripe_live":
            result["valid"] = value.startswith("sk_live_") and len(value) >= 30
            result["prefix_check"] = value.startswith("sk_live_")
            result["length_check"] = len(value) >= 30
            result["details"] = "Stripe Live key format" if result["valid"] else "Invalid Stripe Live key format"

        elif key_type == "stripe_test":
            result["valid"] = value.startswith("sk_test_") and len(value) >= 30
            result["prefix_check"] = value.startswith("sk_test_")
            result["length_check"] = len(value) >= 30
            result["details"] = "Stripe Test key format" if result["valid"] else "Invalid Stripe Test key format"

        elif key_type == "openai":
            result["valid"] = value.startswith("sk-") and len(value) >= 23
            result["prefix_check"] = value.startswith("sk-")
            result["length_check"] = len(value) >= 23
            result["details"] = "OpenAI API key format" if result["valid"] else "Invalid OpenAI key format"

        elif key_type == "claude":
            result["valid"] = value.startswith("sk-ant-") and len(value) >= 25
            result["prefix_check"] = value.startswith("sk-ant-")
            result["length_check"] = len(value) >= 25
            result["details"] = "Claude API key format" if result["valid"] else "Invalid Claude key format"

        elif key_type == "github":
            result["valid"] = bool(re.match(r"gh[pousr]_[a-zA-Z0-9]{36}", value))
            result["prefix_check"] = value.startswith("ghp_") or value.startswith("gho_") or value.startswith("ghu_")
            result["length_check"] = len(value) >= 40
            result["details"] = "GitHub token format" if result["valid"] else "Invalid GitHub token format"

        elif key_type == "gitlab":
            result["valid"] = bool(re.match(r"glpat-[A-Za-z0-9-]{20}", value))
            result["prefix_check"] = value.startswith("glpat-")
            result["length_check"] = len(value) >= 26
            result["details"] = "GitLab token format" if result["valid"] else "Invalid GitLab token format"

        elif key_type == "sendgrid":
            result["valid"] = value.startswith("SG.") and len(value) >= 43
            result["prefix_check"] = value.startswith("SG.")
            result["length_check"] = len(value) >= 43
            result["details"] = "SendGrid API key format" if result["valid"] else "Invalid SendGrid key format"

        elif key_type == "mongodb":
            result["valid"] = value.startswith("mongodb")
            result["prefix_check"] = value.startswith("mongodb")
            result["details"] = "MongoDB connection string" if result["valid"] else "Invalid MongoDB connection string"

        elif key_type == "google_oauth":
            result["valid"] = ".apps.googleusercontent.com" in value
            result["details"] = "Google OAuth client" if result["valid"] else "Invalid Google OAuth client"

        else:
            result["valid"] = len(value) >= 16
            result["length_check"] = len(value) >= 16
            result["details"] = f"Generic API key format ({key_type})"

        return result

    def _determine_risk_level(self, key_type: str, verified: bool, is_production: bool) -> str:
        """Determine risk level based on key type and verification status."""
        if not verified:
            return "low"

        # Production keys are higher risk
        if is_production:
            if key_type in ("aws", "gcp", "azure"):
                return "high"
            elif key_type in ("stripe_live", "paypal"):
                return "critical"
            elif key_type in ("openai", "claude", "google_ai"):
                return "high"
            elif key_type in ("github", "gitlab"):
                return "high"

        # Non-production keys
        if key_type in ("stripe_live", "paypal"):
            return "high"
        elif key_type in ("aws", "gcp", "azure"):
            return "medium"
        elif key_type in ("openai", "claude", "google_ai"):
            return "medium"
        elif key_type in ("github", "gitlab"):
            return "medium"
        elif key_type == "stripe_test":
            return "low"

        return "medium"
