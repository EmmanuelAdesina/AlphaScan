"""
Pastebin Scanner for AlphaScan v0.5.

Scans Pastebin for public pastes containing API keys, secrets, and configuration files.
Uses the Pastebin API (if available) or scrapes public pastes.
"""
import logging
from typing import List, Dict, Optional
from scanners.base_scanner import BaseScanner, ScanResult
from utils.http_client import get_http_client

logger = logging.getLogger(__name__)


class PastebinScanner(BaseScanner):
    """
    Scanner that searches Pastebin for public pastes containing secrets.

    Uses the Pastebin API to search for pastes matching configured patterns.
    Falls back to scraping public pastes if API is not available.
    """

    # Search patterns for finding pastes with secrets
    SEARCH_PATTERNS = [
        "api_key", "apikey", "secret_key", "access_token",
        "private_key", "BEGIN PRIVATE KEY", "BEGIN OPENSSH",
        "sk-live", "sk-test", "AKIA", "ghp_",
        "password", "passwd", "credentials",
    ]

    # Pastebin API endpoint
    PASTEBIN_API_URL = "https://pastebin.com/api/v1"

    def __init__(self, api_key: Optional[str] = None,
                 enabled: bool = True):
        super().__init__("pastebin", enabled)
        self.api_key = api_key
        self._http = get_http_client()

    def scan(self) -> ScanResult:
        """
        Scan Pastebin for public pastes containing secrets.

        Returns:
            ScanResult with raw text data from pastes.
        """
        raw_data: List[str] = []
        metadata: Dict = {"pastes_found": 0, "patterns_searched": len(self.SEARCH_PATTERNS)}

        # Try to use Pastebin API if available
        if self.api_key:
            raw_data.extend(self._scan_with_api())
        else:
            # Fall back to scraping public pastes
            raw_data.extend(self._scan_public_pastes())

        metadata["pastes_found"] = len(raw_data)

        return ScanResult(
            scanner_name=self.name,
            source="pastebin",
            raw_data=raw_data,
            metadata=metadata,
        )

    def _scan_with_api(self) -> List[str]:
        """Scan using the Pastebin API."""
        results = []
        try:
            # Search for pastes matching our patterns
            for pattern in self.SEARCH_PATTERNS[:5]:  # Limit to first 5 patterns
                url = f"{self.PASTEBIN_API_URL}/pastes/search"
                params = {
                    "api_key": self.api_key,
                    "q": pattern,
                    "limit": 10,
                }
                try:
                    response = self._http.get(url, params=params, timeout=10)
                    if response and response.status_code == 200:
                        data = response.json()
                        for paste in data.get("results", []):
                            paste_key = paste.get("key", "")
                            content = self._fetch_paste_content(paste_key)
                            if content:
                                results.append(content)
                except Exception as e:
                    logger.debug(f"Pastebin API search failed for '{pattern}': {e}")
                    continue
        except Exception as e:
            logger.error(f"Pastebin API scan failed: {e}")

        return results

    def _scan_public_pastes(self) -> List[str]:
        """Scan public pastes by scraping the Pastebin website."""
        results = []
        try:
            # Fetch the public pastes page
            url = "https://pastebin.com/"
            response = self._http.get(url, timeout=10)
            if not response or response.status_code != 200:
                logger.warning(f"Pastebin public page returned status {response.status_code if response else 'None'}")
                return results

            # Parse the HTML to find paste links
            from html.parser import HTMLParser

            class PasteLinkParser(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self.links = []

                def handle_starttag(self, tag, attrs):
                    if tag == "a":
                        href = dict(attrs).get("href", "")
                        if href and len(href) > 10 and not href.startswith("/api"):
                            if len(href) == 9 and "/" in href:
                                self.links.append(href)

            parser = PasteLinkParser()
            parser.feed(response.text)

            # Fetch content of each paste
            for link in parser.links[:10]:  # Limit to 10 pastes
                paste_url = f"https://pastebin.com{link}"
                try:
                    paste_response = self._http.get(paste_url, timeout=5)
                    if paste_response and paste_response.status_code == 200:
                        content = self._extract_paste_content(paste_response.text)
                        if content:
                            results.append(content)
                except Exception:
                    continue

        except Exception as e:
            logger.error(f"Pastebin public scan failed: {e}")

        return results

    def _fetch_paste_content(self, paste_key: str) -> Optional[str]:
        """Fetch the raw content of a paste by key."""
        try:
            url = f"https://pastebin.com/raw/{paste_key}"
            response = self._http.get(url, timeout=5)
            if response and response.status_code == 200:
                return response.text
        except Exception:
            pass
        return None

    def _extract_paste_content(self, html: str) -> Optional[str]:
        """Extract text content from a paste HTML page."""
        try:
            from html.parser import HTMLParser

            class TextExtractor(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self.text = []
                    self.in_textarea = False

                def handle_starttag(self, tag, attrs):
                    if tag == "textarea":
                        self.in_textarea = True

                def handle_endtag(self, tag):
                    if tag == "textarea":
                        self.in_textarea = False

                def handle_data(self, data):
                    if self.in_textarea:
                        self.text.append(data)

            extractor = TextExtractor()
            extractor.feed(html)
            return "\n".join(extractor.text) if extractor.text else None
        except Exception:
            return None