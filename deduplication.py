"""
AlphaScan Deduplication Engine.

Identifies and merges identical secrets, tracking:
  - first_seen: When the secret was first discovered
  - last_seen: When the secret was most recently observed
  - occurrences: Total number of sightings
  - repositories: All repos where the secret appeared
  - files: All files where the secret appeared
  - history: Timeline of sightings

Two secrets are considered duplicates if they share the same
(source, secret_type, raw_value) tuple. This ensures that
the same API key appearing in multiple locations is properly
merged rather than reported multiple times.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from models import HistoryEntry, Secret

logger = logging.getLogger(__name__)


@dataclass
class DeduplicationResult:
    """Result of deduplication processing."""
    unique_secrets: List[Secret] = field(default_factory=list)
    duplicates_found: int = 0
    merged_count: int = 0
    total_input: int = 0


def deduplicate_secrets(secrets: List[Secret]) -> DeduplicationResult:
    """
    Deduplicate a list of secrets by merging identical values.

    Uses the stable ID computed from (source, secret_type, raw_value)
    as the deduplication key. When a duplicate is found, the
    existing secret is updated with:
      - incremented occurrence count
      - updated last_seen timestamp
      - additional repository/file tracking
      - history entry for the duplicate sighting

    Args:
        secrets: List of Secret objects to deduplicate

    Returns:
        DeduplicationResult with unique secrets and merge stats
    """
    result = DeduplicationResult(total_input=len(secrets))

    # Map of stable_id -> Secret (for merging)
    seen: Dict[str, Secret] = {}

    for secret in secrets:
        stable_id = secret.compute_stable_id()

        if stable_id in seen:
            # Merge duplicate into existing
            existing = seen[stable_id]
            _merge_secret(existing, secret)
            result.duplicates_found += 1
            result.merged_count += 1
        else:
            # New unique secret
            # Use stable_id as the canonical ID for consistency
            secret.id = stable_id
            # Initialize occurrence tracking
            if "occurrences" not in secret.metadata:
                secret.metadata["occurrences"] = 1
            if "repositories" not in secret.metadata:
                secret.metadata["repositories"] = [secret.repository] if secret.repository else []
            if "files" not in secret.metadata:
                secret.metadata["files"] = [secret.file] if secret.file else []
            seen[stable_id] = secret

    result.unique_secrets = list(seen.values())
    logger.info(
        f"Deduplication: {result.total_input} input → "
        f"{len(result.unique_secrets)} unique, "
        f"{result.duplicates_found} duplicates merged"
    )
    return result


def _merge_secret(existing: Secret, duplicate: Secret) -> None:
    """Merge a duplicate sighting into an existing secret.

    Updates the existing secret with information from the duplicate
    without losing any data from either sighting.
    """
    # Update last_seen to the most recent timestamp
    if duplicate.discovered_at > existing.last_seen:
        existing.last_seen = duplicate.discovered_at
    elif duplicate.last_seen > existing.last_seen:
        existing.last_seen = duplicate.last_seen

    # Track repositories
    repos = existing.metadata.get("repositories", [])
    if duplicate.repository and duplicate.repository not in repos:
        repos.append(duplicate.repository)
        existing.metadata["repositories"] = repos

    # Track files
    files = existing.metadata.get("files", [])
    if duplicate.file and duplicate.file not in files:
        files.append(duplicate.file)
        existing.metadata["files"] = files

    # Increment occurrences
    existing.metadata["occurrences"] = existing.metadata.get("occurrences", 1) + 1

    # Merge history
    now = datetime.now(timezone.utc).isoformat()
    existing.history.append(HistoryEntry(
        timestamp=now,
        event="duplicate_sighting",
        details={
            "source": duplicate.source,
            "repository": duplicate.repository,
            "file": duplicate.file,
            "discovered_at": duplicate.discovered_at,
        },
    ))

    # Keep highest confidence score
    if duplicate.confidence_score > existing.confidence_score:
        existing.confidence_score = duplicate.confidence_score

    # Keep highest validation level
    if duplicate.validation_level.rank > existing.validation_level.rank:
        existing.validation_level = duplicate.validation_level

    # Keep most specific verification status
    _update_verification(existing, duplicate)


def _update_verification(existing: Secret, duplicate: Secret) -> None:
    """Update verification status based on new sighting.

    If the duplicate has a more definitive verification result,
    update the existing secret's verification status.
    """
    # Priority: definitive results override uncertain ones
    definitive_statuses = {
        "active": 0,
        "invalid": 0,
        "expired": 1,
        "revoked": 1,
        "disabled": 1,
        "valid_format": 2,
        "insufficient_scope": 2,
        "rate_limited": 3,
        "unreachable": 3,
        "unknown": 4,
        "unsupported": 5,
    }

    existing_priority = definitive_statuses.get(existing.verification_status.value, 4)
    duplicate_priority = definitive_statuses.get(duplicate.verification_status.value, 4)

    # Lower priority number = more definitive result
    if duplicate_priority < existing_priority:
        existing.verification_status = duplicate.verification_status
        existing.verification_reason = duplicate.verification_reason
        existing.verified_at = duplicate.verified_at
