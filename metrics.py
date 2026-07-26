"""
AlphaScan Metrics Engine.

Produces realistic, enterprise-grade metrics that reflect the
actual intelligence pipeline rather than raw scan counts.

Replaces simplistic "findings found" metrics with:
  - Assets Crawled
  - Files Analyzed
  - Candidate Secrets
  - High Confidence Secrets
  - Provider Verified
  - Currently Active
  - Expired
  - Revoked
  - Unknown
  - Needs Review
  - False Positives Removed
  - Duplicate Secrets Merged
  - Verification Failures
  - Average Confidence
  - Scanner Statistics
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from models import ConfidenceCategory, Secret, ValidationLevel, VerificationStatus
from storage import Storage, get_storage

logger = logging.getLogger(__name__)


@dataclass
class ScanMetrics:
    """Complete metrics for a scan cycle."""
    # ── Scanning ────────────────────────────────────────────────────
    assets_crawled: int = 0
    files_analyzed: int = 0

    # ── Detection ───────────────────────────────────────────────────
    candidate_secrets: int = 0
    false_positives_removed: int = 0
    duplicate_secrets_merged: int = 0

    # ── Quality ─────────────────────────────────────────────────────
    high_confidence_secrets: int = 0     # confidence >= 70
    medium_confidence_secrets: int = 0   # confidence 40-69
    low_confidence_secrets: int = 0      # confidence < 40

    # ── Verification ────────────────────────────────────────────────
    provider_verified: int = 0
    currently_active: int = 0
    expired: int = 0
    revoked: int = 0
    disabled: int = 0
    unknown: int = 0
    needs_review: int = 0
    verification_failures: int = 0

    # ── Confidence ──────────────────────────────────────────────────
    average_confidence: float = 0.0

    # ── Validation Levels ───────────────────────────────────────────
    format_validated: int = 0
    structure_validated: int = 0
    heuristic_validated: int = 0
    provider_validated: int = 0
    active_validated: int = 0

    # ── Scanner Statistics ──────────────────────────────────────────
    scanner_stats: Dict[str, Dict[str, int]] = field(default_factory=dict)

    # ── Family Distribution ─────────────────────────────────────────
    family_distribution: Dict[str, int] = field(default_factory=dict)

    # ── Timestamp ───────────────────────────────────────────────────
    scan_timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "assets_crawled": self.assets_crawled,
            "files_analyzed": self.files_analyzed,
            "candidate_secrets": self.candidate_secrets,
            "false_positives_removed": self.false_positives_removed,
            "duplicate_secrets_merged": self.duplicate_secrets_merged,
            "high_confidence_secrets": self.high_confidence_secrets,
            "medium_confidence_secrets": self.medium_confidence_secrets,
            "low_confidence_secrets": self.low_confidence_secrets,
            "provider_verified": self.provider_verified,
            "currently_active": self.currently_active,
            "expired": self.expired,
            "revoked": self.revoked,
            "disabled": self.disabled,
            "unknown": self.unknown,
            "needs_review": self.needs_review,
            "verification_failures": self.verification_failures,
            "average_confidence": round(self.average_confidence, 2),
            "validation_levels": {
                "format": self.format_validated,
                "structure": self.structure_validated,
                "heuristic": self.heuristic_validated,
                "provider": self.provider_validated,
                "active": self.active_validated,
            },
            "scanner_stats": self.scanner_stats,
            "family_distribution": self.family_distribution,
            "scan_timestamp": self.scan_timestamp,
        }


def compute_metrics(secrets: List[Secret] = None) -> ScanMetrics:
    """
    Compute comprehensive metrics from stored secrets.

    If secrets list is provided, computes from that list.
    Otherwise, computes from the storage database (aggregation queries).
    """
    from datetime import datetime, timezone

    metrics = ScanMetrics(
        scan_timestamp=datetime.now(timezone.utc).isoformat(),
    )

    if secrets is not None:
        _compute_from_list(metrics, secrets)
    else:
        storage = get_storage()
        _compute_from_storage(metrics, storage)

    return metrics


def _compute_from_list(metrics: ScanMetrics, secrets: List[Secret]) -> None:
    """Compute metrics from an in-memory list of secrets."""
    if not secrets:
        return

    metrics.candidate_secrets = len(secrets)
    total_confidence = 0.0

    # Family distribution
    family_counts: Dict[str, int] = {}
    scanner_counts: Dict[str, Dict[str, int]] = {}

    for secret in secrets:
        total_confidence += secret.confidence_score

        # Confidence categories
        cat = ConfidenceCategory.from_score(secret.confidence_score)
        if cat == ConfidenceCategory.CRITICAL or cat == ConfidenceCategory.HIGH:
            metrics.high_confidence_secrets += 1
        elif cat == ConfidenceCategory.MEDIUM:
            metrics.medium_confidence_secrets += 1
        else:
            metrics.low_confidence_secrets += 1

        # False positives (low confidence, not verified)
        if secret.confidence_score < 20 and secret.verification_status in (
            VerificationStatus.UNKNOWN, VerificationStatus.INVALID
        ):
            metrics.false_positives_removed += 1

        # Verification status
        if secret.verification_status == VerificationStatus.ACTIVE:
            metrics.currently_active += 1
            metrics.provider_verified += 1
        elif secret.verification_status == VerificationStatus.VALID_FORMAT:
            metrics.provider_verified += 1
        elif secret.verification_status == VerificationStatus.EXPIRED:
            metrics.expired += 1
        elif secret.verification_status == VerificationStatus.REVOKED:
            metrics.revoked += 1
        elif secret.verification_status == VerificationStatus.DISABLED:
            metrics.disabled += 1
        elif secret.verification_status == VerificationStatus.UNKNOWN:
            metrics.unknown += 1
        elif secret.verification_status in (
            VerificationStatus.UNSUPPORTED, VerificationStatus.UNREACHABLE,
            VerificationStatus.RATE_LIMITED,
        ):
            metrics.verification_failures += 1

        # Needs review
        if secret.secret_family in ("needs_review", "unknown_secret"):
            metrics.needs_review += 1

        # Validation levels
        if secret.validation_level == ValidationLevel.FORMAT:
            metrics.format_validated += 1
        elif secret.validation_level == ValidationLevel.STRUCTURE:
            metrics.structure_validated += 1
        elif secret.validation_level == ValidationLevel.HEURISTIC:
            metrics.heuristic_validated += 1
        elif secret.validation_level == ValidationLevel.PROVIDER:
            metrics.provider_validated += 1
        elif secret.validation_level == ValidationLevel.ACTIVE:
            metrics.active_validated += 1

        # Family distribution
        family = secret.secret_family or "unclassified"
        family_counts[family] = family_counts.get(family, 0) + 1

        # Scanner stats
        scanner = secret.scanner or "unknown"
        if scanner not in scanner_counts:
            scanner_counts[scanner] = {"count": 0, "high_confidence": 0, "verified": 0}
        scanner_counts[scanner]["count"] += 1
        if secret.confidence_score >= 70:
            scanner_counts[scanner]["high_confidence"] += 1
        if secret.verification_status == VerificationStatus.ACTIVE:
            scanner_counts[scanner]["verified"] += 1

    metrics.average_confidence = total_confidence / len(secrets) if secrets else 0
    metrics.family_distribution = family_counts
    metrics.scanner_stats = scanner_counts


def _compute_from_storage(metrics: ScanMetrics, storage: Storage) -> None:
    """Compute metrics using SQL aggregation (efficient for 100k+ secrets)."""
    conn = storage._get_conn()

    # Total candidates
    row = conn.execute("SELECT COUNT(*) FROM secrets").fetchone()
    metrics.candidate_secrets = row[0]

    # Confidence distribution
    row = conn.execute(
        "SELECT AVG(confidence_score), "
        "SUM(CASE WHEN confidence_score >= 70 THEN 1 ELSE 0 END), "
        "SUM(CASE WHEN confidence_score >= 40 AND confidence_score < 70 THEN 1 ELSE 0 END), "
        "SUM(CASE WHEN confidence_score < 40 THEN 1 ELSE 0 END) "
        "FROM secrets"
    ).fetchone()
    metrics.average_confidence = row[0] or 0.0
    metrics.high_confidence_secrets = row[1] or 0
    metrics.medium_confidence_secrets = row[2] or 0
    metrics.low_confidence_secrets = row[3] or 0

    # False positives (low confidence + unverified)
    row = conn.execute(
        "SELECT COUNT(*) FROM secrets WHERE confidence_score < 20 "
        "AND verification_status IN ('unknown', 'invalid')"
    ).fetchone()
    metrics.false_positives_removed = row[0]

    # Verification status distribution
    row = conn.execute(
        "SELECT "
        "SUM(CASE WHEN verification_status = 'active' THEN 1 ELSE 0 END), "
        "SUM(CASE WHEN verification_status IN ('active', 'valid_format') THEN 1 ELSE 0 END), "
        "SUM(CASE WHEN verification_status = 'expired' THEN 1 ELSE 0 END), "
        "SUM(CASE WHEN verification_status = 'revoked' THEN 1 ELSE 0 END), "
        "SUM(CASE WHEN verification_status = 'disabled' THEN 1 ELSE 0 END), "
        "SUM(CASE WHEN verification_status = 'unknown' THEN 1 ELSE 0 END), "
        "SUM(CASE WHEN verification_status IN ('unsupported', 'unreachable', 'rate_limited') THEN 1 ELSE 0 END), "
        "SUM(CASE WHEN secret_family IN ('needs_review', 'unknown_secret') THEN 1 ELSE 0 END) "
        "FROM secrets"
    ).fetchone()
    metrics.currently_active = row[0] or 0
    metrics.provider_verified = row[1] or 0
    metrics.expired = row[2] or 0
    metrics.revoked = row[3] or 0
    metrics.disabled = row[4] or 0
    metrics.unknown = row[5] or 0
    metrics.verification_failures = row[6] or 0
    metrics.needs_review = row[7] or 0

    # Validation level distribution
    row = conn.execute(
        "SELECT "
        "SUM(CASE WHEN validation_level = 'format' THEN 1 ELSE 0 END), "
        "SUM(CASE WHEN validation_level = 'structure' THEN 1 ELSE 0 END), "
        "SUM(CASE WHEN validation_level = 'heuristic' THEN 1 ELSE 0 END), "
        "SUM(CASE WHEN validation_level = 'provider' THEN 1 ELSE 0 END), "
        "SUM(CASE WHEN validation_level = 'active' THEN 1 ELSE 0 END) "
        "FROM secrets"
    ).fetchone()
    metrics.format_validated = row[0] or 0
    metrics.structure_validated = row[1] or 0
    metrics.heuristic_validated = row[2] or 0
    metrics.provider_validated = row[3] or 0
    metrics.active_validated = row[4] or 0

    # Family distribution
    rows = conn.execute(
        "SELECT secret_family, COUNT(*) FROM secrets GROUP BY secret_family ORDER BY COUNT(*) DESC"
    ).fetchall()
    metrics.family_distribution = {r[0]: r[1] for r in rows}

    # Scanner stats
    rows = conn.execute(
        "SELECT scanner, COUNT(*), "
        "SUM(CASE WHEN confidence_score >= 70 THEN 1 ELSE 0 END), "
        "SUM(CASE WHEN verification_status = 'active' THEN 1 ELSE 0 END) "
        "FROM secrets GROUP BY scanner"
    ).fetchall()
    metrics.scanner_stats = {
        r[0]: {"count": r[1], "high_confidence": r[2], "verified": r[3]}
        for r in rows
    }
