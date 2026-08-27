"""Compact, Reddit-style discussion board for the LunaTicK Talk screen."""

from __future__ import annotations

from collections import Counter
import html
import sqlite3

import streamlit as st

import supabase_store


DB = "lunatick.db"
DEFAULT_BOARD_SLUG = "general"
DEFAULT_BOARDS = [
    ("general", "🌙 General", "Open discussion"),
    ("rituals", "🕯️ Full Moon Rituals", "Share practices"),
    ("astrology", "♒ Astrology", "Charts & transits"),
    ("sightings", "🔭 Sky Sightings", "Photos & observations"),
    ("memes", "😹 Cosmic Memes", "Lunar humor"),
    ("intentions", "✨ Intentions", "Set & reflect"),
]


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
    raise ValueError("A signed-in LunaTicK identity is required to use Boards.")


def init_boards_db() -> None:
    """Initialize the active backend's board catalog without importing SQLite posts."""
    if _using_supabase_backend():
        _supabase().seed_boards(
            [{"slug": slug, "name": name, "description": desc} for slug, name, desc in DEFAULT_BOARDS]
        )
        return

    conn = sqlite3.connect(DB)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS boards (
                slug TEXT PRIMARY KEY,
                name TEXT,
                description TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS board_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                board_slug TEXT,
                author_hash TEXT,
                author_name TEXT,
                title TEXT,
                content TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        for slug, name, desc in DEFAULT_BOARDS:
            conn.execute(
                "INSERT OR IGNORE INTO boards (slug, name, description) VALUES (?, ?, ?)",
                (slug, name, desc),
            )
        conn.commit()
    finally:
        conn.close()


def list_boards() -> list[dict]:
    if _using_supabase_backend():
        store = _supabase()
        boards = store.list_boards()
        counts = Counter(store.list_board_post_slugs())
        return [
            {
                "slug": row["slug"],
                "name": row["name"],
                "description": row.get("description") or "",
                "post_count": counts.get(row["slug"], 0),
            }
            for row in boards
        ]

    conn = sqlite3.connect(DB)
    try:
        rows = conn.execute("SELECT slug, name, description FROM boards").fetchall()
        boards = [{"slug": row[0], "name": row[1], "description": row[2]} for row in rows]
        for board in boards:
            board["post_count"] = conn.execute(
                "SELECT COUNT(*) FROM board_posts WHERE board_slug=?", (board["slug"],)
            ).fetchone()[0]
        return boards
    finally:
        conn.close()


def create_post(board_slug: str, author_hash: str, author_name: str, title: str, content: str) -> None:
    """Create one lasting message-board post."""
    if _using_supabase_backend():
        _supabase().create_board_post(
            board_slug, _resolve_auth_subject(author_hash), title.strip(), content.strip()
        )
        return

    conn = sqlite3.connect(DB)
    try:
        conn.execute(
            """
            INSERT INTO board_posts (board_slug, author_hash, author_name, title, content)
            VALUES (?, ?, ?, ?, ?)
            """,
            (board_slug, author_hash, author_name, title.strip(), content.strip()),
        )
        conn.commit()
    finally:
        conn.close()


def list_posts(board_slug: str | None = None, limit: int = 30) -> list[dict]:
    if _using_supabase_backend():
        rows = _supabase().list_board_posts(board_slug, limit)
        profiles = _supabase().get_public_profile_summaries(
            [row["profile_auth_subject"] for row in rows]
        )
        return [
            {
                "id": row["id"],
                "board": row["board_slug"],
                "author": (
                    profiles.get(row["profile_auth_subject"], {}).get("username")
                    or profiles.get(row["profile_auth_subject"], {}).get("display_name")
                    or "Moon Wanderer"
                ),
                "title": row["title"],
                "content": row["content"],
                "created_at": row.get("created_at"),
            }
            for row in rows
        ]

    conn = sqlite3.connect(DB)
    try:
        if board_slug:
            rows = conn.execute(
                """
                SELECT id, board_slug, author_name, title, content, created_at
                FROM board_posts WHERE board_slug=? ORDER BY created_at DESC LIMIT ?
                """,
                (board_slug, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT id, board_slug, author_name, title, content, created_at
                FROM board_posts ORDER BY created_at DESC LIMIT ?
                """,
                (limit,),
            ).fetchall()
    finally:
        conn.close()
    return [
        {
            "id": row[0],
            "board": row[1],
            "author": row[2],
            "title": row[3],
            "content": row[4],
            "created_at": row[5],
        }
        for row in rows
    ]


def _board_label(slug: str) -> str:
    return next((name for key, name, _ in DEFAULT_BOARDS if key == slug), "🌙 Discussion")


def render_boards_tab() -> None:
    """Render a simple all-discussions feed with one destination for new posts."""
    init_boards_db()
    user_hash = st.session_state.get("user_hash", "anonymous")
    display_name = st.session_state.get("display_name", "Moon Wanderer")

    with st.expander("Start a discussion", expanded=False):
        with st.form("lunatick_talk_board_post", clear_on_submit=True):
            title = st.text_input(
                "Title", max_chars=120, placeholder="What is on your mind?"
            )
            body = st.text_area(
                "Post", height=92, max_chars=3000, placeholder="Share a thought with the community…"
            )
            post = st.form_submit_button("Post to the board", type="primary", use_container_width=True)
        if post:
            if title.strip() and body.strip():
                create_post(DEFAULT_BOARD_SLUG, user_hash, display_name, title, body)
                st.success("Posted to the board.")
                st.rerun()
            else:
                st.warning("Add a title and message before posting.")

    posts = list_posts(limit=12)
    with st.container(height=245, border=True):
        if not posts:
            st.caption("No discussions yet. Start the first thread.")
        for post in posts:
            board = html.escape(_board_label(str(post.get("board") or "")))
            author = html.escape(str(post.get("author") or "Moon Wanderer"))
            title = html.escape(str(post.get("title") or "Untitled"))
            content = html.escape(str(post.get("content") or "")).replace("\n", "<br>")
            created_at = html.escape(str(post.get("created_at") or "")[:16])
            st.markdown(
                f"<article style='border-bottom:1px solid #30363d;padding:.5rem 0 .58rem;'>"
                f"<div style='color:#8b949e;font-size:.65rem;'>{board} · @{author} · {created_at}</div>"
                f"<div style='color:#f0f6fc;font-weight:700;margin:.18rem 0;'>{title}</div>"
                f"<div style='color:#c9d1d9;font-size:.88rem;line-height:1.42;'>{content}</div>"
                f"</article>",
                unsafe_allow_html=True,
            )
