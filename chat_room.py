# chat_room.py
# Lightweight chat for Streamlit (refresh-based, no websockets)

from __future__ import annotations

import sqlite3

import streamlit as st

import supabase_store

DB = "lunatick.db"


def _using_supabase_backend() -> bool:
    return supabase_store.data_backend_from_streamlit_secrets() == "supabase"


def _supabase() -> supabase_store.SupabaseStore:
    return supabase_store.SupabaseStore(supabase_store.SupabaseSettings.from_streamlit_secrets())


def _resolve_auth_subject(user_reference: str) -> str:
    """Map existing current-user hash callers to the canonical Auth0 subject."""
    reference = str(user_reference or "").strip()
    subject = str(st.session_state.get("auth_subject", "")).strip()
    user_hash = str(st.session_state.get("user_hash", "")).strip()
    if subject and reference == user_hash:
        return subject
    if reference:
        return reference
    if subject:
        return subject
    raise ValueError("A signed-in LunaTicK identity is required to use Chat.")


def init_chat_db() -> None:
    """Initialize the legacy SQLite chat table only when SQLite is active."""
    if _using_supabase_backend():
        return

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            author_hash TEXT,
            author_name TEXT,
            content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    conn.close()


def post_message(author_hash: str, author_name: str, content: str) -> bool:
    content = content.strip()
    if not content or len(content) > 1000:
        return False

    if _using_supabase_backend():
        _supabase().create_chat_message(_resolve_auth_subject(author_hash), content)
        return True

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute(
        "INSERT INTO chat_messages (author_hash, author_name, content) VALUES (?, ?, ?)",
        (author_hash, author_name, content),
    )
    conn.commit()
    conn.close()
    return True


def recent_messages(limit: int = 50) -> list:
    if _using_supabase_backend():
        rows = _supabase().list_chat_messages(limit)
        profiles = _supabase().get_public_profile_summaries(
            [row["profile_auth_subject"] for row in rows]
        )
        # PostgREST returns newest first; restore the original chronological chat display.
        return [
            {
                "author": (
                    profiles.get(row["profile_auth_subject"], {}).get("display_name")
                    or profiles.get(row["profile_auth_subject"], {}).get("username")
                    or "Moon Wanderer"
                ),
                "content": row["content"],
                "created_at": row.get("created_at"),
            }
            for row in reversed(rows)
        ]

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute(
        """
        SELECT author_name, content, created_at FROM chat_messages
        ORDER BY id DESC LIMIT ?
        """,
        (limit,),
    )
    rows = list(reversed(c.fetchall()))
    conn.close()
    return [{"author": row[0], "content": row[1], "created_at": row[2]} for row in rows]


def render_chat_tab() -> None:
    init_chat_db()
    user_hash = st.session_state.get("user_hash", "anonymous")
    display_name = st.session_state.get("display_name", "Moon Wanderer")

    st.markdown("### 💬 LunaTick Chat")
    st.caption("Community lounge — refresh to see new messages.")

    if st.button("🔄 Refresh"):
        st.rerun()

    messages = recent_messages(40)
    box = st.container(height=360)
    with box:
        if not messages:
            st.caption("Silence under the moon… say something.")
        for message in messages:
            timestamp = str(message["created_at"])[11:16] if message["created_at"] else ""
            st.markdown(
                f"**{message['author']}** "
                f"<span style='color:#484f58;font-size:0.7rem'>{timestamp}</span>  \n"
                f"{message['content']}",
                unsafe_allow_html=True,
            )

    with st.form("chat_form", clear_on_submit=True):
        text = st.text_input(
            "Message",
            max_chars=500,
            label_visibility="collapsed",
            placeholder="Type a message…",
        )
        if st.form_submit_button("Send"):
            if post_message(user_hash, display_name, text):
                st.rerun()
            else:
                st.warning("Empty or too long.")
