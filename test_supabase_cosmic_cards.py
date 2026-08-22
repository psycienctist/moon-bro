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
        assert direction == "incoming"
        return [
            {
                "id": 9,
                "sender_auth_subject": "auth0|other",
                "receiver_auth_subject": subject,
                "message": "Let us connect.",
                "status": "pending",
                "created_at": "2026-08-22T00:00:00+00:00",
            }
        ]

    def resolve_card_trade(self, trade_id: int, subject: str, accept: bool) -> bool:
        self.resolutions.append((trade_id, subject, accept))
        return True

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
assert my_card["hd_profile"]
assert my_card["hd_authority"]
assert store.profiles["auth0|current"]["hd_profile"] == my_card["hd_profile"]

updates_before_other_card = len(store.updates)
other_cards = cards.list_users_with_cards("current_hash")
assert len(other_cards) == 1
assert other_cards[0]["profile_auth_subject"] == "auth0|other"
assert len(store.updates) == updates_before_other_card

saved, note = cards.send_trade("current_hash", "auth0|other", "Let us connect.")
assert saved is True
assert note == "Trade (friend request) sent!"
assert store.trades == [("auth0|current", "auth0|other", "Let us connect.")]

incoming = cards.list_trades("current_hash", "incoming")
assert incoming[0]["sender"] == "auth0|other"
assert cards.resolve_trade(9, "current_hash", True) is True
assert store.resolutions == [(9, "auth0|current", True)]
assert cards.friends_of("current_hash") == ["auth0|other"]

print("Supabase Cosmic Card profile and card-trade cutover passed.")
