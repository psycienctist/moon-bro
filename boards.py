# boards.py
# Simple message boards for Streamlit moon-bro

from __future__ import annotations

from collections import Counter

import streamlit as st
import sqlite3

import supabase_store

DB = "lunatick.db"

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
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS boards (
            slug TEXT PRIMARY KEY,
            name TEXT,
            description TEXT
        )
        """
    )
    c.execute(
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
        c.execute(
            "INSERT OR IGNORE INTO boards (slug, name, description) VALUES (?, ?, ?)",
            (slug, name, desc),
        )
    conn.commit()
    conn.close()


def list_boards() -> list:
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
    c = conn.cursor()
    c.execute("SELECT slug, name, description FROM boards")
    boards = [{"slug": r[0], "name": r[1], "description": r[2]} for r in c.fetchall()]
    for board in boards:
        c.execute("SELECT COUNT(*) FROM board_posts WHERE board_slug=?", (board["slug"],))
        board["post_count"] = c.fetchone()[0]
    conn.close()
    return boards


def create_post(board_slug: str, author_hash: str, author_name: str, title: str, content: str) -> None:
    if _using_supabase_backend():
        _supabase().create_board_post(
            board_slug, _resolve_auth_subject(author_hash), title.strip(), content.strip()
        )
        return

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute(
        """
        INSERT INTO board_posts (board_slug, author_hash, author_name, title, content)
        VALUES (?, ?, ?, ?, ?)
        """,
        (board_slug, author_hash, author_name, title.strip(), content.strip()),
    )
    conn.commit()
    conn.close()


def list_posts(board_slug: str | None = None, limit: int = 30) -> list:
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
    c = conn.cursor()
    if board_slug:
        c.execute(
            """
            SELECT id, board_slug, author_name, title, content, created_at
            FROM board_posts WHERE board_slug=? ORDER BY created_at DESC LIMIT ?
            """,
            (board_slug, limit),
        )
    else:
        c.execute(
            """
            SELECT id, board_slug, author_name, title, content, created_at
            FROM board_posts ORDER BY created_at DESC LIMIT ?
            """,
            (limit,),
        )
    rows = c.fetchall()
    conn.close()
    return [
        {"id": r[0], "board": r[1], "author": r[2], "title": r[3], "content": r[4], "created_at": r[5]}
        for r in rows
    ]


def render_boards_tab() -> None:
    init_boards_db()
    user_hash = st.session_state.get("user_hash", "anonymous")
    display_name = st.session_state.get("display_name", "Moon Wanderer")

    st.markdown("### 📋 Message Boards")
    boards = list_boards()
    board_labels = {board["name"]: board["slug"] for board in boards}
    board_labels["🌐 All Boards"] = None

    choice = st.selectbox("Board", list(board_labels.keys()))
    slug = board_labels[choice]

    with st.expander("✍️ New post", expanded=False):
        if slug is None:
            post_board = st.selectbox("Post to", [board["name"] for board in boards], key="post_board_pick")
            post_slug = board_labels[post_board]
        else:
            post_slug = slug
        title = st.text_input("Title", max_chars=120)
        body = st.text_area("Content", height=120, max_chars=3000)
        if st.button("Post", type="primary"):
            if title.strip() and body.strip():
                create_post(post_slug, user_hash, display_name, title, body)
                st.success("Posted.")
                st.rerun()
            else:
                st.warning("Title and content required.")

    posts = list_posts(slug)
    if not posts:
        st.info("No posts yet. Be the first signal.")
    for post in posts:
        st.markdown(
            f"""
            <div style="background:#161b22;border:1px solid #30363d;border-radius:12px;
                        padding:0.9rem 1rem;margin-bottom:0.7rem;">
              <div style="font-size:0.7rem;color:#8b949e;">{post['board']} · @{post['author']} · {str(post['created_at'])[:16]}</div>
              <div style="font-weight:700;color:#f0f6fc;margin:0.25rem 0;">{post['title']}</div>
              <div style="color:#c9d1d9;font-size:0.95rem;white-space:pre-wrap;">{post['content']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
