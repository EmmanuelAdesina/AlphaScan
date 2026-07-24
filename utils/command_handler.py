"""
Discord Command Handler for AlphaScan v0.5 CEO Mode.
Processes Discord commands for controlling AlphaScan through the CEO.

Commands:
    !status - Show current state
    !focus [type] - Focus on specific key type
    !stop [scanner] - Stop a scanner
    !start [scanner] - Start a scanner
    !write [service] - Write new scanner
    !retry - Retry last failed scanner
    !reset - Reset memory
    !ask [question] - Ask CEO a question
    !help - Show commands
"""
import logging
from typing import Dict, Optional, List, Callable, Any

logger = logging.getLogger(__name__)


class DiscordCommandHandler:
    """
    Handles Discord commands for AlphaScan v0.5 CEO Mode.
    Delegates to the CEO controller, knowledge base, and executor.
    """

    def __init__(self, engine=None, ceo_controller=None, knowledge_base=None,
                 decision_executor=None, notifier=None, scanner_manager=None):
        self._engine = engine
        self._ceo = ceo_controller
        self._kb = knowledge_base
        self._executor = decision_executor
        self._notifier = notifier
        self._scanner_manager = scanner_manager
        self._commands: Dict[str, Callable] = {}
        self._register_commands()

    def _register_commands(self) -> None:
        """Register all available commands."""
        self._commands = {
            "!status": self._cmd_status,
            "!focus": self._cmd_focus,
            "!stop": self._cmd_stop,
            "!start": self._cmd_start,
            "!write": self._cmd_write,
            "!retry": self._cmd_retry,
            "!reset": self._cmd_reset,
            "!ask": self._cmd_ask,
            "!help": self._cmd_help,
        }

    def process_command(self, command: str) -> Dict:
        """
        Process a Discord command.

        Args:
            command: Command string (e.g., "!status", "!stop pastebin").

        Returns:
            Dict with 'success', 'message', and optional 'data'.
        """
        if not command or not command.startswith("!"):
            return {"success": False,
                    "message": "Invalid command. Use `!help` for available commands."}

        # Parse command and arguments
        parts = command.strip().split(None, 1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        # Find matching command (exact match, then prefix match)
        handler = self._commands.get(cmd)
        if handler is None:
            # Check if any registered command is a prefix of this cmd
            for registered_cmd in sorted(self._commands.keys(), key=len, reverse=True):
                if cmd.startswith(registered_cmd):
                    handler = self._commands[registered_cmd]
                    break

        if handler is None:
            return {"success": False,
                    "message": f"Unknown command: `{cmd}`. Use `!help` for available commands."}

        try:
            result = handler(args)
            # Log the command
            if self._kb:
                msg = result.get("message", "")
                self._kb.record_user_command(command, msg)
            return result
        except Exception as e:
            logger.error(f"Command '{cmd}' failed: {e}")
            return {"success": False, "message": f"Command failed: {e}"}

    def _cmd_status(self, args: str = "") -> Dict:
        """Show current state of AlphaScan."""
        status_parts = []

        if self._engine:
            status = self._engine.get_status()
            status_parts.append("🤖 **AlphaScan v0.5 - CEO Mode**\n")
            status_parts.append(f"• Running: {'✅ Yes' if status.get('running') else '❌ No'}")
            status_parts.append(f"• Cycle: #{status.get('cycle', 0)}")
            status_parts.append(f"• Total Keys Found: {status.get('total_keys_found', 0)}")
            status_parts.append(f"• Total Scans: {status.get('total_scans', 0)}")
            status_parts.append(f"• Scan Interval: {status.get('scan_interval', 300)}s")

            if status.get("last_scan_time"):
                status_parts.append(f"• Last Scan: {status['last_scan_time']}")
            if status.get("last_scan_duration"):
                status_parts.append(f"• Last Duration: {status['last_scan_duration']:.1f}s")
            if status.get("discovered_key_types"):
                status_parts.append(f"• Key Types: {', '.join(status['discovered_key_types'])}")
            if status.get("enabled_scanners"):
                status_parts.append(f"• Active Scanners: {', '.join(status['enabled_scanners'])}")
        else:
            status_parts.append("⚠️ Engine not available.")

        if self._ceo:
            ceo_status = self._ceo.get_status()
            status_parts.append("")
            status_parts.append("**🧠 CEO Status:**")
            status_parts.append(f"• Cycles Without Keys: {ceo_status.get('cycles_without_keys', 0)}")
            status_parts.append(f"• Pending Questions: {ceo_status.get('pending_questions', 0)}")
            if ceo_status.get("current_pending"):
                pq = ceo_status["current_pending"]
                status_parts.append(f"• Current Question: {pq.get('question', 'None')}")

        return {"success": True, "message": "\n".join(status_parts)}

    def _cmd_focus(self, args: str = "") -> Dict:
        """Focus on a specific key type."""
        if not args:
            return {"success": False,
                    "message": "Usage: `!focus [key_type]` - Focus scanners on a specific key type."}

        # Record the focus decision
        if self._kb:
            self._kb.record_ceo_decision(
                decision=f"Focus on key type: {args}",
                reason="User command",
                outcome="executing",
            )

        return {"success": True,
                "message": f"🎯 Focus set to: **{args}**. Adjusting scanner priorities..."}

    def _cmd_stop(self, args: str = "") -> Dict:
        """Stop a scanner."""
        if not args:
            return {"success": False,
                    "message": "Usage: `!stop [scanner_name]` - Stop a running scanner."}

        scanner_name = args.strip().lower()

        # Disable via scanner manager
        if self._scanner_manager:
            self._scanner_manager.disable_scanner(scanner_name)

        # Record in knowledge base
        if self._kb:
            self._kb.record_ceo_decision(
                decision=f"Stopped scanner: {scanner_name}",
                reason=f"User command: !stop {scanner_name}",
                outcome="completed",
            )

        return {"success": True,
                "message": f"🛑 Scanner **{scanner_name}** has been stopped."}

    def _cmd_start(self, args: str = "") -> Dict:
        """Start a scanner."""
        if not args:
            return {"success": False,
                    "message": "Usage: `!start [scanner_name]` - Start a scanner."}

        scanner_name = args.strip().lower()

        # Enable via scanner manager
        if self._scanner_manager:
            self._scanner_manager.enable_scanner(scanner_name)

        # Record in knowledge base
        if self._kb:
            self._kb.record_ceo_decision(
                decision=f"Started scanner: {scanner_name}",
                reason=f"User command: !start {scanner_name}",
                outcome="completed",
            )

        return {"success": True,
                "message": f"▶️ Scanner **{scanner_name}** has been started."}

    def _cmd_write(self, args: str = "") -> Dict:
        """Write a new scanner for a service."""
        if not args:
            return {"success": False,
                    "message": "Usage: `!write [service_name]` - Generate a new scanner for a service."}

        service = args.strip().lower()

        # Check if already exists
        if self._kb:
            if self._kb.scanner_exists(service):
                return {"success": False,
                        "message": f"⚠️ Scanner for **{service}** already exists."}
            if self._kb.scanner_already_tried(service):
                return {"success": False,
                        "message": f"⚠️ Scanner for **{service}** was already attempted."}

        # Delegate to the engine's improver if available
        if self._engine:
            try:
                description = f"Add a scanner for {service}"
                success, msg = self._engine.improver.trigger_improvement(description)

                if success:
                    return {"success": True,
                            "message": f"✍️ Generated scanner for **{service}**. {msg}"}
                else:
                    return {"success": False,
                            "message": f"❌ Failed to generate scanner for **{service}**: {msg}"}
            except Exception as e:
                logger.error(f"Failed to generate scanner: {e}")
                return {"success": False,
                        "message": f"❌ Error generating scanner: {e}"}
        else:
            return {"success": False,
                    "message": "Engine not available for code generation."}

    def _cmd_retry(self, args: str = "") -> Dict:
        """Retry the last failed scanner."""
        if not self._kb:
            return {"success": False, "message": "Knowledge base not available."}

        failed = self._kb._data["scanners"]["failed"]
        if not failed:
            return {"success": True, "message": "No failed scanners to retry."}

        last_failed = failed[-1]
        return self._cmd_write(last_failed)

    def _cmd_reset(self, args: str = "") -> Dict:
        """Reset CEO memory."""
        if not self._kb:
            return {"success": False, "message": "Knowledge base not available."}

        self._kb.reset()
        return {"success": True, "message": "🔄 CEO memory has been reset. Knowledge base cleared."}

    def _cmd_ask(self, args: str = "") -> Dict:
        """Ask the CEO a question."""
        if not args:
            return {"success": False,
                    "message": "Usage: `!ask [your question]` - Ask the CEO a question."}

        # If there's a pending question from CEO, treat this as a response
        if self._ceo:
            pending = self._ceo.get_pending_question()
            if pending:
                # Treat as response to pending question
                result = self._ceo.handle_user_response(pending["id"], args)
                if self._executor:
                    exec_result = self._executor.execute(result)
                    return {
                        "success": exec_result["success"],
                        "message": f"💬 {exec_result.get('message', result.get('message', ''))}",
                    }
                else:
                    return {"success": True,
                            "message": f"💬 {result.get('message', 'Response processed.')}"}

        # If no pending question, provide analysis
        if self._ceo and self._kb:
            state = self._kb.get_full_state()
            return {
                "success": True,
                "message": (
                    f"🤔 **CEO Analysis on: '{args}'**\n\n"
                    f"Current Status:\n"
                    f"• Total scans run: {state.get('total_scans_run', 0)}\n"
                    f"• Total keys found: {state.get('total_keys_found', 0)}\n"
                    f"• Active scanners: {len(state.get('existing_scanners', []))}\n"
                    f"• Tried scanners: {len(state.get('tried_scanners', []))}\n"
                    f"• Failed scanners: {len(state.get('failed_scanners', []))}\n"
                    f"• Cycles without keys: {state.get('cycles_without_keys', 0)}\n"
                    f"• Total decisions made: {len(state.get('recent_decisions', []))}"
                ),
            }

        return {"success": True, "message": f"🤔 Received your question: '{args}'"}

    def _cmd_help(self, args: str = "") -> Dict:
        """Show available commands."""
        commands = [
            ("!status", "Show current scan state and CEO status"),
            ("!focus [type]", "Focus on a specific key type"),
            ("!stop [scanner]", "Stop a scanner"),
            ("!start [scanner]", "Start a scanner"),
            ("!write [service]", "Generate a new scanner for a service"),
            ("!retry", "Retry the last failed scanner"),
            ("!reset", "Reset CEO memory"),
            ("!ask [question]", "Ask the CEO a question"),
            ("!help", "Show this help message"),
        ]

        lines = ["🤖 **AlphaScan v0.5 CEO Mode - Commands**\n"]
        for cmd, desc in commands:
            lines.append(f"`{cmd}` - {desc}")

        lines.append("")
        lines.append("The CEO will automatically ask questions when stuck. "
                      "Respond with the option text to provide input.")

        return {"success": True, "message": "\n".join(lines)}