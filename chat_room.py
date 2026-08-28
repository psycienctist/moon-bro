"""Lightweight auto-refreshing chat for the LunaTicK Talk screen."""

from __future__ import annotations

import html
import sqlite3
from urllib.parse import quote

import streamlit as st

import supabase_store


DB = "lunatick.db"
LIVE_CHAT_REFRESH_SECONDS = 5


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
    try:
        conn.execute(
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
    finally:
        conn.close()


def post_message(author_hash: str, author_name: str, content: str) -> bool:
    """Store one short community-chat message."""
    content = content.strip()
    if not content or len(content) > 1000:
        return False

    if _using_supabase_backend():
        _supabase().create_chat_message(_resolve_auth_subject(author_hash), content)
        return True

    conn = sqlite3.connect(DB)
    try:
        conn.execute(
            "INSERT INTO chat_messages (author_hash, author_name, content) VALUES (?, ?, ?)",
            (author_hash, author_name, content),
        )
        conn.commit()
    finally:
        conn.close()
    return True


def recent_messages(limit: int = 50) -> list[dict]:
    """Return visible messages in chronological order."""
    if _using_supabase_backend():
        rows = _supabase().list_chat_messages(limit)
        profiles = _supabase().get_public_profile_summaries(
            [row["profile_auth_subject"] for row in rows]
        )
        return [
            {
                "author": (
                    profiles.get(row["profile_auth_subject"], {}).get("display_name")
                    or profiles.get(row["profile_auth_subject"], {}).get("username")
                    or "Moon Wanderer"
                ),
                "profile_username": profiles.get(row["profile_auth_subject"], {}).get("username") or "",
                "content": row["content"],
                "created_at": row.get("created_at"),
            }
            for row in reversed(rows)
        ]

    conn = sqlite3.connect(DB)
    try:
        rows = conn.execute(
            """
            SELECT author_name, content, created_at FROM chat_messages
            ORDER BY id DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()
    finally:
        conn.close()
    return [
        {"author": row[0], "profile_username": "", "content": row[1], "created_at": row[2]}
        for row in reversed(rows)
    ]


def _render_chat_panel() -> None:
    """Render the refreshed portion of the Talk view."""
    user_hash = st.session_state.get("user_hash", "anonymous")
    display_name = st.session_state.get("display_name", "Moon Wanderer")
    messages = recent_messages(40)

    with st.container(height=195, border=True):
        if not messages:
            st.caption("No messages yet. Be the first voice in the room.")
        for message in messages:
            timestamp = str(message.get("created_at") or "")[11:16]
            author = html.escape(str(message.get("author") or "Moon Wanderer"))
            profile_username = str(message.get("profile_username") or "").strip()
            profile_label = html.escape(profile_username or str(message.get("author") or "Moon Wanderer"))
            author_markup = (
                f"<a href='?profile={quote(profile_username, safe='')}' style='color:#bc8cff;font-weight:700;text-decoration:none;'>@{profile_label}</a>"
                if profile_username else f"<span style='color:#bc8cff;font-weight:700;'>@{profile_label}</span>"
            )
            content = html.escape(str(message.get("content") or "")).replace("\n", "<br>")
            st.markdown(
                f"<div style='margin:0 0 .5rem;'>"
                f"{author_markup} "
                f"<span style='color:#8b949e;font-size:.68rem;'>{timestamp}</span><br>"
                f"<span style='color:#e6edf3;'>{content}</span></div>",
                unsafe_allow_html=True,
            )

    with st.form("lunatick_talk_live_chat_form", clear_on_submit=True):
        text = st.text_input(
            "Message",
            max_chars=500,
            label_visibility="collapsed",
            placeholder="Say something to the room…",
            key="lunatick_talk_message",
        )
        send = st.form_submit_button("Send", type="primary", use_container_width=True)
    if send:
        if post_message(user_hash, display_name, text):
            st.rerun()
        else:
            st.warning("Write a message of up to 500 characters.")


def render_chat_tab() -> None:
    """Render a client-visible chat feed that refreshes every few seconds."""
    init_chat_db()
    fragment = getattr(st, "fragment", None)
    if fragment is None:
        _render_chat_panel()
        return

    @fragment(run_every=LIVE_CHAT_REFRESH_SECONDS)
    def _live_chat_fragment() -> None:
        _render_chat_panel()

    _live_chat_fragment()
