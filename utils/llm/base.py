"""
Base LLM provider abstraction.

All LLM providers (Groq, NVIDIA NIM, Regex) implement this interface
so the application can transparently switch between them.
"""
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class LLMResult:
    """Result from an LLM extraction call."""
    keys: List[Dict] = field(default_factory=list)
    provider: str = "unknown"
    success: bool = False
    error: Optional[str] = None
    latency: float = 0.0


class BaseLLM(ABC):
    """
    Abstract base class for all LLM providers.

    Each provider must implement ``extract`` and ``is_available``.
    The ``extract`` method takes a list of text strings and returns
    a list of classified key dictionaries.
    """

    def __init__(self, name: str = "base"):
        self.name = name
        self._available: bool = True

    @abstractmethod
    def extract(self, texts: List[str]) -> LLMResult:
        """
        Extract and classify API keys from text.

        Args:
            texts: List of text strings to scan.

        Returns:
            LLMResult with extracted keys and metadata.
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this provider is available (API key configured, etc.)."""
        pass

    def mark_unavailable(self, reason: str = "") -> None:
        """Mark this provider as unavailable (e.g., after repeated failures)."""
        self._available = False
        logger.warning(f"LLM provider '{self.name}' marked unavailable: {reason}")
