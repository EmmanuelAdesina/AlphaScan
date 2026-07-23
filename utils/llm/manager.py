"""
LLM Manager - handles automatic failover between providers.

Priority order:
    1. Groq (primary)
    2. NVIDIA NIM (secondary)
    3. Regex (fallback, always available)
"""
import logging
from typing import List, Dict, Optional

from utils.llm.base import BaseLLM, LLMResult
from utils.llm.groq_provider import GroqProvider
from utils.llm.nvidia_provider import NvidiaProvider
from utils.llm.regex_provider import RegexProvider

logger = logging.getLogger(__name__)


class LLMManager:
    """
    Manages LLM providers with automatic failover.

    Tries providers in priority order. If a provider fails, it is
    temporarily marked unavailable and the next provider is tried.
    The regex provider is always available as a last resort.
    """

    def __init__(
        self,
        groq_api_key: Optional[str] = None,
        groq_model: Optional[str] = None,
        nvidia_api_key: Optional[str] = None,
        nvidia_base_url: Optional[str] = None,
        nvidia_model: Optional[str] = None,
    ):
        self.providers: List[BaseLLM] = []

        # Build providers in priority order
        self.groq = GroqProvider(api_key=groq_api_key, model=groq_model)
        self.nvidia = NvidiaProvider(
            api_key=nvidia_api_key,
            base_url=nvidia_base_url,
            model=nvidia_model,
        )
        self.regex = RegexProvider()

        self.providers = [self.groq, self.nvidia, self.regex]
        self._active_provider: str = "regex"

    def extract(self, texts: List[str]) -> LLMResult:
        """
        Extract keys using the best available provider.

        Tries each provider in priority order. If a provider fails,
        it is marked unavailable and the next provider is tried.

        Args:
            texts: List of text strings to scan.

        Returns:
            LLMResult with extracted keys.
        """
        if not texts:
            return LLMResult(keys=[], provider="none", success=True)

        for provider in self.providers:
            if not provider.is_available():
                logger.debug(f"Provider '{provider.name}' not available, skipping")
                continue

            logger.debug(f"Trying LLM provider: {provider.name}")
            result = provider.extract(texts)

            if result.success and result.keys:
                self._active_provider = provider.name
                logger.info(
                    f"LLM extraction succeeded with provider '{provider.name}' "
                    f"({len(result.keys)} keys, {result.latency:.2f}s)"
                )
                return result

            if result.success and not result.keys:
                # Provider succeeded but found no keys
                self._active_provider = provider.name
                logger.info(
                    f"LLM provider '{provider.name}' found no keys "
                    f"(success, {result.latency:.2f}s)"
                )
                return result

            # Provider failed - mark it unavailable and try next
            if result.error:
                logger.warning(
                    f"LLM provider '{provider.name}' failed: {result.error}"
                )
                provider.mark_unavailable(result.error)

        # All providers failed - this should not happen since regex is always available
        logger.error("All LLM providers failed - this should not happen")
        return LLMResult(
            keys=[],
            provider="none",
            success=False,
            error="All LLM providers failed",
        )

    def get_active_provider(self) -> str:
        """Get the name of the currently active provider."""
        return self._active_provider

    def get_provider_status(self) -> Dict:
        """Get status of all providers."""
        return {
            "active": self._active_provider,
            "providers": {
                p.name: {
                    "available": p.is_available(),
                    "configured": bool(getattr(p, "api_key", None)),
                }
                for p in self.providers
            },
        }

    def reset_provider(self, name: str) -> None:
        """Reset a provider's availability (e.g., after fixing an issue)."""
        for provider in self.providers:
            if provider.name == name:
                provider._available = True
                logger.info(f"Provider '{name}' reset to available")
                break
