"""
LLM provider abstraction for AlphaScan.

Provides a unified interface for AI-powered key extraction with automatic
failover between providers:

    Groq (primary) → NVIDIA NIM (secondary) → Regex (fallback)

Each provider implements the same ``BaseLLM`` interface so the rest of
the application does not need to know which provider is active.
"""
from utils.llm.base import BaseLLM, LLMResult
from utils.llm.groq_provider import GroqProvider
from utils.llm.nvidia_provider import NvidiaProvider
from utils.llm.regex_provider import RegexProvider
from utils.llm.manager import LLMManager

__all__ = [
    "BaseLLM",
    "LLMResult",
    "GroqProvider",
    "NvidiaProvider",
    "RegexProvider",
    "LLMManager",
]
