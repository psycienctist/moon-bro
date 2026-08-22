"""Offline regression check for LunaTicK profile presence persistence."""

from __future__ import annotations

import os
import sqlite3
import sys
import tempfile
import types


class SessionState(dict):
    """Tiny attribute-accessible stand-in for Streamlit session state."""

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __setattr__(self, name, value):
        self[name] = value


fake_streamlit = types.SimpleNamespace(session_state=SessionState())
sys.modules["streamlit"] = fake_streamlit

import auth  # noqa: E402


def make_legacy_database(path: str) -> None:
    """Simulate the pre-presence schema that existing alpha users have."""
    conn = sqlite3.connect(path)
    conn.execute(
        """
        CREATE TABLE oidc_identities (
            subject TEXT PRIMARY KEY,
            user_hash TEXT UNIQUE NOT NULL,
            email TEXT,
            display_name TEXT,
            birth_date TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        INSERT INTO oidc_identities (subject, user_hash, email, display_name)
        VALUES ('auth0|alpha', 'abc123def456', 'alpha@example.com', 'Alpha Moon')
        """
    )
    conn.commit()
    conn.close()


def main() -> None:
    with tempfile.TemporaryDirectory() as directory:
        database_path = os.path.join(directory, "lunatick-test.db")
        make_legacy_database(database_path)
        auth.DB = database_path
        auth.init_auth_db()

        fake_streamlit.session_state.clear()
        fake_streamlit.session_state.auth_subject = "auth0|alpha"
        fake_streamlit.session_state.user_hash = "abc123def456"
        fake_streamlit.session_state.email = "alpha@example.test"

        saved, message = auth.update_presence_profile(
            "alpha_orbit", "Alpha Moon", "🪐", "Listening to the tides."
        )
        assert saved, message
        assert fake_streamlit.session_state.username == "alpha_orbit"
        assert fake_streamlit.session_state.avatar == "🪐"
        assert fake_streamlit.session_state.bio == "Listening to the tides."

        conn = sqlite3.connect(database_path)
        row = conn.execute(
            "SELECT username, display_name, avatar, bio FROM oidc_identities WHERE subject='auth0|alpha'"
        ).fetchone()
        assert row == ("alpha_orbit", "Alpha Moon", "🪐", "Listening to the tides.")

        public_profile = auth.get_public_profile("@ALPHA_ORBIT")
        assert public_profile == {
            "username": "alpha_orbit",
            "display_name": "Alpha Moon",
            "avatar": "🪐",
            "bio": "Listening to the tides.",
        }
        assert "email" not in public_profile
        assert "birth_date" not in public_profile
        assert auth.get_public_profile("not-a-valid-handle") is None
        assert auth.get_public_profile("missing_user") is None

        conn.execute(
            """
            INSERT INTO oidc_identities (subject, user_hash, username, display_name, avatar)
            VALUES ('auth0|beta', '987654abcdef', 'taken_name', 'Beta Moon', '🌙')
            """
        )
        conn.commit()
        conn.close()

        saved, message = auth.update_presence_profile(
            "alpha_orbit", "alpha@example.test", "🪐", ""
        )
        assert not saved and "email address" in message

        saved, message = auth.update_presence_profile(
            "alpha_orbit", "alpha", "🪐", ""
        )
        assert not saved and "different from your email" in message

        saved, message = auth.update_presence_profile(
            "taken_name", "Alpha Moon", "🪐", ""
        )
        assert not saved and "already claimed" in message

        saved, message = auth.update_presence_profile(
            "Too-Many-Dashes", "Alpha Moon", "🪐", ""
        )
        assert not saved and "lowercase" in message

    print("Profile presence migration and persistence checks passed.")


if __name__ == "__main__":
    main()
