"""
AI-powered key extraction and classification using LLM providers.
Uses Groq (primary), NVIDIA NIM (secondary), and regex (fallback).
"""
import logging
import time
from typing import List, Dict, Optional

from config.settings import (
    GROQ_API_KEY, NVIDIA_API_KEY, NVIDIA_BASE_URL, NVIDIA_MODEL,
)
from config.patterns import KeyClassifier
from utils.llm.manager import LLMManager

logger = logging.getLogger(__name__)


class GroqParser:
    """
    Uses LLM providers to extract and classify API keys from text.

    Provider priority:
        1. Groq (primary)
        2. NVIDIA NIM (secondary)
        3. Regex (fallback, always available)
    """

    def __init__(self, api_key: Optional[str] = None,
                 classifier: Optional[KeyClassifier] = None,
                 llm_manager: Optional[LLMManager] = None):
        self.llm_manager = llm_manager or LLMManager(
            groq_api_key=api_key or GROQ_API_KEY,
            nvidia_api_key=NVIDIA_API_KEY,
            nvidia_base_url=NVIDIA_BASE_URL,
            nvidia_model=NVIDIA_MODEL,
        )
        self.classifier = classifier or KeyClassifier()

    def extract(self, texts: List[str]) -> List[Dict]:
        """
        Extract and classify API keys from a list of text strings.

        Uses the LLM manager which automatically fails over between
        Groq -> NVIDIA -> Regex.

        Args:
            texts: List of text strings to scan.

        Returns:
            List of classified key dicts.
        """
        if not texts:
            return []

        start_time = time.time()

        try:
            result = self.llm_manager.extract(texts)

            if result.success:
                logger.info(
                    f"LLM extraction completed with provider '{result.provider}': "
                    f"{len(result.keys)} keys in {result.latency:.2f}s"
                )
                return result.keys
            else:
                logger.warning(
                    f"LLM extraction failed: {result.error}. Falling back to regex."
                )
        except Exception as e:
            logger.warning(f"LLM extraction error: {e}. Falling back to regex.")

        # Final fallback: regex classification
        return self._extract_with_regex(texts)

    def _extract_with_regex(self, texts: List[str]) -> List[Dict]:
        """Extract keys using regex-based classification (fallback)."""
        results = []
        for text in texts:
            # Try to classify the entire text
            classified = self.classifier.classify(text)
            if classified:
                results.append(classified)
            else:
                # Try line-by-line extraction
                for line in text.split("\n"):
                    classified = self.classifier.classify(line)
                    if classified:
                        results.append(classified)
        return results

    def classify_key(self, key_value: str) -> Optional[Dict]:
        """Classify a single key value."""
        return self.classifier.classify(key_value)