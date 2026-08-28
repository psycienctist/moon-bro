from __future__ import annotations

import importlib
import sys
import types


class FakeSessionState(dict):
    def __getattr__(self, name: str):
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __setattr__(self, name: str, value):
        self[name] = value


class FakeStore:
    def __init__(self) -> None:
        self.created_threads: list[tuple[str, str]] = []
        self.created_messages: list[tuple[int, str, str, str]] = []

    def list_accepted_card_contacts(self, member_id: str) -> list[str]:
        return ["auth0|friend"] if member_id == "auth0|viewer" else ["auth0|viewer"] if member_id == "auth0|friend" else []

    def get_or_create_direct_message_thread(self, viewer: str, friend: str) -> dict:
        self.created_threads.append((viewer, friend))
        return {"id": 41}

    def list_direct_messages_for_participant(self, thread_id: int, participant: str) -> list[dict]:
        assert (thread_id, participant) == (41, "auth0|viewer")
        return [{"id": 1, "sender_name": "Friend Moon", "content": "Welcome!", "created_at": "2026-08-28T01:00:00+00:00"}]

    def create_direct_message(self, thread_id: int, sender: str, sender_name: str, content: str) -> dict:
        self.created_messages.append((thread_id, sender, sender_name, content))
        return {"id": 2}


fake_streamlit = types.SimpleNamespace(
    session_state=FakeSessionState(auth_subject="auth0|viewer", display_name="Viewer Moon")
)
sys.modules["streamlit"] = fake_streamlit
messages = importlib.import_module("direct_messages")
store = FakeStore()
messages._using_supabase_backend = lambda: True
messages._store = lambda: store

assert messages.can_message_member("auth0|friend") is True
assert messages.can_message_member("auth0|stranger") is False
assert messages.can_message_member("auth0|viewer") is False
assert messages.open_member_conversation("auth0|friend") == {"id": 41}
assert store.created_threads == [("auth0|viewer", "auth0|friend")]
assert messages.open_member_conversation("auth0|stranger") is None
assert messages.list_member_messages(41, "auth0|friend")[0]["content"] == "Welcome!"
assert messages.list_member_messages(41, "auth0|stranger") == []
assert messages.send_member_message(41, "auth0|friend", "Hello there") is True
assert store.created_messages == [(41, "auth0|viewer", "Viewer Moon", "Hello there")]
assert messages.send_member_message(41, "auth0|stranger", "Nope") is False
assert messages.send_member_message(41, "auth0|friend", "") is False
assert messages.send_member_message(41, "auth0|friend", "x" * 1201) is False
print("Profile direct-message connection gate checks passed.")
