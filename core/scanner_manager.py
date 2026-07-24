"""
Scanner manager for AlphaScan v0.5.
Manages all scanners, runs them in parallel, and collects results.
"""
import logging
import time
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from scanners.base_scanner import BaseScanner, ScanResult

logger = logging.getLogger(__name__)


class ScannerManager:
    """
    Manages all scanner instances, runs them in parallel,
    and collects their results.

    Features:
    - Auto-recovery: if a scanner crashes, it is disabled and
      re-enabled on the next cycle after a cooldown period.
    """

    def __init__(self, scanners: Optional[List[BaseScanner]] = None):
        self.scanners: List[BaseScanner] = scanners or []
        self._results: List[ScanResult] = []
        self._failed_scanners: Dict[str, float] = {}  # name -> last_failure_time
        self._cooldown_seconds = 300  # 5 minutes

    def add_scanner(self, scanner: BaseScanner) -> None:
        """Add a scanner to the manager."""
        self.scanners.append(scanner)
        logger.info(f"Added scanner: {scanner.name}")

    def remove_scanner(self, name: str) -> bool:
        """Remove a scanner by name."""
        for scanner in self.scanners:
            if scanner.name == name:
                self.scanners.remove(scanner)
                logger.info(f"Removed scanner: {name}")
                return True
        return False

    def get_scanner(self, name: str) -> Optional[BaseScanner]:
        """Get a scanner by name."""
        for scanner in self.scanners:
            if scanner.name == name:
                return scanner
        return None

    def enable_scanner(self, name: str) -> bool:
        """Enable a scanner by name."""
        scanner = self.get_scanner(name)
        if scanner is None:
            return False
        scanner.enabled = True
        if name in self._failed_scanners:
            del self._failed_scanners[name]
        logger.info(f"Enabled scanner: {name}")
        return True

    def disable_scanner(self, name: str) -> bool:
        """Disable a scanner by name."""
        scanner = self.get_scanner(name)
        if scanner is None:
            return False
        scanner.enabled = False
        logger.info(f"Disabled scanner: {name}")
        return True

    def scan_all(self, parallel: bool = True) -> List[ScanResult]:
        """
        Run all enabled scanners and collect results.

        Args:
            parallel: If True, run scanners in parallel using thread pool.

        Returns:
            List of ScanResult objects from all scanners.
        """
        # Refresh scanner availability (re-enable after cooldown)
        self._refresh_scanner_availability()

        enabled_scanners = [s for s in self.scanners if s.is_enabled()]
        if not enabled_scanners:
            logger.warning("No enabled scanners found")
            return []

        results: List[ScanResult] = []

        if parallel and len(enabled_scanners) > 1:
            results = self._scan_parallel(enabled_scanners)
        else:
            results = self._scan_sequential(enabled_scanners)

        self._results = results
        return results

    def _scan_parallel(self, scanners: List[BaseScanner]) -> List[ScanResult]:
        """Run scanners in parallel using ThreadPoolExecutor."""
        results: List[ScanResult] = []

        with ThreadPoolExecutor(max_workers=len(scanners)) as executor:
            future_to_scanner = {
                executor.submit(scanner.safe_scan): scanner
                for scanner in scanners
            }

            for future in as_completed(future_to_scanner):
                scanner = future_to_scanner[future]
                try:
                    result = future.result(timeout=120)
                    if result:
                        results.append(result)
                        logger.info(f"Scanner '{scanner.name}' completed successfully")
                    else:
                        logger.warning(f"Scanner '{scanner.name}' returned no results")
                        self._on_scanner_failure(scanner.name)
                except Exception as e:
                    logger.error(f"Scanner '{scanner.name}' failed: {e}")
                    self._on_scanner_failure(scanner.name)

        return results

    def _scan_sequential(self, scanners: List[BaseScanner]) -> List[ScanResult]:
        """Run scanners sequentially."""
        results: List[ScanResult] = []
        for scanner in scanners:
            try:
                result = scanner.safe_scan()
                if result:
                    results.append(result)
                    logger.info(f"Scanner '{scanner.name}' completed successfully")
                else:
                    logger.warning(f"Scanner '{scanner.name}' returned no results")
                    self._on_scanner_failure(scanner.name)
            except Exception as e:
                logger.error(f"Scanner '{scanner.name}' failed: {e}")
                self._on_scanner_failure(scanner.name)
        return results

    def _on_scanner_failure(self, scanner_name: str) -> None:
        """Handle scanner failure by disabling it temporarily."""
        self._failed_scanners[scanner_name] = time.time()
        scanner = self.get_scanner(scanner_name)
        if scanner:
            scanner.enabled = False
            logger.warning(
                f"Scanner '{scanner_name}' disabled due to repeated failures. "
                f"Will retry after {self._cooldown_seconds}s cooldown."
            )

    def _refresh_scanner_availability(self) -> None:
        """Re-enable scanners after cooldown period."""
        current_time = time.time()
        for scanner in self.scanners:
            if not scanner.is_enabled() and scanner.name in self._failed_scanners:
                last_failure = self._failed_scanners[scanner.name]
                if current_time - last_failure >= self._cooldown_seconds:
                    scanner.enabled = True
                    logger.info(f"Scanner '{scanner.name}' re-enabled after cooldown")
                    del self._failed_scanners[scanner.name]

    def get_all_raw_data(self, results: Optional[List[ScanResult]] = None) -> List[str]:
        """
        Extract all raw data from scan results.

        Args:
            results: Optional list of results to extract from.
                     Uses last scan results if not provided.

        Returns:
            List of raw text strings from all scanners.
        """
        if results is None:
            results = self._results

        all_data: List[str] = []
        for result in results:
            all_data.extend(result.raw_data)
        return all_data

    def get_scanner_stats(self) -> List[Dict]:
        """Get statistics for all scanners."""
        return [scanner.get_stats() for scanner in self.scanners]

    def get_enabled_scanners(self) -> List[str]:
        """Get list of enabled scanner names."""
        return [s.name for s in self.scanners if s.is_enabled()]

    def get_failed_scanners(self) -> List[str]:
        """Get list of currently failed scanner names."""
        return list(self._failed_scanners.keys())