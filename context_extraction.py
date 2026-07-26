"""
AlphaScan Context Extraction Engine.

Detection must never rely only on regex. Incorporates:
  - filename
  - directory path
  - repository name
  - organization
  - variable names
  - JSON keys
  - YAML keys
  - comments
  - surrounding lines
  - language
  - file extension
  - git commit message
  - historical observations
  - parser confidence
  - AI classification

Context extraction gathers all available surrounding evidence
and passes it to the confidence scoring engine for multi-factor
assessment.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class ContextResult:
    """Complete context analysis for a potential secret."""
    variable_name: str = ""
    json_key: str = ""
    yaml_key: str = ""
    filename: str = ""
    directory_path: str = ""
    file_extension: str = ""
    language: str = ""
    surrounding_lines: List[str] = field(default_factory=list)
    comments_nearby: List[str] = field(default_factory=list)
    repository: str = ""
    organization: str = ""
    commit_message: str = ""
    parser_confidence: float = 0.0
    ai_classification: str = ""
    ai_confidence: float = 0.0
    historical_occurrences: int = 0

    # Derived context
    is_env_file: bool = False
    is_config_file: bool = False
    is_test_file: bool = False
    is_deployment_file: bool = False
    is_ci_file: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "variable_name": self.variable_name,
            "json_key": self.json_key,
            "yaml_key": self.yaml_key,
            "filename": self.filename,
            "directory_path": self.directory_path,
            "file_extension": self.file_extension,
            "language": self.language,
            "surrounding_lines": self.surrounding_lines[:5],
            "comments_nearby": self.comments_nearby[:3],
            "repository": self.repository,
            "organization": self.organization,
            "is_env_file": self.is_env_file,
            "is_config_file": self.is_config_file,
            "is_test_file": self.is_test_file,
            "parser_confidence": self.parser_confidence,
            "ai_confidence": self.ai_confidence,
            "historical_occurrences": self.historical_occurrences,
        }


# ── Language Detection ──────────────────────────────────────────────

_EXTENSION_LANGUAGE_MAP = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".jsx": "javascript",
    ".tsx": "typescript",
    ".rb": "ruby",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".kt": "kotlin",
    ".php": "php",
    ".cs": "csharp",
    ".cpp": "cpp",
    ".c": "c",
    ".swift": "swift",
    ".sh": "shell",
    ".bash": "shell",
    ".zsh": "shell",
    ".ps1": "powershell",
    ".sql": "sql",
    ".r": "r",
    ".lua": "lua",
    ".pl": "perl",
    ".scala": "scala",
    ".hs": "haskell",
    ".ex": "elixir",
    ".erl": "erlang",
    ".dart": "dart",
    ".vue": "vue",
    ".svelte": "svelte",
}

_FILE_LANGUAGE_MAP = {
    "Makefile": "make",
    "Dockerfile": "docker",
    "Jenkinsfile": "jenkins",
    "Vagrantfile": "ruby",
    "Gemfile": "ruby",
    "Rakefile": "ruby",
    "Pipfile": "python",
    "pyproject.toml": "python",
    "setup.py": "python",
    "requirements.txt": "python",
    "package.json": "javascript",
    "Cargo.toml": "rust",
    "go.mod": "go",
}


def detect_language(filename: str, file_extension: str = "") -> str:
    """Detect programming language from filename and extension."""
    if not file_extension:
        file_extension = Path(filename).suffix.lower() if filename else ""

    if file_extension in _EXTENSION_LANGUAGE_MAP:
        return _EXTENSION_LANGUAGE_MAP[file_extension]

    basename = Path(filename).name if filename else ""
    if basename in _FILE_LANGUAGE_MAP:
        return _FILE_LANGUAGE_MAP[basename]

    if basename.startswith(".env") or basename == ".env":
        return "env"
    if basename.endswith(".yml") or basename.endswith(".yaml"):
        return "yaml"
    if basename.endswith(".json"):
        return "json"
    if basename.endswith(".toml"):
        return "toml"
    if basename.endswith(".ini") or basename.endswith(".cfg"):
        return "ini"

    return "unknown"


# ── Variable/Key Name Extraction ────────────────────────────────────

def extract_variable_name(text: str, secret_position: int = 0) -> str:
    """
    Extract the variable name or JSON/YAML key associated with
    a secret found at a given position in text.
    """
    lines = text.split("\n")
    line_num = 0
    char_count = 0
    for i, line in enumerate(lines):
        if char_count + len(line) >= secret_position:
            line_num = i
            break
        char_count += len(line) + 1

    relevant_lines = lines[max(0, line_num - 3):line_num + 1]
    relevant_text = "\n".join(relevant_lines)

    assign_patterns = [
        re.compile(r'([A-Z_][A-Z0-9_]{2,})\s*=\s*[\"\']'),
        re.compile(r'([a-zA-Z_][a-zA-Z0-9_]{2,})\s*[:=]\s*[\"\']'),
    ]

    for pattern in assign_patterns:
        match = pattern.search(relevant_text)
        if match:
            return match.group(1)

    key_patterns = [
        re.compile(r'\"([a-zA-Z_][a-zA-Z0-9_-]{2,})\"\s*:\s*[\"\']'),
        re.compile(r'([a-zA-Z_][a-zA-Z0-9_-]{2,})\s*:\s*[\"\']'),
    ]

    for pattern in key_patterns:
        match = pattern.search(relevant_text)
        if match:
            return match.group(1)

    return ""


def extract_json_key(text: str, secret_position: int = 0) -> str:
    """Extract the JSON key associated with a secret value."""
    return extract_variable_name(text, secret_position)


def extract_yaml_key(text: str, secret_position: int = 0) -> str:
    """Extract the YAML key associated with a secret value."""
    return extract_variable_name(text, secret_position)


# ── Surrounding Lines ──────────────────────────────────────────────

def extract_surrounding_lines(
    text: str,
    secret_position: int = 0,
    context_lines: int = 5,
) -> List[str]:
    """Extract lines surrounding a detected secret for context analysis."""
    lines = text.split("\n")
    line_num = 0
    char_count = 0
    for i, line in enumerate(lines):
        if char_count + len(line) >= secret_position:
            line_num = i
            break
        char_count += len(line) + 1

    start = max(0, line_num - context_lines)
    end = min(len(lines), line_num + context_lines + 1)
    return lines[start:end]


# ── Comment Extraction ──────────────────────────────────────────────

def extract_nearby_comments(
    text: str,
    secret_position: int = 0,
    language: str = "",
) -> List[str]:
    """Extract comments near a detected secret."""
    surrounding = extract_surrounding_lines(text, secret_position, 3)

    comment_patterns = {
        "python": re.compile(r'#\s*(.*)'),
        "ruby": re.compile(r'#\s*(.*)'),
        "javascript": re.compile(r'//\s*(.*)'),
        "typescript": re.compile(r'//\s*(.*)'),
        "go": re.compile(r'//\s*(.*)'),
        "rust": re.compile(r'//\s*(.*)'),
        "java": re.compile(r'//\s*(.*)'),
        "shell": re.compile(r'#\s*(.*)'),
        "yaml": re.compile(r'#\s*(.*)'),
        "toml": re.compile(r'#\s*(.*)'),
        "ini": re.compile(r'[;#]\s*(.*)'),
        "default": re.compile(r'[;#]\s*(.*)|//\s*(.*)'),
    }

    pattern = comment_patterns.get(language, comment_patterns["default"])
    comments = []
    for line in surrounding:
        match = pattern.search(line)
        if match:
            comment_text = match.group(1) if match.group(1) else (match.group(2) or "")
            comment_text = comment_text.strip()
            if comment_text:
                comments.append(comment_text)

    return comments


# ── File Classification ─────────────────────────────────────────────

def classify_file(filename: str) -> Dict[str, bool]:
    """Classify a filename to determine its context type."""
    if not filename:
        return {
            "is_env_file": False,
            "is_config_file": False,
            "is_test_file": False,
            "is_deployment_file": False,
            "is_ci_file": False,
        }

    fn_lower = filename.lower()
    basename = Path(fn_lower).name

    is_env = (
        basename.startswith(".env") or
        basename == ".env" or
        basename.endswith(".env")
    )

    is_config = any(pattern in fn_lower for pattern in [
        "config", "settings", "configuration", "appsettings",
        "application", "default", "local", "production",
        "staging", "development", "secret", "credentials",
    ])

    is_test = any(pattern in fn_lower for pattern in [
        "test", "spec", "fixture", "mock", "stub", "sample",
        "example", "demo", "playground", "sandbox", "dummy",
    ])

    is_deployment = any(pattern in fn_lower for pattern in [
        "dockerfile", "docker-compose", "terraform", "ansible",
        "kubernetes", "k8s", "helm", "deploy", "nginx", "apache",
    ])

    is_ci = any(pattern in fn_lower for pattern in [
        "jenkinsfile", ".gitlab-ci", ".github/workflows",
        "travis", "circleci", "bitbucket-pipelines",
    ])

    return {
        "is_env_file": is_env,
        "is_config_file": is_config,
        "is_test_file": is_test,
        "is_deployment_file": is_deployment,
        "is_ci_file": is_ci,
    }


# ── Main Context Extraction ─────────────────────────────────────────

def extract_context(
    raw_value: str,
    source: str = "",
    repository: str = "",
    organization: str = "",
    filename: str = "",
    file_path: str = "",
    content: str = "",
    secret_position: int = 0,
    metadata: Dict[str, Any] = None,
) -> ContextResult:
    """
    Extract comprehensive context for a detected secret.

    Gathers all available surrounding evidence that will be
    passed to the confidence scoring engine for multi-factor
    assessment.
    """
    metadata = metadata or {}

    file_extension = Path(filename).suffix.lower() if filename else ""
    language = detect_language(filename, file_extension)

    variable_name = ""
    if content:
        pos = content.find(raw_value)
        if pos >= 0:
            secret_position = pos
        variable_name = extract_variable_name(content, secret_position)

    json_key = extract_json_key(content, secret_position) if content else ""
    yaml_key = extract_yaml_key(content, secret_position) if content else ""

    surrounding_lines = []
    if content:
        surrounding_lines = extract_surrounding_lines(content, secret_position)

    comments_nearby = []
    if content:
        comments_nearby = extract_nearby_comments(content, secret_position, language)

    file_flags = classify_file(filename)

    result = ContextResult(
        variable_name=variable_name,
        json_key=json_key,
        yaml_key=yaml_key,
        filename=filename,
        directory_path=file_path,
        file_extension=file_extension,
        language=language,
        surrounding_lines=surrounding_lines[:10],
        comments_nearby=comments_nearby[:5],
        repository=repository,
        organization=organization,
        is_env_file=file_flags["is_env_file"],
        is_config_file=file_flags["is_config_file"],
        is_test_file=file_flags["is_test_file"],
        is_deployment_file=file_flags["is_deployment_file"],
        is_ci_file=file_flags["is_ci_file"],
        parser_confidence=metadata.get("parser_confidence", 0.0),
        ai_classification=metadata.get("ai_classification", ""),
        ai_confidence=metadata.get("ai_confidence", 0.0),
        historical_occurrences=metadata.get("historical_occurrences", 0),
    )

    return result
