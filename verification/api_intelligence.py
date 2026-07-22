"""
API Key Intelligence for AlphaScan v0.5.

Detects and verifies API keys from cloud providers, payment processors,
AI providers, and development platforms.
"""
import re
import logging
from typing import Dict, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)

# ── API Key Patterns ────────────────────────────────────────────────────────
API_KEY_PATTERNS = {
    # Cloud Providers
    "aws": re.compile(r"AKIA[0-9A-Z]{16}"),
    "gcp": re.compile(r"AIza[0-9A-Za-z_-]{35}"),
    "azure": re.compile(r"(?<![a-zA-Z0-9])[a-zA-Z0-9]{32}(?![a-zA-Z0-9])"),

    # Payment Processors
    "stripe_live": re.compile(r"sk_live_[a-zA-Z0-9]{24,}"),
    "stripe_test": re.compile(r"sk_test_[a-zA-Z0-9]{24,}"),
    "paypal": re.compile(r"(?<![a-zA-Z0-9])[a-zA-Z0-9]{32}(?![a-zA-Z0-9])"),

    # AI Providers
    "openai": re.compile(r"sk-[a-zA-Z0-9-]{20,}"),
    "claude": re.compile(r"sk-ant-[a-zA-Z0-9_-]{20,}"),
    "google_ai": re.compile(r"AIza[0-9A-Za-z_-]{35}"),

    # Development Platforms
    "github": re.compile(r"gh[pousr]_[a-zA-Z0-9]{36}"),
    "gitlab": re.compile(r"glpat-[A-Za-z0-9-]{20}"),

    # Databases
    "mongodb": re.compile(r"mongodb(?:\+srv)?://[^\s]+"),
    "supabase": re.compile(r"(?<![a-zA-Z0-9])[a-zA-Z0-9]{20}\.[a-zA-Z0-9]{20}(?![a-zA-Z0-9])"),
    "firebase": re.compile(r"(?<![a-zA-Z0-9])[a-zA-Z0-9]{40}(?![a-zA-Z0-9])"),

    # Email/SMS
    "twilio": re.compile(r"(?<![a-zA-Z0-9])[a-zA-Z0-9]{34}(?![a-zA-Z0-9])"),
    "sendgrid": re.compile(r"SG\.[a-zA-Z0-9_-]{40}"),
    "mailgun": re.compile(r"(?<![a-zA-Z0-9])[a-zA-Z0-9]{32}(?![a-zA-Z0-9])"),

    # OAuth
    "google_oauth": re.compile(r"[0-9]+-[a-zA-Z0-9]{32}\.apps\.googleusercontent\.com"),

    # Generic
    "generic_apikey": re.compile(r'(?i)(?:api[_-]?key|apikey|secret[_-]?key|access[_-]?token)["\']?\s*[:=]\s*["\']?([a-zA-Z0-9_-]{32,})'),
    "generic_bearer": re.compile(r"(?i)bearer\s+([a-zA-Z0-9._-]{20,})"),
}

# Rank mapping for API key types
API_RANK_MAP = {
    "aws": 7, "gcp": 7, "azure": 7,
    "stripe_live": 8, "stripe_test": 8, "paypal": 8,
    "openai": 9, "claude": 9, "google_ai": 9,
    "github": 10, "gitlab": 10,
    "mongodb": 10, "supabase": 10, "firebase": 10,
    "twilio": 10, "sendgrid": 10, "mailgun": 10,
    "google_oauth": 10,
    "generic_apikey": 10, "generic_bearer": 10,
}

# Descriptions for API key types
API_DESCRIPTIONS = {
    "aws": "AWS Access Key ID",
    "gcp": "Google Cloud API key",
    "azure": "Azure API key",
    "stripe_live": "Stripe Live secret key",
    "stripe_test": "Stripe Test secret key",
    "paypal": "PayPal API key",
    "openai": "OpenAI API key",
    "claude": "Anthropic/Claude API key",
    "google_ai": "Google AI API key",
    "github": "GitHub token",
    "gitlab": "GitLab token",
    "mongodb": "MongoDB connection string",
    "supabase": "Supabase key",
    "firebase": "Firebase API key",
    "twilio": "Twilio API key",
    "sendgrid": "SendGrid API key",
    "mailgun": "Mailgun API key",
    "google_oauth": "Google OAuth client",
    "generic_apikey": "Generic API key",
    "generic_bearer": "Generic Bearer token",
}

# Prefix for masking
API_PREFIXES = {
    "aws": "AKIA",
    "gcp": "AIza",
    "azure": "[redacted]",
    "stripe_live": "sk_live_",
    "stripe_test": "sk_test_",
    "paypal": "[redacted]",
    "openai": "sk-",
    "claude": "sk-ant-",
    "google_ai": "AIza",
    "github": "ghp_",
    "gitlab": "glpat-",
    "mongodb": "mongodb",
    "supabase": "[redacted]",
    "firebase": "[redacted]",
    "twilio": "[redacted]",
    "sendgrid": "SG.",
    "mailgun": "[redacted]",
    "google_oauth": "[redacted]",
    "generic_apikey": "[redacted]",
    "generic_bearer": "[redacted]",
}


class APIIntelligence:
    """
    Detects and verifies API keys from various providers.
    Uses format validation for verification (passive).
    """

    def __init__(self):
        self._patterns = API_KEY_PATTERNS

    def detect(self, text: str) -> List[Dict]:
        """
        Detect API keys in text.

        Args:
            text: Text to scan for API keys.

        Returns:
            List of detected API key dicts with analysis.
        """
        results = []

        for key_type, pattern in self._patterns.items():
            for match in pattern.finditer(text):
                value = match.group(1) if match.groups() else match.group(0)

                analysis = self._analyze_key(key_type, value, text)
                if analysis:
                    results.append(analysis)

        return results

    def _analyze_key(self, key_type: str, value: str, context: str) -> Optional[Dict]:
        """Analyze a detected API key."""
        rank = API_RANK_MAP.get(key_type, 10)
        description = API_DESCRIPTIONS.get(key_type, "Unknown API Key")

        # Check for production vs test environment
        context_lower = context.lower() if context else ""
        is_production = any(kw in context_lower for kw in ["prod", "production", "live"])
        is_test = any(kw in context_lower for kw in ["test", "dev", "staging", "sandbox"])

        # Adjust rank based on environment
        if is_production and not is_test:
            rank = max(0, rank - 1)  # Boost rank for production keys
        elif is_test:
            rank = min(10, rank + 1)  # Penalize test keys

        return {
            "type": key_type,
            "value": value,
            "description": description,
            "rank": rank,
            "context": context[:200] if context else "",
            "is_production": is_production,
            "is_test": is_test,
            "detected_at": datetime.utcnow().isoformat(),
        }

    def verify(self, key_data: Dict) -> Dict:
        """
        Verify an API key entry using format validation.

        Args:
            key_data: Dict with API key information.

        Returns:
            Dict with verification results.
        """
        key_type = key_data.get("type", "")
        value = key_data.get("value", "")

        checks = {}

        # Format validation based on key type
        if key_type == "aws":
            checks["format_valid"] = bool(re.match(r"AKIA[0-9A-Z]{16}", value))
            checks["length_valid"] = len(value) == 20
        elif key_type in ("gcp", "google_ai"):
            checks["format_valid"] = bool(re.match(r"AIza[0-9A-Za-z_-]{35}", value))
            checks["length_valid"] = len(value) >= 39
        elif key_type == "azure":
            checks["format_valid"] = len(value) == 32 and value.isalnum()
        elif key_type in ("stripe_live", "stripe_test"):
            prefix = "sk_live_" if key_type == "stripe_live" else "sk_test_"
            checks["format_valid"] = value.startswith(prefix) and len(value) >= 30
        elif key_type == "openai":
            checks["format_valid"] = value.startswith("sk-") and len(value) >= 23
        elif key_type == "claude":
            checks["format_valid"] = value.startswith("sk-ant-") and len(value) >= 25
        elif key_type == "github":
            checks["format_valid"] = bool(re.match(r"gh[pousr]_[a-zA-Z0-9]{36}", value))
        elif key_type == "gitlab":
            checks["format_valid"] = bool(re.match(r"glpat-[A-Za-z0-9-]{20}", value))
        elif key_type == "sendgrid":
            checks["format_valid"] = value.startswith("SG.") and len(value) >= 43
        elif key_type == "mongodb":
            checks["format_valid"] = value.startswith("mongodb")
        elif key_type == "google_oauth":
            checks["format_valid"] = ".apps.googleusercontent.com" in value
        else:
            checks["format_valid"] = len(value) >= 16

        verified = checks.get("format_valid", False)

        return {
            "verified": verified,
            "method": "format_validation",
            "checks": checks,
            "risk_level": "high" if verified else "low",
            "note": "Format validation only - no live API calls made",
        }

    def get_all_patterns(self) -> Dict:
        """Get all API key patterns for knowledge base export."""
        return {
            key_type: {
                "pattern": pattern.pattern,
                "description": API_DESCRIPTIONS.get(key_type, ""),
                "rank": API_RANK_MAP.get(key_type, 10),
            }
            for key_type, pattern in self._patterns.items()
        }
