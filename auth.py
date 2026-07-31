# auth.py
# Persistent username + password login for Streamlit moon-bro

import streamlit as st
import sqlite3
import hashlib
import secrets
from datetime import datetime

DB = "lunatick.db"


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
    conn.commit()
    conn.close()


def _hash_password(password: str, salt: str) -> str:
    return hashlib.sha256((salt + password).encode("utf-8")).hexdigest()


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
    # Stable user id from username (persistent across sessions)
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
        # Mirror into cosmic_cards user_profiles so cards/trading work immediately
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


def update_user_profile(username: str, display_name: str, birth_date: str | None):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute(
        "UPDATE users SET display_name=?, birth_date=? WHERE username=?",
        (display_name, birth_date, username.strip().lower()),
    )
    user_hash = hashlib.sha256(username.strip().lower().encode()).hexdigest()[:16]
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
    conn.commit()
    conn.close()


def logout():
    for key in ["is_authenticated", "user_hash", "username", "display_name", "birth_date"]:
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
    """Full-page login / register gate. Returns True if user is logged in."""
    init_auth_db()

    if st.session_state.get("is_authenticated"):
        return True

    st.markdown(
        """
        <div style="text-align:center; margin: 2rem 0 1.5rem 0;">
          <div style="font-family:'Orbitron',sans-serif; font-size:2.4rem; color:#bc8cff; letter-spacing:4px;">🌙 LUNATICK</div>
          <div style="color:#8b949e; font-size:0.9rem; margin-top:0.4rem;">Sign in once — your moon profile stays with you.</div>
        </div>
        """,
        unsafe_allow_html=True,
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
                    apply_user_to_session(result)
                    st.success(f"Welcome back, {result['display_name']}!")
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
                    ok, result = register_user(u, p, d)
                    if ok:
                        # Auto-login after register
                        ok2, user = login_user(u, p)
                        if ok2:
                            apply_user_to_session(user)
                            st.success("Account created — you're in!")
                            st.rerun()
                        else:
                            st.success("Account created. Please log in.")
                    else:
                        st.error(result)

    st.caption("Your password is stored hashed. Only you can access your journal and card.")
    return False
