"""
Scanner manager for APIS.
Manages all scanners, runs them in parallel, and collects results.
"""
import logging
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from scanners.base_scanner import BaseScanner, ScanResult

logger = logging.getLogger(__name__)


class ScannerManager:
    """
    Manages all scanner instances, runs them in parallel,
    and collects their results.
    """

    def __init__(self, scanners: Optional[List[BaseScanner]] = None):
        self.scanners: List[BaseScanner] = scanners or []
        self._results: List[ScanResult] = []

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

    def scan_all(self, parallel: bool = True) -> List[ScanResult]:
        """
        Run all enabled scanners and collect results.

        Args:
            parallel: If True, run scanners in parallel using thread pool.

        Returns:
            List of ScanResult objects from all scanners.
        """
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
                except Exception as e:
                    logger.error(
                        f"Scanner '{scanner.name}' failed: {e}"
                    )

        return results

    def _scan_sequential(self, scanners: List[BaseScanner]) -> List[ScanResult]:
        """Run scanners sequentially."""
        results: List[ScanResult] = []
        for scanner in scanners:
            result = scanner.safe_scan()
            if result:
                results.append(result)
        return results

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
