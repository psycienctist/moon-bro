"""Offline regression check for LunaTicK SQLite backup snapshots."""

from __future__ import annotations

import json
import os
import sqlite3
import tempfile

import database_backup


def main() -> None:
    with tempfile.TemporaryDirectory() as directory:
        source_path = os.path.join(directory, "source.db")
        source = sqlite3.connect(source_path)
        source.execute("CREATE TABLE profile_test (username TEXT PRIMARY KEY, bio TEXT)")
        source.execute(
            "INSERT INTO profile_test (username, bio) VALUES (?, ?)",
            ("moon_orbit", "Safe beneath the same sky."),
        )
        source.commit()
        source.close()

        backup_bytes, manifest, filename = database_backup.create_verified_backup(source_path)
        assert filename.endswith(".sqlite")
        assert manifest["integrity_check"] == "ok"
        assert manifest["table_counts"] == {"profile_test": 1}
        assert len(manifest["sha256"]) == 64
        assert len(backup_bytes) == manifest["database_bytes"]

        restored_path = os.path.join(directory, "restored.db")
        with open(restored_path, "wb") as restored_file:
            restored_file.write(backup_bytes)
        restored = sqlite3.connect(restored_path)
        restored_row = restored.execute("SELECT username, bio FROM profile_test").fetchone()
        restored.close()
        assert restored_row == ("moon_orbit", "Safe beneath the same sky.")

        manifest_data = json.loads(database_backup.manifest_bytes(manifest).decode("utf-8"))
        assert manifest_data["sha256"] == manifest["sha256"]

    print("SQLite backup snapshot, integrity check, manifest, and recovery test passed.")


if __name__ == "__main__":
    main()
