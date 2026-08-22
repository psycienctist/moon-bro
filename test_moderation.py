"""Offline regression checks for founder-only LunaTicK Community moderation."""

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


fake_streamlit = types.SimpleNamespace(
    session_state=FakeSessionState(
        auth_subject="auth0|founder",
        email="founder@example.test",
    ),
    secrets={
        "storage": {"data_backend": "supabase"},
        "backup": {"owner_email": "founder@example.test"},
    },
)
sys.modules["streamlit"] = fake_streamlit

moderation = importlib.import_module("moderation")


class FakeStore:
    def __init__(self) -> None:
        self.roles: dict[str, dict[str, Any]] = {}
        self.visibility: list[tuple[str, int, bool]] = []
        self.deleted: list[tuple[str, int]] = []
        self.actions: list[dict[str, Any]] = []

    def get_moderator_role(self, subject: str):
        return self.roles.get(subject)

    def upsert_moderator_role(self, subject: str, role: str, granted_by: str):
        self.roles[subject] = {"auth_subject": subject, "role": role, "granted_by_auth_subject": granted_by}
        return self.roles[subject]

    def set_moderation_visibility(self, target_type: str, target_id: int, hidden: bool):
        self.visibility.append((target_type, target_id, hidden))

    def delete_moderation_content(self, target_type: str, target_id: int):
        self.deleted.append((target_type, target_id))

    def log_moderation_action(self, actor: str, target_type: str, action: str, **kwargs: Any):
        self.actions.append({"actor": actor, "target_type": target_type, "action": action, **kwargs})


store = FakeStore()
moderation._store = lambda: store

assert moderation.current_role() == "founder"
assert store.roles["auth0|founder"]["role"] == "founder"
assert moderation.is_moderator() is True

fake_streamlit.session_state["email"] = "moderator@example.test"
store.roles["auth0|founder"] = {"auth_subject": "auth0|founder", "role": "moderator"}
assert moderation.current_role() == "moderator"

row = {"id": 22, "profile_auth_subject": "auth0|member", "is_hidden": False, "content": "Public record"}
moderation._act_on_content(store, "auth0|founder", "board_post", row, "hide", "Violation")
assert store.visibility == [("board_post", 22, True)]
assert store.actions[-1]["action"] == "hide"
assert store.actions[-1]["target_auth_subject"] == "auth0|member"
assert "content" not in store.actions[-1]["details"]

moderation._act_on_content(store, "auth0|founder", "chat_message", row, "delete", "Removal")
assert store.deleted == [("chat_message", 22)]
assert store.actions[-1]["action"] == "delete"
assert "journal" not in " ".join(str(item) for item in store.actions).lower()

assert moderation._record_title("talk_post", {"is_anonymous": True}, "Private Name") == "Talk post · Anonymous"
assert moderation._record_title("talk_comment", {"is_anonymous": False}, "Public Name") == "Talk comment · Public Name"

print("Founder moderation roles, public-content actions, and Journal exclusion passed.")
