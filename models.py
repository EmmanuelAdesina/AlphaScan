"""
AlphaScan unified models.

Defines both the legacy Finding dataclass (backward compatible) and the
new canonical Secret model used by the intelligence pipeline.

The legacy Finding model is preserved for existing scanners, parsers,
and validators. The Secret model is the new canonical representation
that flows through the layered intelligence pipeline:

  Collectors → Normalization → Context Extraction → Secret Detection
  → Secret Classification → Confidence Scoring → Deduplication
  → Provider Verification → Risk Classification → Storage → Dashboard
"""
from __future__ import annotations

import enum
import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union


# ── Validation Levels ──────────────────────────────────────────────

class ValidationLevel(str, enum.Enum):
    """Progressive validation levels for secrets.

    Each level indicates what has been verified and provides
    an explanation of the verification performed.
    """
    NONE = "none"
    FORMAT = "format"
    STRUCTURE = "structure"
    HEURISTIC = "heuristic"
    PROVIDER = "provider"
    ACTIVE = "active"

    @property
    def description(self) -> str:
        descriptions = {
            ValidationLevel.NONE: "No validation performed. Secret detected but unverified.",
            ValidationLevel.FORMAT: "Format validated: matches expected pattern/regex for this secret type.",
            ValidationLevel.STRUCTURE: "Structure validated: internal composition (length, charset, segments) verified.",
            ValidationLevel.HEURISTIC: "Heuristic validated: context, entropy, and surrounding evidence analyzed.",
            ValidationLevel.PROVIDER: "Provider validated: credential confirmed recognized by the issuing provider.",
            ValidationLevel.ACTIVE: "Active validated: credential confirmed currently active and functional.",
        }
        return descriptions.get(self, "Unknown validation level.")

    @property
    def rank(self) -> int:
        return {
            ValidationLevel.NONE: 0,
            ValidationLevel.FORMAT: 1,
            ValidationLevel.STRUCTURE: 2,
            ValidationLevel.HEURISTIC: 3,
            ValidationLevel.PROVIDER: 4,
            ValidationLevel.ACTIVE: 5,
        }[self]


# ── Verification Status ────────────────────────────────────────────

class VerificationStatus(str, enum.Enum):
    """Provider verification result status.

    Never collapses verification into a single boolean.
    Each status has distinct meaning and evidence requirements.
    """
    UNKNOWN = "unknown"
    UNSUPPORTED = "unsupported"
    VALID_FORMAT = "valid_format"
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    DISABLED = "disabled"
    INSUFFICIENT_SCOPE = "insufficient_scope"
    RATE_LIMITED = "rate_limited"
    UNREACHABLE = "unreachable"
    INVALID = "invalid"

    @property
    def badge(self) -> str:
        badges = {
            VerificationStatus.UNKNOWN: "❓ Unknown",
            VerificationStatus.UNSUPPORTED: "🚫 Unsupported",
            VerificationStatus.VALID_FORMAT: "🟡 Format Valid",
            VerificationStatus.ACTIVE: "✅ Currently Active",
            VerificationStatus.EXPIRED: "⏰ Expired",
            VerificationStatus.REVOKED: "🔒 Revoked",
            VerificationStatus.DISABLED: "⛔ Disabled",
            VerificationStatus.INSUFFICIENT_SCOPE: "⚠️ Insufficient Scope",
            VerificationStatus.RATE_LIMITED: "⏳ Rate Limited",
            VerificationStatus.UNREACHABLE: "🔌 Unreachable",
            VerificationStatus.INVALID: "❌ Invalid",
        }
        return badges.get(self, "❓ Unknown")

    @property
    def display_priority(self) -> int:
        return {
            VerificationStatus.ACTIVE: 0,
            VerificationStatus.VALID_FORMAT: 1,
            VerificationStatus.EXPIRED: 2,
            VerificationStatus.REVOKED: 3,
            VerificationStatus.DISABLED: 4,
            VerificationStatus.INSUFFICIENT_SCOPE: 5,
            VerificationStatus.RATE_LIMITED: 6,
            VerificationStatus.UNREACHABLE: 7,
            VerificationStatus.INVALID: 8,
            VerificationStatus.UNSUPPORTED: 9,
            VerificationStatus.UNKNOWN: 10,
        }[self]


# ── Confidence Categories ──────────────────────────────────────────

class ConfidenceCategory(str, enum.Enum):
    """Human-readable confidence bands."""
    CRITICAL = "critical"     # 90-100
    HIGH = "high"             # 70-89
    MEDIUM = "medium"         # 40-69
    LOW = "low"               # 20-39
    UNLIKELY = "unlikely"     # 0-19

    @classmethod
    def from_score(cls, score: float) -> "ConfidenceCategory":
        if score >= 90:
            return cls.CRITICAL
        if score >= 70:
            return cls.HIGH
        if score >= 40:
            return cls.MEDIUM
        if score >= 20:
            return cls.LOW
        return cls.UNLIKELY


# ── Secret History Entry ───────────────────────────────────────────

@dataclass
class HistoryEntry:
    """A single event in the lifecycle of a secret."""
    timestamp: str
    event: str
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "event": self.event,
            "details": self.details,
        }


# ── Canonical Secret Model ────────────────────────────────────────

@dataclass
class Secret:
    """
    Canonical Secret Intelligence model.

    This is the authoritative representation of a detected secret,
    enriched through the full intelligence pipeline. Every field has
    a clear purpose and evidence trail.

    Pipeline stages that populate fields:
      Collectors:           source, collector, finding_target, repository, branch, commit
      Normalization:        file, line_number, discovered_at
      Context Extraction:   organization, metadata (context fields)
      Secret Detection:     secret_family, secret_type, provider, raw_value
      Secret Classification: refined secret_family, secret_type, provider
      Confidence Scoring:   confidence_score, metadata (confidence breakdown)
      Deduplication:        id (stable), last_seen, history, metadata (occurrences)
      Provider Verification: validation_level, provider_status, verification_status,
                            verification_reason, verified_at, metadata (provider response)
      Risk Classification:  metadata (risk assessment)
    """
    # ── Identity ───────────────────────────────────────────────────
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # ── Source & Location ──────────────────────────────────────────
    source: str = ""                        # e.g. "censys", "github", "pastebin"
    finding_target: str = ""                # IP, URL, repo path — original scan target
    repository: str = ""                    # e.g. "org/repo-name"
    organization: str = ""                  # e.g. "mycompany"
    branch: str = ""                        # e.g. "main"
    commit: str = ""                        # commit SHA
    file: str = ""                          # e.g. "config/settings.py"
    line_number: Optional[int] = None       # line where secret was found

    # ── Scanner & Collector ────────────────────────────────────────
    scanner: str = ""                       # scanner module name
    collector: str = ""                     # collector module name

    # ── Temporal ───────────────────────────────────────────────────
    discovered_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    last_seen: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    # ── Classification ─────────────────────────────────────────────
    secret_family: str = ""                 # e.g. "github_pat", "aws_key", "openai_api"
    secret_type: str = ""                   # e.g. "GitHub Fine-Grained PAT", "AWS Access Key"
    provider: str = ""                      # e.g. "github", "aws", "openai"

    # ── Confidence & Validation ────────────────────────────────────
    confidence_score: float = 0.0           # 0-100
    validation_level: ValidationLevel = ValidationLevel.NONE
    provider_status: Optional[str] = None   # raw provider response status
    verification_status: VerificationStatus = VerificationStatus.UNKNOWN
    verification_reason: str = ""           # human-readable explanation
    verified_at: Optional[str] = None       # when provider verification occurred

    # ── Value ──────────────────────────────────────────────────────
    masked_value: str = ""                  # safe for display/export
    raw_value: str = ""                     # full secret — controlled access only

    # ── Extended ───────────────────────────────────────────────────
    metadata: Dict[str, Any] = field(default_factory=dict)
    history: List[HistoryEntry] = field(default_factory=list)

    def __post_init__(self) -> None:
        # Compute masked_value from raw_value if not explicitly set
        if self.raw_value and not self.masked_value:
            self.masked_value = self._mask(self.raw_value, self.secret_type)

    @staticmethod
    def _mask(value: str, secret_type: str = "") -> str:
        """Mask a secret value for safe display.

        Shows enough context to identify the type/prefix while
        hiding the majority of the value.
        """
        if not value:
            return "[empty]"
        if len(value) <= 10:
            return value[:4] + "..."
        # Private keys — show type only
        if secret_type and any(kw in secret_type.lower() for kw in
                               ("rsa", "ssh", "dsa", "ec", "openssh", "private key", "pgp")):
            return f"[{secret_type}:{len(value)}_chars]"
        # Crypto private keys — show prefix + last 4
        if any(kw in secret_type.lower() for kw in ("ethereum", "bitcoin", "solana")):
            return value[:6] + "..." + value[-4:]
        # API keys — show prefix + last 4
        if len(value) > 16:
            return value[:8] + "..." + value[-4:]
        return value[:6] + "..."

    def compute_stable_id(self) -> str:
        """Compute a deterministic ID for deduplication.

        Two secrets with the same (secret_type, raw_value)
        should produce the same stable ID for merging,
        regardless of source (the same API key can appear
        in multiple scanners).
        """
        composite = f"{self.secret_type}|{self.raw_value}"
        return hashlib.sha256(composite.encode("utf-8", errors="replace")).hexdigest()[:16]

    def to_dict(self, include_raw: bool = False) -> Dict[str, Any]:
        """Serialize to dict. Raw values only included when explicitly authorized."""
        d = {
            "id": self.id,
            "source": self.source,
            "finding_target": self.finding_target,
            "repository": self.repository,
            "organization": self.organization,
            "branch": self.branch,
            "commit": self.commit,
            "file": self.file,
            "line_number": self.line_number,
            "scanner": self.scanner,
            "collector": self.collector,
            "discovered_at": self.discovered_at,
            "last_seen": self.last_seen,
            "secret_family": self.secret_family,
            "secret_type": self.secret_type,
            "provider": self.provider,
            "confidence_score": self.confidence_score,
            "confidence_category": ConfidenceCategory.from_score(self.confidence_score).value,
            "validation_level": self.validation_level.value,
            "validation_level_description": self.validation_level.description,
            "provider_status": self.provider_status,
            "verification_status": self.verification_status.value,
            "verification_badge": self.verification_status.badge,
            "verification_reason": self.verification_reason,
            "verified_at": self.verified_at,
            "masked_value": self.masked_value,
            "entropy": self.metadata.get("entropy", 0.0),
            "metadata": self.metadata,
            "history": [h.to_dict() for h in self.history],
        }
        if include_raw:
            d["raw_value"] = self.raw_value
        return d

    def to_export_dict(self) -> Dict[str, Any]:
        """Minimal dict for paginated API responses and exports."""
        return {
            "id": self.id,
            "source": self.source,
            "repository": self.repository,
            "file": self.file,
            "finding_target": self.finding_target,
            "secret_type": self.secret_type,
            "confidence": self.confidence_score,
            "confidence_category": ConfidenceCategory.from_score(self.confidence_score).value,
            "validation_level": self.validation_level.value,
            "verified": self.verification_status.value,
            "verification_badge": self.verification_status.badge,
            "masked_value": self.masked_value,
            "entropy": self.metadata.get("entropy", 0.0),
            "discovered_at": self.discovered_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Secret":
        """Deserialize from dict."""
        vl = data.get("validation_level", "none")
        vs = data.get("verification_status", "unknown")
        history_data = data.get("history", [])
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            source=data.get("source", ""),
            finding_target=data.get("finding_target", ""),
            repository=data.get("repository", ""),
            organization=data.get("organization", ""),
            branch=data.get("branch", ""),
            commit=data.get("commit", ""),
            file=data.get("file", ""),
            line_number=data.get("line_number"),
            scanner=data.get("scanner", ""),
            collector=data.get("collector", ""),
            discovered_at=data.get("discovered_at", datetime.now(timezone.utc).isoformat()),
            last_seen=data.get("last_seen", datetime.now(timezone.utc).isoformat()),
            secret_family=data.get("secret_family", ""),
            secret_type=data.get("secret_type", ""),
            provider=data.get("provider", ""),
            confidence_score=data.get("confidence_score", 0.0),
            validation_level=ValidationLevel(vl) if isinstance(vl, str) else vl,
            provider_status=data.get("provider_status"),
            verification_status=VerificationStatus(vs) if isinstance(vs, str) else vs,
            verification_reason=data.get("verification_reason", ""),
            verified_at=data.get("verified_at"),
            masked_value=data.get("masked_value", ""),
            raw_value=data.get("raw_value", ""),
            metadata=data.get("metadata", {}),
            history=[
                HistoryEntry(
                    timestamp=h.get("timestamp", ""),
                    event=h.get("event", ""),
                    details=h.get("details", {}),
                )
                for h in history_data
            ] if isinstance(history_data, list) else [],
        )

    @classmethod
    def from_finding(cls, finding: "Finding") -> "Secret":
        """Convert a legacy Finding to a new Secret model.

        Preserves backward compatibility: existing scanners continue
        producing Findings, which are upgraded to Secrets by the pipeline.
        """
        metadata = dict(finding.metadata)
        # Extract secrets from extracted_secrets if present
        extracted = finding.extracted_secrets or []
        validation = finding.validation_results or []

        # Use first extracted secret as primary classification
        secret_type = ""
        raw_value = ""
        provider = ""
        secret_family = ""
        confidence = 0.0

        if extracted:
            first = extracted[0]
            raw_value = first.get("value", "")
            secret_type = first.get("type", "")
            confidence = 50.0  # default baseline for legacy findings
            # Map legacy type to family/provider
            family_info = _map_legacy_type(secret_type)
            secret_family = family_info["family"]
            provider = family_info["provider"]
            secret_type = family_info["display_type"]

        if validation:
            first_val = validation[0]
            confidence += 20.0 if first_val.get("format_valid") else -30.0
            confidence += 10.0 if first_val.get("valid") else -20.0

        confidence = max(0.0, min(100.0, confidence))

        # Determine validation level from validation results
        vl = ValidationLevel.NONE
        if validation:
            fv = validation[0]
            if fv.get("valid"):
                if fv.get("wallet_has_funds"):
                    vl = ValidationLevel.ACTIVE
                elif fv.get("format_valid"):
                    vl = ValidationLevel.FORMAT
                else:
                    vl = ValidationLevel.HEURISTIC
            elif fv.get("format_valid"):
                vl = ValidationLevel.FORMAT

        secret = cls(
            source=finding.source,
            finding_target=finding.target,
            repository=finding.metadata.get("repo", ""),
            file=finding.metadata.get("path", ""),
            scanner=finding.source,
            discovered_at=finding.timestamp,
            secret_family=secret_family,
            secret_type=secret_type,
            provider=provider,
            confidence_score=confidence,
            validation_level=vl,
            raw_value=raw_value,
            metadata=metadata,
        )
        secret.id = finding.content_hash or secret.compute_stable_id()
        return secret


# ── Legacy Finding (backward compatible) ───────────────────────────

@dataclass
class Finding:
    """
    Unified exposure finding model (LEGACY — preserved for backward compatibility).

    All scanners must return Finding objects. The pipeline:
        Scanner -> Finding -> Parser -> Validator -> Reporter

    The intelligence pipeline converts Findings to Secrets:
        Finding.from_finding() -> Secret
    """
    source: str
    target: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat() + "Z")
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
            timestamp=data.get("timestamp", datetime.now(timezone.utc).isoformat() + "Z"),
            extracted_secrets=data.get("extracted_secrets", []),
            validation_results=data.get("validation_results", []),
            content_hash=data.get("content_hash"),
        )


# ── Legacy type mapping ────────────────────────────────────────────

_FAMILY_MAP = {
    "ssh_rsa": {"family": "ssh_key", "provider": "ssh", "display_type": "RSA Private Key"},
    "ssh_openssh": {"family": "ssh_key", "provider": "ssh", "display_type": "OpenSSH Private Key"},
    "ssh_ec": {"family": "ssh_key", "provider": "ssh", "display_type": "EC Private Key"},
    "ssh_dsa": {"family": "ssh_key", "provider": "ssh", "display_type": "DSA Private Key"},
    "ssh_pkcs8": {"family": "ssh_key", "provider": "ssh", "display_type": "PKCS8 Private Key"},
    "eth_private_key": {"family": "ethereum_key", "provider": "ethereum", "display_type": "Ethereum Private Key"},
    "btc_wif": {"family": "bitcoin_key", "provider": "bitcoin", "display_type": "Bitcoin WIF"},
    "openai": {"family": "openai_api", "provider": "openai", "display_type": "OpenAI API Key"},
    "anthropic": {"family": "anthropic_api", "provider": "anthropic", "display_type": "Anthropic API Key"},
    "aws": {"family": "aws_key", "provider": "aws", "display_type": "AWS Access Key"},
    "google": {"family": "google_api", "provider": "google", "display_type": "Google AI API Key"},
    "github": {"family": "github_pat", "provider": "github", "display_type": "GitHub Classic PAT"},
    "gitlab": {"family": "gitlab_pat", "provider": "gitlab", "display_type": "GitLab PAT"},
    "stripe_live": {"family": "stripe_key", "provider": "stripe", "display_type": "Stripe Secret Key"},
    "stripe_test": {"family": "stripe_key", "provider": "stripe", "display_type": "Stripe Publishable Key"},
    "sendgrid": {"family": "sendgrid_api", "provider": "sendgrid", "display_type": "SendGrid API Key"},
    "mongodb": {"family": "database_uri", "provider": "mongodb", "display_type": "MongoDB URI"},
    "postgresql": {"family": "database_uri", "provider": "postgresql", "display_type": "PostgreSQL URI"},
    "mysql": {"family": "database_uri", "provider": "mysql", "display_type": "MySQL URI"},
    "generic_apikey": {"family": "unknown_secret", "provider": "", "display_type": "Unknown Secret"},
    "generic_bearer": {"family": "unknown_secret", "provider": "", "display_type": "Unknown Secret"},
}


def _map_legacy_type(legacy_type: str) -> Dict[str, str]:
    """Map legacy parser type to new family/provider/display_type."""
    return _FAMILY_MAP.get(legacy_type, {
        "family": "unknown_secret",
        "provider": "",
        "display_type": legacy_type or "Unknown Secret",
    })
