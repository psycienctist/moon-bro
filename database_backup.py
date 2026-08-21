"""Safe, owner-triggered SQLite export support for LunaTicK alpha data."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DB = "lunatick.db"


def _table_counts(conn: sqlite3.Connection) -> dict[str, int]:
    """Return row counts for every user table in a snapshot."""
    tables = [
        row[0]
        for row in conn.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
            """
        ).fetchall()
    ]
    counts: dict[str, int] = {}
    for table in tables:
        quoted_table = '"' + table.replace('"', '""') + '"'
        counts[table] = int(conn.execute(f"SELECT COUNT(*) FROM {quoted_table}").fetchone()[0])
    return counts


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_handle:
        for chunk in iter(lambda: file_handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def create_verified_backup(source_db: str = DB) -> tuple[bytes, dict[str, Any], str]:
    """Create an online SQLite snapshot and return bytes, manifest, and filename.

    SQLite's backup API copies a consistent snapshot even while the Streamlit app
    has the database open. The source file is never modified.
    """
    source_path = Path(source_db)
    if not source_path.exists():
        raise FileNotFoundError(
            "No local LunaTicK database exists in this runtime yet. "
            "Sign in and save a profile before creating a backup."
        )

    created_at = datetime.now(timezone.utc)
    filename = f"lunatick_sqlite_backup_{created_at.strftime('%Y%m%dT%H%M%SZ')}.sqlite"

    with tempfile.TemporaryDirectory(prefix="lunatick_backup_") as temporary_directory:
        snapshot_path = Path(temporary_directory) / filename
        source = sqlite3.connect(source_path)
        destination = sqlite3.connect(snapshot_path)
        try:
            source.backup(destination)
        finally:
            destination.close()
            source.close()

        verify_conn = sqlite3.connect(snapshot_path)
        try:
            integrity_result = verify_conn.execute("PRAGMA integrity_check").fetchone()[0]
            if integrity_result.lower() != "ok":
                raise RuntimeError(f"SQLite integrity check failed: {integrity_result}")
            table_counts = _table_counts(verify_conn)
        finally:
            verify_conn.close()

        backup_bytes = snapshot_path.read_bytes()
        manifest = {
            "format": "LunaTicK SQLite snapshot",
            "created_at_utc": created_at.isoformat(),
            "database_filename": filename,
            "database_bytes": len(backup_bytes),
            "sha256": _file_sha256(snapshot_path),
            "integrity_check": "ok",
            "table_counts": table_counts,
            "restore_note": "Keep this .sqlite file unchanged. Open it with SQLite or restore it by replacing the target lunatick.db only while the application is stopped.",
        }
        return backup_bytes, manifest, filename


def manifest_bytes(manifest: dict[str, Any]) -> bytes:
    """Serialize recovery metadata as an adjacent downloadable JSON file."""
    return (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")


def manifest_filename(database_filename: str) -> str:
    return database_filename.replace(".sqlite", ".manifest.json")
