"""
AlphaScan Storage Layer.

SQLite-backed storage for 100,000+ findings without loading
everything into memory. Supports streaming queries, pagination,
and efficient filtering for the export API.

Design principles:
  - Streaming queries: rows fetched in batches, not all at once
  - Pagination: offset/limit with total count
  - Filtering: WHERE clauses built from query parameters
  - Indexed columns for fast lookups on common filter fields
  - JSON metadata stored as TEXT, parsed on read
"""
from __future__ import annotations

import csv
import io
import json
import logging
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Generator, Iterator, List, Optional, Tuple

from models import Secret, ValidationLevel, VerificationStatus

logger = logging.getLogger(__name__)

DB_PATH = Path("data/findings.db")


class Storage:
    """SQLite-backed storage for secrets with streaming and pagination."""

    # ── Schema definition (column 'commit' renamed to 'commit_sha' to avoid SQLite keyword conflict) ──
    _CREATE_SECRETS_TABLE = """CREATE TABLE IF NOT EXISTS secrets (
        id TEXT PRIMARY KEY,
        source TEXT NOT NULL DEFAULT '',
        finding_target TEXT NOT NULL DEFAULT '',
        repository TEXT NOT NULL DEFAULT '',
        organization TEXT NOT NULL DEFAULT '',
        branch TEXT NOT NULL DEFAULT '',
        commit_sha TEXT NOT NULL DEFAULT '',
        file TEXT NOT NULL DEFAULT '',
        line_number INTEGER,
        scanner TEXT NOT NULL DEFAULT '',
        collector TEXT NOT NULL DEFAULT '',
        discovered_at TEXT NOT NULL DEFAULT '',
        last_seen TEXT NOT NULL DEFAULT '',
        secret_family TEXT NOT NULL DEFAULT '',
        secret_type TEXT NOT NULL DEFAULT '',
        provider TEXT NOT NULL DEFAULT '',
        confidence_score REAL NOT NULL DEFAULT 0.0,
        confidence_category TEXT NOT NULL DEFAULT '',
        validation_level TEXT NOT NULL DEFAULT 'none',
        provider_status TEXT,
        verification_status TEXT NOT NULL DEFAULT 'unknown',
        verification_reason TEXT NOT NULL DEFAULT '',
        verified_at TEXT,
        masked_value TEXT NOT NULL DEFAULT '',
        raw_value TEXT NOT NULL DEFAULT '',
        entropy REAL NOT NULL DEFAULT 0.0,
        metadata_json TEXT NOT NULL DEFAULT '{}',
        history_json TEXT NOT NULL DEFAULT '[]',
        created_at TEXT NOT NULL DEFAULT ''
    )"""

    _CREATE_INDEXES = [
        "CREATE INDEX IF NOT EXISTS idx_secrets_source ON secrets(source)",
        "CREATE INDEX IF NOT EXISTS idx_secrets_repository ON secrets(repository)",
        "CREATE INDEX IF NOT EXISTS idx_secrets_secret_type ON secrets(secret_type)",
        "CREATE INDEX IF NOT EXISTS idx_secrets_secret_family ON secrets(secret_family)",
        "CREATE INDEX IF NOT EXISTS idx_secrets_validation_level ON secrets(validation_level)",
        "CREATE INDEX IF NOT EXISTS idx_secrets_verification_status ON secrets(verification_status)",
        "CREATE INDEX IF NOT EXISTS idx_secrets_confidence_score ON secrets(confidence_score)",
        "CREATE INDEX IF NOT EXISTS idx_secrets_discovered_at ON secrets(discovered_at)",
        "CREATE INDEX IF NOT EXISTS idx_secrets_provider ON secrets(provider)",
    ]

    _CREATE_METRICS_TABLE = """CREATE TABLE IF NOT EXISTS scan_metrics (
        id TEXT PRIMARY KEY,
        scan_date TEXT NOT NULL DEFAULT '',
        metrics_json TEXT NOT NULL DEFAULT '{}',
        created_at TEXT NOT NULL DEFAULT ''
    )"""

    _CREATE_EXPORT_INDEX_TABLE = """CREATE TABLE IF NOT EXISTS export_index (
        id TEXT PRIMARY KEY,
        export_date TEXT NOT NULL DEFAULT '',
        export_dir TEXT NOT NULL DEFAULT '',
        findings_count INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL DEFAULT ''
    )"""

    def __init__(self, db_path: str | Path = DB_PATH) -> None:
        self.db_path = Path(db_path)
        if str(db_path) != ":memory:":
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database schema."""
        conn = self._get_conn()
        conn.execute(self._CREATE_SECRETS_TABLE)
        for idx_sql in self._CREATE_INDEXES:
            conn.execute(idx_sql)
        conn.execute(self._CREATE_METRICS_TABLE)
        conn.execute(self._CREATE_EXPORT_INDEX_TABLE)
        conn.commit()
        logger.info(f"Storage initialized: {self.db_path}")

    def _get_conn(self) -> sqlite3.Connection:
        """Get or create database connection."""
        if self._conn is None:
            self._conn = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False,
            )
            self._conn.row_factory = sqlite3.Row
            if str(self.db_path) != ":memory:":
                try:
                    self._conn.execute("PRAGMA journal_mode=WAL")
                    self._conn.execute("PRAGMA cache_size=-64000")
                except sqlite3.OperationalError:
                    pass
        return self._conn

    def close(self) -> None:
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    # ── Column list (for INSERT/SELECT) ──────────────────────────────

    _SECRETS_COLUMNS = [
        "id", "source", "finding_target", "repository", "organization",
        "branch", "commit_sha", "file", "line_number", "scanner", "collector",
        "discovered_at", "last_seen", "secret_family", "secret_type", "provider",
        "confidence_score", "confidence_category", "validation_level",
        "provider_status", "verification_status", "verification_reason",
        "verified_at", "masked_value", "raw_value", "entropy",
        "metadata_json", "history_json", "created_at",
    ]

    _SECRETS_INSERT_SQL = f"""
        INSERT OR REPLACE INTO secrets ({', '.join(_SECRETS_COLUMNS)})
        VALUES ({', '.join(['?'] * len(_SECRETS_COLUMNS))})
    """

    # ── Insert / Upsert ─────────────────────────────────────────────

    def _secret_to_row(self, secret: Secret, now: str) -> Tuple:
        """Convert a Secret object to a database row tuple."""
        metadata_json = json.dumps(secret.metadata)
        history_json = json.dumps([h.to_dict() for h in secret.history])
        return (
            secret.id,
            secret.source,
            secret.finding_target,
            secret.repository,
            secret.organization,
            secret.branch,
            secret.commit,
            secret.file,
            secret.line_number,
            secret.scanner,
            secret.collector,
            secret.discovered_at,
            secret.last_seen,
            secret.secret_family,
            secret.secret_type,
            secret.provider,
            secret.confidence_score,
            _confidence_category(secret.confidence_score),
            secret.validation_level.value,
            secret.provider_status,
            secret.verification_status.value,
            secret.verification_reason,
            secret.verified_at,
            secret.masked_value,
            secret.raw_value,
            secret.metadata.get("entropy", 0.0),
            metadata_json,
            history_json,
            now,
        )

    def insert_secret(self, secret: Secret) -> None:
        """Insert a single secret. Uses stable ID for dedup upsert."""
        conn = self._get_conn()
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(self._SECRETS_INSERT_SQL, self._secret_to_row(secret, now))
        conn.commit()

    def insert_secrets_batch(self, secrets: List[Secret], batch_size: int = 500) -> None:
        """Insert secrets in batches for performance."""
        conn = self._get_conn()
        now = datetime.now(timezone.utc).isoformat()

        for i in range(0, len(secrets), batch_size):
            batch = secrets[i:i + batch_size]
            rows = [self._secret_to_row(secret, now) for secret in batch]
            conn.executemany(self._SECRETS_INSERT_SQL, rows)
            conn.commit()
        logger.info(f"Inserted {len(secrets)} secrets in batches")

    # ── Query ───────────────────────────────────────────────────────

    def get_secret(self, secret_id: str) -> Optional[Secret]:
        """Get a single secret by ID."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM secrets WHERE id = ?",
            (secret_id,),
        ).fetchone()
        if row is None:
            return None
        return _row_to_secret(row)

    def count_secrets(self, filters: Dict[str, Any] = None) -> int:
        """Count secrets matching filters. Efficient for pagination."""
        conn = self._get_conn()
        where, params = _build_where(filters or {})
        sql = f"SELECT COUNT(*) FROM secrets {where}"
        result = conn.execute(sql, params).fetchone()
        return result[0]

    def list_secrets(
        self,
        filters: Dict[str, Any] = None,
        offset: int = 0,
        limit: int = 50,
        sort_by: str = "discovered_at",
        sort_desc: bool = True,
    ) -> Tuple[List[Secret], int]:
        """
        List secrets with pagination and filtering.

        Returns (secrets, total_count) for pagination metadata.
        Only fetches the requested page, not all results.
        """
        conn = self._get_conn()
        filters = filters or {}
        where, params = _build_where(filters)
        total = self.count_secrets(filters)

        direction = "DESC" if sort_desc else "ASC"
        valid_sorts = {
            "discovered_at", "confidence_score", "secret_type",
            "source", "repository", "validation_level", "last_seen",
        }
        if sort_by not in valid_sorts:
            sort_by = "discovered_at"

        sql = f"""
            SELECT * FROM secrets {where}
            ORDER BY {sort_by} {direction}
            LIMIT ? OFFSET ?
        """
        rows = conn.execute(sql, params + [limit, offset]).fetchall()
        secrets = [_row_to_secret(r) for r in rows]
        return secrets, total

    def stream_secrets(
        self,
        filters: Dict[str, Any] = None,
        batch_size: int = 1000,
    ) -> Iterator[Secret]:
        """
        Stream secrets matching filters in batches.

        Never loads all secrets into memory. Yields one secret at a time,
        fetching from SQLite in configurable batch sizes. Designed for
        export endpoints that handle 100,000+ findings.
        """
        conn = self._get_conn()
        filters = filters or {}
        where, params = _build_where(filters)
        sql = f"SELECT * FROM secrets {where} ORDER BY discovered_at ASC"

        cursor = conn.execute(sql, params)
        while True:
            rows = cursor.fetchmany(batch_size)
            if not rows:
                break
            for row in rows:
                yield _row_to_secret(row)

    def stream_secrets_as_dicts(
        self,
        filters: Dict[str, Any] = None,
        include_raw: bool = False,
        batch_size: int = 1000,
    ) -> Iterator[Dict[str, Any]]:
        """Stream secrets as dicts (for JSON/CSV export)."""
        for secret in self.stream_secrets(filters, batch_size):
            yield secret.to_export_dict() if not include_raw else secret.to_dict(include_raw=True)

    # ── Metrics ─────────────────────────────────────────────────────

    def insert_metrics(self, metrics: Dict[str, Any]) -> str:
        """Store scan metrics."""
        conn = self._get_conn()
        metrics_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        scan_date = now[:10]
        conn.execute(
            "INSERT INTO scan_metrics (id, scan_date, metrics_json, created_at) VALUES (?, ?, ?, ?)",
            (metrics_id, scan_date, json.dumps(metrics), now),
        )
        conn.commit()
        return metrics_id

    def get_latest_metrics(self) -> Optional[Dict[str, Any]]:
        """Get the most recent scan metrics."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT metrics_json FROM scan_metrics ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
        if row is None:
            return None
        return json.loads(row[0])

    # ── Export Index ─────────────────────────────────────────────────

    def insert_export_index(self, export_date: str, export_dir: str, findings_count: int) -> str:
        """Record a daily export in the index."""
        conn = self._get_conn()
        export_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "INSERT INTO export_index (id, export_date, export_dir, findings_count, created_at) VALUES (?, ?, ?, ?, ?)",
            (export_id, export_date, export_dir, findings_count, now),
        )
        conn.commit()
        return export_id

    def get_export_history(self) -> List[Dict[str, Any]]:
        """Get all past exports for the index."""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM export_index ORDER BY export_date DESC"
        ).fetchall()
        return [dict(r) for r in rows]


# ── Helper Functions ────────────────────────────────────────────────

def _confidence_category(score: float) -> str:
    if score >= 90:
        return "critical"
    if score >= 70:
        return "high"
    if score >= 40:
        return "medium"
    if score >= 20:
        return "low"
    return "unlikely"


def _row_to_secret(row: sqlite3.Row) -> Secret:
    """Convert a database row to a Secret object."""
    metadata = {}
    if row["metadata_json"]:
        try:
            metadata = json.loads(row["metadata_json"])
        except (json.JSONDecodeError, TypeError):
            metadata = {}

    history = []
    if row["history_json"]:
        try:
            history_data = json.loads(row["history_json"])
            from models import HistoryEntry
            history = [
                HistoryEntry(
                    timestamp=h.get("timestamp", ""),
                    event=h.get("event", ""),
                    details=h.get("details", {}),
                )
                for h in history_data
            ]
        except (json.JSONDecodeError, TypeError):
            history = []

    return Secret(
        id=row["id"],
        source=row["source"],
        finding_target=row["finding_target"],
        repository=row["repository"],
        organization=row["organization"],
        branch=row["branch"],
        commit=row["commit_sha"],
        file=row["file"],
        line_number=row["line_number"],
        scanner=row["scanner"],
        collector=row["collector"],
        discovered_at=row["discovered_at"],
        last_seen=row["last_seen"],
        secret_family=row["secret_family"],
        secret_type=row["secret_type"],
        provider=row["provider"],
        confidence_score=row["confidence_score"],
        validation_level=ValidationLevel(row["validation_level"]),
        provider_status=row["provider_status"],
        verification_status=VerificationStatus(row["verification_status"]),
        verification_reason=row["verification_reason"],
        verified_at=row["verified_at"],
        masked_value=row["masked_value"],
        raw_value=row["raw_value"],
        metadata=metadata,
        history=history,
    )


def _build_where(filters: Dict[str, Any]) -> Tuple[str, List[Any]]:
    """
    Build SQL WHERE clause and parameters from filter dict.

    Supported filters:
      - source: exact match
      - repository: LIKE match
      - secret_type: exact match
      - secret_family: exact match
      - confidence_min: minimum confidence score
      - confidence_max: maximum confidence score
      - validation_level: exact match
      - verification_status: exact match
      - verified: maps to verification_status values (bool or string)
      - date_from: discovered_at >= date
      - date_to: discovered_at <= date
      - date: single date (discovered_at BETWEEN start and end of day)
      - provider: exact match
    """
    conditions = []
    params = []

    if filters.get("source"):
        conditions.append("source = ?")
        params.append(filters["source"])

    if filters.get("repository"):
        conditions.append("repository LIKE ?")
        params.append(f"%{filters['repository']}%")

    if filters.get("secret_type"):
        conditions.append("secret_type = ?")
        params.append(filters["secret_type"])

    if filters.get("secret_family"):
        conditions.append("secret_family = ?")
        params.append(filters["secret_family"])

    if filters.get("confidence_min") is not None:
        conditions.append("confidence_score >= ?")
        params.append(float(filters["confidence_min"]))
    if filters.get("confidence_max") is not None:
        conditions.append("confidence_score <= ?")
        params.append(float(filters["confidence_max"]))

    if filters.get("validation_level"):
        conditions.append("validation_level = ?")
        params.append(filters["validation_level"])

    verified = filters.get("verified")
    if verified is not None:
        if isinstance(verified, bool):
            if verified:
                conditions.append("verification_status IN (?, ?, ?, ?, ?, ?)")
                params.extend(["active", "valid_format", "expired", "revoked", "disabled", "insufficient_scope"])
            else:
                conditions.append("verification_status IN (?, ?, ?)")
                params.extend(["unknown", "invalid", "unsupported"])
        elif isinstance(verified, str):
            conditions.append("verification_status = ?")
            params.append(verified)

    if filters.get("verification_status"):
        conditions.append("verification_status = ?")
        params.append(filters["verification_status"])

    if filters.get("date_from"):
        conditions.append("discovered_at >= ?")
        params.append(filters["date_from"])
    if filters.get("date_to"):
        conditions.append("discovered_at <= ?")
        params.append(filters["date_to"])

    if filters.get("date"):
        date = filters["date"]
        conditions.append("discovered_at >= ? AND discovered_at < ?")
        params.append(f"{date}T00:00:00")
        params.append(f"{date}T23:59:59.999999")

    if filters.get("provider"):
        conditions.append("provider = ?")
        params.append(filters["provider"])

    where_clause = ""
    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)

    return where_clause, params


# ── Global storage instance (lazy init) ─────────────────────────────

_storage: Optional[Storage] = None


def get_storage() -> Storage:
    """Get the global storage instance (dependency injection entry point)."""
    global _storage
    if _storage is None:
        _storage = Storage()
    return _storage


def reset_storage() -> None:
    """Reset storage for testing."""
    global _storage
    if _storage:
        _storage.close()
    _storage = None
