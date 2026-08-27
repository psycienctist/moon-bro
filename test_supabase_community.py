"""Offline regression checks for the Phase E Community Supabase cutover."""

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


class FakeCommunityStore:
    def __init__(self) -> None:
        self.created_board_posts: list[tuple[str, str, str, str]] = []
        self.created_chat_messages: list[tuple[str, str]] = []
        self.created_talk_posts: list[dict[str, Any]] = []
        self.created_comments: list[dict[str, Any]] = []
        self.votes: dict[tuple[str, int], str] = {}
        self.board_votes: dict[tuple[str, int], str] = {}
        self.seeded_boards: list[dict[str, str]] = []
        self.hidden_posts: list[int] = []

    def seed_boards(self, rows: list[dict[str, str]]) -> None:
        self.seeded_boards = list(rows)

    def list_boards(self) -> list[dict[str, str]]:
        return [{"slug": "general", "name": "🌙 General", "description": "Open discussion"}]

    def list_board_post_slugs(self) -> list[str]:
        return ["general", "general"]

    def create_board_post(self, slug: str, subject: str, title: str, content: str) -> dict[str, Any]:
        self.created_board_posts.append((slug, subject, title, content))
        return {"id": 1}

    def list_board_posts(self, slug: str | None, limit: int) -> list[dict[str, Any]]:
        return [
            {
                "id": 1,
                "board_slug": "general",
                "profile_auth_subject": "auth0|other",
                "title": "A title",
                "content": "A board reflection.",
                "created_at": "2026-08-22T00:00:00+00:00",
            }
        ]

    def get_board_post_votes(self, subject: str, post_ids: list[int]) -> dict[int, str]:
        return {
            post_id: vote_type
            for (voter_subject, post_id), vote_type in self.board_votes.items()
            if voter_subject == subject and post_id in post_ids
        }

    def set_board_post_vote(self, subject: str, post_id: int, vote_type: str | None) -> tuple[int, int]:
        key = (subject, post_id)
        if vote_type:
            self.board_votes[key] = vote_type
        else:
            self.board_votes.pop(key, None)
        votes = [value for (_, candidate_post_id), value in self.board_votes.items() if candidate_post_id == post_id]
        return votes.count("up"), votes.count("down")

    def create_chat_message(self, subject: str, content: str) -> dict[str, Any]:
        self.created_chat_messages.append((subject, content))
        return {"id": 2}

    def list_chat_messages(self, limit: int) -> list[dict[str, Any]]:
        return [
            {"id": 2, "profile_auth_subject": "auth0|other", "content": "Newer", "created_at": "2026-08-22T00:02:00+00:00"},
            {"id": 1, "profile_auth_subject": "auth0|current", "content": "Older", "created_at": "2026-08-22T00:01:00+00:00"},
        ]

    def create_talk_post(self, subject: str, content: str, sign: str, phase: str, anonymous: bool, image_path: str | None) -> dict[str, Any]:
        payload = {
            "id": 10,
            "profile_auth_subject": subject,
            "content": content,
            "user_moon_sign": sign,
            "current_moon_phase": phase,
            "is_anonymous": anonymous,
            "image_path": image_path,
        }
        self.created_talk_posts.append(payload)
        return payload

    def list_talk_posts(self, limit: int, phase_filter: str | None) -> list[dict[str, Any]]:
        return [
            {
                "id": 10,
                "profile_auth_subject": "auth0|current",
                "user_moon_sign": "Cancer",
                "current_moon_phase": "Full Moon",
                "content": "gratitude and hope",
                "image_path": None,
                "upvotes": 1,
                "downvotes": 0,
                "created_at": "2026-08-22T00:00:00+00:00",
                "is_anonymous": True,
                "is_hidden": False,
            },
            {
                "id": 11,
                "profile_auth_subject": "auth0|other",
                "user_moon_sign": "Leo",
                "current_moon_phase": "Full Moon",
                "content": "connection and joy",
                "image_path": None,
                "upvotes": 0,
                "downvotes": 0,
                "created_at": "2026-08-22T00:01:00+00:00",
                "is_anonymous": False,
                "is_hidden": False,
            },
        ]

    def create_talk_comment(self, post_id: int, subject: str, content: str, anonymous: bool) -> dict[str, Any]:
        payload = {"id": 20, "post_id": post_id, "profile_auth_subject": subject, "content": content, "is_anonymous": anonymous}
        self.created_comments.append(payload)
        return payload

    def list_talk_comments(self, post_id: int) -> list[dict[str, Any]]:
        return [
            {
                "id": 20,
                "post_id": post_id,
                "profile_auth_subject": "auth0|other",
                "content": "Thank you.",
                "created_at": "2026-08-22T00:01:00+00:00",
                "upvotes": 0,
                "downvotes": 0,
                "is_anonymous": False,
                "is_hidden": False,
            }
        ]

    def get_talk_vote(self, subject: str, post_id: int) -> str | None:
        return self.votes.get((subject, post_id))

    def set_talk_vote(self, subject: str, post_id: int, vote_type: str | None) -> tuple[int, int]:
        if vote_type:
            self.votes[(subject, post_id)] = vote_type
        else:
            self.votes.pop((subject, post_id), None)
        return (1, 0)

    def hide_talk_post(self, post_id: int) -> None:
        self.hidden_posts.append(post_id)

    def get_profile_by_auth_subject(self, subject: str) -> dict[str, Any] | None:
        return {"display_name": "Current Moon", "birth_date": "1990-01-01"}

    def update_profile_fields(self, subject: str, fields: dict[str, Any]) -> dict[str, Any]:
        return dict(fields)

    def get_public_profile_summaries(self, subjects: list[str]) -> dict[str, dict[str, str]]:
        return {
            "auth0|current": {"username": "current_moon", "display_name": "Current Moon", "avatar": "🌙"},
            "auth0|other": {"username": "other_moon", "display_name": "Other Moon", "avatar": "🪐"},
        }


fake_streamlit = types.SimpleNamespace(
    session_state=FakeSessionState(
        auth_subject="auth0|current",
        user_hash="current_hash",
        display_name="Current Moon",
    )
)
sys.modules["streamlit"] = fake_streamlit

boards = importlib.import_module("boards")
chat = importlib.import_module("chat_room")
talk = importlib.import_module("lunatick_talk_db")
store = FakeCommunityStore()

for module in (boards, chat, talk):
    module._using_supabase_backend = lambda: True
    module._supabase = lambda: store

boards.init_boards_db()
assert store.seeded_boards[0]["slug"] == "general"
assert boards.list_boards()[0]["post_count"] == 2
boards.create_post("general", "current_hash", "Ignored name", "  A title  ", " A board reflection. ")
assert store.created_board_posts == [("general", "auth0|current", "A title", "A board reflection.")]
board_posts = boards.list_posts("general", viewer_hash="current_hash")
assert board_posts[0]["author"] == "other_moon"
assert board_posts[0]["author_reference"] == "auth0|other"
assert boards.set_post_vote("current_hash", 1, "up") == (1, 0)
assert boards.list_posts("general", viewer_hash="current_hash")[0]["viewer_vote"] == "up"
assert boards.set_post_vote("current_hash", 1, "down") == (0, 1)
assert boards.set_post_vote("current_hash", 1, None) == (0, 0)

assert chat.post_message("current_hash", "Ignored name", "  Hello chat  ") is True
assert store.created_chat_messages == [("auth0|current", "Hello chat")]
chat_messages = chat.recent_messages(40)
assert [row["content"] for row in chat_messages] == ["Older", "Newer"]
assert chat_messages[0]["author"] == "Current Moon"

post_id = talk.create_post("Ignored name", "  gratitude and hope  ", "Cancer", "Full Moon", True)
assert post_id == 10
assert store.created_talk_posts[-1]["profile_auth_subject"] == "auth0|current"
posts = talk.get_posts(limit=20, phase_filter="Full Moon")
assert posts[0][2] == "Anonymous"
assert posts[1][2] == "Other Moon"
assert "auth0|current" not in posts[0][2]
assert "gratitude" in talk.get_lunatick_pulse("Full Moon")

talk.create_comment(10, "Ignored name", "  Thank you.  ", False)
assert store.created_comments[-1]["profile_auth_subject"] == "auth0|current"
comments = talk.get_comments(10)
assert comments[0][3] == "Other Moon"
talk.set_user_vote("current_hash", 10, "up")
assert talk.get_user_vote("current_hash", 10) == "up"
talk.set_user_vote("current_hash", 10, None)
assert talk.get_user_vote("current_hash", 10) is None
talk.hide_post(10)
assert store.hidden_posts == [10]

print("Supabase Community Chat, Boards, and LunaTicK Talk cutover passed.")
