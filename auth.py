# auth.py
# Native Streamlit OIDC authentication and profile presence for LunaTicK.
#
# Auth0 hosts the email-and-password account experience. Streamlit owns the
# secure identity cookie. This module stores only LunaTicK-facing profile data;
# passwords and provider tokens never enter the local application database.

from __future__ import annotations

import hashlib
import re
import sqlite3
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

import requests
import streamlit as st

import supabase_store

DB = "lunatick.db"
AUTH_PROVIDER = "auth0"
DEFAULT_AVATAR = "🌙"
USERNAME_PATTERN = re.compile(r"^[a-z0-9_]{3,24}$")
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
DEFAULT_AUTH0_DATABASE_CONNECTION = "Username-Password-Authentication"


def _connect() -> sqlite3.Connection:
    """Open the local alpha profile database with row access by column name."""
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def using_supabase_backend() -> bool:
    """Return whether the fresh Supabase profile path is explicitly activated."""
    return supabase_store.data_backend_from_streamlit_secrets() == "supabase"


def _supabase() -> supabase_store.SupabaseStore:
    """Create the server-only Supabase store only after the backend switch is on."""
    return supabase_store.SupabaseStore(supabase_store.SupabaseSettings.from_streamlit_secrets())


def init_auth_db() -> None:
    """Create and migrate the local identity-to-profile mapping when SQLite is active."""
    if using_supabase_backend():
        return

    conn = _connect()
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS oidc_identities (
            subject TEXT PRIMARY KEY,
            user_hash TEXT UNIQUE NOT NULL,
            email TEXT,
            username TEXT,
            display_name TEXT,
            avatar TEXT,
            bio TEXT,
            birth_date TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # Existing alpha databases were created before public presence fields
    # existed. SQLite requires an explicit additive migration for each column.
    existing_columns = {row["name"] for row in c.execute("PRAGMA table_info(oidc_identities)")}
    for column, definition in (
        ("username", "TEXT"),
        ("avatar", "TEXT"),
        ("bio", "TEXT"),
    ):
        if column not in existing_columns:
            c.execute(f"ALTER TABLE oidc_identities ADD COLUMN {column} {definition}")

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


def _auth0_password_reset_config() -> tuple[str, str, str] | None:
    """Return the existing Auth0 database reset endpoint and public client settings.

    The endpoint sends a recovery email through Auth0. LunaTicK neither receives
    nor stores a password, reset ticket, or provider token.
    """
    try:
        config = st.secrets.get("auth", {}).get("auth0", {})
        metadata_url = str(config.get("server_metadata_url", "")).strip()
        client_id = str(config.get("client_id", "")).strip()
        connection = str(
            config.get("database_connection", DEFAULT_AUTH0_DATABASE_CONNECTION)
        ).strip()
    except Exception:
        return None

    parsed = urlparse(metadata_url)
    if not parsed.scheme or not parsed.netloc or not client_id or not connection:
        return None
    return f"{parsed.scheme}://{parsed.netloc}/dbconnections/change_password", client_id, connection


def request_password_reset(email: str, http_client: Any = requests) -> tuple[bool, str]:
    """Ask Auth0 to email a database-password reset link without revealing account status."""
    clean_email = (email or "").strip().lower()
    if not EMAIL_PATTERN.fullmatch(clean_email):
        return False, "Enter a valid email address."

    config = _auth0_password_reset_config()
    if config is None:
        return False, "Password recovery is temporarily unavailable. Please try again later."
    endpoint, client_id, connection = config

    try:
        response = http_client.post(
            endpoint,
            json={"client_id": client_id, "email": clean_email, "connection": connection},
            timeout=15,
        )
    except requests.RequestException:
        return False, "Password recovery is temporarily unavailable. Please try again later."

    # Always use a generic success result on an Auth0 response. This avoids
    # revealing whether an address belongs to a LunaTicK account.
    if response.ok:
        return True, "If an account exists for that email, Auth0 has sent a password-reset link."
    return False, "Password recovery could not be started. Please try again shortly."


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


def _default_username(user_hash: str) -> str:
    """Create a private, editable initial handle without exposing email address."""
    return f"moon_{user_hash[:6]}"


def _public_display_name(value: Any, email: str = "") -> str:
    """Normalize a public label and reject full-email or legacy local-part fallbacks."""
    name = supabase_store.public_display_name(value)
    email_local_part = (email or "").strip().lower().partition("@")[0]
    if email_local_part and name.lower() == email_local_part:
        return supabase_store.PUBLIC_DISPLAY_NAME_FALLBACK
    return name


def _display_name_from_claims(email: str) -> str:
    """Choose an initial public label without deriving one from an email address."""
    display_name = (
        _claim("name")
        or _claim("nickname")
        or _claim("preferred_username")
        or ""
    )
    return _public_display_name(display_name, email)


def _clean_username(username: str) -> str:
    """Normalize an app-facing username to its stable canonical form."""
    return (username or "").strip().lower().lstrip("@")


def _username_is_available(conn: sqlite3.Connection, username: str, subject: str) -> bool:
    """Check handle availability while allowing a user to retain their own handle."""
    row = conn.execute(
        """
        SELECT subject FROM oidc_identities
        WHERE lower(COALESCE(username, '')) = lower(?) AND subject != ?
        LIMIT 1
        """,
        (username, subject),
    ).fetchone()
    return row is None


def _presence_from_row(
    row: sqlite3.Row | None,
    user_hash: str,
    email: str,
) -> tuple[str, str, str, str | None, str]:
    """Return stable, complete profile values from an existing or new record."""
    default_username = _default_username(user_hash)
    if row is None:
        return (
            default_username,
            _display_name_from_claims(email),
            DEFAULT_AVATAR,
            None,
            "",
        )

    username = _clean_username(row["username"] or default_username)
    display_name = _public_display_name(row["display_name"] or _display_name_from_claims(email), email)
    avatar = (row["avatar"] or DEFAULT_AVATAR).strip()[:8] or DEFAULT_AVATAR
    bio = (row["bio"] or "").strip()[:240]
    birth_date = row["birth_date"]
    return username, display_name, avatar, birth_date, bio


def _session_user(
    *,
    subject: str,
    user_hash: str,
    email: str,
    username: str,
    display_name: str,
    avatar: str,
    bio: str,
    birth_date: str | None,
) -> dict[str, str | None]:
    """Build the app's established authenticated session representation."""
    return {
        "username": username,
        "auth_subject": subject,
        "user_hash": user_hash,
        "email": email or None,
        "display_name": display_name,
        "avatar": avatar,
        "bio": bio or "",
        "birth_date": birth_date,
    }


def _native_user_from_supabase(subject: str, email: str, user_hash: str) -> dict[str, str | None]:
    """Create or restore the fresh canonical profile in Supabase by Auth0 subject."""
    store = _supabase()
    existing = store.get_profile_by_auth_subject(subject)
    username, display_name, avatar, birth_date, bio = _presence_from_row(existing, user_hash, email)

    # A fresh-start profile is created on first native sign-in. The immutable
    # Auth0 subject is the upsert conflict key; no SQLite row is read or copied.
    store.upsert_profile(
        {
            "auth_subject": subject,
            "user_hash": user_hash,
            "email": email or None,
            "username": username,
            "display_name": display_name,
            "avatar": avatar,
            "bio": bio or "",
            "birth_date": birth_date,
        }
    )
    return _session_user(
        subject=subject,
        user_hash=user_hash,
        email=email,
        username=username,
        display_name=display_name,
        avatar=avatar,
        bio=bio,
        birth_date=birth_date,
    )


def _native_user_from_sqlite(subject: str, email: str, user_hash: str) -> dict[str, str | None]:
    """Restore the legacy SQLite profile while the rollback backend is selected."""
    conn = _connect()
    existing = conn.execute(
        """
        SELECT username, display_name, avatar, bio, birth_date
        FROM oidc_identities WHERE subject=?
        """,
        (subject,),
    ).fetchone()
    username, display_name, avatar, birth_date, bio = _presence_from_row(existing, user_hash, email)

    if existing:
        conn.execute(
            """
            UPDATE oidc_identities
            SET email=?, username=?, display_name=?, avatar=?, bio=?, updated_at=CURRENT_TIMESTAMP
            WHERE subject=?
            """,
            (email or None, username, display_name, avatar, bio or None, subject),
        )
    else:
        conn.execute(
            """
            INSERT INTO oidc_identities
                (subject, user_hash, email, username, display_name, avatar, bio, birth_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, NULL)
            """,
            (subject, user_hash, email or None, username, display_name, avatar, bio or None),
        )

    conn.commit()
    conn.close()
    return _session_user(
        subject=subject,
        user_hash=user_hash,
        email=email,
        username=username,
        display_name=display_name,
        avatar=avatar,
        bio=bio,
        birth_date=birth_date,
    )


def native_user_from_identity() -> dict[str, str | None] | None:
    """Map the logged-in OIDC identity to the active backend's canonical profile."""
    if not _native_user_is_logged_in():
        return None

    subject = str(_claim("sub", "")).strip()
    if not subject:
        # A standards-compliant OIDC identity must include an immutable subject.
        # Do not fall back to email; email can change and would split profiles.
        return None

    email = str(_claim("email", "")).strip().lower()
    user_hash = _stable_user_hash(subject)
    if using_supabase_backend():
        return _native_user_from_supabase(subject, email, user_hash)
    return _native_user_from_sqlite(subject, email, user_hash)


def apply_user_to_session(user: dict[str, str | None]) -> None:
    """Populate the session keys consumed by LunaTicK modules and profile UI."""
    st.session_state.is_authenticated = True
    st.session_state.username = user["username"]
    st.session_state.auth_subject = user["auth_subject"]
    st.session_state.user_hash = user["user_hash"]
    st.session_state.email = user.get("email") or ""
    st.session_state.display_name = user["display_name"]
    st.session_state.avatar = user.get("avatar") or DEFAULT_AVATAR
    st.session_state.bio = user.get("bio") or ""

    if user.get("birth_date"):
        try:
            st.session_state.birth_date = datetime.strptime(
                str(user["birth_date"]), "%Y-%m-%d"
            ).date()
        except ValueError:
            st.session_state.birth_date = user["birth_date"]


def get_public_profile(username: str) -> dict[str, str] | None:
    """Return only the profile fields safe to show to another LunaTicK user."""
    clean_username = _clean_username(username)
    if not USERNAME_PATTERN.fullmatch(clean_username):
        return None

    if using_supabase_backend():
        return _supabase().get_public_profile_by_username(clean_username)

    conn = _connect()
    row = conn.execute(
        """
        SELECT username, display_name, avatar, bio
        FROM oidc_identities
        WHERE lower(username) = lower(?)
        LIMIT 1
        """,
        (clean_username,),
    ).fetchone()
    conn.close()

    if row is None:
        return None

    return {
        "username": _clean_username(row["username"]),
        "display_name": _public_display_name(row["display_name"]),
        "avatar": (row["avatar"] or DEFAULT_AVATAR).strip()[:8] or DEFAULT_AVATAR,
        "bio": (row["bio"] or "").strip()[:240],
    }


def update_presence_profile(
    username: str,
    display_name: str,
    avatar: str,
    bio: str,
) -> tuple[bool, str]:
    """Validate and save LunaTicK-facing profile and community presence fields."""
    subject = str(st.session_state.get("auth_subject", "")).strip()
    if not subject:
        return False, "Your sign-in session is missing. Please sign in again."

    clean_username = _clean_username(username)
    clean_display_name = (display_name or "").strip()
    clean_avatar = (avatar or DEFAULT_AVATAR).strip()[:8] or DEFAULT_AVATAR
    clean_bio = (bio or "").strip()

    if not USERNAME_PATTERN.fullmatch(clean_username):
        return False, "Username must be 3–24 lowercase letters, numbers, or underscores."
    if not clean_display_name:
        return False, "Display name cannot be empty."
    if "@" in clean_display_name:
        return False, "Display name cannot contain an email address."
    email_local_part = str(st.session_state.get("email", "")).strip().lower().partition("@")[0]
    if email_local_part and clean_display_name.lower() == email_local_part:
        return False, "Choose a display name that is different from your email address."
    if len(clean_display_name) > 48:
        return False, "Display name must be 48 characters or fewer."
    if len(clean_bio) > 240:
        return False, "Bio must be 240 characters or fewer."

    if using_supabase_backend():
        store = _supabase()
        if not store.username_is_available(clean_username, subject):
            return False, "That username is already claimed. Please choose another."

        existing = store.get_profile_by_auth_subject(subject) or {}
        store.upsert_profile(
            {
                "auth_subject": subject,
                "user_hash": str(existing.get("user_hash") or st.session_state.get("user_hash", "")),
                "email": str(existing.get("email") or st.session_state.get("email", "")).strip() or None,
                "username": clean_username,
                "display_name": clean_display_name,
                "avatar": clean_avatar,
                "bio": clean_bio,
                "birth_date": existing.get("birth_date"),
            }
        )
    else:
        conn = _connect()
        if not _username_is_available(conn, clean_username, subject):
            conn.close()
            return False, "That username is already claimed. Please choose another."

        conn.execute(
            """
            UPDATE oidc_identities
            SET username=?, display_name=?, avatar=?, bio=?, updated_at=CURRENT_TIMESTAMP
            WHERE subject=?
            """,
            (clean_username, clean_display_name, clean_avatar, clean_bio or None, subject),
        )
        conn.commit()
        conn.close()

    st.session_state.username = clean_username
    st.session_state.display_name = clean_display_name
    st.session_state.avatar = clean_avatar
    st.session_state.bio = clean_bio
    return True, "Profile saved."


def update_user_profile(username: str, display_name: str, birth_date: str | None) -> None:
    """Persist birth-profile values while preserving the public presence fields."""
    subject = str(st.session_state.get("auth_subject", "")).strip()
    if not subject:
        return

    clean_username = _clean_username(username) or _default_username(
        str(st.session_state.get("user_hash", "moon"))
    )
    clean_name = _public_display_name(display_name)

    if using_supabase_backend():
        _supabase().update_profile_fields(
            subject,
            {"username": clean_username, "display_name": clean_name, "birth_date": birth_date},
        )
        st.session_state.username = clean_username
        st.session_state.display_name = clean_name
        if birth_date:
            try:
                st.session_state.birth_date = datetime.strptime(birth_date, "%Y-%m-%d").date()
            except ValueError:
                st.session_state.birth_date = birth_date
        return

    conn = _connect()
    conn.execute(
        """
        UPDATE oidc_identities
        SET username=?, display_name=?, birth_date=?, updated_at=CURRENT_TIMESTAMP
        WHERE subject=?
        """,
        (clean_username, clean_name, birth_date, subject),
    )
    conn.commit()
    conn.close()

    st.session_state.username = clean_username
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
        "email",
        "auth_subject",
        "display_name",
        "avatar",
        "bio",
        "birth_date",
    ):
        st.session_state.pop(key, None)

    st.session_state.is_authenticated = False
    st.session_state.user_hash = "anonymous"

    if _native_user_is_logged_in():
        # With Auth0 end-session discovery disabled, this clears LunaTicK's
        # identity cookie and starts a clean sign-in session without a provider
        # redirect that can fail externally.
        st.logout()


def render_login_page() -> bool:
    """Render the native non-Google sign-in gate and restore OIDC identities."""
    init_auth_db()

    if not _native_auth_available():
        st.error(
            "LunaTicK needs Streamlit 1.48.1 or later for secure native sign-in. "
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
        st.login(AUTH_PROVIDER)

    with st.expander("Forgot your password?", expanded=False):
        st.caption(
            "Enter the email used for your LunaTicK account. Auth0 will send a secure reset link if an account exists."
        )
        with st.form("auth0_password_recovery_form", clear_on_submit=True):
            recovery_email = st.text_input(
                "Account email",
                type="email",
                placeholder="you@example.com",
                key="auth0_recovery_email",
            )
            send_recovery = st.form_submit_button("Email password-reset link", use_container_width=True)
        if send_recovery:
            sent, message = request_password_reset(recovery_email)
            if sent:
                st.success(message)
            else:
                st.warning(message)

    st.caption(
        "Keep your account signed in for up to 30 days. "
        "Use Log out in Settings whenever you are on a shared device."
    )
    return False
