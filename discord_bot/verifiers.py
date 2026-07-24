"""
Discord Bot Verifiers for AlphaScan v0.5
Handles endpoint verification and key validation for Discord interactions.
"""
import asyncio
import logging
from typing import Dict, List, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class EndpointVerifier:
    """Verify configured endpoints."""

    def __init__(self):
        self.endpoints = self._get_configured_endpoints()

    def _get_configured_endpoints(self) -> List[Dict[str, str]]:
        """Get all configured endpoints."""
        try:
            from config.settings import (
                CENSYS_API_ID,
                GITHUB_TOKEN,
                GROQ_API_KEY,
                DISCORD_WEBHOOK_URL,
                NVIDIA_API_KEY,
                ETHERSCAN_API_KEY,
            )

            endpoints = []

            if CENSYS_API_ID:
                endpoints.append({
                    "name": "Censys API",
                    "url": "https://censys.io/api/v1/account",
                })

            if GITHUB_TOKEN:
                endpoints.append({
                    "name": "GitHub API",
                    "url": "https://api.github.com/user",
                })

            if GROQ_API_KEY:
                endpoints.append({
                    "name": "Groq API",
                    "url": "https://api.groq.com/openai/v1/models",
                })

            if DISCORD_WEBHOOK_URL:
                endpoints.append({
                    "name": "Discord Webhook",
                    "url": DISCORD_WEBHOOK_URL,
                })

            if NVIDIA_API_KEY:
                endpoints.append({
                    "name": "NVIDIA API",
                    "url": "https://api.nvidia.com/v1/models",
                })

            if ETHERSCAN_API_KEY:
                endpoints.append({
                    "name": "Etherscan API",
                    "url": "https://api.etherscan.io/api",
                })

            return endpoints
        except Exception as e:
            logger.error(f"Error getting configured endpoints: {e}")
            return []

    async def verify_all(self) -> Dict[str, List]:
        """Verify all endpoints."""
        online = []
        offline = []
        slow = []

        tasks = [self._verify_endpoint(ep) for ep in self.endpoints]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for endpoint, result in zip(self.endpoints, results):
            if isinstance(result, Exception):
                offline.append({
                    "name": endpoint["name"],
                    "error": str(result),
                })
            elif result["status"] == "online":
                online.append(result)
            elif result["status"] == "slow":
                slow.append(result)
            else:
                offline.append(result)

        return {
            "online": online,
            "offline": offline,
            "slow": slow,
        }

    async def _verify_endpoint(self, endpoint: Dict) -> Dict:
        """Verify a single endpoint."""
        try:
            from utils.http_client import get_http_client

            client = get_http_client()
            url = endpoint["url"]

            # Try to send a simple HEAD request
            response = await asyncio.to_thread(
                client.head,
                url,
                timeout=5,
            )

            if response is None:
                return {
                    "name": endpoint["name"],
                    "status": "offline",
                    "error": "Timeout",
                }

            latency = response.elapsed.total_seconds() * 1000 if hasattr(response, 'elapsed') else 0

            if response.status_code >= 400:
                return {
                    "name": endpoint["name"],
                    "status": "offline",
                    "error": f"HTTP {response.status_code}",
                }

            if latency > 1000:
                return {
                    "name": endpoint["name"],
                    "status": "slow",
                    "latency": f"{latency:.0f}",
                }

            return {
                "name": endpoint["name"],
                "status": "online",
                "latency": f"{latency:.0f}",
            }
        except asyncio.TimeoutError:
            return {
                "name": endpoint["name"],
                "status": "offline",
                "error": "Timeout",
            }
        except Exception as e:
            logger.error(f"Error verifying endpoint {endpoint['name']}: {e}")
            return {
                "name": endpoint["name"],
                "status": "offline",
                "error": str(e),
            }


class KeyVerifier:
    """Verify configured API keys."""

    def __init__(self):
        self.keys = self._get_configured_keys()

    def _get_configured_keys(self) -> Dict[str, str]:
        """Get all configured API keys (without exposing values)."""
        try:
            from config.settings import (
                CENSYS_API_ID,
                GITHUB_TOKEN,
                GROQ_API_KEY,
                DISCORD_WEBHOOK_URL,
                NVIDIA_API_KEY,
                ETHERSCAN_API_KEY,
            )

            keys = {}

            if CENSYS_API_ID:
                keys["Censys"] = "CENSYS_API_ID"
            if GITHUB_TOKEN:
                keys["GitHub"] = "GITHUB_TOKEN"
            if GROQ_API_KEY:
                keys["Groq"] = "GROQ_API_KEY"
            if DISCORD_WEBHOOK_URL:
                keys["Discord"] = "DISCORD_WEBHOOK_URL"
            if NVIDIA_API_KEY:
                keys["NVIDIA"] = "NVIDIA_API_KEY"
            if ETHERSCAN_API_KEY:
                keys["Etherscan"] = "ETHERSCAN_API_KEY"

            return keys
        except Exception as e:
            logger.error(f"Error getting configured keys: {e}")
            return {}

    async def verify_all(self) -> Dict[str, Dict]:
        """Verify all configured API keys."""
        results = {}

        for provider, env_var in self.keys.items():
            result = await self._verify_key(provider, env_var)
            results[provider] = result

        return results

    async def _verify_key(self, provider: str, env_var: str) -> Dict[str, Any]:
        """Verify a single API key."""
        try:
            # Check if key is loaded
            from config.settings import __dict__ as settings_dict
            import os

            key_value = os.getenv(env_var)
            is_loaded = bool(key_value)

            result = {
                "loaded": is_loaded,
                "valid": False,
                "invalid": False,
                "rate_limited": False,
                "expired": False,
                "permission_denied": False,
            }

            if not is_loaded:
                result["invalid"] = True
                return result

            # Try to verify using existing verifier modules
            try:
                if provider == "GitHub":
                    from verification.verifiers.api_verifier import APIVerifier

                    verifier = APIVerifier()
                    is_valid = await asyncio.to_thread(
                        verifier.verify_github, key_value
                    )
                    result["valid"] = is_valid

                elif provider == "Groq":
                    from utils.llm.groq_provider import GroqProvider

                    provider_obj = GroqProvider()
                    # Try to use the provider
                    result["valid"] = True  # If it initializes, assume valid

                elif provider == "Etherscan":
                    from verification.crypto_intelligence import CryptoIntelligence

                    intel = CryptoIntelligence()
                    result["valid"] = True  # If it initializes, assume valid

                else:
                    # For other providers, just check if loaded
                    result["valid"] = is_loaded

            except Exception as e:
                if "rate" in str(e).lower():
                    result["rate_limited"] = True
                elif "permission" in str(e).lower():
                    result["permission_denied"] = True
                elif "expired" in str(e).lower():
                    result["expired"] = True
                else:
                    result["invalid"] = True

            return result
        except Exception as e:
            logger.error(f"Error verifying key for {provider}: {e}")
            return {
                "loaded": False,
                "valid": False,
                "invalid": True,
                "rate_limited": False,
                "expired": False,
                "permission_denied": False,
            }
