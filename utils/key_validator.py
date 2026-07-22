"""
Key validator module for APIS.
Validates discovered API keys using pattern matching and optional live checks.
"""
import re
import logging
from typing import List, Dict, Optional, Tuple
from config.patterns import KeyClassifier
from config.settings import KEY_LOG_PREVIEW_LENGTH

logger = logging.getLogger(__name__)


class KeyValidator:
    """
    Validates API keys discovered by scanners.
    Uses regex patterns for initial validation and optionally checks live endpoints.
    """

    # Validation rules per key type: (min_length, max_length, extra_check)
    VALIDATION_RULES: Dict[str, Dict] = {
        "openai": {"min_len": 20, "max_len": 200, "prefix": "sk-"},
        "claude": {"min_len": 20, "max_len": 200, "prefix": "sk-ant-"},
        "aws": {"min_len": 20, "max_len": 20, "prefix": "AKIA"},
        "google": {"min_len": 35, "max_len": 50, "prefix": "AIza"},
        "github": {"min_len": 36, "max_len": 80, "prefix": "ghp_"},
        "stripe_live": {"min_len": 24, "max_len": 100, "prefix": "sk_live_"},
        "stripe_test": {"min_len": 24, "max_len": 100, "prefix": "sk_test_"},
        "discord": {"min_len": 59, "max_len": 80, "prefix": None},
        "slack": {"min_len": 10, "max_len": 200, "prefix": "xox"},
        "mongodb": {"min_len": 10, "max_len": 500, "prefix": "mongodb"},
        "postgresql": {"min_len": 10, "max_len": 500, "prefix": "postgresql"},
        "mysql": {"min_len": 10, "max_len": 500, "prefix": "mysql"},
    }

    def __init__(self, classifier: Optional[KeyClassifier] = None):
        self.classifier = classifier or KeyClassifier()

    def validate(self, key_data: Dict) -> bool:
        """
        Validate a single key entry.

        Args:
            key_data: Dict with 'type' and 'value' keys.

        Returns:
            True if the key passes validation, False otherwise.
        """
        key_type = key_data.get("type", "")
        value = key_data.get("value", "")

        if not value:
            return False

        # Check against validation rules
        rules = self.VALIDATION_RULES.get(key_type)
        if rules:
            if len(value) < rules["min_len"]:
                logger.debug(f"Key too short for type {key_type}")
                return False
            if len(value) > rules["max_len"]:
                logger.debug(f"Key too long for type {key_type}")
                return False
            if rules.get("prefix") and not value.startswith(rules["prefix"]):
                logger.debug(f"Key prefix mismatch for type {key_type}")
                return False
        else:
            # Generic validation: must be at least 20 chars and look like a key
            if len(value) < 20:
                return False

        return True

    def validate_batch(self, keys: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """
        Validate a batch of keys.

        Returns:
            Tuple of (valid_keys, invalid_keys).
        """
        valid = []
        invalid = []
        for key in keys:
            if self.validate(key):
                valid.append(key)
            else:
                invalid.append(key)
        return valid, invalid

    def mask_key(self, value: str) -> str:
        """Mask a key value for safe logging."""
        if len(value) <= KEY_LOG_PREVIEW_LENGTH:
            return "*" * len(value)
        return value[:KEY_LOG_PREVIEW_LENGTH] + "*" * 3

    def is_duplicate(self, key_value: str, existing_keys: List[Dict]) -> bool:
        """Check if a key value already exists in the collection."""
        for existing in existing_keys:
            if existing.get("value") == key_value:
                return True
        return False
