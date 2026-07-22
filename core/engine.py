"""
Main engine for APIS.
Orchestrates scanning, parsing, validation, notification, and self-improvement.
"""
import logging
import time
import json
import threading
from typing import List, Dict, Optional
from datetime import datetime
from dataclasses import dataclass, field

from config.settings import SCAN_INTERVAL, DEBUG
from core.scanner_manager import ScannerManager
from utils.groq_parser import GroqParser
from utils.key_validator import KeyValidator
from utils.discord_notifier import DiscordNotifier
from scanners.censys_scanner import CensysScanner
from scanners.github_scanner import GitHubScanner
from scanners.port_scanner import PortScanner, ServiceScanner

logger = logging.getLogger(__name__)


@dataclass
class EngineState:
    """Tracks the current state of the APIS engine."""
    running: bool = False
    cycle: int = 0
    last_scan_time: Optional[str] = None
    last_scan_duration: float = 0.0
    total_keys_found: int = 0
    total_scans: int = 0
    last_error: Optional[str] = None
    discovered_key_types: List[str] = field(default_factory=list)


class ApisEngine:
    """
    Main APIS engine that orchestrates all components.

    The engine runs in a loop:
    1. Scan (all scanners in parallel)
    2. Parse (extract keys using Groq AI + regex fallback)
    3. Validate (check key patterns and rules)
    4. Notify (send report to Discord)
    5. Self-improve (learn from results, generate improvements)
    """

    def __init__(self, scan_interval: int = SCAN_INTERVAL):
        self.scan_interval = scan_interval
        self.state = EngineState()

        # Initialize components
        self.scanner_manager = ScannerManager()
        self.parser = GroqParser()
        self.validator = KeyValidator()
        self.notifier = DiscordNotifier()

        # Initialize self-improvement engine (lazy import to avoid circular deps)
        self._improver = None

        # Initialize scanners
        self._init_scanners()

        # Data storage
        self._all_keys: List[Dict] = []
        self._lock = threading.Lock()

    def _init_scanners(self) -> None:
        """Initialize and register all scanners."""
        # Censys scanner (enabled if credentials configured)
        censys = CensysScanner()
        censys.enabled = bool(censys.api_id and censys.api_secret)
        self.scanner_manager.add_scanner(censys)

        # GitHub scanner (enabled if token configured)
        github = GitHubScanner()
        github.enabled = bool(github.token)
        self.scanner_manager.add_scanner(github)

        # Port scanner (always enabled for local scanning)
        port = PortScanner()
        self.scanner_manager.add_scanner(port)

        # Service scanner
        service = ServiceScanner()
        self.scanner_manager.add_scanner(service)

    @property
    def improver(self):
        """Lazy-load the self-improvement engine."""
        if self._improver is None:
            from self_improve.code_generator import SelfImprovementEngine
            self._improver = SelfImprovementEngine(self)
        return self._improver

    def run(self) -> None:
        """Main engine loop. Runs until stopped."""
        self.state.running = True
        self.notifier.send_info("🚀 APIS engine started")

        while self.state.running:
            try:
                self._run_cycle()
            except Exception as e:
                logger.error(f"Engine cycle error: {e}")
                self.state.last_error = str(e)
                self.notifier.send_error(str(e), "main loop")

            if self.state.running:
                time.sleep(self.scan_interval)

    def _run_cycle(self) -> None:
        """Execute a single scan cycle."""
        cycle_start = time.time()
        self.state.cycle += 1
        self.state.total_scans += 1

        logger.info(f"Starting scan cycle #{self.state.cycle}")

        # Step 1: Scan
        results = self.scanner_manager.scan_all()
        all_raw_data = self.scanner_manager.get_all_raw_data(results)

        # Step 2: Parse (extract keys)
        keys = self.parser.extract(all_raw_data)

        # Step 3: Validate
        valid_keys, invalid_keys = self.validator.validate_batch(keys)

        # Deduplicate
        unique_keys = self._deduplicate_keys(valid_keys)

        # Update state
        with self._lock:
            self._all_keys.extend(unique_keys)
            self.state.total_keys_found += len(unique_keys)
            self.state.last_scan_time = datetime.utcnow().isoformat()

        # Track new key types
        new_types = self._track_new_key_types(unique_keys)
        for key_type in new_types:
            if key_type not in self.state.discovered_key_types:
                self.state.discovered_key_types.append(key_type)
                self.notifier.send_new_key_type(
                    key_type,
                    unique_keys[0].get("masked_value", ""),
                    confidence=0.8,
                )

        # Step 4: Notify
        cycle_duration = time.time() - cycle_start
        self.state.last_scan_duration = cycle_duration
        self.notifier.send_status(
            cycle=self.state.cycle,
            duration=cycle_duration,
            keys_found=len(unique_keys),
        )
        self.notifier.send_key_report(unique_keys)

        # Step 5: Self-improvement
        try:
            self.improver.learn_from_results(unique_keys, results)
            self.improver.check_for_improvements()
        except Exception as e:
            logger.error(f"Self-improvement error: {e}")

        # Save data
        self._save_data()

        logger.info(
            f"Cycle #{self.state.cycle} completed in {cycle_duration:.1f}s. "
            f"Found {len(unique_keys)} valid keys."
        )

    def _deduplicate_keys(self, keys: List[Dict]) -> List[Dict]:
        """Remove duplicate keys by value."""
        seen = set()
        unique = []
        for key in keys:
            value = key.get("value", "")
            if value not in seen:
                seen.add(value)
                unique.append(key)
        return unique

    def _track_new_key_types(self, keys: List[Dict]) -> List[str]:
        """Identify new key types in the results."""
        new_types = []
        for key in keys:
            key_type = key.get("type", "generic")
            if key_type not in self.state.discovered_key_types:
                new_types.append(key_type)
        return list(set(new_types))

    def _save_data(self) -> None:
        """Save current state to data files."""
        try:
            from config.settings import KEYS_HISTORY_FILE, METRICS_FILE
            import json

            # Save keys history
            with open(KEYS_HISTORY_FILE, "w") as f:
                json.dump(self._all_keys[-1000:], f, indent=2, default=str)

            # Save metrics
            metrics = {
                "cycle": self.state.cycle,
                "total_keys_found": self.state.total_keys_found,
                "total_scans": self.state.total_scans,
                "last_scan_time": self.state.last_scan_time,
                "last_scan_duration": self.state.last_scan_duration,
                "discovered_key_types": self.state.discovered_key_types,
                "scanner_stats": self.scanner_manager.get_scanner_stats(),
            }
            with open(METRICS_FILE, "w") as f:
                json.dump(metrics, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save data: {e}")

    def stop(self) -> None:
        """Stop the engine."""
        self.state.running = False
        self.notifier.send_info("🛑 APIS engine stopped")

    def force_scan(self) -> Dict:
        """Force an immediate scan cycle (for API endpoint)."""
        self._run_cycle()
        return {
            "cycle": self.state.cycle,
            "keys_found": len(self._all_keys),
            "last_scan_time": self.state.last_scan_time,
        }

    def get_status(self) -> Dict:
        """Get current engine status."""
        return {
            "running": self.state.running,
            "cycle": self.state.cycle,
            "total_keys_found": self.state.total_keys_found,
            "total_scans": self.state.total_scans,
            "last_scan_time": self.state.last_scan_time,
            "last_scan_duration": self.state.last_scan_duration,
            "last_error": self.state.last_error,
            "discovered_key_types": self.state.discovered_key_types,
            "scan_interval": self.scan_interval,
            "enabled_scanners": self.scanner_manager.get_enabled_scanners(),
        }

    def get_keys(self) -> List[Dict]:
        """Get all discovered keys (masked)."""
        return self._all_keys

    def get_results(self) -> List[Dict]:
        """Get recent scan results summary."""
        return [
            {
                "cycle": self.state.cycle,
                "keys_found": len(self._all_keys),
                "timestamp": self.state.last_scan_time,
            }
        ]
