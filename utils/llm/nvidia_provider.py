"""
NVIDIA NIM LLM provider.

Secondary LLM provider for AI-powered key extraction.
Uses NVIDIA NIM (NVIDIA Inference Microservices) API.
"""
import json
import time
import logging
from typing import List, Dict, Optional

from utils.llm.base import BaseLLM, LLMResult
from utils.http_client import get_http_client
from config.patterns import KeyClassifier

logger = logging.getLogger(__name__)

# Default NVIDIA NIM endpoint
DEFAULT_NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"


class NvidiaProvider(BaseLLM):
    """
    NVIDIA NIM LLM provider for key extraction.

    Used as a fallback when Groq is unavailable.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        super().__init__("nvidia")
        self.api_key = api_key
        self.base_url = (base_url or DEFAULT_NVIDIA_BASE_URL).rstrip("/")
        self.model = model or "nvidia/llama-2-70b"
        self._http = get_http_client()
        self._classifier = KeyClassifier()

    def is_available(self) -> bool:
        """Check if NVIDIA NIM is available."""
        return bool(self.api_key) and self._available

    def extract(self, texts: List[str]) -> LLMResult:
        """
        Extract keys using NVIDIA NIM API.

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
                error="NVIDIA API key not configured",
            )

        if not texts:
            return LLMResult(keys=[], provider=self.name, success=True)

        start_time = time.time()

        combined_text = "\n".join(texts[:50])
        prompt = self._build_prompt(combined_text)

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
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
            "stream": False,
        }

        response = self._http.post(
            url,
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
            error_msg = f"NVIDIA NIM API returned HTTP {response.status_code}"
            try:
                error_data = response.json()
                if "error" in error_data:
                    error_msg = str(error_data["error"])
            except Exception:
                pass
            logger.warning(f"NVIDIA NIM API error: {error_msg}")
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
            logger.warning(f"Failed to parse NVIDIA NIM response: {e}")
            return LLMResult(
                keys=[],
                provider=self.name,
                success=False,
                error=f"Failed to parse response: {e}",
                latency=time.time() - start_time,
            )

    def _build_prompt(self, text: str) -> str:
        """Build the extraction prompt."""
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
        """Parse JSON from the LLM response."""
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            return json.loads(content)

    def _normalize_results(self, results: List[Dict]) -> List[Dict]:
        """Normalize results."""
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
