"""Owner-triggered, verified logical Supabase export support for LunaTicK."""

from __future__ import annotations

import hashlib
import io
import json
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import supabase_store


@dataclass(frozen=True)
class SnapshotTable:
    """One known LunaTicK table and its deterministic export order."""

    name: str
    columns: str
    order: str


# This fixed catalog deliberately contains every active application table, but
# never Supabase system tables, authentication-provider data, or credentials.
SNAPSHOT_TABLES = (
    SnapshotTable(
        "profiles",
        "auth_subject,user_hash,username,display_name,avatar,bio,email,birth_date,birth_time,"
        "birth_place,lat,lon,utc_offset,hd_profile,hd_authority,created_at,updated_at",
        "auth_subject.asc",
    ),
    SnapshotTable(
        "journal_entries",
        "id,profile_auth_subject,phase,prompt_type,content,created_at",
        "id.asc",
    ),
    SnapshotTable("boards", "slug,name,description,created_at", "slug.asc"),
    SnapshotTable(
        "board_posts",
        "id,board_slug,profile_auth_subject,title,content,created_at,updated_at,is_hidden",
        "id.asc",
    ),
    SnapshotTable(
        "chat_messages",
        "id,profile_auth_subject,content,created_at,is_hidden",
        "id.asc",
    ),
    SnapshotTable(
        "lunatick_talk_posts",
        "id,profile_auth_subject,user_moon_sign,current_moon_phase,content,image_path,upvotes,"
        "downvotes,created_at,is_anonymous,is_hidden",
        "id.asc",
    ),
    SnapshotTable(
        "lunatick_talk_comments",
        "id,post_id,profile_auth_subject,content,upvotes,downvotes,created_at,is_anonymous,is_hidden",
        "id.asc",
    ),
    SnapshotTable(
        "user_votes",
        "profile_auth_subject,post_id,vote_type,created_at",
        "profile_auth_subject.asc,post_id.asc",
    ),
    SnapshotTable(
        "card_trades",
        "id,sender_auth_subject,receiver_auth_subject,message,status,created_at,resolved_at",
        "id.asc",
    ),
    SnapshotTable(
        "migration_log",
        "id,run_id,stage,severity,entity,source_count,target_count,details,created_at",
        "id.asc",
    ),
)


def _json_bytes(value: Any) -> bytes:
    """Serialize a portable deterministic JSON document."""
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_all_rows(
    store: supabase_store.SupabaseStore, table: SnapshotTable, page_size: int
) -> list[dict[str, Any]]:
    """Read one approved table in deterministic pages from the server-only adapter."""
    rows: list[dict[str, Any]] = []
    offset = 0
    while True:
        page = store.list_backup_rows(
            table.name,
            table.columns,
            order=table.order,
            limit=page_size,
            offset=offset,
        )
        rows.extend(page)
        if len(page) < page_size:
            return rows
        offset += len(page)


def create_verified_supabase_backup(
    store: supabase_store.SupabaseStore, page_size: int = 500
) -> tuple[bytes, dict[str, Any], str]:
    """Create a portable LunaTicK Supabase logical snapshot and external manifest.

    The source is accessed only through the server-side service credential. The
    returned ZIP contains no credential. Because the REST API cannot wrap reads
    from every table in one database transaction, this is a best-effort logical
    snapshot; the manifest records the exact read window and per-table counts.
    Create a fresh export after periods of active writing.
    """
    started_at = datetime.now(timezone.utc)
    page_size = max(1, min(int(page_size), 1000))
    tables: dict[str, list[dict[str, Any]]] = {}
    table_counts: dict[str, int] = {}

    for table in SNAPSHOT_TABLES:
        rows = _read_all_rows(store, table, page_size)
        tables[table.name] = rows
        table_counts[table.name] = len(rows)

    completed_at = datetime.now(timezone.utc)
    snapshot = {
        "format": "LunaTicK Supabase logical snapshot",
        "format_version": 1,
        "snapshot_started_at_utc": started_at.isoformat(),
        "snapshot_completed_at_utc": completed_at.isoformat(),
        "tables": tables,
    }
    snapshot_bytes = _json_bytes(snapshot)
    filename = f"lunatick_supabase_backup_{completed_at.strftime('%Y%m%dT%H%M%SZ')}.zip"

    inner_manifest = {
        "format": "LunaTicK Supabase logical snapshot",
        "format_version": 1,
        "snapshot_filename": "snapshot.json",
        "snapshot_sha256": _sha256(snapshot_bytes),
        "snapshot_started_at_utc": started_at.isoformat(),
        "snapshot_completed_at_utc": completed_at.isoformat(),
        "table_counts": table_counts,
        "consistency_note": (
            "Application-level logical export. It is not a globally transactional database dump; "
            "create a fresh snapshot after active writing before a recovery operation."
        ),
        "recovery_note": (
            "Do not upload this archive directly into production. Preserve the ZIP and external "
            "manifest unchanged. Recover first into a controlled Supabase environment, validate "
            "the snapshot hash and row counts, stop application writes, then use an explicitly "
            "reviewed restore procedure."
        ),
    }

    archive_buffer = io.BytesIO()
    with zipfile.ZipFile(archive_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("snapshot.json", snapshot_bytes)
        archive.writestr("manifest.json", _json_bytes(inner_manifest))
    backup_bytes = archive_buffer.getvalue()

    manifest = {
        **inner_manifest,
        "archive_filename": filename,
        "archive_bytes": len(backup_bytes),
        "archive_sha256": _sha256(backup_bytes),
    }
    return backup_bytes, manifest, filename


def manifest_bytes(manifest: dict[str, Any]) -> bytes:
    """Serialize recovery metadata as a separate, downloadable JSON file."""
    return _json_bytes(manifest)


def manifest_filename(archive_filename: str) -> str:
    """Return the adjacent manifest filename for a logical snapshot archive."""
    return archive_filename.replace(".zip", ".manifest.json")
