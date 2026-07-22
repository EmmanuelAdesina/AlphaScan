"""
Auto-deploy module for APIS self-improvement system.
Handles writing generated code to disk and reloading modules.
"""
import os
import ast
import logging
import importlib
import sys
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from datetime import datetime

from config.settings import BASE_DIR

logger = logging.getLogger(__name__)


class AutoDeployer:
    """
    Handles deployment of generated code:
    - Validates code syntax
    - Writes code to files
    - Reloads modules dynamically
    - Tracks deployment history
    """

    # Allowed directories for code deployment
    ALLOWED_DIRS = {
        BASE_DIR / "scanners",
        BASE_DIR / "utils",
        BASE_DIR / "self_improve",
        BASE_DIR / "core",
        BASE_DIR / "api",
        BASE_DIR / "config",
    }

    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or BASE_DIR
        self.deployment_history: List[Dict] = []

    def validate_code(self, code: str, filename: str) -> Tuple[bool, str]:
        """
        Validate generated code for syntax and basic correctness.

        Args:
            code: Python source code string.
            filename: Target filename (for error messages).

        Returns:
            Tuple of (is_valid, error_message).
        """
        # 1. Syntax check using AST
        try:
            ast.parse(code, filename=filename)
        except SyntaxError as e:
            return False, f"Syntax error: {e}"

        # 2. Check for dangerous imports
        dangerous_imports = ["os.system", "subprocess.call", "subprocess.Popen",
                           "eval(", "exec(", "__import__"]
        for danger in dangerous_imports:
            if danger in code:
                return False, f"Potentially dangerous code: '{danger}' found"

        # 3. Check for basic structure (at least one class or function)
        try:
            tree = ast.parse(code)
            has_definition = False
            for node in ast.walk(tree):
                if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                    has_definition = True
                    break
            if not has_definition:
                return False, "No class or function definition found"
        except Exception as e:
            return False, f"AST analysis failed: {e}"

        return True, ""

    def deploy_code(self, code: str, filename: str,
                    module_path: Optional[str] = None) -> Tuple[bool, str]:
        """
        Deploy generated code to a file.

        Args:
            code: Python source code.
            filename: Target filename (e.g., "new_scanner.py").
            module_path: Module path for import (e.g., "scanners.new_scanner").

        Returns:
            Tuple of (success, message).
        """
        # Validate code first
        is_valid, error = self.validate_code(code, filename)
        if not is_valid:
            return False, f"Code validation failed: {error}"

        # Determine target path
        if module_path:
            # Convert module path to file path
            parts = module_path.split(".")
            target_dir = self.base_dir.joinpath(*parts[:-1])
            target_file = target_dir / f"{parts[-1]}.py"
        else:
            target_file = self.base_dir / filename

        # Ensure target directory exists
        target_file.parent.mkdir(parents=True, exist_ok=True)

        # Write code to file
        try:
            with open(target_file, "w") as f:
                f.write(code)
            logger.info(f"Code deployed to {target_file}")
        except Exception as e:
            return False, f"Failed to write file: {e}"

        # Record deployment
        self.deployment_history.append({
            "filename": str(target_file),
            "timestamp": datetime.utcnow().isoformat(),
            "status": "success",
        })

        return True, f"Code deployed to {target_file}"

    def reload_module(self, module_name: str) -> Tuple[bool, str]:
        """
        Reload a module after code changes.

        Args:
            module_name: Full module path (e.g., "scanners.new_scanner").

        Returns:
            Tuple of (success, message).
        """
        try:
            if module_name in sys.modules:
                importlib.reload(sys.modules[module_name])
                return True, f"Module '{module_name}' reloaded"
            else:
                importlib.import_module(module_name)
                return True, f"Module '{module_name}' imported"
        except Exception as e:
            return False, f"Failed to reload module '{module_name}': {e}"

    def update_pattern_file(self, pattern_name: str, pattern: str,
                           description: str, prefix: str = "[redacted]") -> Tuple[bool, str]:
        """
        Add a new pattern to the patterns.py file.

        Args:
            pattern_name: Name of the pattern.
            pattern: Regex pattern string.
            description: Description of the pattern.
            prefix: Prefix for masking.

        Returns:
            Tuple of (success, message).
        """
        patterns_file = self.base_dir / "config" / "patterns.py"

        try:
            with open(patterns_file, "r") as f:
                content = f.read()

            # Find the PATTERNS list and add new entry
            new_entry = (
                f'    ("{pattern_name}", r"{pattern}", '
                f'"{description}", "{prefix}"),\n'
            )

            # Insert before the closing bracket of PATTERNS list
            # Find the last entry before the closing ]
            lines = content.split("\n")
            insert_idx = None
            for i, line in enumerate(lines):
                if line.strip().startswith("("):
                    insert_idx = i + 1

            if insert_idx is not None:
                lines.insert(insert_idx, new_entry.rstrip())
                new_content = "\n".join(lines)
                with open(patterns_file, "w") as f:
                    f.write(new_content)
                return True, f"Pattern '{pattern_name}' added to patterns.py"
            else:
                return False, "Could not find insertion point in patterns.py"

        except Exception as e:
            return False, f"Failed to update patterns: {e}"

    def get_deployment_history(self) -> List[Dict]:
        """Get deployment history."""
        return self.deployment_history
