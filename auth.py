# auth.py
# Persistent username + password login with 30-day signed session cookies

import streamlit as st
import sqlite3
import hashlib
import hmac
import secrets
import time
from datetime import datetime, timedelta, timezone

try:
    import extra_streamlit_components as stx
    HAS_COOKIES = True
except ImportError:
    HAS_COOKIES = False

DB = "lunatick.db"
COOKIE_NAME = "lunatick_session"
SESSION_DAYS = 30


def _session_secret() -> str:
    """Prefer Streamlit secrets; fall back so local/dev still works."""
    try:
        return str(st.secrets.get("SESSION_SECRET", "lunatick-default-secret-change-me"))
    except Exception:
        return "lunatick-default-secret-change-me"


def init_auth_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            display_name TEXT,
            birth_date TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            username TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # Soft cleanup only — signed cookies still work if row is missing
    now = datetime.now(timezone.utc).isoformat()
    try:
        c.execute("DELETE FROM sessions WHERE expires_at < ?", (now,))
    except Exception:
        pass
    conn.commit()
    conn.close()


def _hash_password(password: str, salt: str) -> str:
    return hashlib.sha256((salt + password).encode("utf-8")).hexdigest()


def _get_cookie_manager():
    """
    Always construct with a stable key. Do NOT cache the component instance
    in session_state — that breaks cookie hydration after browser reopen.
    """
    if not HAS_COOKIES:
        return None
    return stx.CookieManager(key="lunatick_cookies_v2")


def _make_signed_token(username: str) -> str:
    """username:expiry_unix:hmac — self-validating, survives DB restarts."""
    exp = int(time.time()) + SESSION_DAYS * 86400
    payload = f"{username.strip().lower()}:{exp}"
    sig = hmac.new(
        _session_secret().encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()[:32]
    return f"{payload}:{sig}"


def _parse_signed_token(token: str | None) -> str | None:
    """Return username if token is valid and not expired, else None."""
    if not token or not isinstance(token, str):
        return None
    try:
        parts = token.strip().split(":")
        if len(parts) != 3:
            return None
        username, exp_s, sig = parts
        exp = int(exp_s)
        if exp < int(time.time()):
            return None
        payload = f"{username}:{exp_s}"
        expected = hmac.new(
            _session_secret().encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()[:32]
        if not hmac.compare_digest(sig, expected):
            return None
        return username.strip().lower()
    except Exception:
        return None


def create_session_token(username: str) -> str:
    token = _make_signed_token(username)
    expires = datetime.now(timezone.utc) + timedelta(days=SESSION_DAYS)
    try:
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute(
            "INSERT OR REPLACE INTO sessions (token, username, expires_at) VALUES (?, ?, ?)",
            (token, username.strip().lower(), expires.isoformat()),
        )
        conn.commit()
        conn.close()
    except Exception:
        pass
    return token


def revoke_session_token(token: str | None):
    if not token:
        return
    try:
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("DELETE FROM sessions WHERE token=?", (token,))
        conn.commit()
        conn.close()
    except Exception:
        pass


def _user_row(username: str) -> dict | None:
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute(
        "SELECT username, display_name, birth_date FROM users WHERE username=?",
        (username.strip().lower(),),
    )
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    uname, display_name, birth_date = row
    user_hash = hashlib.sha256(uname.encode()).hexdigest()[:16]
    return {
        "username": uname,
        "user_hash": user_hash,
        "display_name": display_name or uname,
        "birth_date": birth_date,
    }


def user_from_session_token(token: str | None) -> dict | None:
    """Validate signed cookie first; DB session row is optional."""
    username = _parse_signed_token(token)
    if not username:
        return None
    return _user_row(username)


def set_session_cookie(token: str):
    cm = _get_cookie_manager()
    if cm is None:
        return
    expires = datetime.utcnow() + timedelta(days=SESSION_DAYS)
    try:
        cm.set(
            COOKIE_NAME,
            token,
            expires_at=expires,
            key="lunatick_set_session",
        )
    except TypeError:
        # Older extra_streamlit_components may not accept key=
        try:
            cm.set(COOKIE_NAME, token, expires_at=expires)
        except Exception:
            pass
    except Exception:
        pass


def clear_session_cookie():
    cm = _get_cookie_manager()
    if cm is None:
        return
    try:
        cm.delete(COOKIE_NAME)
    except Exception:
        try:
            cm.set(
                COOKIE_NAME,
                "",
                expires_at=datetime.utcnow() - timedelta(days=1),
            )
        except Exception:
            pass


def _read_cookie_token() -> str | None:
    cm = _get_cookie_manager()
    if cm is None:
        return None

    # Prefer get_all (hydrates component); fall back to get
    try:
        cookies = cm.get_all()
    except Exception:
        cookies = None

    if cookies is None:
        # Component not ready yet this run
        return None

    token = None
    if isinstance(cookies, dict):
        token = cookies.get(COOKIE_NAME)
    if not token:
        try:
            token = cm.get(COOKIE_NAME)
        except Exception:
            token = None
    if token is not None:
        token = str(token).strip()
    return token or None


def try_restore_from_cookie() -> bool:
    """If a valid signed session cookie exists, restore session."""
    if st.session_state.get("is_authenticated"):
        return True

    # Avoid infinite restore loops
    if st.session_state.get("_cookie_restore_attempted"):
        return False

    token = _read_cookie_token()
    if token is None:
        # CookieManager still loading — mark nothing; caller may rerun next paint
        return False

    st.session_state._cookie_restore_attempted = True

    if not token:
        return False

    user = user_from_session_token(token)
    if not user:
        # Invalid / expired / user deleted — clear bad cookie
        clear_session_cookie()
        return False

    apply_user_to_session(user)
    st.session_state._session_token = token
    return True


def register_user(username: str, password: str, display_name: str = "") -> tuple[bool, str]:
    username = username.strip().lower()
    display_name = (display_name or username).strip()

    if len(username) < 3 or len(username) > 24:
        return False, "Username must be 3–24 characters."
    if not username.replace("_", "").replace("-", "").isalnum():
        return False, "Username: letters, numbers, _ or - only."
    if len(password) < 6:
        return False, "Password must be at least 6 characters."

    salt = secrets.token_hex(16)
    pw_hash = _hash_password(password, salt)
    user_hash = hashlib.sha256(username.encode()).hexdigest()[:16]

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    try:
        c.execute(
            """
            INSERT INTO users (username, password_hash, salt, display_name)
            VALUES (?, ?, ?, ?)
            """,
            (username, pw_hash, salt, display_name),
        )
        try:
            c.execute(
                """
                INSERT OR IGNORE INTO user_profiles (user_hash, display_name, birth_date)
                VALUES (?, ?, NULL)
                """,
                (user_hash, display_name),
            )
        except Exception:
            pass
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return False, "That username is already taken."
    except Exception as e:
        conn.close()
        return False, f"Could not register: {e}"
    conn.close()
    return True, user_hash


def login_user(username: str, password: str) -> tuple[bool, str | dict]:
    username = username.strip().lower()
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute(
        "SELECT username, password_hash, salt, display_name, birth_date FROM users WHERE username=?",
        (username,),
    )
    row = c.fetchone()
    conn.close()

    if not row:
        return False, "Invalid username or password."

    uname, stored_hash, salt, display_name, birth_date = row
    if _hash_password(password, salt) != stored_hash:
        return False, "Invalid username or password."

    user_hash = hashlib.sha256(uname.encode()).hexdigest()[:16]
    return True, {
        "username": uname,
        "user_hash": user_hash,
        "display_name": display_name or uname,
        "birth_date": birth_date,
    }


def complete_login(user: dict):
    """Apply session + issue 30-day signed cookie."""
    apply_user_to_session(user)
    token = create_session_token(user["username"])
    st.session_state._session_token = token
    st.session_state._cookie_restore_attempted = True
    set_session_cookie(token)


def update_user_profile(username: str, display_name: str, birth_date: str | None):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute(
        "UPDATE users SET display_name=?, birth_date=? WHERE username=?",
        (display_name, birth_date, username.strip().lower()),
    )
    user_hash = hashlib.sha256(username.strip().lower().encode()).hexdigest()[:16]
    try:
        c.execute(
            """
            INSERT INTO user_profiles (user_hash, display_name, birth_date)
            VALUES (?, ?, ?)
            ON CONFLICT(user_hash) DO UPDATE SET
                display_name=excluded.display_name,
                birth_date=excluded.birth_date
            """,
            (user_hash, display_name, birth_date),
        )
    except Exception:
        pass
    conn.commit()
    conn.close()


def logout():
    token = st.session_state.get("_session_token")
    if not token and HAS_COOKIES:
        token = _read_cookie_token()
    revoke_session_token(token)
    clear_session_cookie()
    for key in [
        "is_authenticated", "user_hash", "username",
        "display_name", "birth_date", "_session_token",
        "_cookie_restore_attempted",
    ]:
        if key in st.session_state:
            del st.session_state[key]
    st.session_state.is_authenticated = False
    st.session_state.user_hash = "anonymous"


def apply_user_to_session(user: dict):
    st.session_state.is_authenticated = True
    st.session_state.username = user["username"]
    st.session_state.user_hash = user["user_hash"]
    st.session_state.display_name = user["display_name"]
    if user.get("birth_date"):
        try:
            st.session_state.birth_date = datetime.strptime(
                user["birth_date"], "%Y-%m-%d"
            ).date()
        except Exception:
            st.session_state.birth_date = user["birth_date"]


def render_login_page():
    """Full-page login / register gate. Returns True if user is logged in."""
    init_auth_db()

    # Mount cookie manager every run so the browser cookie can hydrate
    _get_cookie_manager()

    if st.session_state.get("is_authenticated"):
        return True

    # First paint often has empty cookies — wait one cycle without flashing form
    if "_cookie_boot" not in st.session_state:
        st.session_state._cookie_boot = True
        # Give CookieManager a chance; try restore then soft rerun once
        if try_restore_from_cookie():
            st.rerun()
        # If cookies not ready, rerun once more before showing form
        if _read_cookie_token() is None and HAS_COOKIES:
            st.rerun()

    if try_restore_from_cookie():
        st.rerun()

    if st.session_state.get("is_authenticated"):
        return True

    st.markdown(
        """
        <div style="text-align:center; margin: 2rem 0 1.5rem 0;">
          <div style="font-family:'Orbitron',sans-serif; font-size:2.4rem; color:#bc8cff; letter-spacing:4px;">🌙 LUNATICK</div>
          <div style="color:#8b949e; font-size:0.9rem; margin-top:0.4rem;">Sign in once — stay logged in for 30 days.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not HAS_COOKIES:
        st.warning(
            "Install `extra-streamlit-components` for stay-logged-in cookies: "
            "`pip install extra-streamlit-components`"
        )

    tab_login, tab_register = st.tabs(["Log in", "Create account"])

    with tab_login:
        with st.form("login_form"):
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Log in", type="primary", use_container_width=True)
            if submitted:
                ok, result = login_user(u, p)
                if ok:
                    complete_login(result)
                    st.success(
                        f"Welcome back, {result['display_name']}! "
                        f"Staying signed in for {SESSION_DAYS} days."
                    )
                    st.rerun()
                else:
                    st.error(result)

    with tab_register:
        with st.form("register_form"):
            u = st.text_input("Choose a username", help="3–24 chars, letters/numbers/_/-")
            d = st.text_input("Display name (optional)")
            p = st.text_input("Password", type="password", help="At least 6 characters")
            p2 = st.text_input("Confirm password", type="password")
            submitted = st.form_submit_button(
                "Create account", type="primary", use_container_width=True
            )
            if submitted:
                if p != p2:
                    st.error("Passwords do not match.")
                else:
                    ok, msg = register_user(u, p, d)
                    if ok:
                        ok2, user = login_user(u, p)
                        if ok2:
                            complete_login(user)
                            st.success("Account created — you're in for 30 days!")
                            st.rerun()
                        else:
                            st.success("Account created. Please log in.")
                    else:
                        st.error(msg)

    st.caption(
        "Passwords are hashed. Signed session cookie lasts 30 days — "
        "log out anytime to clear it."
    )
    return False
