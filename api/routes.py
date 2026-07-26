"""
AlphaScan FastAPI Routes — Findings Export API.

Endpoints:
  GET /          — Service status
  GET /health     — Health check
  GET /findings   — Paginated findings with filtering
  GET /findings/{id} — Single finding detail
  GET /export/json — Download all findings as JSON (streaming)
  GET /export/csv  — Download all findings as CSV (streaming)
  GET /metrics    — Scan metrics

  GET /exports     — Export history index

When running in production (Docker), the API also serves the
pre-built Next.js frontend from the ./static/ directory.
"""
from __future__ import annotations

import csv
import io
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from models import Secret, ValidationLevel, VerificationStatus, ConfidenceCategory
from storage import Storage, get_storage, reset_storage
from metrics import compute_metrics, ScanMetrics
from daily_export import create_daily_export, get_export_history

logger = logging.getLogger(__name__)

app = FastAPI(
    title="AlphaScan Findings Export API",
    version="1.0.0",
    description="Enterprise-grade Secret Intelligence Engine with secure findings export, "
                    "paginated access, streaming downloads, and comprehensive metrics.",
)

# ── Serve pre-built frontend (production) ──────────────────────────
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
if STATIC_DIR.is_dir():
    logger.info(f"Serving frontend from {STATIC_DIR}")

# ── Storage dependency injection ────────────────────────────────────

def _get_app_storage() -> Storage:
    """Get the storage instance for the application."""
    return get_storage()


# ── Authorization for full value export ────────────────────────────────────

def _is_authorized_for_raw_values(request: Request) -> bool:
    """
    Determine if the request is authorized for full secret values.

    By default, only masked values are exported. Full values require:
    - An explicit 'include_raw' query parameter
    - Authorization header with a valid token
    - Or the request coming from an explicitly authorized target

    The authorization system supports:
    - User-owned test datasets (marked via config)
    - Explicitly authorized targets (marked via config)
    - Authorization tokens (for CI/CD pipelines, etc.)

    This ensures secrets are never leaked accidentally via the API.
    """
    include_raw_param = request.query_params.get("include_raw", "false").lower() in ("true", "1", "yes")

    if not include_raw_param:
        return False

    # Check authorization header
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        # In production, validate against a token store/service
        # For now, check against config
        from config import EXPORT_AUTH_TOKENS, AUTHORIZED_EXPORT_TARGETS
        if token in EXPORT_AUTH_TOKENS:
            return True

    # Check if target is explicitly authorized
    authorized_targets = _get_authorized_targets()
    target_param = request.query_params.get("target", "")
    if target_param and target_param in authorized_targets:
        return True

    return False


def _get_authorized_targets() -> List[str]:
    """Get the list of explicitly authorized export targets."""
    from config import AUTHORIZED_EXPORT_TARGETS
    return AUTHORIZED_EXPORT_TARGETS


# ── Filtering helpers ──────────────────────────────────────────────

def _parse_filters(
    source: Optional[str] = None,
    repository: Optional[str] = None,
    secret_type: Optional[str] = None,
    confidence_min: Optional[float] = None,
    confidence_max: Optional[float] = None,
    validation_level: Optional[str] = None,
    verified: Optional[str] = None,
    date: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    provider: Optional[str] = None,
) -> Dict[str, Any]:
    """Parse query parameters into filter dict."""
    filters: Dict[str, Any] = {}

    if source:
        filters["source"] = source
    if repository:
        filters["repository"] = repository
    if secret_type:
        filters["secret_type"] = secret_type
    if confidence_min is not None:
        filters["confidence_min"] = confidence_min
    if confidence_max is not None:
        filters["confidence_max"] = confidence_max
    if validation_level:
        # Validate the level string
        valid_levels = [vl.value for vl in ValidationLevel]
        if validation_level not in valid_levels:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid validation_level: {validation_level}. "
                               f"Valid values: {valid_levels}",
            )
        filters["validation_level"] = validation_level
    if verified:
        # Handle boolean-like values
        if verified.lower() in ("true", "1", "yes"):
            filters["verified"] = True
        elif verified.lower() in ("false", "0", "no"):
            filters["verified"] = False
        else:
            # Treat as a verification_status string
            valid_statuses = [vs.value for vs in VerificationStatus]
            if verified not in valid_statuses:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid verified filter: {verified}. "
                               f"Valid values: {valid_statuses}",
                )
            filters["verification_status"] = verified
    if date:
        filters["date"] = date
    if date_from:
        filters["date_from"] = date_from
    if date_to:
        filters["date_to"] = date_to
    if provider:
        filters["provider"] = provider

    return filters


# ── API Endpoints ────────────────────────────────────────────────────

@app.get("/")
def root():
    """Service status and version info."""
    index_path = STATIC_DIR / "index.html"
    if index_path.is_file():
        return FileResponse(index_path)
    return {
        "status": "ok",
        "service": "AlphaScan",
        "version": "1.0.0",
        "pipeline": "Collectors → Normalization → Context Extraction → Secret Detection "
                        "→ Secret Classification → Confidence Scoring → Deduplication "
                        "→ Provider Verification → Risk Classification → Storage → Dashboard",
    }


@app.get("/health")
def health():
    """Health check endpoint."""
    storage = _get_app_storage()
    try:
        count = storage.count_secrets()
        return {
            "status": "healthy",
            "total_findings": count,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Storage health check failed")


@app.get("/findings")
def list_findings(
    request: Request,
    source: Optional[str] = None,
    repository: Optional[str] = None,
    secret_type: Optional[str] = None,
    confidence_min: Optional[float] = None,
    confidence_max: Optional[float] = None,
    validation_level: Optional[str] = None,
    verified: Optional[str] = None,
    date: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    provider: Optional[str] = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    sort_by: str = Query(default="discovered_at"),
    sort_desc: bool = Query(default=True),
):
    """
    List findings with pagination and filtering.

    Returns paginated findings with the following fields for each result:
    - source
    - repository
    - file
    - finding_target
    - secret_type
    - confidence
    - validation_level
    - verified
    - masked_value
    - entropy
    - discovered_at

    Supports filtering on:
    - source, repository, secret_type, validation_level, verified, date, provider
    - confidence_min / confidence_max for confidence range filtering
    - date / date_from / date_to for temporal filtering

    Default behavior: only exports masked values. Full values require
    explicit authorization.
    """
    storage = _get_app_storage()
    filters = _parse_filters(
        source=source,
        repository=repository,
        secret_type=secret_type,
        confidence_min=confidence_min,
        confidence_max=confidence_max,
        validation_level=validation_level,
        verified=verified,
        date=date,
        date_from=date_from,
        date_to=date_to,
        provider=provider,
    )

    secrets, total = storage.list_secrets(
        filters=filters,
        offset=offset,
        limit=limit,
        sort_by=sort_by,
        sort_desc=sort_desc,
    )

    # Determine if full values should be included
    include_raw = _is_authorized_for_raw_values(request)

    result_list = []
    for secret in secrets:
        if include_raw:
            result_list.append(secret.to_dict(include_raw=True))
        else:
            result_list.append(secret.to_export_dict())

    return {
        "findings": result_list,
        "total": total,
        "offset": offset,
        "limit": limit,
        "filters": filters,
        "include_raw": include_raw,
    }


@app.get("/findings/{finding_id}")
def get_finding(finding_id: str, request: Request):
    """
    Get a single finding by ID.

    Returns full finding details including:
    - All secret metadata
    - Confidence breakdown
    - Verification details
    - History timeline
    - Risk classification

    By default, only masked values are shown. Full values require authorization.
    """
    storage = _get_app_storage()
    secret = storage.get_secret(finding_id)

    if secret is None:
        raise HTTPException(status_code=404, detail=f"Finding {finding_id} not found")

    include_raw = _is_authorized_for_raw_values(request)

    if include_raw:
        return secret.to_dict(include_raw=True)
    else:
        return secret.to_export_dict()


# ── Streaming Export Endpoints ──────────────────────────────────────

@app.get("/export/json")
def export_json(
    request: Request,
    source: Optional[str] = None,
    repository: Optional[str] = None,
    secret_type: Optional[str] = None,
    confidence_min: Optional[float] = None,
    confidence_max: Optional[float] = None,
    validation_level: Optional[str] = None,
    verified: Optional[str] = None,
    date: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    provider: Optional[str] = None,
):
    """
    Export all findings as JSON.

    Returns a streaming response that handles 100,000+ findings
    without loading everything into memory. Supports the same
    filters as /findings.

    By default, only exports masked values. Full values require
    explicit authorization via include_raw=true and either:
    - An Authorization header with a valid token, OR
    - An explicitly authorized target parameter
    """
    filters = _parse_filters(
        source=source,
        repository=repository,
        secret_type=secret_type,
        confidence_min=confidence_min,
        confidence_max=confidence_max,
        validation_level=validation_level,
        verified=verified,
        date=date,
        date_from=date_from,
        date_to=date_to,
        provider=provider,
    )

    include_raw = _is_authorized_for_raw_values(request)
    storage = _get_app_storage()

    def json_stream_generator():
        """Generate JSON chunks for streaming response."""
        # First chunk: opening bracket + metadata
        yield '{"findings": ['

        first = True
        for secret_dict in storage.stream_secrets_as_dicts(
            filters=filters,
            include_raw=include_raw,
            batch_size=2000,
        ):
            if not first:
                yield ","
            yield json.dumps(secret_dict, indent=None)
            first = False

        # Final chunk: closing bracket
        yield "], "
        # Include metadata
        yield '"total": ' + str(storage.count_secrets(filters)) + ", "
        yield '"filters": ' + json.dumps(filters) + ", "
        yield '"include_raw": ' + json.dumps(include_raw) + ", "
        yield '"exported_at": "' + datetime.now(timezone.utc).isoformat() + '"}'

    media_type = "application/json"
    return StreamingResponse(
        json_stream_generator(),
        media_type=media_type,
        headers={
            "Content-Disposition": "attachment; filename=findings_export.json",
            "X-Total-Count": str(storage.count_secrets(filters)),
        },
    )


@app.get("/export/csv")
def export_csv(
    request: Request,
    source: Optional[str] = None,
    repository: Optional[str] = None,
    secret_type: Optional[str] = None,
    confidence_min: Optional[float] = None,
    confidence_max: Optional[float] = None,
    validation_level: Optional[str] = None,
    verified: Optional[str] = None,
    date: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    provider: Optional[str] = None,
):
    """
    Export all findings as CSV.

    Returns a streaming response that handles 100,000+ findings
    without loading everything into memory. Supports the same
    filters as /findings.

    By default, only exports masked values. Full values require
    explicit authorization.
    """
    filters = _parse_filters(
        source=source,
        repository=repository,
        secret_type=secret_type,
        confidence_min=confidence_min,
        confidence_max=confidence_max,
        validation_level=validation_level,
        verified=verified,
        date=date,
        date_from=date_from,
        date_to=date_to,
        provider=provider,
    )

    include_raw = _is_authorized_for_raw_values(request)
    storage = _get_app_storage()

    def csv_stream_generator():
        """Generate CSV rows for streaming response."""
        # Header row
        yield "id,source,repository,file,finding_target,secret_type," \
              "confidence,confidence_category,validation_level,verified," \
              "verification_badge,masked_value,entropy,discovered_at\n"

        for secret_dict in storage.stream_secrets_as_dicts(
            filters=filters,
            include_raw=include_raw,
            batch_size=2000,
        ):
            # Use csv module for proper escaping
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow([
                secret_dict.get("id", ""),
                secret_dict.get("source", ""),
                secret_dict.get("repository", ""),
                secret_dict.get("file", ""),
                secret_dict.get("finding_target", ""),
                secret_dict.get("secret_type", ""),
                secret_dict.get("confidence", 0),
                secret_dict.get("confidence_category", ""),
                secret_dict.get("validation_level", ""),
                secret_dict.get("verified", ""),
                secret_dict.get("verification_badge", ""),
                secret_dict.get("masked_value", ""),
                secret_dict.get("entropy", 0),
                secret_dict.get("discovered_at", ""),
            ])
            yield output.getvalue()

    media_type = "text/csv"
    return StreamingResponse(
        csv_stream_generator(),
        media_type=media_type,
        headers={
            "Content-Disposition": "attachment; filename=findings_export.csv",
            "X-Total-Count": str(storage.count_secrets(filters)),
        },
    )


@app.get("/metrics")
def get_metrics():
    """
    Get comprehensive scan metrics.

    Returns realistic, enterprise-grade metrics that reflect the
    intelligence pipeline rather than raw scan counts:

    - Assets Crawled: Total assets scanned
    - Files Analyzed: Files processed through context extraction
    - Candidate Secrets: Raw detection results before filtering
    - High Confidence Secrets: Confidence >= 70
    - Provider Verified: Secrets verified against provider
    - Currently Active: Confirmed active credentials
    - Expired: Confirmed expired credentials
    - Revoked: Confirmed revoked credentials
    - Unknown: No provider verification available
    - Needs Review: Secrets requiring manual review
    - False Positives Removed: Secrets identified as false positives
    - Duplicate Secrets Merged: Identical secrets merged
    - Verification Failures: Provider verification errors
    - Average Confidence: Mean confidence across all secrets

    Also includes scanner statistics and family distribution.
    """
    storage = _get_app_storage()
    metrics = compute_metrics()  # Computes from storage (aggregation queries)

    return metrics.to_dict()


@app.get("/exports")
def list_exports():
    """
    List all previous daily exports.

    Returns an index of past exports with dates, directories,
    and finding counts for each export batch.
    """
    history = get_export_history()
    return {
        "exports": history,
        "total_exports": len(history),
    }


# ── SPA Fallback (MUST be last — catches all unmatched routes) ──────
if STATIC_DIR.is_dir():
    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        """Serve static files or fall back to index.html for SPA routes."""
        # Prevent matching API paths
        if full_path in ("health", "findings", "metrics", "exports", "export"):
            raise HTTPException(status_code=404, detail="Not found")
        # `next export` writes routes as e.g. `secrets.html`, rather than
        # `secrets/index.html`. Resolve that form too; otherwise a request for
        # /secrets falls through to the dashboard HTML and the findings page
        # never mounts after a reload or a direct link.
        requested_path = (STATIC_DIR / full_path).resolve()
        try:
            requested_path.relative_to(STATIC_DIR.resolve())
        except ValueError:
            raise HTTPException(status_code=404, detail="Not found")

        candidates = (
            requested_path,
            requested_path.with_suffix(".html") if not requested_path.suffix else requested_path,
            requested_path / "index.html",
        )
        for file_path in candidates:
            if file_path.is_file():
                return FileResponse(file_path)

        index = STATIC_DIR / "index.html"
        if index.is_file():
            return FileResponse(index)
        raise HTTPException(status_code=404, detail="Not found")
