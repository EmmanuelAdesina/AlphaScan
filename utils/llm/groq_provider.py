"""
Groq LLM provider.

Primary LLM provider for AI-powered key extraction.
Uses the Groq API (OpenAI-compatible endpoint).
"""
import json
import time
import logging
from typing import List, Dict, Optional

from utils.llm.base import BaseLLM, LLMResult
from utils.http_client import get_http_client
from config.patterns import KeyClassifier

logger = logging.getLogger(__name__)

# Groq API endpoint (OpenAI-compatible)
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# Models supported by Groq (ordered by preference)
GROQ_MODELS = [
    "llama-3.1-8b-instant",
    "llama-3.2-3b-preview",
    "gemma2-9b-it",
    "mixtral-8x7b-32768",
]


class GroqProvider(BaseLLM):
    """
    Groq LLM provider for key extraction.

    Uses the Groq API to extract and classify API keys from text.
    Falls back to regex classification when the API is unavailable.
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        super().__init__("groq")
        self.api_key = api_key
        self.model = model or GROQ_MODELS[0]
        self._http = get_http_client()
        self._classifier = KeyClassifier()

    def is_available(self) -> bool:
        """Check if Groq is available (API key configured and not marked down)."""
        return bool(self.api_key) and self._available

    def extract(self, texts: List[str]) -> LLMResult:
        """
        Extract keys using Groq AI API.

        Args:
            texts: List of text strings to scan.

        Returns:
            LLMResult with extracted keys.
        """
        if not self.is_available():
            return LLMResult(
                keys=[],
                provider=self.name,
                success=False,
                error="Groq API key not configured",
            )

        if not texts:
            return LLMResult(keys=[], provider=self.name, success=True)

        start_time = time.time()

        # Build the prompt
        combined_text = "\n".join(texts[:50])  # Limit to first 50 texts
        prompt = self._build_prompt(combined_text)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are an expert security analyst extracting API keys, "
                        "secrets, and tokens from text. Return ONLY valid JSON."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.1,
            "max_tokens": 4096,
        }

        response = self._http.post(
            GROQ_API_URL,
            json=payload,
            headers=headers,
            timeout=30,
        )

        if response is None:
            return LLMResult(
                keys=[],
                provider=self.name,
                success=False,
                error="HTTP request failed (timeout or connection error)",
                latency=time.time() - start_time,
            )

        if response.status_code != 200:
            error_msg = f"Groq API returned HTTP {response.status_code}"
            try:
                error_data = response.json()
                error_msg = error_data.get("error", {}).get("message", error_msg)
            except Exception:
                pass
            logger.warning(f"Groq API error: {error_msg}")

            # If it's a 400 (bad request), try a different model
            if response.status_code == 400 and self.model != GROQ_MODELS[-1]:
                logger.info(f"Trying alternate model: {GROQ_MODELS[-1]}")
                self.model = GROQ_MODELS[-1]
                return self.extract(texts)

            return LLMResult(
                keys=[],
                provider=self.name,
                success=False,
                error=error_msg,
                latency=time.time() - start_time,
            )

        try:
            data = response.json()
            content = data["choices"][0]["message"]["content"].strip()
            results = self._parse_response(content)
            normalized = self._normalize_results(results)

            return LLMResult(
                keys=normalized,
                provider=self.name,
                success=True,
                latency=time.time() - start_time,
            )
        except (KeyError, json.JSONDecodeError) as e:
            logger.warning(f"Failed to parse Groq response: {e}")
            return LLMResult(
                keys=[],
                provider=self.name,
                success=False,
                error=f"Failed to parse response: {e}",
                latency=time.time() - start_time,
            )

    def _build_prompt(self, text: str) -> str:
        """Build the extraction prompt for the LLM."""
        return (
            "Extract all API keys, secrets, and tokens from the following text. "
            "For each key found, return a JSON array with objects containing: "
            '"type" (the key type like "openai", "claude", "aws", "google", '
            '"github", "stripe", "discord", "slack", "mongodb", "postgresql", '
            '"mysql", or "generic"), '
            '"value" (the actual key string), "description" (what the key is for). '
            "Only return valid JSON, no other text. If no keys found, return an empty array.\n\n"
            f"Text:\n{text}"
        )

    def _parse_response(self, content: str) -> List[Dict]:
        """Parse JSON from the LLM response, handling code blocks."""
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # Try to extract JSON from code blocks
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            return json.loads(content)

    def _normalize_results(self, results: List[Dict]) -> List[Dict]:
        """Normalize LLM results into the expected key dict format."""
        normalized = []
        for item in results:
            if isinstance(item, dict) and "value" in item:
                item.setdefault("type", "generic")
                item.setdefault("description", "")
                item["masked_value"] = self._classifier._mask_value(
                    item["value"], item.get("type", "generic")
                )
                normalized.append(item)
        return normalized
