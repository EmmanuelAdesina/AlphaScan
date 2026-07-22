"""
Strategy Analyzer for AlphaScan v0.5.

Analyzes scan results and metrics to propose ROI-based strategy pivots.
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime
from collections import defaultdict

logger = logging.getLogger(__name__)


class StrategyAnalyzer:
    """
    Analyzes scanning performance and proposes strategy pivots.

    ROI-based pivoting: if a scanning source yields low-value keys,
    the system proposes pivoting to higher-value sources.
    """

    def __init__(self, pivot_threshold: float = 0.15):
        self._pivot_threshold = pivot_threshold
        self._strategy_history: List[Dict] = []
        self._current_strategy = "balanced"
        self._source_performance: Dict[str, Dict] = defaultdict(
            lambda: {"keys_found": 0, "valid_keys": 0, "total_value": 0, "scans": 0}
        )

    def analyze_performance(self, scan_results: List, verified_keys: List[Dict]) -> Dict:
        """
        Analyze scan performance and identify pivot opportunities.

        Args:
            scan_results: List of ScanResult objects from scanners.
            verified_keys: List of verified key dicts.

        Returns:
            Analysis report with pivot recommendations.
        """
        # Update source performance metrics
        for result in scan_results:
            scanner_name = result.scanner_name
            self._source_performance[scanner_name]["scans"] += 1
            self._source_performance[scanner_name]["keys_found"] += len(result.raw_data)

        for key in verified_keys:
            scanner_name = key.get("source", "unknown")
            rank = key.get("rank", 10)
            # Value is inverse of rank (rank 0 = highest value)
            value = (10 - rank) / 10.0
            self._source_performance[scanner_name]["valid_keys"] += 1
            self._source_performance[scanner_name]["total_value"] += value

        # Calculate ROI for each source
        source_roi = {}
        for source, perf in self._source_performance.items():
            if perf["scans"] > 0:
                roi = perf["total_value"] / max(perf["scans"], 1)
                source_roi[source] = roi
            else:
                source_roi[source] = 0.0

        # Identify underperforming sources
        avg_roi = sum(source_roi.values()) / max(len(source_roi), 1)
        underperforming = [s for s, roi in source_roi.items() if roi < avg_roi * self._pivot_threshold]
        overperforming = [s for s, roi in source_roi.items() if roi > avg_roi * (1 + self._pivot_threshold)]

        # Generate pivot proposal if needed
        pivot_proposal = None
        if underperforming and avg_roi < 0.3:
            pivot_proposal = self._generate_pivot_proposal(
                source_roi, underperforming, overperforming, avg_roi
            )

        return {
            "source_performance": dict(self._source_performance),
            "source_roi": source_roi,
            "average_roi": avg_roi,
            "underperforming_sources": underperforming,
            "overperforming_sources": overperforming,
            "pivot_proposal": pivot_proposal,
            "current_strategy": self._current_strategy,
        }

    def _generate_pivot_proposal(self, source_roi: Dict, underperforming: List[str],
                                 overperforming: List[str], avg_roi: float) -> Optional[Dict]:
        """Generate a strategy pivot proposal."""
        if not overperforming:
            return None

        best_source = max(source_roi, key=source_roi.get)

        proposal = {
            "current_strategy": self._current_strategy,
            "proposed_strategy": f"focus_on_{best_source}",
            "current_sources": list(source_roi.keys()),
            "underperforming_sources": underperforming,
            "best_source": best_source,
            "expected_roi_improvement": max(0, source_roi[best_source] - avg_roi),
            "confidence": min(1.0, source_roi[best_source] / max(avg_roi, 0.01)),
            "reasoning": (
                f"Source '{best_source}' has ROI of {source_roi[best_source]:.3f}, "
                f"significantly above average ({avg_roi:.3f}). "
                f"Pivoting to focus on this source."
            ),
            "timestamp": datetime.utcnow().isoformat(),
        }

        return proposal

    def propose_feature(self, analysis: Dict) -> Optional[Dict]:
        """
        Propose a new feature based on analysis.

        Args:
            analysis: Analysis report from analyze_performance.

        Returns:
            Feature proposal dict or None.
        """
        # Check if there are unclassified keys that need new patterns
        source_perf = analysis.get("source_performance", {})

        # Look for sources with high raw data but low valid keys
        for source, perf in source_perf.items():
            if perf["keys_found"] > 10 and perf["valid_keys"] == 0:
                return {
                    "feature": f"new_scanner_for_{source}",
                    "description": f"Add specialized scanner for {source} to improve key extraction",
                    "confidence": 0.7,
                    "estimated_impact": "high",
                    "reasoning": (
                        f"Source '{source}' found {perf['keys_found']} items but "
                        f"0 valid keys. A specialized scanner could improve extraction."
                    ),
                }

        # Check for low overall ROI
        if analysis.get("average_roi", 0) < 0.2:
            return {
                "feature": "new_key_patterns",
                "description": "Add new key detection patterns to improve classification",
                "confidence": 0.6,
                "estimated_impact": "medium",
                "reasoning": "Low average ROI suggests keys are being missed or misclassified.",
            }

        return None

    def apply_pivot(self, proposal: Dict) -> bool:
        """Apply a strategy pivot proposal."""
        if not proposal:
            return False

        old_strategy = self._current_strategy
        self._current_strategy = proposal["proposed_strategy"]

        self._strategy_history.append({
            "timestamp": datetime.utcnow().isoformat(),
            "old_strategy": old_strategy,
            "new_strategy": self._current_strategy,
            "proposal": proposal,
        })

        logger.info(f"Strategy pivoted from '{old_strategy}' to '{self._current_strategy}'")
        return True

    def get_current_strategy(self) -> str:
        """Get the current strategy."""
        return self._current_strategy

    def get_strategy_history(self) -> List[Dict]:
        """Get strategy change history."""
        return list(self._strategy_history)

    def get_source_performance(self) -> Dict:
        """Get source performance metrics."""
        return dict(self._source_performance)
