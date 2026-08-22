"""Offline checks for LunaTicK's Auth0-managed password recovery flow."""

from __future__ import annotations

import sys
import types
from typing import Any


fake_streamlit = types.SimpleNamespace(
    secrets={
        "auth": {
            "auth0": {
                "server_metadata_url": "https://example.us.auth0.com/.well-known/openid-configuration",
                "client_id": "lunatick-client-id",
                "database_connection": "Username-Password-Authentication",
            }
        }
    },
    session_state={},
)
sys.modules["streamlit"] = fake_streamlit

import auth


class FakeResponse:
    def __init__(self, ok: bool) -> None:
        self.ok = ok


class FakeHttp:
    def __init__(self, response: FakeResponse) -> None:
        self.response = response
        self.calls: list[dict[str, Any]] = []

    def post(self, url: str, **kwargs: Any) -> FakeResponse:
        self.calls.append({"url": url, **kwargs})
        return self.response


http = FakeHttp(FakeResponse(True))
sent, message = auth.request_password_reset("  Moon.User@Example.com ", http)
assert sent is True
assert "If an account exists" in message
assert http.calls == [
    {
        "url": "https://example.us.auth0.com/dbconnections/change_password",
        "json": {
            "client_id": "lunatick-client-id",
            "email": "moon.user@example.com",
            "connection": "Username-Password-Authentication",
        },
        "timeout": 15,
    }
]
assert "password" not in http.calls[0]["json"]

http = FakeHttp(FakeResponse(True))
sent, message = auth.request_password_reset("not-an-email", http)
assert sent is False
assert message == "Enter a valid email address."
assert http.calls == []

http = FakeHttp(FakeResponse(False))
sent, message = auth.request_password_reset("moon.user@example.com", http)
assert sent is False
assert "could not be started" in message

fake_streamlit.secrets = {"auth": {"auth0": {"client_id": "missing-metadata"}}}
sent, message = auth.request_password_reset("moon.user@example.com", FakeHttp(FakeResponse(True)))
assert sent is False
assert "temporarily unavailable" in message

print("Auth0 password-recovery endpoint, privacy message, and configuration checks passed.")
