"""
Regex-based LLM provider (fallback).

When both Groq and NVIDIA NIM are unavailable, this provider
uses regex-based classification to extract keys from text.
It never fails (no network calls) so the application can always
continue scanning.
"""
import time
import logging
from typing import List, Dict, Optional

from utils.llm.base import BaseLLM, LLMResult
from config.patterns import KeyClassifier

logger = logging.getLogger(__name__)


class RegexProvider(BaseLLM):
    """
    Regex-based key extraction provider.

    This is the ultimate fallback - it uses no network calls and
    therefore can never fail due to network issues.
    """

    def __init__(self, classifier: Optional[KeyClassifier] = None):
        super().__init__("regex")
        self._classifier = classifier or KeyClassifier()

    def is_available(self) -> bool:
        """Regex provider is always available."""
        return True

    def extract(self, texts: List[str]) -> LLMResult:
        """
        Extract keys using regex-based classification.

        Args:
            texts: List of text strings to scan.

        Returns:
            LLMResult with extracted keys.
        """
        start_time = time.time()
        results = []

        for text in texts:
            # Try to classify the entire text
            classified = self._classifier.classify(text)
            if classified:
                results.append(classified)
            else:
                # Try line-by-line extraction
                for line in text.split("\n"):
                    classified = self._classifier.classify(line)
                    if classified:
                        results.append(classified)

        return LLMResult(
            keys=results,
            provider=self.name,
            success=True,
            latency=time.time() - start_time,
        )
