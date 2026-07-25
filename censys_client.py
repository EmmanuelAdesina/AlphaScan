"""
AlphaScan Censys Platform API Client.
Uses Personal Access Token (PAT) authentication.
No legacy API ID/Secret. No basic auth.

Censys Platform API v3 docs:
_BASE_URL = "https://api.platform.censys.io/v3"
# Alternative search endpoint path (try /v3/search if /v3/global/search returns 404)
_SEARCH_PATH = "/global/search"
"""
import logging
import time
from typing import Any, Dict, List, Optional

import requests

try:
    from .config import CENSYS_PAT
except ImportError:
    from config import CENSYS_PAT

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.platform.censys.io/v3"
_MAX_RETRIES = 3
_RETRY_DELAY_SEC = 2.0  # doubles each retry


class CensysClient:
    """
    Reusable Censys Platform API client.

    Usage:
        client = CensysClient()
        results = client.search_hosts("api_key", per_page=10)
    """

    def __init__(self, pat: Optional[str] = None) -> None:
        self.pat = pat or CENSYS_PAT
        self._session = requests.Session()
        self._session.headers.update({
            "Authorization": f"Bearer {self.pat}",
            "Accept": "application/json",
            "User-Agent": "AlphaScan/1.0",
        })

    # ── Public helpers ──────────────────────────────────────────────

    def search_hosts(self, query: str, per_page: int = 25, cursor: Optional[str] = None ) -> Dict[str, Any]:
        """
        Search Censys Platform API v3 for hosts.

        Example queries:
            services.http.response.headers.server: nginx
            location.country_code: US
            services.service_name: SSH
            autonomous_system.name: Google

        Returns:
            {
                "hits": [...],
                "cursor": "..."
            }
        """

        url = f"{_BASE_URL}{_SEARCH_PATH}"

        params = {
            "query": query,
            "per_page": per_page,
        }

        # Fallback to /search if /global/search returns 404
        try:
            response = self._request(
                "GET",
                url,
                params=params,
            )
            result = response.get("result", {})
            return {
                "hits": result.get("hits", []),
                "cursor": result.get("cursor"),
            }
        except CensysNotFound:
            if _SEARCH_PATH == "/global/search":
                return self.search_hosts_fallback(query, per_page, cursor)
        return {"hits": [], "cursor": None}

        if cursor:
            params["cursor"] = cursor

        response = self._request(
            "GET",
            url,
            params=params
        )

        result = response.get("result", {})

        return {
            "hits": result.get("hits", []),
            "cursor": result.get("cursor")
        }

    def search_hosts_fallback(self, query: str, per_page: int = 25, cursor: Optional[str] = None) -> Dict[str, Any]:
        """Fallback search using /v3/search if /v3/global/search 404s."""
        url = f"{_BASE_URL}/search"
        params: Dict[str, Any] = {"query": query, "per_page": per_page}
        if cursor:
            params["cursor"] = cursor
        response = self._request("GET", url, params=params)
        result = response.get("result", {})
        return {"hits": result.get("hits", []), "cursor": result.get("cursor")}

    def get_host(self, ip: str) -> Optional[Dict]:
        """
        Retrieve a single host asset by IP.
        """

        url = f"{_BASE_URL}/global/asset/host/{ip}"

        try:
            response = self._request(
                "GET",
                url
            )

            return response.get(
                "result",
                response
            )

        except CensysNotFound:
            return None

    def verify_auth(self) -> bool:
        """
        Lightweight authentication check.
        Returns True if the PAT is valid, False otherwise.
        Does not raise on failure.
        """
        try:
            # Censys v3 doesn't have a dedicated /me endpoint as v2 did,
            # so we use a minimal hosts search as the health-check.
            self.get_host("8.8.8.8")
            return True
        except CensysAuthError:
            return False
        except CensysError:
            # Non-auth failures during a health-check are also considered
            # "working" from an auth perspective.
            return True

    # ── Internal request logic ──────────────────────────────────────

    def _request(self, method: str, url: str, **kwargs: Any) -> Dict:
        """
        Perform an authenticated request with retry & error handling.
        Raises CensysError subclasses on failure.
        """
        last_exc: Optional[Exception] = None
        delay = _RETRY_DELAY_SEC

        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                resp = self._session.request(method, url, timeout=15, **kwargs)

                if resp.status_code == 401:
                    raise CensysAuthError(
                        "Invalid or expired Personal Access Token (PAT). "
                        "Generate a new one at https://console.censys.io/api"
                    )
                if resp.status_code == 403:
                    raise CensysPermissionError(
                        f"Permission denied. Your PAT may lack the required scopes. "
                        f"Body: {resp.text[:200]}"
                    )
                if resp.status_code == 404:
                    raise CensysNotFound(f"Resource not found: {url}")
                if resp.status_code == 429:
                    retry_after = resp.headers.get("Retry-After", str(delay))
                    logger.warning(
                        f"Censys rate limited. Retrying after {retry_after}s "
                        f"(attempt {attempt}/{_MAX_RETRIES})"
                    )
                    time.sleep(float(retry_after))
                    continue
                if 500 <= resp.status_code < 600:
                    logger.warning(
                        f"Censys server error {resp.status_code}. "
                        f"Retrying in {delay}s (attempt {attempt}/{_MAX_RETRIES})"
                    )
                    time.sleep(delay)
                    delay *= 2.0
                    continue

                # Success (2xx)
                resp.raise_for_status()
                return resp.json()

            except (CensysAuthError, CensysPermissionError, CensysNotFound):
                # Non-retryable errors — re-raise immediately
                raise
            except requests.RequestException as e:
                last_exc = e
                logger.debug(
                    f"Censys request failed (attempt {attempt}/{_MAX_RETRIES}): {e}"
                )
                if attempt < _MAX_RETRIES:
                    time.sleep(delay)
                    delay *= 2.0

        # If we exhausted retries
        raise CensysError(
            f"Censys request failed after {_MAX_RETRIES} retries"
        ) from last_exc


# ── Custom Exceptions ──────────────────────────────────────────────


class CensysError(Exception):
    """Base Censys API error."""


class CensysAuthError(CensysError):
    """401 — Invalid or expired PAT."""


class CensysPermissionError(CensysError):
    """403 — PAT lacks required scopes."""


class CensysNotFound(CensysError):
    """404 — Resource does not exist."""

