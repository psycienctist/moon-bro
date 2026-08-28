"""Offline regression checks for the Phase D Cosmic Card Supabase cutover."""

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


class FakeStore:
    def __init__(self) -> None:
        self.current_subject = "auth0|current"
        self.profiles = {
            "auth0|current": {
                "auth_subject": "auth0|current",
                "user_hash": "current_hash",
                "display_name": "Current Moon",
                "birth_date": "1990-01-02",
                "birth_time": "13:30",
                "birth_place": "Austin, TX",
                "lat": 30.2672,
                "lon": -97.7431,
                "utc_offset": -6.0,
                "hd_profile": None,
                "hd_authority": None,
            },
            "auth0|other": {
                "auth_subject": "auth0|other",
                "user_hash": "other_hash",
                "display_name": "Other Moon",
                "birth_date": "1992-04-05",
                "birth_time": "09:15",
                "birth_place": "Denver, CO",
                "lat": 39.7392,
                "lon": -104.9903,
                "utc_offset": -7.0,
                "hd_profile": None,
                "hd_authority": None,
            },
        }
        self.updates: list[tuple[str, dict[str, Any]]] = []
        self.trades: list[tuple[str, str, str]] = []
        self.resolutions: list[tuple[int, str, bool]] = []
        self.seen_acknowledgements: list[str] = []

    def get_profile_by_auth_subject(self, subject: str) -> dict[str, Any] | None:
        profile = self.profiles.get(subject)
        return dict(profile) if profile else None

    def update_profile_fields(self, subject: str, fields: dict[str, Any]) -> dict[str, Any]:
        self.updates.append((subject, dict(fields)))
        self.profiles[subject].update(fields)
        return dict(self.profiles[subject])

    def list_card_profiles(self, exclude_subject: str) -> list[dict[str, Any]]:
        return [dict(profile) for subject, profile in self.profiles.items() if subject != exclude_subject]

    def has_pending_card_trade(self, sender: str, receiver: str) -> bool:
        return False

    def create_card_trade(self, sender: str, receiver: str, message: str) -> dict[str, Any]:
        self.trades.append((sender, receiver, message))
        return {"id": 1, "sender_auth_subject": sender, "receiver_auth_subject": receiver}

    def list_card_trades(self, subject: str, direction: str) -> list[dict[str, Any]]:
        assert subject == self.current_subject
        if direction == "incoming":
            return [
                {
                    "id": 9,
                    "sender_auth_subject": "auth0|other",
                    "receiver_auth_subject": subject,
                    "message": "Let us connect.",
                    "status": "pending",
                    "created_at": "2026-08-22T00:00:00+00:00",
                    "sender_seen_at": None,
                }
            ]
        assert direction == "outgoing"
        return [
            {
                "id": 10,
                "sender_auth_subject": subject,
                "receiver_auth_subject": "auth0|other",
                "message": "",
                "status": "accepted",
                "created_at": "2026-08-21T00:00:00+00:00",
                "resolved_at": "2026-08-22T00:00:00+00:00",
                "sender_seen_at": None,
            }
        ]

    def resolve_card_trade(self, trade_id: int, subject: str, accept: bool) -> bool:
        self.resolutions.append((trade_id, subject, accept))
        return True

    def mark_accepted_card_trades_seen(self, subject: str) -> int:
        self.seen_acknowledgements.append(subject)
        return 1

    def list_accepted_card_contacts(self, subject: str) -> list[str]:
        assert subject == self.current_subject
        return ["auth0|other"]


fake_streamlit = types.SimpleNamespace(
    session_state=FakeSessionState(
        auth_subject="auth0|current",
        user_hash="current_hash",
        display_name="Current Moon",
    )
)
sys.modules["streamlit"] = fake_streamlit

cards = importlib.import_module("cosmic_cards")
store = FakeStore()
cards._using_supabase_backend = lambda: True
cards._supabase = lambda: store

profile = cards.get_or_create_profile("current_hash")
assert profile["auth_subject"] == "auth0|current"
assert profile["birth_place"] == "Austin, TX"

cards.save_profile(
    "current_hash",
    "Current Moon",
    "1990-01-03",
    birth_time="14:45",
    birth_place="Dallas, TX",
    lat=32.7767,
    lon=-96.7970,
    utc_offset=-6.0,
)
subject, birth_update = store.updates[-1]
assert subject == "auth0|current"
assert birth_update["birth_date"] == "1990-01-03"
assert birth_update["birth_place"] == "Dallas, TX"
assert birth_update["lat"] == 32.7767
assert "user_hash" not in birth_update

my_card = cards.build_card("current_hash")
assert my_card is not None
assert my_card["profile_auth_subject"] == "auth0|current"
assert "hd_profile" not in my_card
assert "hd_authority" not in my_card
assert "rarity" not in my_card
assert my_card["natal"]["has_rising"] is True

updates_before_other_card = len(store.updates)
other_cards = cards.list_users_with_cards("current_hash")
assert len(other_cards) == 1
assert other_cards[0]["profile_auth_subject"] == "auth0|other"
assert "birth_date" not in other_cards[0]
assert "birth_time" not in other_cards[0]
assert "birth_place" not in other_cards[0]
assert "lat" not in other_cards[0]
assert "lon" not in other_cards[0]
assert len(store.updates) == updates_before_other_card

friend_card = cards.build_friend_card("current_hash", "auth0|other")
assert friend_card is not None
assert friend_card["display_name"] == "Other Moon"
for private_field in ("birth_date", "birth_time", "birth_place", "lat", "lon", "utc_offset", "auth_subject", "profile_auth_subject", "user_hash"):
    assert private_field not in friend_card

saved, note = cards.send_trade("current_hash", "auth0|other", "Let us connect.")
assert saved is True
assert note == "Card trade sent!"
assert store.trades == [("auth0|current", "auth0|other", "Let us connect.")]

incoming = cards.list_trades("current_hash", "incoming")
assert incoming[0]["sender"] == "auth0|other"
assert incoming[0]["sender_seen_at"] is None
outgoing = cards.list_trades("current_hash", "outgoing")
assert outgoing[0]["status"] == "accepted"
assert outgoing[0]["sender_seen_at"] is None
assert cards.mark_accepted_trades_seen("current_hash") == 1
assert store.seen_acknowledgements == ["auth0|current"]
assert cards.resolve_trade(9, "current_hash", True) is True
assert store.resolutions == [(9, "auth0|current", True)]
assert cards.friends_of("current_hash") == ["auth0|other"]

assert cards._has_actual_coordinates(None, None) is False
assert cards._has_actual_coordinates(0.0, 0.0) is False
assert cards._has_actual_coordinates(30.2672, -97.7431) is True
print("Supabase Cosmic Card single-face and share-safe collection checks passed.")
