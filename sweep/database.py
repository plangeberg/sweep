"""SQLite database — schema, operations, WAL mode for crash safety."""

import sqlite3
import os
from datetime import datetime, timezone


SCHEMA_VERSION = 1

SCHEMA_SQL = """
-- Project metadata
CREATE TABLE IF NOT EXISTS metadata (
    key TEXT PRIMARY KEY,
    value TEXT
);

-- Crawled folders
CREATE TABLE IF NOT EXISTS folders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    parent_path TEXT,
    modified_at TEXT,
    created_at TEXT,
    discovered_at TEXT NOT NULL
);

-- Crawled files
CREATE TABLE IF NOT EXISTS files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    folder_id INTEGER NOT NULL REFERENCES folders(id),
    path TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    extension TEXT,
    size_bytes INTEGER,
    modified_at TEXT,
    created_at TEXT,
    content_hash TEXT,
    discovered_at TEXT NOT NULL
);

-- Resume tracking
CREATE TABLE IF NOT EXISTS crawl_state (
    path TEXT PRIMARY KEY,
    status TEXT NOT NULL CHECK(status IN ('pending', 'in_progress', 'complete', 'error')),
    file_count INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    updated_at TEXT NOT NULL
);

-- Error log (queryable)
CREATE TABLE IF NOT EXISTS errors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT NOT NULL,
    category TEXT NOT NULL,
    message TEXT,
    occurred_at TEXT NOT NULL
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_files_extension ON files(extension);
CREATE INDEX IF NOT EXISTS idx_files_folder_id ON files(folder_id);
CREATE INDEX IF NOT EXISTS idx_files_modified ON files(modified_at);
CREATE INDEX IF NOT EXISTS idx_folders_parent ON folders(parent_path);
CREATE INDEX IF NOT EXISTS idx_crawl_state_status ON crawl_state(status);
"""


def now_utc() -> str:
    """Current time as ISO 8601 UTC string."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def timestamp_to_utc(ts: float) -> str:
    """Convert a POSIX timestamp to ISO 8601 UTC string."""
    try:
        return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except (OSError, ValueError, OverflowError):
        return ""


class SweepDatabase:
    """SQLite database for crawl results. WAL mode for crash safety."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.executescript(SCHEMA_SQL)
        self._init_metadata()
        self.conn.commit()

    def _init_metadata(self):
        """Set metadata if not already present."""
        existing = self.conn.execute(
            "SELECT value FROM metadata WHERE key='schema_version'"
        ).fetchone()
        if not existing:
            self.conn.execute(
                "INSERT INTO metadata (key, value) VALUES ('schema_version', ?)",
                (str(SCHEMA_VERSION),),
            )
            self.conn.execute(
                "INSERT INTO metadata (key, value) VALUES ('created_at', ?)",
                (now_utc(),),
            )

    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.commit()
            self.conn.close()
            self.conn = None

    # --- Folder operations ---

    def insert_folder(self, path: str, name: str, parent_path: str,
                      modified_at: str, created_at: str) -> int:
        """Insert a folder record. Returns the folder ID."""
        cursor = self.conn.execute(
            """INSERT OR IGNORE INTO folders
               (path, name, parent_path, modified_at, created_at, discovered_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (path, name, parent_path, modified_at, created_at, now_utc()),
        )
        if cursor.lastrowid:
            return cursor.lastrowid
        # Already existed — get the ID
        row = self.conn.execute(
            "SELECT id FROM folders WHERE path = ?", (path,)
        ).fetchone()
        return row[0] if row else 0

    # --- File operations ---

    def insert_files_batch(self, files: list):
        """Bulk insert file records. Each item: (folder_id, path, name, ext, size, modified, created, hash)."""
        discovered = now_utc()
        self.conn.executemany(
            """INSERT OR IGNORE INTO files
               (folder_id, path, name, extension, size_bytes,
                modified_at, created_at, content_hash, discovered_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [(f[0], f[1], f[2], f[3], f[4], f[5], f[6], f[7], discovered)
             for f in files],
        )

    # --- Crawl state operations ---

    def set_dir_state(self, path: str, status: str,
                      file_count: int = 0, error_count: int = 0):
        """Set or update directory crawl state."""
        self.conn.execute(
            """INSERT INTO crawl_state (path, status, file_count, error_count, updated_at)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(path) DO UPDATE SET
                   status=excluded.status,
                   file_count=excluded.file_count,
                   error_count=excluded.error_count,
                   updated_at=excluded.updated_at""",
            (path, status, file_count, error_count, now_utc()),
        )

    def get_completed_dirs(self) -> set:
        """Return set of directory paths that are fully crawled."""
        rows = self.conn.execute(
            "SELECT path FROM crawl_state WHERE status = 'complete'"
        ).fetchall()
        return {row[0] for row in rows}

    def get_crawl_stats(self) -> dict:
        """Get summary stats for progress reporting."""
        total_files = self.conn.execute("SELECT COUNT(*) FROM files").fetchone()[0]
        total_folders = self.conn.execute("SELECT COUNT(*) FROM folders").fetchone()[0]
        total_errors = self.conn.execute("SELECT COUNT(*) FROM errors").fetchone()[0]

        state_counts = {}
        for row in self.conn.execute(
            "SELECT status, COUNT(*) FROM crawl_state GROUP BY status"
        ).fetchall():
            state_counts[row[0]] = row[1]

        return {
            "total_files": total_files,
            "total_folders": total_folders,
            "total_errors": total_errors,
            "dirs_complete": state_counts.get("complete", 0),
            "dirs_pending": state_counts.get("pending", 0),
            "dirs_in_progress": state_counts.get("in_progress", 0),
            "dirs_error": state_counts.get("error", 0),
        }

    # --- Error logging ---

    def log_error(self, path: str, category: str, message: str):
        """Log an error to the errors table."""
        self.conn.execute(
            "INSERT INTO errors (path, category, message, occurred_at) VALUES (?, ?, ?, ?)",
            (path, category, message, now_utc()),
        )

    # --- Commit ---

    def commit(self):
        """Commit current transaction."""
        self.conn.commit()

    # --- Query support ---

    def query_files(self, extension: str = None, path_prefix: str = None,
                    min_size: int = None, max_size: int = None,
                    limit: int = 100) -> list:
        """Query files with optional filters. Returns list of dicts."""
        conditions = []
        params = []

        if extension:
            ext = extension if extension.startswith(".") else f".{extension}"
            conditions.append("extension = ?")
            params.append(ext.lower())
        if path_prefix:
            conditions.append("path LIKE ?")
            params.append(f"{path_prefix}%")
        if min_size is not None:
            conditions.append("size_bytes >= ?")
            params.append(min_size)
        if max_size is not None:
            conditions.append("size_bytes <= ?")
            params.append(max_size)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        params.append(limit)

        rows = self.conn.execute(
            f"SELECT path, name, extension, size_bytes, modified_at FROM files {where} ORDER BY path LIMIT ?",
            params,
        ).fetchall()

        return [
            {"path": r[0], "name": r[1], "extension": r[2],
             "size_bytes": r[3], "modified_at": r[4]}
            for r in rows
        ]
