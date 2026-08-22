"""Offline regression checks for the Phase F private Journal Supabase cutover."""

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
                "phase": "Full Moon",
                "prompt_type": "phase",
                "content": "Second private reflection.",
                "created_at": "2026-08-22T00:02:00+00:00",
            },
            {
                "id": 1,
                "phase": "Waxing Gibbous",
                "prompt_type": "free",
                "content": "First private reflection.",
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
    session_state=FakeSessionState(
        auth_subject="auth0|current",
        user_hash="current_hash",
        current_phase="Full Moon",
        sun_sign="Cancer",
        moon_sign="Pisces",
    )
)
sys.modules["streamlit"] = fake_streamlit

journal = importlib.import_module("journal")
store = FakeJournalStore()
journal._using_supabase_backend = lambda: True
journal._supabase = lambda: store

journal.init_db()
journal.save_entry("Full Moon", "phase", "  A private entry.  ")
assert store.created == [("auth0|current", "Full Moon", "phase", "A private entry.")]
entries = journal.get_recent_entries(limit=2)
assert entries == [
    ("Full Moon", "phase", "Second private reflection.", "2026-08-22T00:02:00+00:00"),
    ("Waxing Gibbous", "free", "First private reflection.", "2026-08-21T00:01:00+00:00"),
]
assert store.last_list_subject == "auth0|current"
assert store.last_limit == 2
assert "auth0|current" not in str(entries)

reflection = importlib.import_module("daily_reflection")
reflection.talk_db.get_lunatick_pulse = lambda phase: "Community pulse."
reflection.journal_ui.get_recent_entries = journal.get_recent_entries
context = reflection.gather_context()
assert context["pulse"] == "Community pulse."
assert "Second private reflection" in context["journal_summary"]

print("Supabase Journal owner-only persistence and reflection compatibility passed.")
