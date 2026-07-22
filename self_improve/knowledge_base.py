"""
Knowledge base for APIS self-improvement system.
Persists learned patterns, scanning success rates, and improvement history.
"""
import json
import logging
import sqlite3
from typing import List, Dict, Optional, Any
from datetime import datetime
from pathlib import Path
from config.settings import KNOWLEDGE_DB_FILE, DATA_DIR

logger = logging.getLogger(__name__)


class KnowledgeBase:
    """
    Persistent knowledge base that stores:
    - Key classification patterns (including AI-learned ones)
    - Scanning success rates by source/port
    - Improvement history
    - Failed attempts
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = str(db_path or KNOWLEDGE_DB_FILE)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize the SQLite database."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Key patterns table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS key_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                pattern TEXT NOT NULL,
                description TEXT,
                prefix TEXT,
                source TEXT,
                confidence REAL DEFAULT 0.0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Scanning success table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scanning_success (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                keys_found INTEGER DEFAULT 0,
                valid INTEGER DEFAULT 0,
                last_seen TEXT,
                UNIQUE(source)
            )
        """)

        # Improvements history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS improvements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                feature TEXT NOT NULL,
                code_changed TEXT,
                success BOOLEAN DEFAULT FALSE,
                details TEXT
            )
        """)

        # Failed attempts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS failed_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                feature TEXT NOT NULL,
                error TEXT,
                details TEXT
            )
        """)

        conn.commit()
        conn.close()
        logger.info(f"Knowledge base initialized at {self.db_path}")

    def add_pattern(self, name: str, pattern: str, description: str = "",
                    prefix: str = "[redacted]", source: str = "learned",
                    confidence: float = 0.0) -> bool:
        """Add a new key pattern to the knowledge base."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT OR REPLACE INTO key_patterns "
                "(name, pattern, description, prefix, source, confidence) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (name, pattern, description, prefix, source, confidence),
            )
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to add pattern: {e}")
            return False
        finally:
            conn.close()

    def get_patterns(self) -> List[Dict]:
        """Get all key patterns from the knowledge base."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM key_patterns ORDER BY created_at DESC")
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def update_scanning_success(self, source: str, keys_found: int,
                                valid: int) -> None:
        """Update scanning success metrics for a source."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO scanning_success (source, keys_found, valid, last_seen) "
            "VALUES (?, ?, ?, ?) "
            "ON CONFLICT(source) DO UPDATE SET "
            "keys_found = keys_found + ?, valid = valid + ?, last_seen = ?",
            (source, keys_found, valid, datetime.utcnow().isoformat(),
             keys_found, valid, datetime.utcnow().isoformat()),
        )
        conn.commit()
        conn.close()

    def get_scanning_success(self) -> List[Dict]:
        """Get scanning success rates."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM scanning_success ORDER BY keys_found DESC")
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def add_improvement(self, feature: str, code_changed: str = "",
                        success: bool = True, details: str = "") -> None:
        """Record an improvement attempt."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO improvements (date, feature, code_changed, success, details) "
            "VALUES (?, ?, ?, ?, ?)",
            (datetime.utcnow().isoformat(), feature, code_changed, success, details),
        )
        conn.commit()
        conn.close()

    def add_failed_attempt(self, feature: str, error: str,
                           details: str = "") -> None:
        """Record a failed improvement attempt."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO failed_attempts (date, feature, error, details) "
            "VALUES (?, ?, ?, ?)",
            (datetime.utcnow().isoformat(), feature, error, details),
        )
        conn.commit()
        conn.close()

    def get_improvement_history(self, limit: int = 50) -> List[Dict]:
        """Get improvement history."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM improvements ORDER BY date DESC LIMIT ?",
            (limit,),
        )
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def to_dict(self) -> Dict:
        """Export entire knowledge base as a dictionary (for JSON export)."""
        return {
            "key_patterns": self.get_patterns(),
            "scanning_success": self.get_scanning_success(),
            "improvements": self.get_improvement_history(),
        }

    def export_json(self, filepath: Optional[str] = None) -> str:
        """Export knowledge base to JSON file."""
        filepath = filepath or str(DATA_DIR / "knowledge_export.json")
        data = self.to_dict()
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2, default=str)
        return filepath
