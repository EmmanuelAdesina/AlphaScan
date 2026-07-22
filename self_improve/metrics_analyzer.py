"""
Metrics analyzer for APIS self-improvement system.
Analyzes scan results and metrics to identify areas for improvement.
"""
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime
from collections import Counter, defaultdict

from self_improve.knowledge_base import KnowledgeBase

logger = logging.getLogger(__name__)


class MetricsAnalyzer:
    """
    Analyzes scan results and metrics to identify:
    - Which scanning queries yield the most valid keys
    - Which key types are most commonly found
    - Areas for improvement (detection accuracy, speed, new key types)
    - Unclassified keys that need new patterns
    """

    def __init__(self, knowledge_base: Optional[KnowledgeBase] = None):
        self.kb = knowledge_base or KnowledgeBase()
        self._metrics: Dict[str, Any] = {
            "total_scans": 0,
            "total_keys_found": 0,
            "keys_by_type": defaultdict(int),
            "unclassified_keys": [],
            "scanner_success": defaultdict(lambda: {"found": 0, "valid": 0}),
            "code_generation_attempts": 0,
            "code_generation_success": 0,
            "self_deployment_history": [],
        }

    def analyze_results(self, keys: List[Dict], scan_results: List) -> Dict:
        """
        Analyze scan results to identify patterns and improvement opportunities.

        Args:
            keys: List of classified key dicts.
            scan_results: List of ScanResult objects.

        Returns:
            Analysis report dict.
        """
        report: Dict[str, Any] = {
            "total_keys": len(keys),
            "keys_by_type": {},
            "unclassified_count": 0,
            "new_key_types": [],
            "improvement_opportunities": [],
            "scanner_performance": {},
        }

        # Count keys by type
        type_counts: Counter = Counter()
        for key in keys:
            key_type = key.get("type", "generic")
            type_counts[key_type] += 1

        report["keys_by_type"] = dict(type_counts)

        # Identify new key types
        existing_types = set(k["name"] for k in self.kb.get_patterns())
        for key_type in type_counts:
            if key_type not in existing_types and key_type != "generic":
                report["new_key_types"].append(key_type)

        # Analyze scanner performance
        scanner_perf: Dict[str, Dict] = {}
        for result in scan_results:
            scanner_name = result.scanner_name
            if scanner_name not in scanner_perf:
                scanner_perf[scanner_name] = {"items_found": 0, "keys_extracted": 0}
            scanner_perf[scanner_name]["items_found"] += len(result.raw_data)

        report["scanner_performance"] = scanner_perf

        # Identify improvement opportunities
        opportunities = self._identify_improvements(keys, type_counts, scan_results)
        report["improvement_opportunities"] = opportunities

        # Update internal metrics
        self._update_metrics(keys, scan_results)

        # Update knowledge base
        self._update_knowledge_base(keys, scan_results)

        logger.info(f"Metrics analysis complete: {len(keys)} keys, "
                     f"{len(opportunities)} improvement opportunities")

        return report

    def _identify_improvements(self, keys: List[Dict], type_counts: Counter,
                               scan_results: List) -> List[Dict]:
        """Identify specific improvement opportunities."""
        opportunities = []

        # Check for unclassified keys (type == "generic")
        generic_count = type_counts.get("generic", 0)
        if generic_count > 0:
            opportunities.append({
                "type": "new_pattern",
                "priority": "high",
                "description": f"Found {generic_count} unclassified keys",
                "action": "Generate new classification pattern",
            })

        # Check for scanners with low yield
        for result in scan_results:
            if len(result.raw_data) == 0:
                opportunities.append({
                    "type": "scanner_optimization",
                    "priority": "medium",
                    "description": f"Scanner '{result.scanner_name}' found no data",
                    "action": "Review scanner configuration or disable",
                })

        # Check for key types that need validation methods
        for key_type, count in type_counts.items():
            if key_type == "generic" and count > 5:
                opportunities.append({
                    "type": "validation_improvement",
                    "priority": "high",
                    "description": f"Many generic keys ({count}) - need better classification",
                    "action": "Add new regex patterns or AI classification",
                })

        return opportunities

    def _update_metrics(self, keys: List[Dict], scan_results: List) -> None:
        """Update internal metrics tracking."""
        self._metrics["total_scans"] += 1
        self._metrics["total_keys_found"] += len(keys)

        for key in keys:
            key_type = key.get("type", "generic")
            self._metrics["keys_by_type"][key_type] += 1

        for result in scan_results:
            scanner_name = result.scanner_name
            self._metrics["scanner_success"][scanner_name]["found"] += len(result.raw_data)

    def _update_knowledge_base(self, keys: List[Dict], scan_results: List) -> None:
        """Update the knowledge base with new findings."""
        # Update scanning success rates
        for result in scan_results:
            keys_from_scanner = sum(
                1 for k in keys if k.get("source") == result.scanner_name
            )
            self.kb.update_scanning_success(
                source=result.scanner_name,
                keys_found=len(result.raw_data),
                valid=keys_from_scanner,
            )

    def get_metrics(self) -> Dict:
        """Get current metrics."""
        return {
            "total_scans": self._metrics["total_scans"],
            "total_keys_found": self._metrics["total_keys_found"],
            "keys_by_type": dict(self._metrics["keys_by_type"]),
            "scanner_success": dict(self._metrics["scanner_success"]),
            "code_generation_attempts": self._metrics["code_generation_attempts"],
            "code_generation_success": self._metrics["code_generation_success"],
        }

    def record_code_generation(self, success: bool) -> None:
        """Record a code generation attempt."""
        self._metrics["code_generation_attempts"] += 1
        if success:
            self._metrics["code_generation_success"] += 1

    def get_success_rate(self) -> float:
        """Get code generation success rate."""
        attempts = self._metrics["code_generation_attempts"]
        if attempts == 0:
            return 0.0
        return self._metrics["code_generation_success"] / attempts

    def identify_priority_scanners(self) -> List[str]:
        """Identify which scanners yield the most valid keys."""
        sorted_scanners = sorted(
            self._metrics["scanner_success"].items(),
            key=lambda x: x[1]["found"],
            reverse=True,
        )
        return [name for name, _ in sorted_scanners[:3]]
