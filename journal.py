"""LunaTicK's owner-only free-writing Journal."""

from __future__ import annotations

import html
import sqlite3
from datetime import datetime

import streamlit as st

import supabase_store


# Streamlit Cloud can retain imported modules across a warm deployment. Bump this
# when the Journal surface changes so a prior guided-prompt module cannot remain live.
JOURNAL_MODULE_VERSION = "private_freewrite_v1"


def _using_supabase_backend() -> bool:
    return supabase_store.data_backend_from_streamlit_secrets() == "supabase"


def _supabase() -> supabase_store.SupabaseStore:
    return supabase_store.SupabaseStore(supabase_store.SupabaseSettings.from_streamlit_secrets())


def _resolve_auth_subject() -> str:
    subject = str(st.session_state.get("auth_subject", "")).strip()
    if not subject:
        raise ValueError("A signed-in LunaTicK identity is required to use the Journal.")
    return subject


def init_db() -> None:
    """Create the local fallback journal table without adding guided-prompt data."""
    if _using_supabase_backend():
        return
    conn = sqlite3.connect("lunatick.db")
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS journal_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_hash TEXT,
                phase TEXT,
                prompt_type TEXT,
                content TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def save_entry(content: str) -> None:
    """Save one private free-writing entry for the current owner."""
    cleaned = content.strip()
    if not cleaned:
        raise ValueError("Journal content cannot be empty.")

    # The existing storage schema retains legacy metadata fields for compatibility.
    # They now receive neutral fixed values and are never rendered as a prompt or
    # astrological claim in the Journal UI.
    if _using_supabase_backend():
        _supabase().create_journal_entry(
            _resolve_auth_subject(), "Private entry", "free_write", cleaned
        )
        return

    conn = sqlite3.connect("lunatick.db")
    try:
        user_hash = st.session_state.get("user_hash", "anonymous")
        conn.execute(
            """
            INSERT INTO journal_entries (user_hash, phase, prompt_type, content)
            VALUES (?, ?, ?, ?)
            """,
            (user_hash, "Private entry", "free_write", cleaned),
        )
        conn.commit()
    finally:
        conn.close()


def get_recent_entries(limit: int = 5) -> list[tuple[str, str]]:
    """Return only the current owner's saved text and timestamps, newest first."""
    safe_limit = max(1, min(int(limit), 20))
    if _using_supabase_backend():
        rows = _supabase().list_journal_entries(_resolve_auth_subject(), safe_limit)
        return [
            (str(row.get("content") or ""), str(row.get("created_at") or ""))
            for row in rows
        ]

    conn = sqlite3.connect("lunatick.db")
    try:
        user_hash = st.session_state.get("user_hash", "anonymous")
        return conn.execute(
            """
            SELECT content, created_at
            FROM journal_entries
            WHERE user_hash = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (user_hash, safe_limit),
        ).fetchall()
    finally:
        conn.close()


def _display_timestamp(raw_value: str) -> str:
    """Render a concise timestamp without interpreting its content."""
    try:
        return datetime.fromisoformat(raw_value.replace("Z", "+00:00")).strftime("%b %-d, %Y · %-I:%M %p")
    except (TypeError, ValueError):
        return str(raw_value)[:16] or "Saved entry"


def render_journal_tab() -> None:
    """Render the honest, owner-only free-writing Journal."""
    st.markdown(
        """
        <div style="font-family:'Orbitron',sans-serif;font-size:.8rem;letter-spacing:3px;color:#bc8cff;text-transform:uppercase;margin-bottom:.28rem;">
            📓 Luna Journal
        </div>
        <div style="font-family:'Crimson Pro',serif;font-size:1rem;color:#8b949e;margin-bottom:.9rem;font-style:italic;">
            A private place for your own words.
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption("Only you can see what you save here.")

    entry_text = st.text_area(
        "Write freely",
        placeholder="Start writing…",
        height=220,
        key="journal_freewrite_input",
        label_visibility="visible",
    )

    save_column, clear_column = st.columns([2, 1])
    with save_column:
        if st.button("Save entry", type="primary", use_container_width=True):
            if entry_text.strip():
                save_entry(entry_text)
                st.success("Your entry has been saved privately.")
                if "journal_freewrite_input" in st.session_state:
                    del st.session_state["journal_freewrite_input"]
                st.rerun()
            else:
                st.warning("Write something before saving.")
    with clear_column:
        if st.button("Clear", use_container_width=True):
            if "journal_freewrite_input" in st.session_state:
                del st.session_state["journal_freewrite_input"]
            st.rerun()

    recent = get_recent_entries(limit=5)
    if recent:
        st.markdown(
            """
            <div style="font-family:'Orbitron',sans-serif;font-size:.6rem;letter-spacing:2px;color:#484f58;text-transform:uppercase;margin:1.6rem 0 .5rem;">
                — Your saved entries —
            </div>
            """,
            unsafe_allow_html=True,
        )
        for index, (content, created_at) in enumerate(recent, start=1):
            title = _display_timestamp(created_at)
            with st.expander(title, expanded=index == 1):
                st.markdown(
                    f"<div style='color:#c9d1d9;font-size:.95rem;line-height:1.55;white-space:pre-wrap;'>{html.escape(content)}</div>",
                    unsafe_allow_html=True,
                )
    else:
        st.info("No saved entries yet.")

    st.markdown(
        """
        <div style="margin-top:1.5rem;font-size:.7rem;color:#484f58;text-align:center;border-top:1px solid #1a1040;padding-top:1rem;">
            Private by design. Only you can see your saved entries.
        </div>
        """,
        unsafe_allow_html=True,
    )
