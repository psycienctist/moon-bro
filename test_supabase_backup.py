"""Offline regression checks for the LunaTicK Supabase logical backup snapshot."""

from __future__ import annotations

import hashlib
import io
import json
import zipfile

import supabase_backup


class FakeStore:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str, int, int]] = []
        self.rows = {
            "profiles": [
                {
                    "auth_subject": "auth0|owner",
                    "username": "owner_moon",
                    "display_name": "Owner Moon",
                    "email": "owner@example.test",
                }
            ],
            "journal_entries": [
                {
                    "id": 1,
                    "profile_auth_subject": "auth0|owner",
                    "phase": "Full Moon",
                    "prompt_type": "phase",
                    "content": "Private reflection.",
                    "created_at": "2026-08-22T00:00:00+00:00",
                }
            ],
            "boards": [{"slug": "general", "name": "General", "description": "Open discussion"}],
        }

    def list_backup_rows(self, table: str, columns: str, *, order: str, limit: int, offset: int):
        self.calls.append((table, columns, order, limit, offset))
        return self.rows.get(table, [])[offset : offset + limit]


def main() -> None:
    store = FakeStore()
    archive_bytes, manifest, filename = supabase_backup.create_verified_supabase_backup(store, page_size=1)

    assert filename.endswith(".zip")
    assert manifest["format"] == "LunaTicK Supabase logical snapshot"
    assert manifest["table_counts"]["profiles"] == 1
    assert manifest["table_counts"]["journal_entries"] == 1
    assert manifest["table_counts"]["boards"] == 1
    assert manifest["table_counts"]["chat_messages"] == 0
    assert manifest["archive_sha256"] == hashlib.sha256(archive_bytes).hexdigest()
    assert manifest["snapshot_filename"] == "snapshot.json"
    assert "Do not upload this archive directly into production" in manifest["recovery_note"]

    with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
        assert sorted(archive.namelist()) == ["manifest.json", "snapshot.json"]
        snapshot_bytes = archive.read("snapshot.json")
        snapshot = json.loads(snapshot_bytes.decode("utf-8"))
        inner_manifest = json.loads(archive.read("manifest.json").decode("utf-8"))

    assert inner_manifest["snapshot_sha256"] == hashlib.sha256(snapshot_bytes).hexdigest()
    assert snapshot["tables"]["profiles"][0]["auth_subject"] == "auth0|owner"
    assert snapshot["tables"]["journal_entries"][0]["content"] == "Private reflection."
    assert any(call[0] == "profiles" and call[4] == 0 for call in store.calls)
    assert any(call[0] == "profiles" and call[4] == 1 for call in store.calls)
    assert json.loads(supabase_backup.manifest_bytes(manifest).decode("utf-8"))["archive_sha256"] == manifest["archive_sha256"]
    assert supabase_backup.manifest_filename(filename).endswith(".manifest.json")

    print("Supabase logical backup snapshot, checksums, pagination, and manifest passed.")


if __name__ == "__main__":
    main()
