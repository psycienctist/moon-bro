"""Offline regression checks for LunaTicK's owner-only free-writing Journal."""

from __future__ import annotations

import importlib
import sys
import types
from typing import Any


class FakeSessionState(dict):
    def __getattr__(self, name: str) -> Any:
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __setattr__(self, name: str, value: Any) -> None:
        self[name] = value


class FakeJournalStore:
    def __init__(self) -> None:
        self.created: list[tuple[str, str, str, str]] = []
        self.entries = [
            {
                "id": 2,
                "phase": "Private entry",
                "prompt_type": "free_write",
                "content": "Second private entry.",
                "created_at": "2026-08-22T00:02:00+00:00",
            },
            {
                "id": 1,
                "phase": "Private entry",
                "prompt_type": "free_write",
                "content": "First private entry.",
                "created_at": "2026-08-21T00:01:00+00:00",
            },
        ]
        self.last_list_subject = ""
        self.last_limit = 0

    def create_journal_entry(self, subject: str, phase: str, prompt_type: str, content: str) -> dict[str, Any]:
        self.created.append((subject, phase, prompt_type, content))
        return {"id": len(self.created), "profile_auth_subject": subject}

    def list_journal_entries(self, subject: str, limit: int) -> list[dict[str, Any]]:
        self.last_list_subject = subject
        self.last_limit = limit
        return list(self.entries[:limit])


fake_streamlit = types.SimpleNamespace(
    session_state=FakeSessionState(auth_subject="auth0|current", user_hash="current_hash")
)
sys.modules["streamlit"] = fake_streamlit

journal = importlib.import_module("journal")
store = FakeJournalStore()
journal._using_supabase_backend = lambda: True
journal._supabase = lambda: store

journal.init_db()
journal.save_entry("  A private entry.  ")
assert store.created == [("auth0|current", "Private entry", "free_write", "A private entry.")]
entries = journal.get_recent_entries(limit=2)
assert entries == [
    ("Second private entry.", "2026-08-22T00:02:00+00:00"),
    ("First private entry.", "2026-08-21T00:01:00+00:00"),
]
assert store.last_list_subject == "auth0|current"
assert store.last_limit == 2
assert "auth0|current" not in str(entries)

journal_source = open("journal.py", encoding="utf-8").read()
for retired_surface in ("daily_reflection", "record_practice_day", "prompt_mode", "current_phase"):
    assert retired_surface not in journal_source
assert '"Private entry", "free_write"' in journal_source

print("Supabase Journal owner-only free-writing persistence checks passed.")
