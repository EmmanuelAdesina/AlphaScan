"""
Main engine for AlphaScan v0.5.
Orchestrates scanning, verification, notification, self-improvement, and autonomy.
"""
import logging
import time
import json
import threading
import os
from typing import List, Dict, Optional
from datetime import datetime
from dataclasses import dataclass, field

from config.settings import (
    SCAN_INTERVAL, DEBUG, AUTONOMOUS_MODE, AUTO_PUSH_GITHUB,
    ALLOW_AUTO_RESTART, AUTO_PIVOT_THRESHOLD,
    ENABLE_SSH_DETECTION, ENABLE_CRYPTO_DETECTION, ENABLE_API_DETECTION,
    VERIFICATION_TIMEOUT,
)
from core.scanner_manager import ScannerManager
from utils.groq_parser import GroqParser
from utils.key_validator import KeyValidator
from utils.discord_notifier import DiscordNotifier
from verification.verifier import SecretVerifier
from verification.discord_reporter import DiscordReporter
from verification.key_rank import KeyRanker
from autonomous.env_manager import EnvManager
from autonomous.strategy_analyzer import StrategyAnalyzer
from autonomous.git_manager import GitManager
from autonomous.command_handler import CommandHandler
from autonomous.module_registry import ModuleRegistry
from autonomous.decision_logger import DecisionLogger
from scanners.censys_scanner import CensysScanner
from scanners.github_scanner import GitHubScanner
from scanners.port_scanner import PortScanner, ServiceScanner
from scanners.pastebin_scanner import PastebinScanner
from scanners.telegram_scanner import TelegramScanner

logger = logging.getLogger(__name__)


@dataclass
class EngineState:
    """Tracks the current state of the AlphaScan engine."""
    running: bool = False
    cycle: int = 0
    last_scan_time: Optional[str] = None
    last_scan_duration: float = 0.0
    total_keys_found: int = 0
    total_scans: int = 0
    last_error: Optional[str] = None
    discovered_key_types: List[str] = field(default_factory=list)
    uptime_start: Optional[str] = None
    autonomous_decisions: int = 0
    keys_by_rank: Dict = field(default_factory=dict)


class AlphaScanEngine:
    """
    Main AlphaScan v0.5 engine that orchestrates all components.

    The engine runs in a loop:
    1. Scan (all scanners in parallel)
    2. Detect & Classify (SSH, crypto, API keys)
    3. Verify (3-layer pipeline: format, entropy, context)
    4. Report (clean classified Discord reports)
    5. Self-improve (learn, generate, deploy)
    6. Autonomous decisions (pivot, deploy, manage environment)
    """

    def __init__(self, scan_interval: int = SCAN_INTERVAL):
        self.scan_interval = scan_interval
        self.state = EngineState()
        self.state.uptime_start = datetime.utcnow().isoformat()

        # Initialize components
        self.scanner_manager = ScannerManager()
        self.parser = GroqParser()
        self.validator = KeyValidator()
        self.notifier = DiscordNotifier()

        # v0.5: Verification system
        self.verifier = SecretVerifier()
        self.ranker = KeyRanker()
        self.reporter = DiscordReporter()

        # v0.5: Autonomous system
        self.env_manager = EnvManager(notifier=self.notifier)
        self.strategy_analyzer = StrategyAnalyzer(pivot_threshold=AUTO_PIVOT_THRESHOLD)
        self.git_manager = GitManager(auto_push=AUTO_PUSH_GITHUB)
        self.command_handler = CommandHandler(
            engine=self, notifier=self.notifier,
            git_manager=self.git_manager, env_manager=self.env_manager,
        )
        self.module_registry = ModuleRegistry()
        self.decision_logger = DecisionLogger()

        # Initialize self-improvement engine (lazy import to avoid circular deps)
        self._improver = None

        # Initialize scanners
        self._init_scanners()

        # Data storage
        self._all_keys: List[Dict] = []
        self._verified_keys: List[Dict] = []
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

        # v0.5: Pastebin scanner (always enabled)
        pastebin = PastebinScanner()
        self.scanner_manager.add_scanner(pastebin)

        # v0.5: Telegram scanner (always enabled)
        telegram = TelegramScanner()
        self.scanner_manager.add_scanner(telegram)

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
        self.state.uptime_start = datetime.utcnow().isoformat()
        self.notifier.send_info("🚀 AlphaScan v0.5 engine started")

        # Check for missing API keys
        missing = self.env_manager.detect_key_needs()
        if missing:
            self.notifier.send_info(
                f"⚠️ Missing API keys: {', '.join(missing)}. "
                f"Requesting via Discord..."
            )
            for key_name in missing:
                service_name = key_name.replace("_", " ").title()
                self.env_manager.request_key_via_discord(service_name, key_name)

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

        # Step 2: Detect & Classify (using Groq AI + regex + new intelligence modules)
        keys = self.parser.extract(all_raw_data)

        # v0.5: Also use the new intelligence modules for detection
        if ENABLE_SSH_DETECTION or ENABLE_CRYPTO_DETECTION or ENABLE_API_DETECTION:
            additional_keys = self._detect_with_intelligence(all_raw_data)
            keys.extend(additional_keys)

        # Step 3: Verify (3-layer pipeline)
        verified_keys, rejected_keys = self.verifier.verify_batch(keys)

        # Deduplicate
        unique_keys = self._deduplicate_keys(verified_keys)

        # Update state
        with self._lock:
            self._all_keys.extend(unique_keys)
            self._verified_keys = unique_keys
            self.state.total_keys_found += len(unique_keys)
            self.state.last_scan_time = datetime.utcnow().isoformat()

            # Update keys by rank
            rank_summary = self.ranker.get_rank_summary(unique_keys)
            self.state.keys_by_rank = rank_summary["by_rank"]

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

        # Step 4: Report (clean classified Discord reports)
        cycle_duration = time.time() - cycle_start
        self.state.last_scan_duration = cycle_duration

        # v0.5: Use the clean DiscordReporter
        report = self.reporter.generate_report(unique_keys, cycle=self.state.cycle)
        self.notifier.send_report(report)

        # Send status update
        self.notifier.send_status(
            cycle=self.state.cycle,
            duration=cycle_duration,
            keys_found=len(unique_keys),
        )

        # v0.5: Autonomous decision-making
        if AUTONOMOUS_MODE:
            self._autonomous_cycle(results, unique_keys)

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
            f"Found {len(unique_keys)} verified keys."
        )

    def _detect_with_intelligence(self, raw_data: List[str]) -> List[Dict]:
        """Use the new intelligence modules to detect secrets."""
        additional_keys = []

        for text in raw_data:
            if ENABLE_SSH_DETECTION:
                ssh_keys = self.verifier._ssh_intel.detect(text)
                for key in ssh_keys:
                    key["context"] = text[:500]
                    key["rank"] = key.get("rank", 0)
                    additional_keys.append(key)

            if ENABLE_CRYPTO_DETECTION:
                crypto_keys = self.verifier._crypto_intel.detect(text)
                for key in crypto_keys:
                    key["context"] = text[:500]
                    additional_keys.append(key)

            if ENABLE_API_DETECTION:
                api_keys = self.verifier._api_intel.detect(text)
                for key in api_keys:
                    key["context"] = text[:500]
                    additional_keys.append(key)

        return additional_keys

    def _autonomous_cycle(self, scan_results: List, verified_keys: List[Dict]) -> None:
        """Run autonomous decision-making cycle."""
        try:
            # Analyze performance and propose pivots
            analysis = self.strategy_analyzer.analyze_performance(scan_results, verified_keys)

            # Log the analysis
            self.decision_logger.log_decision(
                decision_type="scan_analysis",
                details=analysis,
                outcome="completed",
                confidence=analysis.get("average_roi", 0),
            )

            # Propose pivot if needed
            pivot_proposal = analysis.get("pivot_proposal")
            if pivot_proposal:
                self.state.autonomous_decisions += 1
                self.notifier.send_pivot_proposal(pivot_proposal)

                # Log the pivot decision
                decision_id = self.decision_logger.log_decision(
                    decision_type="pivot",
                    details=pivot_proposal,
                    outcome="pending",
                    confidence=pivot_proposal.get("confidence", 0),
                    requires_approval=True,
                )

                # Auto-apply if confidence is high enough
                if pivot_proposal.get("confidence", 0) > 0.9:
                    self.strategy_analyzer.apply_pivot(pivot_proposal)
                    self.decision_logger.update_decision(decision_id, "approved")
                    self.notifier.send_info(
                        f"🔄 Auto-applied strategy pivot: {pivot_proposal['proposed_strategy']}"
                    )

            # Propose features if needed
            feature_proposal = self.strategy_analyzer.propose_feature(analysis)
            if feature_proposal:
                self.state.autonomous_decisions += 1
                self.notifier.send_feature_proposal(feature_proposal)

                decision_id = self.decision_logger.log_decision(
                    decision_type="feature",
                    details=feature_proposal,
                    outcome="pending",
                    confidence=feature_proposal.get("confidence", 0),
                    requires_approval=True,
                )

            # Auto-push to GitHub if enabled
            if AUTO_PUSH_GITHUB and self.git_manager.is_available():
                # Commit and push verified keys
                self._save_verified_keys(unique_keys=verified_keys)
                commit_msg = f"Cycle #{self.state.cycle}: {len(verified_keys)} verified keys"
                self.git_manager.commit_changes(commit_msg)

        except Exception as e:
            logger.error(f"Autonomous cycle error: {e}")

    def _save_verified_keys(self, unique_keys: List[Dict]) -> None:
        """Save verified keys to the verified_keys directory."""
        from config.settings import VERIFIED_KEYS_DIR
        try:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filepath = VERIFIED_KEYS_DIR / f"verified_keys_{timestamp}.json"
            with open(filepath, "w") as f:
                json.dump(unique_keys, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save verified keys: {e}")

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
                "autonomous_decisions": self.state.autonomous_decisions,
                "keys_by_rank": self.state.keys_by_rank,
                "verification_stats": self.verifier.get_stats(),
            }
            with open(METRICS_FILE, "w") as f:
                json.dump(metrics, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save data: {e}")

    def stop(self) -> None:
        """Stop the engine."""
        self.state.running = False
        self.notifier.send_info("🛑 AlphaScan v0.5 engine stopped")

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
            "autonomous_mode": AUTONOMOUS_MODE,
            "autonomous_decisions": self.state.autonomous_decisions,
            "uptime_start": self.state.uptime_start,
            "keys_by_rank": self.state.keys_by_rank,
            "current_strategy": self.strategy_analyzer.get_current_strategy(),
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
                "scanner_stats": self.scanner_manager.get_scanner_stats(),
            }
        ]

    def process_command(self, command: str) -> Dict:
        """Process a Discord command."""
        return self.command_handler.process_command(command)
