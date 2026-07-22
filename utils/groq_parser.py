"""
AI-powered key extraction and classification using Groq API.
Falls back to regex-based classification if the API is unavailable.
"""
import logging
import json
from typing import List, Dict, Optional
from config.settings import GROQ_API_KEY
from config.patterns import KeyClassifier

logger = logging.getLogger(__name__)

# Groq API endpoint
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"


class GroqParser:
    """
    Uses Groq AI to extract and classify API keys from text.
    Falls back to regex classification when the API is unavailable.
    """

    def __init__(self, api_key: Optional[str] = None,
                 classifier: Optional[KeyClassifier] = None):
        self.api_key = api_key or GROQ_API_KEY
        self.classifier = classifier or KeyClassifier()
        self._api_available = bool(self.api_key)

    def extract(self, texts: List[str]) -> List[Dict]:
        """
        Extract and classify API keys from a list of text strings.

        Tries Groq AI first, falls back to regex classification.

        Args:
            texts: List of text strings to scan.

        Returns:
            List of classified key dicts.
        """
        if not texts:
            return []

        # Try Groq AI first
        if self._api_available:
            try:
                ai_results = self._extract_with_groq(texts)
                if ai_results:
                    return ai_results
            except Exception as e:
                logger.warning(f"Groq API failed, falling back to regex: {e}")

        # Fallback to regex classification
        return self._extract_with_regex(texts)

    def _extract_with_groq(self, texts: List[str]) -> List[Dict]:
        """Extract keys using Groq AI API."""
        import requests

        # Build prompt for AI
        combined_text = "\n".join(texts[:50])  # Limit to first 50 texts
        prompt = (
            f"Extract all API keys, secrets, and tokens from the following text. "
            f"For each key found, return a JSON array with objects containing: "
            f'"type" (the key type like "openai", "claude", "aws", "google", "github", '
            f'"stripe", "discord", "slack", "mongodb", "postgresql", "mysql", or "generic"), '
            f'"value" (the actual key string), "description" (what the key is for). '
            f"Only return valid JSON, no other text. If no keys found, return an empty array.\n\n"
            f"Text:\n{combined_text}"
        )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": "llama-3.2-3b-preview",
            "messages": [
                {"role": "system", "content": "You are an expert security analyst extracting API keys from text."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.1,
            "max_tokens": 4096,
        }

        response = requests.post(
            GROQ_API_URL,
            headers=headers,
            json=payload,
            timeout=30,
        )
        response.raise_for_status()

        data = response.json()
        content = data["choices"][0]["message"]["content"].strip()

        # Parse JSON response
        try:
            results = json.loads(content)
        except json.JSONDecodeError:
            # Try to extract JSON from code blocks
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            results = json.loads(content)

        # Normalize results
        normalized = []
        for item in results:
            if isinstance(item, dict) and "value" in item:
                item.setdefault("type", "generic")
                item.setdefault("description", "")
                # Add masked value
                item["masked_value"] = self.classifier._mask_value(
                    item["value"], item.get("type", "generic")
                )
                normalized.append(item)

        return normalized

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
