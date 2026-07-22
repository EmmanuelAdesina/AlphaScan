"""
Command Handler for AlphaScan v0.5.

Processes Discord commands for autonomous control of the system.
"""
import logging
from typing import Dict, Optional, List, Callable
from datetime import datetime

logger = logging.getLogger(__name__)


class CommandHandler:
    """
    Handles Discord commands for AlphaScan v0.5.

    Supported commands:
    - !status - Show current scan state, keys found, uptime
    - !approve-pivot - Approve strategy pivot
    - !deny-pivot - Reject strategy pivot
    - !approve-feature - Approve new feature addition
    - !deny-feature - Reject new feature addition
    - !config - Show current configuration (without secrets)
    - !restart - Restart the system
    - !push - Force push to GitHub
    - !rollback - Rollback last change
    - !logs - Show recent logs
    - !help - Show available commands
    - !provide-key <KEY_NAME> <value> - Provide API key
    - !improve <description> - Trigger self-improvement
    - !scan - Force immediate scan
    """

    def __init__(self, engine=None, notifier=None, git_manager=None,
                 env_manager=None, decision_logger=None):
        self._engine = engine
        self._notifier = notifier
        self._git_manager = git_manager
        self._env_manager = env_manager
        self._decision_logger = decision_logger
        self._commands: Dict[str, Callable] = {}
        self._register_commands()

    def _register_commands(self) -> None:
        """Register all available commands."""
        self._commands = {
            "!status": self._cmd_status,
            "!approve-pivot": self._cmd_approve_pivot,
            "!deny-pivot": self._cmd_deny_pivot,
            "!approve-feature": self._cmd_approve_feature,
            "!deny-feature": self._cmd_deny_feature,
            "!config": self._cmd_config,
            "!restart": self._cmd_restart,
            "!push": self._cmd_push,
            "!rollback": self._cmd_rollback,
            "!logs": self._cmd_logs,
            "!help": self._cmd_help,
            "!provide-key": self._cmd_provide_key,
            "!improve": self._cmd_improve,
            "!scan": self._cmd_scan,
        }

    def process_command(self, command: str) -> Dict:
        """
        Process a Discord command.

        Args:
            command: Command string (e.g., "!status", "!improve Add Slack detection").

        Returns:
            Dict with 'success', 'message', and optional 'data'.
        """
        if not command or not command.startswith("!"):
            return {"success": False, "message": "Invalid command. Use !help for available commands."}

        # Parse command and arguments
        parts = command.strip().split(None, 1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        # Find matching command
        handler = self._commands.get(cmd)
        if handler is None:
            # Check for commands with arguments (like !provide-key)
            for registered_cmd, registered_handler in self._commands.items():
                if cmd.startswith(registered_cmd):
                    handler = registered_handler
                    break

        if handler is None:
            return {"success": False, "message": f"Unknown command: {cmd}. Use !help for available commands."}

        try:
            result = handler(args)
            return result
        except Exception as e:
            logger.error(f"Command '{cmd}' failed: {e}")
            return {"success": False, "message": f"Command failed: {e}"}

    def _cmd_status(self, args: str = "") -> Dict:
        """Show current scan state, keys found, uptime."""
        if not self._engine:
            return {"success": False, "message": "Engine not available"}

        status = self._engine.get_status()
        return {
            "success": True,
            "message": "📊 **AlphaScan v0.5 Status**\n" + self._format_status(status),
            "data": status,
        }

    def _cmd_approve_pivot(self, args: str = "") -> Dict:
        """Approve strategy pivot."""
        if self._decision_logger:
            pending = self._decision_logger.get_pending_approvals()
            pivot_decisions = [d for d in pending if d["type"] == "pivot"]
            if pivot_decisions:
                self._decision_logger.update_decision(pivot_decisions[0]["id"], "approved")
                return {"success": True, "message": "✅ Strategy pivot approved. Applying..."}
            return {"success": False, "message": "No pending pivot proposals."}
        return {"success": False, "message": "Decision logger not available."}

    def _cmd_deny_pivot(self, args: str = "") -> Dict:
        """Reject strategy pivot."""
        if self._decision_logger:
            pending = self._decision_logger.get_pending_approvals()
            pivot_decisions = [d for d in pending if d["type"] == "pivot"]
            if pivot_decisions:
                self._decision_logger.update_decision(pivot_decisions[0]["id"], "denied")
                return {"success": True, "message": "❌ Strategy pivot denied."}
            return {"success": False, "message": "No pending pivot proposals."}
        return {"success": False, "message": "Decision logger not available."}

    def _cmd_approve_feature(self, args: str = "") -> Dict:
        """Approve new feature addition."""
        if self._decision_logger:
            pending = self._decision_logger.get_pending_approvals()
            feature_decisions = [d for d in pending if d["type"] == "feature"]
            if feature_decisions:
                self._decision_logger.update_decision(feature_decisions[0]["id"], "approved")
                return {"success": True, "message": "✅ Feature approved. Deploying..."}
            return {"success": False, "message": "No pending feature proposals."}
        return {"success": False, "message": "Decision logger not available."}

    def _cmd_deny_feature(self, args: str = "") -> Dict:
        """Reject new feature addition."""
        if self._decision_logger:
            pending = self._decision_logger.get_pending_approvals()
            feature_decisions = [d for d in pending if d["type"] == "feature"]
            if feature_decisions:
                self._decision_logger.update_decision(feature_decisions[0]["id"], "denied")
                return {"success": True, "message": "❌ Feature denied."}
            return {"success": False, "message": "No pending feature proposals."}
        return {"success": False, "message": "Decision logger not available."}

    def _cmd_config(self, args: str = "") -> Dict:
        """Show current configuration (without secrets)."""
        from config.settings import get_config_summary
        config = get_config_summary()
        return {
            "success": True,
            "message": "⚙️ **Configuration**\n" + self._format_config(config),
            "data": config,
        }

    def _cmd_restart(self, args: str = "") -> Dict:
        """Restart the system."""
        if not self._engine:
            return {"success": False, "message": "Engine not available"}

        self._engine.stop()
        return {
            "success": True,
            "message": "🔄 System restart initiated. The system will restart on next cycle.",
        }

    def _cmd_push(self, args: str = "") -> Dict:
        """Force push to GitHub."""
        if not self._git_manager:
            return {"success": False, "message": "Git manager not available"}

        result = self._git_manager.sync_repo()
        if result["success"]:
            push_result = self._git_manager.push_to_github()
            return {
                "success": push_result["success"],
                "message": f"📤 {push_result['message']}",
            }
        return {"success": False, "message": f"Sync failed: {result.get('error', 'Unknown')}"}

    def _cmd_rollback(self, args: str = "") -> Dict:
        """Rollback last change."""
        if not self._git_manager:
            return {"success": False, "message": "Git manager not available"}

        commit_hash = args.strip() if args else None
        result = self._git_manager.rollback(commit_hash)
        return {
            "success": result["success"],
            "message": f"⏪ {result.get('message', result.get('error', 'Unknown'))}",
        }

    def _cmd_logs(self, args: str = "") -> Dict:
        """Show recent logs."""
        # Read recent lines from the log file or decisions log
        lines = []
        try:
            from config.settings import DECISIONS_LOG_FILE
            if DECISIONS_LOG_FILE.exists():
                with open(DECISIONS_LOG_FILE, "r") as f:
                    all_lines = f.readlines()
                    lines = all_lines[-20:]  # Last 20 lines
        except Exception as e:
            lines = [f"Error reading logs: {e}"]

        if not lines:
            lines = ["No logs available."]

        return {
            "success": True,
            "message": "📋 **Recent Logs**\n```\n" + "".join(lines) + "\n```",
        }

    def _cmd_help(self, args: str = "") -> Dict:
        """Show available commands."""
        commands = [
            ("!status", "Show current scan state, keys found, uptime"),
            ("!approve-pivot", "Approve strategy pivot proposal"),
            ("!deny-pivot", "Reject strategy pivot proposal"),
            ("!approve-feature", "Approve new feature addition"),
            ("!deny-feature", "Reject new feature addition"),
            ("!config", "Show current configuration (without secrets)"),
            ("!restart", "Restart the system"),
            ("!push", "Force push to GitHub"),
            ("!rollback [hash]", "Rollback last change (optional commit hash)"),
            ("!logs", "Show recent logs"),
            ("!help", "Show available commands"),
            ("!provide-key <KEY> <value>", "Provide API key via Discord"),
            ("!improve <description>", "Trigger self-improvement"),
            ("!scan", "Force immediate scan"),
        ]

        lines = ["🤖 **AlphaScan v0.5 - Available Commands**\n"]
        for cmd, desc in commands:
            lines.append(f"`{cmd}` - {desc}")

        return {
            "success": True,
            "message": "\n".join(lines),
        }

    def _cmd_provide_key(self, args: str = "") -> Dict:
        """Provide API key via Discord."""
        if not self._env_manager:
            return {"success": False, "message": "Environment manager not available"}

        result = self._env_manager.listen_for_key_response(f"!provide-key {args}")
        if result:
            return {
                "success": result["success"],
                "message": result.get("message", result.get("error", "Unknown")),
            }
        return {"success": False, "message": "Invalid key provision command."}

    def _cmd_improve(self, args: str = "") -> Dict:
        """Trigger self-improvement."""
        if not self._engine or not args:
            return {"success": False, "message": "Usage: !improve <description>"}

        try:
            success, msg = self._engine.improver.trigger_improvement(args)
            return {
                "success": success,
                "message": f"💡 {msg}",
            }
        except Exception as e:
            return {"success": False, "message": f"Improvement failed: {e}"}

    def _cmd_scan(self, args: str = "") -> Dict:
        """Force immediate scan."""
        if not self._engine:
            return {"success": False, "message": "Engine not available"}

        try:
            result = self._engine.force_scan()
            return {
                "success": True,
                "message": f"🔍 Scan completed. Found {result['keys_found']} keys.",
                "data": result,
            }
        except Exception as e:
            return {"success": False, "message": f"Scan failed: {e}"}

    def _format_status(self, status: Dict) -> str:
        """Format status dict for display."""
        lines = []
        for key, value in status.items():
            if isinstance(value, bool):
                value = "✅ Yes" if value else "❌ No"
            lines.append(f"  • {key.replace('_', ' ').title()}: {value}")
        return "\n".join(lines)

    def _format_config(self, config: Dict) -> str:
        """Format config dict for display."""
        lines = []
        for key, value in config.items():
            if isinstance(value, bool):
                value = "✅" if value else "❌"
            lines.append(f"  • {key.replace('_', ' ').title()}: {value}")
        return "\n".join(lines)
