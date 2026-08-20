# auth.py
# Native Streamlit OIDC authentication for LunaTicK.
#
# Auth0 hosts the email-and-password account experience. Streamlit owns the
# secure identity cookie and restores it automatically for up to 30 days.
# No password or custom browser session token is stored by this application.

from __future__ import annotations

import hashlib
import sqlite3
from datetime import datetime
from typing import Any

import streamlit as st

DB = "lunatick.db"
AUTH_PROVIDER = "auth0"


def init_auth_db() -> None:
    """Create the local identity-to-profile mapping used by active app modules.

    The identity provider is the source of authentication. This small table only
    maps the provider's immutable subject to LunaTicK's existing user_hash and
    retains display/birth-profile values used by the current SQLite-backed alpha.
    """
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS oidc_identities (
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
    conn.commit()
    conn.close()


def _claim(name: str, default: Any = None) -> Any:
    """Read an OpenID Connect claim without assuming a concrete user object type."""
    try:
        value = st.user.get(name)
        return default if value is None else value
    except Exception:
        try:
            value = getattr(st.user, name)
            return default if value is None else value
        except Exception:
            return default


def _native_auth_available() -> bool:
    """Return whether this Streamlit version supports built-in OIDC functions."""
    return hasattr(st, "login") and hasattr(st, "logout") and hasattr(st, "user")


def _native_user_is_logged_in() -> bool:
    if not _native_auth_available():
        return False
    try:
        return bool(st.user.is_logged_in)
    except Exception:
        return False


def _stable_user_hash(subject: str) -> str:
    """Return the existing app's compact, stable identity key from the OIDC subject."""
    return hashlib.sha256(subject.encode("utf-8")).hexdigest()[:16]


def _display_name_from_claims(email: str) -> str:
    """Choose an initial profile label without exposing the raw provider ID."""
    display_name = (
        _claim("name")
        or _claim("nickname")
        or _claim("preferred_username")
        or ""
    )
    if display_name:
        return str(display_name).strip()
    if email and "@" in email:
        return email.split("@", 1)[0]
    return "Moon Wanderer"


def native_user_from_identity() -> dict[str, str | None] | None:
    """Map the logged-in OIDC identity to LunaTicK's active user-session shape."""
    if not _native_user_is_logged_in():
        return None

    subject = str(_claim("sub", "")).strip()
    if not subject:
        # A standards-compliant OIDC identity must include an immutable subject.
        # Do not fall back to email; email can change and would split profiles.
        return None

    email = str(_claim("email", "")).strip().lower()
    initial_name = _display_name_from_claims(email)
    user_hash = _stable_user_hash(subject)

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute(
        "SELECT display_name, birth_date FROM oidc_identities WHERE subject=?",
        (subject,),
    )
    existing = c.fetchone()

    if existing:
        display_name = existing[0] or initial_name
        birth_date = existing[1]
        c.execute(
            """
            UPDATE oidc_identities
            SET email=?, updated_at=CURRENT_TIMESTAMP
            WHERE subject=?
            """,
            (email or None, subject),
        )
    else:
        display_name = initial_name
        birth_date = None
        c.execute(
            """
            INSERT INTO oidc_identities
                (subject, user_hash, email, display_name, birth_date)
            VALUES (?, ?, ?, ?, NULL)
            """,
            (subject, user_hash, email or None, display_name),
        )

    conn.commit()
    conn.close()

    # Existing active modules use username for sidebar presentation and profile
    # updates. Email is friendlier than an opaque OIDC subject.
    return {
        "username": email or subject,
        "auth_subject": subject,
        "user_hash": user_hash,
        "display_name": display_name,
        "birth_date": birth_date,
    }


def apply_user_to_session(user: dict[str, str | None]) -> None:
    """Populate the keys already consumed by journals, cards, and community."""
    st.session_state.is_authenticated = True
    st.session_state.username = user["username"]
    st.session_state.auth_subject = user["auth_subject"]
    st.session_state.user_hash = user["user_hash"]
    st.session_state.display_name = user["display_name"]

    if user.get("birth_date"):
        try:
            st.session_state.birth_date = datetime.strptime(
                str(user["birth_date"]), "%Y-%m-%d"
            ).date()
        except ValueError:
            st.session_state.birth_date = user["birth_date"]


def update_user_profile(username: str, display_name: str, birth_date: str | None) -> None:
    """Persist app-level profile details without handling passwords or sessions."""
    subject = str(st.session_state.get("auth_subject", "")).strip()
    if not subject:
        return

    clean_name = (display_name or "Moon Wanderer").strip() or "Moon Wanderer"
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute(
        """
        UPDATE oidc_identities
        SET email=?, display_name=?, birth_date=?, updated_at=CURRENT_TIMESTAMP
        WHERE subject=?
        """,
        (username.strip().lower() or None, clean_name, birth_date, subject),
    )
    conn.commit()
    conn.close()

    st.session_state.display_name = clean_name
    if birth_date:
        try:
            st.session_state.birth_date = datetime.strptime(birth_date, "%Y-%m-%d").date()
        except ValueError:
            st.session_state.birth_date = birth_date


def logout() -> None:
    """Clear app state and ask Streamlit to remove its native identity cookie."""
    for key in (
        "is_authenticated",
        "user_hash",
        "username",
        "auth_subject",
        "display_name",
        "birth_date",
    ):
        st.session_state.pop(key, None)

    st.session_state.is_authenticated = False
    st.session_state.user_hash = "anonymous"

    if _native_user_is_logged_in():
        # st.logout() clears Streamlit's managed identity cookie and starts a
        # fresh session. It intentionally terminates the current script run.
        st.logout()


def render_login_page() -> bool:
    """Render the native non-Google sign-in gate and restore OIDC identities."""
    init_auth_db()

    if not _native_auth_available():
        st.error(
            "LunaTicK needs Streamlit 1.42 or later for secure native sign-in. "
            "Update the deployment dependencies and restart the app."
        )
        return False

    user = native_user_from_identity()
    if user:
        apply_user_to_session(user)
        return True

    st.markdown(
        """
        <div style="text-align:center; margin: 2rem 0 1.5rem 0;">
          <div style="font-family:'Orbitron',sans-serif; font-size:2.4rem; color:#bc8cff; letter-spacing:4px;">🌙 LUNATICK</div>
          <div style="color:#8b949e; font-size:0.9rem; margin-top:0.4rem;">Your cosmic connection.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("#### Sign in to your LunaTicK account")
    st.caption(
        "Create an email-and-password account or sign in to continue. "
        "LunaTicK does not use Google sign-in."
    )

    if st.button("Continue to secure sign-in", type="primary", use_container_width=True):
        # Auth0's Universal Login handles registration, email/password login,
        # password recovery, rate limiting, and identity verification.
        st.login(AUTH_PROVIDER)

    st.caption(
        "Keep your account signed in for up to 30 days. "
        "Use Log out in Settings whenever you are on a shared device."
    )
    return False
