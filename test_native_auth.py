"""Focused regression check for LunaTicK's native OIDC identity adapter."""

from __future__ import annotations

import importlib
import os
import sys
import tempfile
import types


class FakeUser(dict):
    @property
    def is_logged_in(self):
        return True


class FakeSessionState(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __setattr__(self, name, value):
        self[name] = value


logout_calls: list[bool] = []
fake_streamlit = types.SimpleNamespace(
    session_state=FakeSessionState(),
    user=FakeUser(
        {
            "sub": "auth0|alpha-user-001",
            "email": "moon.wanderer@example.test",
            "name": "Moon Wanderer",
        }
    ),
    login=lambda provider: None,
    logout=lambda: logout_calls.append(True),
)
sys.modules["streamlit"] = fake_streamlit

auth = importlib.import_module("auth")

with tempfile.TemporaryDirectory() as temp_dir:
    auth.DB = os.path.join(temp_dir, "lunatick.db")
    auth.init_auth_db()

    first = auth.native_user_from_identity()
    assert first is not None
    assert first["username"] == auth._default_username(first["user_hash"])
    assert first["display_name"] == "Moon Wanderer"
    assert first["auth_subject"] == "auth0|alpha-user-001"

    auth.apply_user_to_session(first)
    auth.update_user_profile(
        first["username"], "Luna Alpha", "1990-01-01"
    )

    fake_streamlit.session_state.clear()
    second = auth.native_user_from_identity()
    assert second is not None
    assert second["user_hash"] == first["user_hash"]
    assert second["display_name"] == "Luna Alpha"
    assert second["birth_date"] == "1990-01-01"

    auth.apply_user_to_session(second)
    auth.logout()
    assert fake_streamlit.session_state["is_authenticated"] is False
    assert fake_streamlit.session_state["user_hash"] == "anonymous"
    assert logout_calls == [True]

print("Native OIDC identity mapping and logout flow passed.")
