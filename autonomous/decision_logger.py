"""
Decision Logger for AlphaScan v0.5.

Logs all autonomous decisions made by the system for audit trail and analysis.
"""
import json
import logging
import os
from typing import Dict, List, Optional, Union
from datetime import datetime
from pathlib import Path
from config.settings import DECISIONS_LOG_FILE, MAX_DECISION_LOG

logger = logging.getLogger(__name__)


class DecisionLogger:
    """
    Logs all autonomous decisions made by AlphaScan.

    Each decision is logged with:
    - Timestamp
    - Decision type (scan, pivot, feature, deploy, etc.)
    - Decision details
    - Outcome
    - Confidence level
    """

    def __init__(self, log_file: Optional[Union[Path, str]] = None):
        self._log_file = Path(log_file) if log_file else DECISIONS_LOG_FILE
        self._log_file.parent.mkdir(parents=True, exist_ok=True)
        self._decisions: List[Dict] = []
        self._load_existing()

    def log_decision(self, decision_type: str, details: Dict,
                     outcome: str = "pending", confidence: float = 0.0,
                     requires_approval: bool = False) -> str:
        """
        Log a decision made by the autonomous system.

        Args:
            decision_type: Type of decision (scan, pivot, feature, deploy, etc.)
            details: Details about the decision.
            outcome: Outcome of the decision (pending, approved, denied, completed, failed).
            confidence: Confidence level (0.0-1.0).
            requires_approval: Whether human approval is required.

        Returns:
            Decision ID for tracking.
        """
        decision_id = f"dec_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}"

        decision = {
            "id": decision_id,
            "timestamp": datetime.utcnow().isoformat(),
            "type": decision_type,
            "details": details,
            "outcome": outcome,
            "confidence": confidence,
            "requires_approval": requires_approval,
        }

        self._decisions.append(decision)

        # Trim to max log size
        if len(self._decisions) > MAX_DECISION_LOG:
            self._decisions = self._decisions[-MAX_DECISION_LOG:]

        # Write to log file
        self._write_to_file(decision)

        logger.info(f"Decision logged: {decision_id} - {decision_type} - {outcome}")

        return decision_id

    def update_decision(self, decision_id: str, outcome: str,
                        details: Optional[Dict] = None) -> bool:
        """Update a decision's outcome."""
        for decision in self._decisions:
            if decision["id"] == decision_id:
                decision["outcome"] = outcome
                if details:
                    decision["details"].update(details)
                self._write_update(decision)
                return True
        return False

    def get_decisions(self, decision_type: Optional[str] = None,
                      limit: int = 100) -> List[Dict]:
        """Get logged decisions, optionally filtered by type."""
        decisions = self._decisions
        if decision_type:
            decisions = [d for d in decisions if d["type"] == decision_type]
        return decisions[-limit:]

    def get_pending_approvals(self) -> List[Dict]:
        """Get decisions that require human approval and are still pending."""
        return [d for d in self._decisions
                if d.get("requires_approval") and d.get("outcome") == "pending"]

    def get_stats(self) -> Dict:
        """Get decision statistics."""
        total = len(self._decisions)
        by_type = {}
        by_outcome = {}

        for d in self._decisions:
            by_type[d["type"]] = by_type.get(d["type"], 0) + 1
            by_outcome[d["outcome"]] = by_outcome.get(d["outcome"], 0) + 1

        return {
            "total_decisions": total,
            "by_type": by_type,
            "by_outcome": by_outcome,
            "pending_approvals": len(self.get_pending_approvals()),
        }

    def _load_existing(self) -> None:
        """Load existing decisions from log file."""
        if not self._log_file.exists():
            return

        try:
            with open(self._log_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            decision = json.loads(line)
                            self._decisions.append(decision)
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            logger.warning(f"Failed to load existing decisions: {e}")

    def _write_to_file(self, decision: Dict) -> None:
        """Append a decision to the log file."""
        try:
            with open(self._log_file, "a") as f:
                f.write(json.dumps(decision, default=str) + "\n")
        except Exception as e:
            logger.error(f"Failed to write decision to file: {e}")

    def _write_update(self, decision: Dict) -> None:
        """Update a decision in the log file (rewrite entire file)."""
        try:
            with open(self._log_file, "w") as f:
                for d in self._decisions:
                    f.write(json.dumps(d, default=str) + "\n")
        except Exception as e:
            logger.error(f"Failed to update decision log: {e}")
