"""Offline regression checks for the Phase C Supabase profile cutover."""

from __future__ import annotations

import importlib
import sys
import types
from typing import Any


class FakeUser(dict):
    @property
    def is_logged_in(self) -> bool:
        return True


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
        self.profile: dict[str, Any] | None = None
        self.upserts: list[dict[str, Any]] = []

    def get_profile_by_auth_subject(self, subject: str) -> dict[str, Any] | None:
        if self.profile and self.profile["auth_subject"] == subject:
            return dict(self.profile)
        return None

    def upsert_profile(self, profile: dict[str, Any]) -> dict[str, Any]:
        self.profile = dict(profile)
        self.upserts.append(dict(profile))
        return dict(profile)

    def username_is_available(self, username: str, subject: str) -> bool:
        return not self.profile or self.profile["auth_subject"] == subject or self.profile["username"] != username

    def get_public_profile_by_username(self, username: str) -> dict[str, str] | None:
        if not self.profile or self.profile["username"] != username:
            return None
        return {
            "username": self.profile["username"],
            "display_name": self.profile["display_name"],
            "avatar": self.profile["avatar"],
            "bio": self.profile["bio"],
        }


fake_streamlit = types.SimpleNamespace(
    session_state=FakeSessionState(),
    user=FakeUser(
        {
            "sub": "auth0|fresh-supabase-user",
            "email": "fresh.moon@example.test",
            "name": "Fresh Moon",
        }
    ),
    login=lambda provider: None,
    logout=lambda: None,
)
sys.modules["streamlit"] = fake_streamlit

auth = importlib.import_module("auth")
store = FakeStore()
auth.using_supabase_backend = lambda: True
auth._supabase = lambda: store

first = auth.native_user_from_identity()
assert first is not None
assert first["auth_subject"] == "auth0|fresh-supabase-user"
assert first["username"] == auth._default_username(first["user_hash"])
assert store.profile is not None
assert store.profile["email"] == "fresh.moon@example.test"
assert store.profile["birth_date"] is None

auth.apply_user_to_session(first)
saved, message = auth.update_presence_profile(
    "fresh_orbit", "Fresh Orbit", "🪐", "A fresh start in the lunar commons."
)
assert saved is True
assert message == "Profile saved."
assert store.profile is not None
assert store.profile["username"] == "fresh_orbit"
assert store.profile["display_name"] == "Fresh Orbit"
assert store.profile["avatar"] == "🪐"
assert store.profile["email"] == "fresh.moon@example.test"

public_profile = auth.get_public_profile("@FRESH_ORBIT")
assert public_profile == {
    "username": "fresh_orbit",
    "display_name": "Fresh Orbit",
    "avatar": "🪐",
    "bio": "A fresh start in the lunar commons.",
}
assert "email" not in public_profile
assert "auth_subject" not in public_profile

print("Supabase fresh-profile, Settings, and public-lookup cutover passed.")
