"""
Module Registry for AlphaScan v0.5.

Dynamically discovers, loads, and manages scanner modules.
"""
import logging
import importlib
import os
from typing import Dict, List, Optional, Type
from pathlib import Path
from scanners.base_scanner import BaseScanner

logger = logging.getLogger(__name__)


class ModuleRegistry:
    """
    Discovers and manages scanner modules dynamically.

    - Auto-discovers scanner modules in the scanners/ directory
    - Loads modules dynamically
    - Tracks module metadata
    - Supports hot-reloading of modules
    """

    def __init__(self, scanners_dir: Optional[Path] = None):
        self._scanners_dir = scanners_dir or Path(__file__).resolve().parent.parent / "scanners"
        self._modules: Dict[str, Dict] = {}
        self._discover_modules()

    def _discover_modules(self) -> None:
        """Discover all scanner modules in the scanners directory."""
        if not self._scanners_dir.exists():
            logger.warning(f"Scanners directory not found: {self._scanners_dir}")
            return

        for py_file in self._scanners_dir.glob("*.py"):
            if py_file.name.startswith("_") or py_file.name == "base_scanner.py":
                continue

            module_name = py_file.stem
            self._modules[module_name] = {
                "name": module_name,
                "path": str(py_file),
                "loaded": False,
                "instance": None,
                "classes": [],
            }

        logger.info(f"Discovered {len(self._modules)} scanner modules: {list(self._modules.keys())}")

    def get_available_modules(self) -> List[str]:
        """Get list of available module names."""
        return list(self._modules.keys())

    def load_module(self, module_name: str) -> Optional[object]:
        """
        Load a module by name.

        Args:
            module_name: Name of the module (without .py extension).

        Returns:
            The loaded module object, or None if loading failed.
        """
        if module_name not in self._modules:
            logger.warning(f"Module not found: {module_name}")
            return None

        try:
            module = importlib.import_module(f"scanners.{module_name}")
            self._modules[module_name]["loaded"] = True

            # Find BaseScanner subclasses in the module
            classes = []
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and
                    issubclass(attr, BaseScanner) and
                    attr is not BaseScanner):
                    classes.append(attr_name)

            self._modules[module_name]["classes"] = classes

            logger.info(f"Loaded module: {module_name} (classes: {classes})")
            return module

        except Exception as e:
            logger.error(f"Failed to load module {module_name}: {e}")
            return None

    def instantiate_scanner(self, module_name: str, class_name: Optional[str] = None) -> Optional[BaseScanner]:
        """
        Instantiate a scanner from a module.

        Args:
            module_name: Name of the module.
            class_name: Name of the class to instantiate. If None, uses the first BaseScanner subclass.

        Returns:
            Scanner instance, or None if instantiation failed.
        """
        module = self.load_module(module_name)
        if module is None:
            return None

        if class_name is None:
            # Find the first BaseScanner subclass
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and
                    issubclass(attr, BaseScanner) and
                    attr is not BaseScanner):
                    class_name = attr_name
                    break

        if class_name is None:
            logger.warning(f"No BaseScanner subclass found in module: {module_name}")
            return None

        try:
            scanner_class = getattr(module, class_name)
            instance = scanner_class()
            self._modules[module_name]["instance"] = instance
            return instance
        except Exception as e:
            logger.error(f"Failed to instantiate scanner {class_name} from {module_name}: {e}")
            return None

    def reload_module(self, module_name: str) -> bool:
        """Reload a module after code changes."""
        if module_name not in self._modules:
            return False

        try:
            module = importlib.import_module(f"scanners.{module_name}")
            importlib.reload(module)
            self._modules[module_name]["loaded"] = True
            logger.info(f"Reloaded module: {module_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to reload module {module_name}: {e}")
            return False

    def get_module_info(self, module_name: str) -> Optional[Dict]:
        """Get information about a module."""
        return self._modules.get(module_name)

    def get_all_module_info(self) -> List[Dict]:
        """Get information about all modules."""
        return list(self._modules.values())

    def get_scanner_classes(self, module_name: str) -> List[str]:
        """Get list of scanner class names in a module."""
        module = self.load_module(module_name)
        if module is None:
            return []
        return self._modules.get(module_name, {}).get("classes", [])
