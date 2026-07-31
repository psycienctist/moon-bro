# auth.py
# Persistent username + password login with 30-day session cookies

import streamlit as st
import sqlite3
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

try:
    import extra_streamlit_components as stx
    HAS_COOKIES = True
except ImportError:
    HAS_COOKIES = False

DB = "lunatick.db"
COOKIE_NAME = "lunatick_session"
SESSION_DAYS = 30


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
            birth_time TEXT,
            birth_place TEXT,
            birth_lat REAL,
            birth_lon REAL,
            birth_utc_offset REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    c.execute("PRAGMA table_info(users)")
    cols = {row[1] for row in c.fetchall()}
    for col, typedef in [
        ("birth_time", "TEXT"),
        ("birth_place", "TEXT"),
        ("birth_lat", "REAL"),
        ("birth_lon", "REAL"),
        ("birth_utc_offset", "REAL"),
    ]:
        if col not in cols:
            c.execute(f"ALTER TABLE users ADD COLUMN {col} {typedef}")

    c.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            username TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    now = datetime.now(timezone.utc).isoformat()
    c.execute("DELETE FROM sessions WHERE expires_at < ?", (now,))
    conn.commit()
    conn.close()


def _hash_password(password: str, salt: str) -> str:
    return hashlib.sha256((salt + password).encode("utf-8")).hexdigest()


def _get_cookie_manager():
    if not HAS_COOKIES:
        return None
    if "_cookie_manager" not in st.session_state:
        st.session_state._cookie_manager = stx.CookieManager(key="lunatick_cm")
    return st.session_state._cookie_manager


def create_session_token(username: str) -> str:
    token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(days=SESSION_DAYS)
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute(
        "INSERT INTO sessions (token, username, expires_at) VALUES (?, ?, ?)",
        (token, username.strip().lower(), expires.isoformat()),
    )
    conn.commit()
    conn.close()
    return token


def revoke_session_token(token: str | None):
    if not token:
        return
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("DELETE FROM sessions WHERE token=?", (token,))
    conn.commit()
    conn.close()


def user_from_session_token(token: str | None) -> dict | None:
    if not token:
        return None
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT username, expires_at FROM sessions WHERE token=?", (token,))
    row = c.fetchone()
    if not row:
        conn.close()
        return None
    username, expires_at = row
    try:
        exp = datetime.fromisoformat(expires_at)
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if exp < datetime.now(timezone.utc):
            c.execute("DELETE FROM sessions WHERE token=?", (token,))
            conn.commit()
            conn.close()
            return None
    except Exception:
        conn.close()
        return None

    c.execute(
        """
        SELECT username, display_name, birth_date, birth_time, birth_place,
               birth_lat, birth_lon, birth_utc_offset
        FROM users WHERE username=?
        """,
        (username,),
    )
    urow = c.fetchone()
    conn.close()
    if not urow:
        return None
    uname, display_name, birth_date, birth_time, birth_place, blat, blon, boff = urow
    user_hash = hashlib.sha256(uname.encode()).hexdigest()[:16]
    return {
        "username": uname,
        "user_hash": user_hash,
        "display_name": display_name or uname,
        "birth_date": birth_date,
        "birth_time": birth_time,
        "birth_place": birth_place,
        "birth_lat": blat,
        "birth_lon": blon,
        "birth_utc_offset": boff,
    }


def set_session_cookie(token: str):
    cm = _get_cookie_manager()
    if cm is None:
        return
    expires = datetime.now() + timedelta(days=SESSION_DAYS)
    cm.set(COOKIE_NAME, token, expires_at=expires)


def clear_session_cookie():
    cm = _get_cookie_manager()
    if cm is None:
        return
    try:
        cm.delete(COOKIE_NAME)
    except Exception:
        try:
            cm.set(COOKIE_NAME, "", expires_at=datetime.now() - timedelta(days=1))
        except Exception:
            pass


def try_restore_from_cookie() -> bool:
    if st.session_state.get("is_authenticated"):
        return True
    cm = _get_cookie_manager()
    if cm is None:
        return False
    cookies = cm.get_all()
    if cookies is None:
        return False
    token = cookies.get(COOKIE_NAME) or cm.get(COOKIE_NAME)
    if not token:
        return False
    user = user_from_session_token(token)
    if not user:
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
        c.execute(
            """
            INSERT OR IGNORE INTO user_profiles (user_hash, display_name, birth_date)
            VALUES (?, ?, NULL)
            """,
            (user_hash, display_name),
        )
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
        """
        SELECT username, password_hash, salt, display_name, birth_date,
               birth_time, birth_place, birth_lat, birth_lon, birth_utc_offset
        FROM users WHERE username=?
        """,
        (username,),
    )
    row = c.fetchone()
    conn.close()

    if not row:
        return False, "Invalid username or password."

    uname, stored_hash, salt, display_name, birth_date, btime, bplace, blat, blon, boff = row
    if _hash_password(password, salt) != stored_hash:
        return False, "Invalid username or password."

    user_hash = hashlib.sha256(uname.encode()).hexdigest()[:16]
    return True, {
        "username": uname,
        "user_hash": user_hash,
        "display_name": display_name or uname,
        "birth_date": birth_date,
        "birth_time": btime,
        "birth_place": bplace,
        "birth_lat": blat,
        "birth_lon": blon,
        "birth_utc_offset": boff,
    }


def complete_login(user: dict):
    apply_user_to_session(user)
    token = create_session_token(user["username"])
    st.session_state._session_token = token
    set_session_cookie(token)
    # Mirror full profile into cosmic cards store
    try:
        import cosmic_cards

        if user.get("birth_date"):
            cosmic_cards.save_profile(
                user["user_hash"],
                user.get("display_name") or user["username"],
                user.get("birth_date"),
                birth_time=user.get("birth_time"),
                birth_place=user.get("birth_place"),
                birth_lat=user.get("birth_lat"),
                birth_lon=user.get("birth_lon"),
                birth_utc_offset=user.get("birth_utc_offset"),
            )
    except Exception:
        pass


def update_user_profile(
    username: str,
    display_name: str,
    birth_date: str | None,
    birth_time: str | None = None,
    birth_place: str | None = None,
    birth_lat: float | None = None,
    birth_lon: float | None = None,
    birth_utc_offset: float | None = None,
):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute(
        """
        UPDATE users SET
            display_name=?,
            birth_date=?,
            birth_time=?,
            birth_place=?,
            birth_lat=?,
            birth_lon=?,
            birth_utc_offset=?
        WHERE username=?
        """,
        (
            display_name,
            birth_date,
            birth_time,
            birth_place,
            birth_lat,
            birth_lon,
            birth_utc_offset,
            username.strip().lower(),
        ),
    )
    user_hash = hashlib.sha256(username.strip().lower().encode()).hexdigest()[:16]
    c.execute(
        """
        INSERT INTO user_profiles (
            user_hash, display_name, birth_date, birth_time,
            birth_place, birth_lat, birth_lon, birth_utc_offset
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_hash) DO UPDATE SET
            display_name=excluded.display_name,
            birth_date=excluded.birth_date,
            birth_time=excluded.birth_time,
            birth_place=excluded.birth_place,
            birth_lat=excluded.birth_lat,
            birth_lon=excluded.birth_lon,
            birth_utc_offset=excluded.birth_utc_offset
        """,
        (
            user_hash,
            display_name,
            birth_date,
            birth_time,
            birth_place,
            birth_lat,
            birth_lon,
            birth_utc_offset,
        ),
    )
    conn.commit()
    conn.close()


def logout():
    token = st.session_state.get("_session_token")
    if not token and HAS_COOKIES:
        cm = _get_cookie_manager()
        if cm is not None:
            try:
                token = cm.get(COOKIE_NAME)
            except Exception:
                token = None
    revoke_session_token(token)
    clear_session_cookie()
    for key in [
        "is_authenticated", "user_hash", "username",
        "display_name", "birth_date", "_session_token",
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
            st.session_state.birth_date = datetime.strptime(user["birth_date"], "%Y-%m-%d").date()
        except Exception:
            st.session_state.birth_date = user["birth_date"]


def render_login_page():
    init_auth_db()
    _get_cookie_manager()

    if st.session_state.get("is_authenticated"):
        return True

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
            submitted = st.form_submit_button("Create account", type="primary", use_container_width=True)
            if submitted:
                if p != p2:
                    st.error("Passwords do not match.")
                else:
                    ok, err = register_user(u, p, d)
                    if ok:
                        ok2, user = login_user(u, p)
                        if ok2:
                            complete_login(user)
                            st.success("Account created — you're in for 30 days!")
                            st.rerun()
                        else:
                            st.success("Account created. Please log in.")
                    else:
                        st.error(err)

    st.caption(
        "Passwords are hashed. Session cookie lasts 30 days — log out anytime to clear it."
    )
    return False
