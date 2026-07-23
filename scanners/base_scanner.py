"""
Base scanner module for AlphaScan v0.5.
Defines the abstract interface that all scanners must implement.
"""
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class ScanResult:
    """Represents the result of a scan operation."""
    scanner_name: str
    source: str
    raw_data: List[str]
    metadata: Dict = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class BaseScanner(ABC):
    """
    Abstract base class for all scanners.
    All scanners must implement the scan() method.
    """

    def __init__(self, name: str, enabled: bool = True):
        self.name = name
        self.enabled = enabled
        self._last_scan: Optional[datetime] = None
        self._scan_count: int = 0

    @abstractmethod
    def scan(self) -> ScanResult:
        """
        Perform a scan and return results.

        Returns:
            ScanResult containing discovered data.
        """
        pass

    def is_enabled(self) -> bool:
        """Check if this scanner is enabled."""
        return self.enabled

    def get_stats(self) -> Dict:
        """Return scanner statistics."""
        return {
            "name": self.name,
            "enabled": self.enabled,
            "scan_count": self._scan_count,
            "last_scan": self._last_scan.isoformat() if self._last_scan else None,
        }

    def _pre_scan(self) -> None:
        """Hook called before scanning."""
        self._last_scan = datetime.utcnow()
        self._scan_count += 1
        logger.debug(f"Scanner '{self.name}' starting scan #{self._scan_count}")

    def _post_scan(self, result: ScanResult) -> ScanResult:
        """Hook called after scanning."""
        logger.debug(
            f"Scanner '{self.name}' completed scan. "
            f"Found {len(result.raw_data)} items."
        )
        return result

    def safe_scan(self) -> Optional[ScanResult]:
        """
        Wrapper around scan() with error handling and retry logic.
        Implements 3-attempt retry as per requirements.
        """
        max_retries = 3
        for attempt in range(1, max_retries + 1):
            try:
                self._pre_scan()
                result = self.scan()
                return self._post_scan(result)
            except ImportError as e:
                # Optional dependency missing - disable scanner permanently
                logger.warning(
                    f"Scanner '{self.name}' disabled due to missing dependency: {e}"
                )
                self.enabled = False
                return None
            except Exception as e:
                logger.warning(
                    f"Scanner '{self.name}' attempt {attempt}/{max_retries} failed: {e}"
                )
                if attempt == max_retries:
                    logger.error(
                        f"Scanner '{self.name}' failed after {max_retries} attempts"
                    )
                    return None
        return None