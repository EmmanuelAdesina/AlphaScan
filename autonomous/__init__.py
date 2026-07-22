"""
AlphaScan v0.5 - Autonomous System.

Provides true autonomy capabilities:
- Environment management (auto-request API keys)
- Strategy analysis (ROI-based pivoting)
- Git management (auto-push to GitHub)
- Command handling (Discord commands)
- Module registry (dynamic module management)
- Decision logging (audit trail of all autonomous decisions)
"""
from autonomous.env_manager import EnvManager
from autonomous.strategy_analyzer import StrategyAnalyzer
from autonomous.git_manager import GitManager
from autonomous.command_handler import CommandHandler
from autonomous.module_registry import ModuleRegistry
from autonomous.decision_logger import DecisionLogger

__all__ = [
    "EnvManager",
    "StrategyAnalyzer",
    "GitManager",
    "CommandHandler",
    "ModuleRegistry",
    "DecisionLogger",
]
