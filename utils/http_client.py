"""
Centralized HTTP client for AlphaScan.

Every network request in the application should go through this client.
Features:
- Automatic retries with exponential backoff
- Configurable timeouts
- DNS failure handling (never crashes the application)
- Structured logging
- Optional proxy support
"""
import logging
import time
import socket
from typing import Optional, Dict, Any, Union
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class HTTPClient:
    """
    A centralized, resilient HTTP client.

    All scanners and utilities should use this instead of raw ``requests``
    calls so that timeouts, retries, and DNS failures are handled
    consistently across the entire application.
    """

    def __init__(
        self,
        timeout: float = 10.0,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
        user_agent: str = "AlphaScan-v0.5-SecretScanner/1.0",
    ):
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.user_agent = user_agent

        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": user_agent,
            "Accept": "application/json, text/html, */*",
        })

        # Configure retry strategy on the session adapter
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "POST", "PUT", "DELETE", "OPTIONS", "TRACE"],
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self._session.mount("http://", adapter)
        self._session.mount("https://", adapter)

    def get(
        self,
        url: str,
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        timeout: Optional[float] = None,
        **kwargs,
    ) -> Optional[requests.Response]:
        """Perform a GET request with full error handling."""
        return self._request("GET", url, params=params, headers=headers, timeout=timeout, **kwargs)

    def post(
        self,
        url: str,
        json: Optional[Dict] = None,
        data: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        timeout: Optional[float] = None,
        **kwargs,
    ) -> Optional[requests.Response]:
        """Perform a POST request with full error handling."""
        return self._request(
            "POST", url, json=json, data=data, headers=headers, timeout=timeout, **kwargs
        )

    def _request(
        self,
        method: str,
        url: str,
        **kwargs,
    ) -> Optional[requests.Response]:
        """
        Execute an HTTP request with retry, backoff, and DNS failure handling.

        Returns ``None`` if the request ultimately fails (after all retries),
        rather than raising an exception.  This ensures that network failures
        never crash the application.
        """
        effective_timeout = kwargs.pop("timeout", None) or self.timeout
        headers = kwargs.pop("headers", None) or {}

        for attempt in range(1, self.max_retries + 1):
            try:
                logger.debug(
                    f"HTTP {method} {url} (attempt {attempt}/{self.max_retries})"
                )
                response = self._session.request(
                    method=method,
                    url=url,
                    timeout=effective_timeout,
                    headers=headers,
                    **kwargs,
                )
                return response
            except requests.exceptions.ConnectionError as e:
                # This covers DNS resolution failures, connection refused, etc.
                if attempt < self.max_retries:
                    wait = self.backoff_factor * (2 ** (attempt - 1))
                    logger.warning(
                        f"HTTP {method} {url} connection error (attempt {attempt}/"
                        f"{self.max_retries}): {e}. Retrying in {wait:.1f}s..."
                    )
                    time.sleep(wait)
                else:
                    logger.error(
                        f"HTTP {method} {url} failed after {self.max_retries} attempts "
                        f"(connection error): {e}"
                    )
                    return None
            except requests.exceptions.Timeout as e:
                if attempt < self.max_retries:
                    wait = self.backoff_factor * (2 ** (attempt - 1))
                    logger.warning(
                        f"HTTP {method} {url} timeout (attempt {attempt}/"
                        f"{self.max_retries}): {e}. Retrying in {wait:.1f}s..."
                    )
                    time.sleep(wait)
                else:
                    logger.error(
                        f"HTTP {method} {url} timed out after {self.max_retries} attempts"
                    )
                    return None
            except requests.exceptions.RequestException as e:
                logger.error(
                    f"HTTP {method} {url} request error: {e}"
                )
                return None
            except socket.gaierror as e:
                # DNS resolution failure
                logger.error(f"HTTP {method} {url} DNS resolution failed: {e}")
                return None
            except Exception as e:
                logger.error(
                    f"HTTP {method} {url} unexpected error: {e}"
                )
                return None

        return None

    def close(self) -> None:
        """Close the underlying session."""
        self._session.close()

    def update_headers(self, headers: Dict[str, str]) -> None:
        """Update session-level headers."""
        self._session.headers.update(headers)


# ── Module-level singleton ────────────────────────────────────────────────────

_default_client: Optional[HTTPClient] = None


def get_http_client() -> HTTPClient:
    """Get or create the default HTTP client singleton."""
    global _default_client
    if _default_client is None:
        _default_client = HTTPClient()
    return _default_client


def reset_http_client() -> None:
    """Reset the default HTTP client (useful for testing)."""
    global _default_client
    if _default_client is not None:
        _default_client.close()
    _default_client = None
