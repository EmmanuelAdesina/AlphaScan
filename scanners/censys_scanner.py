"""
Censys scanner for APIS.
Uses the Censys API (free tier) to scan for exposed services and API endpoints.
"""
import logging
from typing import List, Dict, Optional
from scanners.base_scanner import BaseScanner, ScanResult
from config.settings import CENSYS_API_ID, CENSYS_API_SECRET, CENSYS_QUERY

logger = logging.getLogger(__name__)


class CensysScanner(BaseScanner):
    """
    Scanner that uses Censys API to find exposed services with potential
    API keys, secrets, and configuration files.
    """

    def __init__(self, api_id: Optional[str] = None,
                 api_secret: Optional[str] = None,
                 query: Optional[str] = None,
                 enabled: bool = True):
        super().__init__("censys", enabled)
        self.api_id = api_id or CENSYS_API_ID
        self.api_secret = api_secret or CENSYS_API_SECRET
        self.query = query or CENSYS_QUERY
        self._client = None

    def _get_client(self):
        """Lazily initialize the Censys client."""
        if self._client is None:
            if not self.api_id or not self.api_secret:
                raise ValueError("Censys API credentials not configured")
            from censys.search import CensysHosts
            self._client = CensysHosts(
                api_id=self.api_id,
                api_secret=self.api_secret,
            )
        return self._client

    def scan(self) -> ScanResult:
        """
        Scan Censys for exposed services matching the configured query.
        Returns raw text data from search results.
        """
        client = self._get_client()
        raw_data: List[str] = []
        metadata: Dict = {"query": self.query, "sources_found": 0}

        # Search for hosts with exposed API keys
        search_results = client.search(self.query)

        for page in search_results:
            for hit in page.get("results", []):
                # Extract relevant fields from Censys results
                services = hit.get("services", [])
                for service in services:
                    # Check for exposed configuration
                    if "http" in service:
                        http_data = service.get("http", {})
                        # Look for API keys in HTTP responses
                        response_text = http_data.get("response", {}).get("body", "")
                        if response_text:
                            raw_data.append(response_text)

                    # Check for exposed services on common ports
                    port = service.get("port", 0)
                    if port in (11434, 7860, 8000, 8080, 5000, 3000):
                        # These ports often have exposed APIs
                        raw_data.append(
                            f"Exposed service on port {port}: "
                            f"{service.get('service_name', 'unknown')}"
                        )

                metadata["sources_found"] += 1

        return ScanResult(
            scanner_name=self.name,
            source="censys",
            raw_data=raw_data,
            metadata=metadata,
        )


class CensysCertScanner(BaseScanner):
    """Scanner that searches Censys certificates for API keys in certificate metadata."""

    def __init__(self, api_id: Optional[str] = None,
                 api_secret: Optional[str] = None,
                 enabled: bool = True):
        super().__init__("censys_certs", enabled)
        self.api_id = api_id or CENSYS_API_ID
        self.api_secret = api_secret or CENSYS_API_SECRET
        self._client = None

    def _get_client(self):
        if self._client is None:
            if not self.api_id or not self.api_secret:
                raise ValueError("Censys API credentials not configured")
            from censys.search import CensysCerts
            self._client = CensysCerts(
                api_id=self.api_id,
                api_secret=self.api_secret,
            )
        return self._client

    def scan(self) -> ScanResult:
        """Search certificates for API keys in SAN fields and metadata."""
        client = self._get_client()
        raw_data: List[str] = []
        metadata: Dict = {"certificates_found": 0}

        # Search for certificates with API-related names
        search_results = client.search("api_key OR secret_key OR access_token")

        for page in search_results:
            for hit in page.get("results", []):
                # Extract names and descriptions from certificates
                names = hit.get("names", [])
                raw_data.extend(names)
                metadata["certificates_found"] += 1

        return ScanResult(
            scanner_name=self.name,
            source="censys_certs",
            raw_data=raw_data,
            metadata=metadata,
        )
