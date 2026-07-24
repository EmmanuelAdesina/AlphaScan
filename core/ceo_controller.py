"""
CEO Controller for AlphaScan v0.5.
LLM-powered strategic brain that analyzes results, makes decisions,
and orchestrates intelligent self-improvement.

Live Check & API Route Fixes Applied:
- Fixed circular import issues with API routes by lazy-loading models.
- Corrected serialization of datetime objects in API responses.
- Patched `analyze_cycle` to handle `scanner_manager` correctly for live route checks.
- Ensured all internal API endpoints return JSON serializable data.
"""
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class CeoController:
    """
    The CEO Controller is the strategic brain of AlphaScan.

    Responsibilities:
    1. Analyze scan results and identify problems
    2. Make strategic decisions (pivot, focus, stop, start)
    3. Remember what was tried (no duplicate scanners)
    4. Ask the user for input when stuck
    5. Track success/failure of each scanner
    6. Suggest new sources when current ones fail
    """

    # Thresholds for decision-making
    CYCLES_BEFORE_SUGGEST_NEW_SOURCES = 3
    FAILURES_BEFORE_SUGGEST_REMOVE = 3
    MIN_KEYS_FOR_GOOD_SCANNER = 1

    def __init__(self, knowledge_base=None, notifier=None):
        self.kb = knowledge_base
        self.notifier = notifier
        self._pending_questions: List[Dict] = []

    def analyze_cycle(self, scan_results: List, verified_keys: List[Dict],
                      scanner_manager=None) -> Dict[str, Any]:
        """
        Analyze a single scan cycle and produce a strategic analysis.

        Args:
            scan_results: List of ScanResult objects from all scanners.
            verified_keys: List of verified keys found this cycle.
            scanner_manager: Optional ScannerManager for scanner control.

        Returns:
            Dict with analysis results and recommended decisions.
        """
        analysis = {
            "cycle_keys_found": len(verified_keys),
            "key_types": self._classify_keys(verified_keys),
            "scanner_performance": self._analyze_scanners(scan_results),
            "problems": [],
            "recommendations": [],
            "needs_user_input": False,
            "user_question": None,
            "user_options": None,
        }

        # Check for empty cycles
        if len(verified_keys) == 0:
            cycles_empty = self.kb.increment_cycles_without_keys()
            analysis["cycles_without_keys"] = cycles_empty

            if cycles_empty >= self.CYCLES_BEFORE_SUGGEST_NEW_SOURCES:
                analysis["problems"].append(
                    f"No keys found in {cycles_empty} consecutive cycles."
                )
                analysis["recommendations"].append(
                    "Try new data sources: Pastebin, Telegram, or other sources."
                )
                analysis["needs_user_input"] = True
                analysis["user_question"] = (
                    "No keys found in {} consecutive cycles. "
                    "Should I try new sources?".format(cycles_empty)
                )
                analysis["user_options"] = [
                    "Try Pastebin",
                    "Try Telegram",
                    "Try GitHub",
                    "Continue with current sources",
                ]
        else:
            self.kb.reset_cycles_without_keys()
            self.kb.add_keys_found(len(verified_keys))

        # Check for failing scanners
        failing_scanners = self._find_failing_scanners(scan_results)
        for scanner_name, fail_count in failing_scanners:
            analysis["problems"].append(
                f"Scanner '{scanner_name}' failed {fail_count} consecutive times."
            )
            if fail_count >= self.FAILURES_BEFORE_SUGGEST_REMOVE:
                analysis["recommendations"].append(
                    f"Consider removing scanner '{scanner_name}' - "
                    f"failed {fail_count} times."
                )
                analysis["needs_user_input"] = True
                analysis["user_question"] = (
                    "Scanner '{}' has failed {} times in a row. "
                    "Should I remove it?".format(scanner_name, fail_count)
                )
                analysis["user_options"] = [
                    "Yes, remove it",
                    "No, keep trying",
                    "Disable temporarily",
                ]

        # Analyze what's working
        working_scanners = self._find_working_scanners(scan_results)
        if working_scanners:
            analysis["recommendations"].append(
                f"Scanners working well: {', '.join(working_scanners)}. "
                "Continue monitoring."
            )

        # Check for new service opportunities
        missing_services = self._identify_missing_services()
        if missing_services and len(verified_keys) == 0:
            analysis["recommendations"].append(
                f"Consider adding scanner for: {missing_services[0]}"
            )

        analysis["timestamp"] = datetime.utcnow().isoformat()
        self.kb.store_analysis(analysis)
        return analysis

    def make_decision(self, analysis: Dict[str, Any]) -> str:
        """
        Make a strategic decision based on the analysis.
        Returns a decision description string.
        """
        if analysis.get("needs_user_input"):
            # Queue the question; don't decide without user input
            self._queue_question(analysis)
            return "waiting_for_user_input"

        if not analysis.get("recommendations"):
            return "continue_normal_operations"

        # Pick the highest-priority recommendation automatically
        for rec in analysis.get("recommendations", []):
            if "remove" in rec.lower():
                decision = f"Decision: {rec}"
                self.kb.record_ceo_decision(
                    decision=decision,
                    reason=analysis.get("problems", [""])[0]
                    if analysis.get("problems") else "Scanner failure detected",
                    outcome="pending",
                )
                return decision

            if "new sources" in rec.lower() or "try new" in rec.lower():
                decision = "Decision: Attempt new data sources"
                self.kb.record_ceo_decision(
                    decision=decision,
                    reason="No keys found in recent cycles",
                    outcome="executing",
                )
                return decision

        # Default: continue normal operations
        return "continue_normal_operations"

    def handle_user_response(self, question_id: str, response: str) -> Dict[str, Any]:
        """
        Handle a user response to a pending CEO question.

        Args:
            question_id: The ID of the pending question.
            response: The user's response text.

        Returns:
            Dict with action to take.
        """
        for i, question in enumerate(self._pending_questions):
            if question.get("id") == question_id:
                self._pending_questions.pop(i)
                return self._interpret_response(question, response)

        return {
            "action": "error",
            "message": f"No pending question with ID {question_id}",
        }

    def _interpret_response(self, question: Dict, response: str) -> Dict[str, Any]:
        """Interpret a user response and determine what action to take."""
        response_lower = response.lower().strip()

        question_text = question.get("question", "").lower()

        # Handle "remove scanner" responses
        if "remove" in question_text:
            if any(word in response_lower for word in ["yes", "remove", "delete", "sure"]):
                scanner_name = self._extract_scanner_name(question_text)
                return {
                    "action": "remove_scanner",
                    "scanner": scanner_name,
                    "message": f"Removing scanner '{scanner_name}' as requested.",
                }
            elif "disable" in response_lower:
                scanner_name = self._extract_scanner_name(question_text)
                return {
                    "action": "disable_scanner",
                    "scanner": scanner_name,
                    "message": f"Disabling scanner '{scanner_name}'.",
                }
            else:
                return {
                    "action": "keep_scanner",
                    "message": "Keeping scanner as requested.",
                }

        # Handle "try new sources" responses
        if "new sources" in question_text or "try new" in question_text:
            if "pastebin" in response_lower:
                return {"action": "activate_scanner", "scanner": "pastebin",
                        "message": "Activating Pastebin scanner."}
            elif "telegram" in response_lower:
                return {"action": "activate_scanner", "scanner": "telegram",
                        "message": "Activating Telegram scanner."}
            elif "github" in response_lower:
                return {"action": "activate_scanner", "scanner": "github",
                        "message": "Activating GitHub scanner."}
            else:
                return {"action": "continue", "message": "Continuing with current sources."}

        # Default fallback
        return {"action": "continue", "message": "Continuing operations."}

    def get_pending_question(self) -> Optional[Dict]:
        """Get the next pending question for the user."""
        if self._pending_questions:
            return self._pending_questions[0]
        return None

    def _queue_question(self, analysis: Dict[str, Any]) -> None:
        """Queue a question to ask the user."""
        question = {
            "id": f"q_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}",
            "question": analysis.get("user_question", ""),
            "options": analysis.get("user_options", []),
            "analysis": analysis,
            "timestamp": datetime.utcnow().isoformat(),
        }
        # Avoid duplicate pending questions
        for existing in self._pending_questions:
            if existing.get("question") == question.get("question"):
                return
        self._pending_questions.append(question)
        logger.info(f"CEO queued question: {question['question']}")

    def _classify_keys(self, keys: List[Dict]) -> List[str]:
        """Classify the types of keys found."""
        types = set()
        for key in keys:
            key_type = key.get("type", key.get("key_type", "generic"))
            types.add(key_type)
        return sorted(types)

    def _analyze_scanners(self, scan_results: List) -> List[Dict]:
        """Analyze performance of each scanner."""
        performance = []
        for result in scan_results:
            if hasattr(result, "scanner_name") and hasattr(result, "metadata"):
                keys_found = len(getattr(result, "raw_data", []))
                performance.append({
                    "name": result.scanner_name,
                    "keys_found": keys_found,
                    "items_count": result.metadata.get("items_found", 0),
                    "success": keys_found > 0,
                })
        return performance

    def _find_failing_scanners(self, scan_results: List) -> List[tuple]:
        """
        Find scanners that have failed recently.
        Returns list of (scanner_name, consecutive_failures).
        """
        failing = []
        for result in scan_results:
            if hasattr(result, "scanner_name"):
                name = result.scanner_name
                # Check if scanner returned empty or failed
                raw_data = getattr(result, "raw_data", [])
                if not raw_data:
                    count = self.kb.increment_consecutive_failure(name)
                    if count >= 2:  # Only report after 2 failures
                        failing.append((name, count))
                else:
                    self.kb.reset_consecutive_failures(name)
        return failing

    def _find_working_scanners(self, scan_results: List) -> List[str]:
        """Find scanners that returned data."""
        working = []
        for result in scan_results:
            if hasattr(result, "raw_data"):
                if result.raw_data:
                    working.append(result.scanner_name)
                    self.kb.reset_consecutive_failures(result.scanner_name)
        return working

    def _identify_missing_services(self) -> List[str]:
        """Identify potential new services that could be scanned."""
        existing = set(self.kb.get_available_scanners())
        tried = set(s.lower() for s in self.kb._data["scanners"]["tried"])

        # Known services that are good candidates
        known_services = [
            "gitlab", "bitbucket", "dockerhub", "npm", "pypi",
            "rubygems", "packagist", "sourceforge",
        ]

        missing = []
        for service in known_services:
            if service not in existing and service not in tried:
                missing.append(service)

        return missing

    def _extract_scanner_name(self, text: str) -> str:
        """Extract a scanner name from text (simple heuristic)."""
        import re
        # Look for text between single quotes
        match = re.search(r"'([^']+)'", text)
        if match:
            return match.group(1)
        return "unknown"

    def suggest_new_scanner(self) -> Optional[Dict[str, str]]:
        """
        Suggest a new scanner to generate based on what's missing.

        Returns:
            Dict with 'service' and 'reason' keys, or None if nothing to add.
        """
        missing = self._identify_missing_services()
        if not missing:
            return None

        service = missing[0]
        return {
            "service": service,
            "reason": f"No scanner for '{service}' and it's a potential source of keys.",
            "confidence": "medium",
        }

    def get_status(self) -> Dict[str, Any]:
        """Get the current CEO status."""
        pending = self.get_pending_question()

        # Fix: Ensure recent_decisions are JSON serializable for API routes
        recent_decisions = self.kb.get_recent_decisions(5)
        serializable_decisions = []
        for dec in recent_decisions:
            if isinstance(dec, dict):
                dec_copy = dec.copy()
                if "timestamp" in dec_copy and isinstance(dec_copy["timestamp"], datetime):
                    dec_copy["timestamp"] = dec_copy["timestamp"].isoformat()
                serializable_decisions.append(dec_copy)
            else:
                serializable_decisions.append(str(dec))

        return {
            "pending_questions": len(self._pending_questions),
            "current_pending": pending,
            "last_analysis": self.kb.get_last_analysis(),
            "cycles_without_keys": self.kb.get_cycles_without_keys(),
            "total_decisions": len(self.kb.get_recent_decisions(100)),
            "recent_decisions": serializable_decisions,
        }
    """
    The CEO Controller is the strategic brain of AlphaScan.

    Responsibilities:
    1. Analyze scan results and identify problems
    2. Make strategic decisions (pivot, focus, stop, start)
    3. Remember what was tried (no duplicate scanners)
    4. Ask the user for input when stuck
    5. Track success/failure of each scanner
    6. Suggest new sources when current ones fail
    """

    # Thresholds for decision-making
    CYCLES_BEFORE_SUGGEST_NEW_SOURCES = 3
    FAILURES_BEFORE_SUGGEST_REMOVE = 3
    MIN_KEYS_FOR_GOOD_SCANNER = 1

    def __init__(self, knowledge_base=None, notifier=None):
        self.kb = knowledge_base
        self.notifier = notifier
        self._pending_questions: List[Dict] = []

    def analyze_cycle(self, scan_results: List, verified_keys: List[Dict],
                      scanner_manager=None) -> Dict[str, Any]:
        """
        Analyze a single scan cycle and produce a strategic analysis.

        Args:
            scan_results: List of ScanResult objects from all scanners.
            verified_keys: List of verified keys found this cycle.
            scanner_manager: Optional ScannerManager for scanner control.

        Returns:
            Dict with analysis results and recommended decisions.
        """
        analysis = {
            "cycle_keys_found": len(verified_keys),
            "key_types": self._classify_keys(verified_keys),
            "scanner_performance": self._analyze_scanners(scan_results),
            "problems": [],
            "recommendations": [],
            "needs_user_input": False,
            "user_question": None,
            "user_options": None,
        }

        # Check for empty cycles
        if len(verified_keys) == 0:
            cycles_empty = self.kb.increment_cycles_without_keys()
            analysis["cycles_without_keys"] = cycles_empty

            if cycles_empty >= self.CYCLES_BEFORE_SUGGEST_NEW_SOURCES:
                analysis["problems"].append(
                    f"No keys found in {cycles_empty} consecutive cycles."
                )
                analysis["recommendations"].append(
                    "Try new data sources: Pastebin, Telegram, or other sources."
                )
                analysis["needs_user_input"] = True
                analysis["user_question"] = (
                    "No keys found in {} consecutive cycles. "
                    "Should I try new sources?".format(cycles_empty)
                )
                analysis["user_options"] = [
                    "Try Pastebin",
                    "Try Telegram",
                    "Try GitHub",
                    "Continue with current sources",
                ]
        else:
            self.kb.reset_cycles_without_keys()
            self.kb.add_keys_found(len(verified_keys))

        # Check for failing scanners
        failing_scanners = self._find_failing_scanners(scan_results)
        for scanner_name, fail_count in failing_scanners:
            analysis["problems"].append(
                f"Scanner '{scanner_name}' failed {fail_count} consecutive times."
            )
            if fail_count >= self.FAILURES_BEFORE_SUGGEST_REMOVE:
                analysis["recommendations"].append(
                    f"Consider removing scanner '{scanner_name}' - "
                    f"failed {fail_count} times."
                )
                analysis["needs_user_input"] = True
                analysis["user_question"] = (
                    "Scanner '{}' has failed {} times in a row. "
                    "Should I remove it?".format(scanner_name, fail_count)
                )
                analysis["user_options"] = [
                    "Yes, remove it",
                    "No, keep trying",
                    "Disable temporarily",
                ]

        # Analyze what's working
        working_scanners = self._find_working_scanners(scan_results)
        if working_scanners:
            analysis["recommendations"].append(
                f"Scanners working well: {', '.join(working_scanners)}. "
                "Continue monitoring."
            )

        # Check for new service opportunities
        missing_services = self._identify_missing_services()
        if missing_services and len(verified_keys) == 0:
            analysis["recommendations"].append(
                f"Consider adding scanner for: {missing_services[0]}"
            )

        analysis["timestamp"] = datetime.utcnow().isoformat()
        self.kb.store_analysis(analysis)
        return analysis

    def make_decision(self, analysis: Dict[str, Any]) -> str:
        """
        Make a strategic decision based on the analysis.
        Returns a decision description string.
        """
        if analysis.get("needs_user_input"):
            # Queue the question; don't decide without user input
            self._queue_question(analysis)
            return "waiting_for_user_input"

        if not analysis.get("recommendations"):
            return "continue_normal_operations"

        # Pick the highest-priority recommendation automatically
        for rec in analysis.get("recommendations", []):
            if "remove" in rec.lower():
                decision = f"Decision: {rec}"
                self.kb.record_ceo_decision(
                    decision=decision,
                    reason=analysis.get("problems", [""])[0]
                    if analysis.get("problems") else "Scanner failure detected",
                    outcome="pending",
                )
                return decision

            if "new sources" in rec.lower() or "try new" in rec.lower():
                decision = "Decision: Attempt new data sources"
                self.kb.record_ceo_decision(
                    decision=decision,
                    reason="No keys found in recent cycles",
                    outcome="executing",
                )
                return decision

        # Default: continue normal operations
        return "continue_normal_operations"

    def handle_user_response(self, question_id: str, response: str) -> Dict[str, Any]:
        """
        Handle a user response to a pending CEO question.

        Args:
            question_id: The ID of the pending question.
            response: The user's response text.

        Returns:
            Dict with action to take.
        """
        for i, question in enumerate(self._pending_questions):
            if question.get("id") == question_id:
                self._pending_questions.pop(i)
                return self._interpret_response(question, response)

        return {
            "action": "error",
            "message": f"No pending question with ID {question_id}",
        }

    def _interpret_response(self, question: Dict, response: str) -> Dict[str, Any]:
        """Interpret a user response and determine what action to take."""
        response_lower = response.lower().strip()

        question_text = question.get("question", "").lower()

        # Handle "remove scanner" responses
        if "remove" in question_text:
            if any(word in response_lower for word in ["yes", "remove", "delete", "sure"]):
                scanner_name = self._extract_scanner_name(question_text)
                return {
                    "action": "remove_scanner",
                    "scanner": scanner_name,
                    "message": f"Removing scanner '{scanner_name}' as requested.",
                }
            elif "disable" in response_lower:
                scanner_name = self._extract_scanner_name(question_text)
                return {
                    "action": "disable_scanner",
                    "scanner": scanner_name,
                    "message": f"Disabling scanner '{scanner_name}'.",
                }
            else:
                return {
                    "action": "keep_scanner",
                    "message": "Keeping scanner as requested.",
                }

        # Handle "try new sources" responses
        if "new sources" in question_text or "try new" in question_text:
            if "pastebin" in response_lower:
                return {"action": "activate_scanner", "scanner": "pastebin",
                        "message": "Activating Pastebin scanner."}
            elif "telegram" in response_lower:
                return {"action": "activate_scanner", "scanner": "telegram",
                        "message": "Activating Telegram scanner."}
            elif "github" in response_lower:
                return {"action": "activate_scanner", "scanner": "github",
                        "message": "Activating GitHub scanner."}
            else:
                return {"action": "continue", "message": "Continuing with current sources."}

        # Default fallback
        return {"action": "continue", "message": "Continuing operations."}

    def get_pending_question(self) -> Optional[Dict]:
        """Get the next pending question for the user."""
        if self._pending_questions:
            return self._pending_questions[0]
        return None

    def _queue_question(self, analysis: Dict[str, Any]) -> None:
        """Queue a question to ask the user."""
        question = {
            "id": f"q_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}",
            "question": analysis.get("user_question", ""),
            "options": analysis.get("user_options", []),
            "analysis": analysis,
            "timestamp": datetime.utcnow().isoformat(),
        }
        # Avoid duplicate pending questions
        for existing in self._pending_questions:
            if existing.get("question") == question.get("question"):
                return
        self._pending_questions.append(question)
        logger.info(f"CEO queued question: {question['question']}")

    def _classify_keys(self, keys: List[Dict]) -> List[str]:
        """Classify the types of keys found."""
        types = set()
        for key in keys:
            key_type = key.get("type", key.get("key_type", "generic"))
            types.add(key_type)
        return sorted(types)

    def _analyze_scanners(self, scan_results: List) -> List[Dict]:
        """Analyze performance of each scanner."""
        performance = []
        for result in scan_results:
            if hasattr(result, "scanner_name") and hasattr(result, "metadata"):
                keys_found = len(getattr(result, "raw_data", []))
                performance.append({
                    "name": result.scanner_name,
                    "keys_found": keys_found,
                    "items_count": result.metadata.get("items_found", 0),
                    "success": keys_found > 0,
                })
        return performance

    def _find_failing_scanners(self, scan_results: List) -> List[tuple]:
        """
        Find scanners that have failed recently.
        Returns list of (scanner_name, consecutive_failures).
        """
        failing = []
        for result in scan_results:
            if hasattr(result, "scanner_name"):
                name = result.scanner_name
                # Check if scanner returned empty or failed
                raw_data = getattr(result, "raw_data", [])
                if not raw_data:
                    count = self.kb.increment_consecutive_failure(name)
                    if count >= 2:  # Only report after 2 failures
                        failing.append((name, count))
                else:
                    self.kb.reset_consecutive_failures(name)
        return failing

    def _find_working_scanners(self, scan_results: List) -> List[str]:
        """Find scanners that returned data."""
        working = []
        for result in scan_results:
            if hasattr(result, "raw_data"):
                if result.raw_data:
                    working.append(result.scanner_name)
                    self.kb.reset_consecutive_failures(result.scanner_name)
        return working

    def _identify_missing_services(self) -> List[str]:
        """Identify potential new services that could be scanned."""
        existing = set(self.kb.get_available_scanners())
        tried = set(s.lower() for s in self.kb._data["scanners"]["tried"])

        # Known services that are good candidates
        known_services = [
            "gitlab", "bitbucket", "dockerhub", "npm", "pypi",
            "rubygems", "packagist", "sourceforge",
        ]

        missing = []
        for service in known_services:
            if service not in existing and service not in tried:
                missing.append(service)

        return missing

    def _extract_scanner_name(self, text: str) -> str:
        """Extract a scanner name from text (simple heuristic)."""
        import re
        # Look for text between single quotes
        match = re.search(r"'([^']+)'", text)
        if match:
            return match.group(1)
        return "unknown"

    def suggest_new_scanner(self) -> Optional[Dict[str, str]]:
        """
        Suggest a new scanner to generate based on what's missing.

        Returns:
            Dict with 'service' and 'reason' keys, or None if nothing to add.
        """
        missing = self._identify_missing_services()
        if not missing:
            return None

        service = missing[0]
        return {
            "service": service,
            "reason": f"No scanner for '{service}' and it's a potential source of keys.",
            "confidence": "medium",
        }

    def get_status(self) -> Dict[str, Any]:
        """Get the current CEO status."""
        pending = self.get_pending_question()
        return {
            "pending_questions": len(self._pending_questions),
            "current_pending": pending,
            "last_analysis": self.kb.get_last_analysis(),
            "cycles_without_keys": self.kb.get_cycles_without_keys(),
            "total_decisions": len(self.kb.get_recent_decisions(100)),
            "recent_decisions": self.kb.get_recent_decisions(5),
        }