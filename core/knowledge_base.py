"""
Knowledge Base v2 - CEO Memory System for AlphaScan.
Persists across restarts and tracks all actions, scanners, decisions, and outcomes.
"""
import json
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class KnowledgeBase:
    """
    CEO memory system that tracks:
    - All scanners that exist
    - All scanners that were tried (including failed ones)
    - All code generated (no duplicates)
    - Scan results per scanner
    - User commands and responses
    - CEO decisions and outcomes
    - Consecutive failure counts per scanner
    """

    def __init__(self, json_path: Optional[str] = None):
        self.json_path = Path(json_path or "data/knowledge.json")
        self.json_path.parent.mkdir(parents=True, exist_ok=True)
        self._data: Dict[str, Any] = self._load()
        logger.info(f"Knowledge Base loaded from {self.json_path}")

    def _load(self) -> Dict[str, Any]:
        """Load knowledge base from JSON file."""
        if self.json_path.exists():
            try:
                with open(self.json_path, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load knowledge base: {e}")
        return self._default_structure()

    def _default_structure(self) -> Dict[str, Any]:
        """Return default knowledge base structure."""
        return {
            "scanners": {
                "existing": [],
                "tried": [],
                "failed": [],
                "consecutive_failures": {},
            },
            "code_generated": [],
            "scan_results": {},
            "user_commands": [],
            "ceo_decisions": [],
            "cycles_without_keys": 0,
            "last_analysis": None,
            "total_scans_run": 0,
            "total_keys_found": 0,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

    def _save(self) -> None:
        """Persist knowledge base to JSON file."""
        self._data["updated_at"] = datetime.utcnow().isoformat()
        try:
            with open(self.json_path, "w") as f:
                json.dump(self._data, f, indent=2, default=str)
        except IOError as e:
            logger.error(f"Failed to save knowledge base: {e}")

    # ── Scanner Tracking ──────────────────────────────────────────────────

    def scanner_exists(self, scanner_name: str) -> bool:
        """Check if a scanner file already exists on disk."""
        scanner_file = Path(f"scanners/{scanner_name}_scanner.py")
        return scanner_file.exists()

    def scanner_already_tried(self, service_name: str) -> bool:
        """Check if a scanner was already attempted/created."""
        normalized = service_name.lower().strip()
        return (
            normalized in [s.lower() for s in self._data["scanners"]["existing"]]
            or normalized in [s.lower() for s in self._data["scanners"]["tried"]]
        )

    def register_scanner(self, scanner_name: str, success: bool = True) -> None:
        """Register a scanner in the knowledge base."""
        normalized = scanner_name.lower().strip()
        if normalized not in [s.lower() for s in self._data["scanners"]["existing"]]:
            self._data["scanners"]["existing"].append(scanner_name)
        if normalized not in [s.lower() for s in self._data["scanners"]["tried"]]:
            self._data["scanners"]["tried"].append(scanner_name)
        if not success:
            self._data["scanners"]["failed"].append(scanner_name)
        self._save()

    def record_scanner_attempt(self, service_name: str, success: bool = False) -> None:
        """Record a scanner generation attempt."""
        normalized = service_name.lower().strip()
        if normalized not in [s.lower() for s in self._data["scanners"]["tried"]]:
            self._data["scanners"]["tried"].append(service_name)
        if not success:
            self._data["scanners"]["failed"].append(service_name)
        self._save()

    def get_consecutive_failures(self, scanner_name: str) -> int:
        """Get consecutive failure count for a scanner."""
        normalized = scanner_name.lower()
        return self._data["scanners"]["consecutive_failures"].get(normalized, 0)

    def increment_consecutive_failure(self, scanner_name: str) -> int:
        """Increment consecutive failure count for a scanner."""
        normalized = scanner_name.lower()
        count = self._data["scanners"]["consecutive_failures"].get(normalized, 0) + 1
        self._data["scanners"]["consecutive_failures"][normalized] = count
        self._save()
        return count

    def reset_consecutive_failures(self, scanner_name: str) -> None:
        """Reset consecutive failure count when a scanner succeeds."""
        normalized = scanner_name.lower()
        self._data["scanners"]["consecutive_failures"].pop(normalized, None)
        self._save()

    # ── Code Generation Tracking ──────────────────────────────────────────

    def code_already_generated(self, description: str) -> bool:
        """Check if code for a description was already generated."""
        desc_lower = description.lower().strip()
        for entry in self._data["code_generated"]:
            if entry.get("description", "").lower().strip() == desc_lower:
                return True
        return False

    def record_code_generation(self, description: str, filename: str,
                               success: bool = True) -> None:
        """Record a code generation event."""
        self._data["code_generated"].append({
            "description": description,
            "filename": filename,
            "success": success,
            "timestamp": datetime.utcnow().isoformat(),
        })
        self._save()

    # ── Scan Results Tracking ─────────────────────────────────────────────

    def record_scan_result(self, scanner_name: str, keys_found: int) -> None:
        """Record scan results for a scanner."""
        normalized = scanner_name.lower()
        if normalized not in self._data["scan_results"]:
            self._data["scan_results"][normalized] = {
                "total_keys": 0,
                "scan_count": 0,
                "last_result": None,
                "history": [],
            }
        entry = self._data["scan_results"][normalized]
        entry["total_keys"] += keys_found
        entry["scan_count"] += 1
        entry["last_result"] = {
            "keys_found": keys_found,
            "timestamp": datetime.utcnow().isoformat(),
        }
        entry["history"].append({
            "keys_found": keys_found,
            "timestamp": datetime.utcnow().isoformat(),
        })
        # Keep only last 100 entries
        if len(entry["history"]) > 100:
            entry["history"] = entry["history"][-100:]
        self._save()

    def get_scanner_stats(self) -> Dict[str, Any]:
        """Get summary statistics for all scanners."""
        stats = {}
        for name, data in self._data["scan_results"].items():
            total_scans = data["scan_count"]
            total_keys = data["total_keys"]
            avg_keys = total_keys / max(total_scans, 1)
            stats[name] = {
                "total_scans": total_scans,
                "total_keys": total_keys,
                "avg_keys_per_scan": round(avg_keys, 2),
                "last_result": data["last_result"],
            }
        return stats

    # ── CEO Decision Tracking ────────────────────────────────────────────

    def record_ceo_decision(self, decision: str, reason: str,
                            outcome: str = "pending") -> str:
        """Record a CEO decision."""
        decision_id = f"ceo_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}"
        self._data["ceo_decisions"].append({
            "id": decision_id,
            "decision": decision,
            "reason": reason,
            "outcome": outcome,
            "timestamp": datetime.utcnow().isoformat(),
        })
        self._save()
        return decision_id

    def update_ceo_decision(self, decision_id: str, outcome: str) -> bool:
        """Update the outcome of a CEO decision."""
        for entry in self._data["ceo_decisions"]:
            if entry["id"] == decision_id:
                entry["outcome"] = outcome
                entry["updated_at"] = datetime.utcnow().isoformat()
                self._save()
                return True
        return False

    def get_recent_decisions(self, limit: int = 10) -> List[Dict]:
        """Get most recent CEO decisions."""
        return self._data["ceo_decisions"][-limit:]

    # ── User Command Tracking ────────────────────────────────────────────

    def record_user_command(self, command: str, response: str) -> None:
        """Record a user command and its response."""
        self._data["user_commands"].append({
            "command": command,
            "response": response,
            "timestamp": datetime.utcnow().isoformat(),
        })
        # Keep only last 200
        if len(self._data["user_commands"]) > 200:
            self._data["user_commands"] = self._data["user_commands"][-200:]
        self._save()

    def get_recent_commands(self, limit: int = 20) -> List[Dict]:
        """Get recent user commands."""
        return self._data["user_commands"][-limit:]

    # ── Cycle Tracking ────────────────────────────────────────────────────

    def increment_cycles_without_keys(self) -> int:
        """Increment the counter for cycles with no keys found."""
        self._data["cycles_without_keys"] = self._data.get("cycles_without_keys", 0) + 1
        self._save()
        return self._data["cycles_without_keys"]

    def reset_cycles_without_keys(self) -> None:
        """Reset the counter when keys are found."""
        self._data["cycles_without_keys"] = 0
        self._save()

    def get_cycles_without_keys(self) -> int:
        """Get number of consecutive cycles without keys."""
        return self._data.get("cycles_without_keys", 0)

    def increment_total_scans(self) -> None:
        """Increment total scan counter."""
        self._data["total_scans_run"] = self._data.get("total_scans_run", 0) + 1
        self._save()

    def add_keys_found(self, count: int) -> None:
        """Add to total keys found counter."""
        self._data["total_keys_found"] = self._data.get("total_keys_found", 0) + count
        self._save()

    # ── Analysis ──────────────────────────────────────────────────────────

    def store_analysis(self, analysis: Dict[str, Any]) -> None:
        """Store the last CEO analysis result."""
        self._data["last_analysis"] = analysis
        self._save()

    def get_last_analysis(self) -> Optional[Dict[str, Any]]:
        """Get the last CEO analysis."""
        return self._data.get("last_analysis")

    def get_available_scanners(self) -> List[str]:
        """Get list of scanner names from the scanners directory."""
        scanners_dir = Path("scanners")
        if not scanners_dir.exists():
            return []
        scanners = []
        for f in scanners_dir.iterdir():
            if f.name.endswith("_scanner.py") and f.name != "base_scanner.py":
                scanners.append(f.name.replace("_scanner.py", ""))
        return scanners

    def get_full_state(self) -> Dict[str, Any]:
        """Get the complete state of the knowledge base."""
        return {
            "existing_scanners": self._data["scanners"]["existing"],
            "tried_scanners": self._data["scanners"]["tried"],
            "failed_scanners": self._data["scanners"]["failed"],
            "consecutive_failures": self._data["scanners"]["consecutive_failures"],
            "total_code_generated": len(self._data["code_generated"]),
            "scanner_stats": self.get_scanner_stats(),
            "cycles_without_keys": self.get_cycles_without_keys(),
            "total_scans_run": self._data.get("total_scans_run", 0),
            "total_keys_found": self._data.get("total_keys_found", 0),
            "recent_decisions": self.get_recent_decisions(5),
            "recent_commands": self.get_recent_commands(5),
        }

    def reset(self) -> None:
        """Reset the entire knowledge base."""
        self._data = self._default_structure()
        self._save()
        logger.info("Knowledge base has been reset.")

    def to_dict(self) -> Dict[str, Any]:
        """Export the full knowledge base as a dictionary."""
        return dict(self._data)