"""
Decision Executor for AlphaScan v0.5.
Executes CEO decisions: remove scanners, activate scanners, generate code, etc.
"""
import logging
import os
from typing import Dict, Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class DecisionExecutor:
    """
    Executes decisions made by the CEO Controller.

    Actions supported:
    - remove_scanner: Delete a scanner file and unregister it
    - disable_scanner: Disable a scanner without deleting
    - activate_scanner: Enable a scanner
    - generate_scanner: Generate a new scanner (via code_generator)
    - continue: No action needed
    """

    def __init__(self, knowledge_base=None, notifier=None, scanner_manager=None,
                 code_generator=None):
        self.kb = knowledge_base
        self.notifier = notifier
        self.scanner_manager = scanner_manager
        self.code_generator = code_generator

    def execute(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a decision action.

        Args:
            action: Dict with 'action' key and any additional parameters.

        Returns:
            Dict with 'success', 'message', and optional 'data'.
        """
        action_type = action.get("action", "continue")

        handlers = {
            "remove_scanner": self._remove_scanner,
            "disable_scanner": self._disable_scanner,
            "activate_scanner": self._activate_scanner,
            "keep_scanner": self._keep_scanner,
            "generate_scanner": self._generate_scanner,
            "continue": self._continue,
            "error": self._error,
        }

        handler = handlers.get(action_type, self._continue)
        try:
            result = handler(action)
            logger.info(f"Executed action '{action_type}': {result.get('message', '')}")
            return result
        except Exception as e:
            logger.error(f"Failed to execute action '{action_type}': {e}")
            return {"success": False, "message": f"Execution failed: {e}"}

    def _remove_scanner(self, action: Dict) -> Dict[str, Any]:
        """Remove a scanner file and unregister it."""
        scanner_name = action.get("scanner", "")
        if not scanner_name:
            return {"success": False, "message": "No scanner name provided."}

        # Remove the scanner file
        scanner_path = Path(f"scanners/{scanner_name}_scanner.py")
        if scanner_path.exists():
            try:
                os.remove(scanner_path)
                logger.info(f"Deleted scanner file: {scanner_path}")
            except OSError as e:
                return {"success": False, "message": f"Failed to delete {scanner_path}: {e}"}
        else:
            logger.warning(f"Scanner file not found: {scanner_path}")

        # Remove from scanner manager
        if self.scanner_manager:
            self.scanner_manager.remove_scanner(scanner_name)

        # Record in knowledge base
        if self.kb:
            self.kb.record_ceo_decision(
                decision=f"Removed scanner '{scanner_name}'",
                reason=action.get("message", "User requested removal"),
                outcome="completed",
            )

        msg = f"Scanner '{scanner_name}' has been removed."
        if self.notifier:
            self.notifier.send_info(f"🗑️ {msg}")
        return {"success": True, "message": msg}

    def _disable_scanner(self, action: Dict) -> Dict[str, Any]:
        """Disable a scanner without deleting it."""
        scanner_name = action.get("scanner", "")
        if not scanner_name:
            return {"success": False, "message": "No scanner name provided."}

        if self.scanner_manager:
            self.scanner_manager.disable_scanner(scanner_name)

        if self.kb:
            self.kb.record_ceo_decision(
                decision=f"Disabled scanner '{scanner_name}'",
                reason=action.get("message", "User requested disable"),
                outcome="completed",
            )

        msg = f"Scanner '{scanner_name}' has been disabled."
        if self.notifier:
            self.notifier.send_info(f"⏸️ {msg}")
        return {"success": True, "message": msg}

    def _activate_scanner(self, action: Dict) -> Dict[str, Any]:
        """Enable a scanner."""
        scanner_name = action.get("scanner", "")
        if not scanner_name:
            return {"success": False, "message": "No scanner name provided."}

        if self.scanner_manager:
            self.scanner_manager.enable_scanner(scanner_name)

        if self.kb:
            self.kb.record_ceo_decision(
                decision=f"Activated scanner '{scanner_name}'",
                reason=action.get("message", "User requested activation"),
                outcome="completed",
            )

        msg = f"Scanner '{scanner_name}' has been activated."
        if self.notifier:
            self.notifier.send_info(f"✅ {msg}")
        return {"success": True, "message": msg}

    def _keep_scanner(self, action: Dict) -> Dict[str, Any]:
        """Keep a scanner (no action needed)."""
        msg = action.get("message", "Keeping scanner as requested.")
        if self.notifier:
            self.notifier.send_info(f"ℹ️ {msg}")
        return {"success": True, "message": msg}

    def _generate_scanner(self, action: Dict) -> Dict[str, Any]:
        """Generate a new scanner via the code generator."""
        service = action.get("service", "")
        if not service:
            return {"success": False, "message": "No service name provided."}

        # Check if already exists or tried
        if self.kb:
            if self.kb.scanner_exists(service) or self.kb.scanner_already_tried(service):
                return {
                    "success": False,
                    "message": f"Scanner for '{service}' already exists or was already tried.",
                }

        if not self.code_generator:
            return {"success": False, "message": "Code generator not available."}

        # Generate the scanner
        try:
            description = f"Add a scanner for {service}"
            success, msg = self.code_generator.trigger_improvement(description)

            if success and self.kb:
                self.kb.register_scanner(service, success=True)
                self.kb.record_code_generation(description, f"{service}_scanner.py", True)

            return {"success": success, "message": msg}
        except Exception as e:
            logger.error(f"Failed to generate scanner for '{service}': {e}")
            return {"success": False, "message": f"Generation failed: {e}"}

    def _continue(self, action: Dict) -> Dict[str, Any]:
        """No action needed."""
        return {"success": True, "message": "No action needed. Continuing normal operations."}

    def _error(self, action: Dict) -> Dict[str, Any]:
        """Handle an error action."""
        msg = action.get("message", "An error occurred.")
        logger.error(f"Decision executor error: {msg}")
        return {"success": False, "message": msg}