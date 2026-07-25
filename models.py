"""
AlphaScan unified models.
Defines the Finding dataclass used across all scanners, parsers, and validators.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class Finding:
    """
    Unified exposure finding model.

    All scanners must return Finding objects. The pipeline:
        Scanner -> Finding -> Parser -> Validator -> Reporter
    """
    source: str                      # e.g. "censys", "github", "pastebin"
    target: str                      # e.g. IP, URL, repo path
    content: str                     # raw exposed content
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")

    # Derived fields (optional, set during processing)
    extracted_secrets: List[Dict[str, Any]] = field(default_factory=list)
    validation_results: List[Dict[str, Any]] = field(default_factory=list)
    content_hash: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.content_hash:
            self.content_hash = hashlib.sha256(
                self.content.encode("utf-8", errors="replace")
            ).hexdigest()[:16]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "content": self.content,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
            "content_hash": self.content_hash,
            "extracted_secrets": self.extracted_secrets,
            "validation_results": self.validation_results,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Finding":
        return cls(
            source=data["source"],
            target=data["target"],
            content=data["content"],
            metadata=data.get("metadata", {}),
            timestamp=data.get("timestamp", datetime.utcnow().isoformat() + "Z"),
            extracted_secrets=data.get("extracted_secrets", []),
            validation_results=data.get("validation_results", []),
            content_hash=data.get("content_hash"),
        )