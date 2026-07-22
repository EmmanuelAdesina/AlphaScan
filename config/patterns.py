"""
Key classification patterns for APIS.

Each pattern is a tuple of (name, regex_pattern, description).
Patterns are evaluated in order; the first match wins.
"""
import re
from typing import List, Tuple, Dict, Optional

# ── Static Pattern Definitions ─────────────────────────────────────────────
# (name, pattern, description, prefix_for_masking)
PATTERNS: List[Tuple[str, str, str, str]] = [
    # Anthropic / Claude (must come before OpenAI since sk-ant- also starts with sk-)
    ("claude", r"sk-ant-[a-zA-Z0-9_-]{20,}", "Anthropic/Claude API key", "sk-ant-"),
    # OpenAI
    ("openai", r"sk-[a-zA-Z0-9-]{20,}", "OpenAI API key", "sk-"),
    # AWS
    ("aws", r"AKIA[0-9A-Z]{16}", "AWS Access Key ID", "AKIA"),
    # Google
    ("google", r"AIza[0-9A-Za-z_-]{35}", "Google API key", "AIza"),
    # GitHub
    ("github", r"gh[pousr]_[a-zA-Z0-9]{36}", "GitHub token", "ghp_"),
    # Stripe Live
    ("stripe_live", r"sk_live_[a-zA-Z0-9]{24,}", "Stripe Live secret key", "sk_live_"),
    # Stripe Test
    ("stripe_test", r"sk_test_[a-zA-Z0-9]{24,}", "Stripe Test secret key", "sk_test_"),
    # Discord
    ("discord", r"[\w-]{24}\.[\w-]{6}\.[\w-]{27}", "Discord bot token", "[redacted]"),
    # Slack
    ("slack", r"xox[baprs]-[a-zA-Z0-9-]{10,}", "Slack token", "xox"),
    # MongoDB connection string
    ("mongodb", r"mongodb(?:\+srv)?://[^\s]+", "MongoDB connection string", "mongodb"),
    # PostgreSQL connection string
    ("postgresql", r"postgresql://[^\s]+", "PostgreSQL connection string", "postgresql"),
    # MySQL connection string
    ("mysql", r"mysql://[^\s]+", "MySQL connection string", "mysql"),
    # Generic API key patterns
    ("generic_apikey", r'(?i)(?:api[_-]?key|apikey|secret[_-]?key|access[_-]?token)["\']?\s*[:=]\s*["\']?([a-zA-Z0-9_-]{32,})', "Generic API key", "[redacted]"),
    ("generic_bearer", r"(?i)bearer\s+([a-zA-Z0-9._-]{20,})", "Generic Bearer token", "[redacted]"),
]


class KeyClassifier:
    """
    Classifies API keys and secrets using regex patterns.
    Supports dynamic addition of new patterns (self-improvement).
    """

    def __init__(self):
        self._patterns: List[Tuple[str, re.Pattern, str, str]] = []
        self._load_patterns(PATTERNS)

    def _load_patterns(self, patterns: List[Tuple[str, str, str, str]]) -> None:
        """Compile and load patterns."""
        for name, pattern, description, prefix in patterns:
            try:
                compiled = re.compile(pattern)
                self._patterns.append((name, compiled, description, prefix))
            except re.error:
                pass  # Skip invalid patterns

    def classify(self, text: str) -> Optional[Dict]:
        """
        Classify a given text string to identify the key type.

        Args:
            text: The text to classify.

        Returns:
            Dict with keys: type, value, description, masked_value
            or None if no pattern matches.
        """
        for name, pattern, description, prefix in self._patterns:
            match = pattern.search(text)
            if match:
                # Extract the matched value (group 1 if exists, else full match)
                value = match.group(1) if match.groups() else match.group(0)
                return {
                    "type": name,
                    "value": value,
                    "description": description,
                    "masked_value": self._mask_value(value, prefix),
                }
        return None

    def classify_batch(self, texts: List[str]) -> List[Dict]:
        """Classify a batch of texts, returning only matched keys."""
        results = []
        for text in texts:
            result = self.classify(text)
            if result:
                results.append(result)
        return results

    def _mask_value(self, value: str, prefix: str) -> str:
        """Mask a key value, showing only the prefix and first few chars."""
        if len(value) <= 10:
            return value[:4] + "..."
        if prefix == "[redacted]":
            return f"[redacted:{value[:6]}...]"
        return f"{value[:len(prefix) + 4]}..."

    def add_pattern(self, name: str, pattern: str, description: str,
                    prefix: str = "[redacted]") -> bool:
        """
        Dynamically add a new pattern (used by self-improvement engine).

        Returns True if the pattern was added successfully.
        """
        try:
            compiled = re.compile(pattern)
            self._patterns.append((name, compiled, description, prefix))
            # Also add to the static list for persistence
            PATTERNS.append((name, pattern, description, prefix))
            return True
        except re.error:
            return False

    def get_pattern_names(self) -> List[str]:
        """Return list of all pattern names."""
        return [p[0] for p in self._patterns]

    def get_all_patterns(self) -> List[Dict]:
        """Return all patterns as dicts (for knowledge base export)."""
        return [
            {"name": p[0], "pattern": p[1].pattern, "description": p[2]}
            for p in self._patterns
        ]


# Singleton instance
classifier = KeyClassifier()
