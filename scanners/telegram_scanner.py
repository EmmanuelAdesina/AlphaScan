"""
Telegram Scanner for AlphaScan v0.5.

Scans public Telegram channels and groups for messages containing API keys,
secrets, and configuration files.
"""
import logging
from typing import List, Dict, Optional
from scanners.base_scanner import BaseScanner, ScanResult
from utils.http_client import get_http_client

logger = logging.getLogger(__name__)


class TelegramScanner(BaseScanner):
    """
    Scanner that searches public Telegram channels for secrets.

    Uses the Telegram Bot API to read messages from public channels
    and groups that may contain exposed API keys and secrets.
    """

    # Public channels known to contain developer content (may contain secrets)
    PUBLIC_CHANNELS = [
        "t.me/s/python",
        "t.me/s/dev",
        "t.me/s/programming",
        "t.me/s/coding",
        "t.me/s/webdev",
        "t.me/s/hacking",
        "t.me/s/security",
    ]

    # Search patterns for finding messages with secrets
    SEARCH_PATTERNS = [
        "api_key", "apikey", "secret_key", "access_token",
        "private_key", "BEGIN PRIVATE KEY", "BEGIN OPENSSH",
        "sk-live", "sk-test", "AKIA", "ghp_",
        "password", "passwd", "credentials",
    ]

    def __init__(self, bot_token: Optional[str] = None,
                 enabled: bool = True):
        super().__init__("telegram", enabled)
        self.bot_token = bot_token
        self._http = get_http_client()

    def scan(self) -> ScanResult:
        """
        Scan public Telegram channels for messages containing secrets.

        Returns:
            ScanResult with raw text data from messages.
        """
        raw_data: List[str] = []
        metadata: Dict = {
            "channels_scanned": 0,
            "messages_found": 0,
            "messages_with_secrets": 0,
        }

        # Try to use Telegram Bot API if available
        if self.bot_token:
            raw_data.extend(self._scan_with_bot_api())
        else:
            # Fall back to scraping public channels
            raw_data.extend(self._scan_public_channels())

        metadata["messages_found"] = len(raw_data)
        metadata["channels_scanned"] = len(self.PUBLIC_CHANNELS)

        return ScanResult(
            scanner_name=self.name,
            source="telegram",
            raw_data=raw_data,
            metadata=metadata,
        )

    def _scan_with_bot_api(self) -> List[str]:
        """Scan using the Telegram Bot API."""
        results = []
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/getUpdates"
            response = self._http.get(url, timeout=10)
            if response and response.status_code == 200:
                data = response.json()
                for update in data.get("result", []):
                    message = update.get("message", {})
                    text = message.get("text", "")
                    if text and self._contains_secret_patterns(text):
                        results.append(text)
        except Exception as e:
            logger.error(f"Telegram Bot API scan failed: {e}")

        return results

    def _scan_public_channels(self) -> List[str]:
        """Scan public Telegram channels by scraping their web versions."""
        results = []
        for channel_url in self.PUBLIC_CHANNELS:
            try:
                response = self._http.get(channel_url, timeout=10)
                if response and response.status_code == 200:
                    messages = self._extract_messages(response.text)
                    for msg in messages:
                        if self._contains_secret_patterns(msg):
                            results.append(msg)
            except Exception as e:
                logger.debug(f"Failed to scan channel {channel_url}: {e}")
                continue

        return results

    def _extract_messages(self, html: str) -> List[str]:
        """Extract message text from a Telegram channel HTML page."""
        messages = []
        try:
            from html.parser import HTMLParser

            class MessageExtractor(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self.messages = []
                    self.current_text = []
                    self.in_message = False

                def handle_starttag(self, tag, attrs):
                    attrs_dict = dict(attrs)
                    if tag == "div" and "tg" in attrs_dict.get("class", ""):
                        self.in_message = True
                        self.current_text = []

                def handle_endtag(self, tag):
                    if tag == "div" and self.in_message:
                        text = " ".join(self.current_text).strip()
                        if text:
                            self.messages.append(text)
                        self.in_message = False
                        self.current_text = []

                def handle_data(self, data):
                    if self.in_message:
                        self.current_text.append(data)

            extractor = MessageExtractor()
            extractor.feed(html)
            messages = extractor.messages
        except Exception:
            pass

        return messages

    def _contains_secret_patterns(self, text: str) -> bool:
        """Check if text contains any secret patterns."""
        text_lower = text.lower()
        for pattern in self.SEARCH_PATTERNS:
            if pattern.lower() in text_lower:
                return True
        return False