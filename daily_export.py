"""
AlphaScan Daily Export Module.

After each scan cycle, creates:
  exports/YYYY-MM-DD/findings.json
  exports/YYYY-MM-DD/findings.csv
  exports/YYYY-MM-DD/metrics.json

Maintains an index of previous exports for historical retrieval.
"""
from __future__ import annotations

import csv
import io
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

from models import Secret
from metrics import compute_metrics, ScanMetrics
from storage import Storage, get_storage

logger = logging.getLogger(__name__)

EXPORTS_DIR = Path("exports")


def create_daily_export(
    secrets: List[Secret] = None,
    metrics: ScanMetrics = None,
    storage: Storage = None,
) -> Dict[str, str]:
    """
    Create a daily export after a scan cycle.

    Creates:
      exports/YYYY-MM-DD/findings.json
      exports/YYYY-MM-DD/findings.csv
      exports/YYYY-MM-DD/metrics.json

    Also maintains an export_index table in the database.

    Args:
        secrets: List of Secret objects (if None, uses storage)
        metrics: ScanMetrics object
        storage: Storage instance (if None, uses global)

    Returns:
        Dict with paths to created files
    """
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%d")
    export_dir = EXPORTS_DIR / date_str
    export_dir.mkdir(parents=True, exist_ok=True)

    storage = storage or get_storage()
    metrics = metrics or ScanMetrics()

    # Get secrets for export (from storage if not provided)
    if secrets is None:
        secrets_list = list(storage.stream_secrets(batch_size=500))
        findings_count = storage.count_secrets()
    else:
        secrets_list = secrets
        findings_count = len(secrets)

    result_paths = {}

    # ── findings.json ────────────────────────────────────────────────
    findings_json_path = export_dir / "findings.json"
    with open(findings_json_path, "w", encoding="utf-8") as f:
        json.dump(
            [s.to_export_dict() for s in secrets_list],
            f,
            indent=2,
            ensure_ascii=False,
        )
    result_paths["findings_json"] = str(findings_json_path)
    logger.info(f"Exported findings.json ({findings_count} findings)")

    # ── findings.csv ─────────────────────────────────────────────────
    findings_csv_path = export_dir / "findings.csv"
    _write_csv_export(secrets_list, findings_csv_path)
    result_paths["findings_csv"] = str(findings_csv_path)
    logger.info(f"Exported findings.csv ({findings_count} findings)")

    # ── metrics.json ─────────────────────────────────────────────────
    metrics_json_path = export_dir / "metrics.json"
    with open(metrics_json_path, "w", encoding="utf-8") as f:
        json.dump(metrics.to_dict(), f, indent=2, ensure_ascii=False)
    result_paths["metrics_json"] = str(metrics_json_path)
    logger.info(f"Exported metrics.json")

    # ── Update export index ──────────────────────────────────────────
    storage.insert_export_index(
        export_date=date_str,
        export_dir=str(export_dir),
        findings_count=findings_count,
    )

    logger.info(f"Daily export created: {export_dir}")
    return result_paths


def _write_csv_export(secrets: List[Secret], path: Path) -> None:
    """Write secrets to a CSV file with the required columns."""
    fieldnames = [
        "id", "source", "repository", "file", "finding_target",
        "secret_type", "confidence", "confidence_category",
        "validation_level", "verified", "verification_badge",
        "masked_value", "entropy", "discovered_at",
    ]

    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for secret in secrets:
            row = secret.to_export_dict()
            for fn in fieldnames:
                if fn not in row:
                    row[fn] = ""
            writer.writerow(row)


def get_export_history() -> List[Dict[str, Any]]:
    """Get the index of all previous exports."""
    storage = get_storage()
    return storage.get_export_history()


def stream_csv_export(
    storage: Storage = None,
    filters: Dict[str, Any] = None,
    include_raw: bool = False,
) -> Iterator[str]:
    """
    Stream a CSV export line by line for large datasets.

    Yields one line at a time, never loading all secrets into memory.
    Designed for 100,000+ findings with streaming responses.
    """
    storage = storage or get_storage()
    filters = filters or {}

    fieldnames = [
        "id", "source", "repository", "file", "finding_target",
        "secret_type", "confidence", "confidence_category",
        "validation_level", "verified", "verification_badge",
        "masked_value", "entropy", "discovered_at",
    ]

    if include_raw:
        fieldnames.append("raw_value")

    # Write header
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    header_line = output.getvalue()
    yield header_line

    # Stream rows
    for secret_dict in storage.stream_secrets_as_dicts(
        filters=filters,
        include_raw=include_raw,
        batch_size=1000,
    ):
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        for fn in fieldnames:
            if fn not in secret_dict:
                secret_dict[fn] = ""
        writer.writerow(secret_dict)
        yield output.getvalue()


def stream_json_export(
    storage: Storage = None,
    filters: Dict[str, Any] = None,
    include_raw: bool = False,
) -> Iterator[str]:
    """
    Stream a JSON export for large datasets.

    Produces a valid JSON array, yielding chunks that can be
    sent as a streaming response without loading all secrets
    into memory.
    """
    storage = storage or get_storage()
    filters = filters or {}

    # Start of JSON array
    yield "[\n"

    first = True
    for secret_dict in storage.stream_secrets_as_dicts(
        filters=filters,
        include_raw=include_raw,
        batch_size=1000,
    ):
        if not first:
            yield ",\n"
        first = False

        json_str = json.dumps(secret_dict, ensure_ascii=False)
        yield f"  {json_str}"

    # End of JSON array
    yield "\n]"
