"""Compact Reddit-style discussion board for the LunaTicK Talk screen."""

from __future__ import annotations

from collections import Counter
import html
import sqlite3

import streamlit as st

import supabase_store


DB = "lunatick.db"
DEFAULT_BOARD_SLUG = "general"
SORT_OPTIONS = ("Newest", "Top", "Controversial")
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


def _current_member_reference(user_hash: str) -> str:
    """Return the active member's stable storage identity for vote ownership."""
    return _resolve_auth_subject(user_hash) if _using_supabase_backend() else str(user_hash)


def init_boards_db() -> None:
    """Initialize board posts and one-vote-per-member storage for the active backend."""
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
                upvotes INTEGER NOT NULL DEFAULT 0,
                downvotes INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        existing_columns = {row[1] for row in conn.execute("PRAGMA table_info(board_posts)")}
        for column in ("upvotes", "downvotes"):
            if column not in existing_columns:
                conn.execute(f"ALTER TABLE board_posts ADD COLUMN {column} INTEGER NOT NULL DEFAULT 0")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS board_post_votes (
                board_post_id INTEGER NOT NULL,
                user_hash TEXT NOT NULL,
                vote_type TEXT NOT NULL CHECK (vote_type IN ('up', 'down')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (board_post_id, user_hash),
                FOREIGN KEY (board_post_id) REFERENCES board_posts(id) ON DELETE CASCADE
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


def _member_votes(user_hash: str, post_ids: list[int]) -> dict[int, str]:
    """Return the current member's vote for each supplied post id."""
    if not post_ids:
        return {}
    if _using_supabase_backend():
        return _supabase().get_board_post_votes(_resolve_auth_subject(user_hash), post_ids)

    placeholders = ",".join("?" for _ in post_ids)
    conn = sqlite3.connect(DB)
    try:
        rows = conn.execute(
            f"SELECT board_post_id, vote_type FROM board_post_votes WHERE user_hash=? AND board_post_id IN ({placeholders})",
            [user_hash, *post_ids],
        ).fetchall()
        return {int(row[0]): str(row[1]) for row in rows}
    finally:
        conn.close()


def list_posts(
    board_slug: str | None = None,
    limit: int = 30,
    viewer_hash: str | None = None,
) -> list[dict]:
    """List visible posts with scores and, when provided, the viewer's own vote."""
    if _using_supabase_backend():
        rows = _supabase().list_board_posts(board_slug, limit)
        profiles = _supabase().get_public_profile_summaries(
            [row["profile_auth_subject"] for row in rows]
        )
        votes = _member_votes(viewer_hash, [int(row["id"]) for row in rows]) if viewer_hash else {}
        return [
            {
                "id": int(row["id"]),
                "board": row["board_slug"],
                "author_reference": row["profile_auth_subject"],
                "author": (
                    profiles.get(row["profile_auth_subject"], {}).get("username")
                    or profiles.get(row["profile_auth_subject"], {}).get("display_name")
                    or "Moon Wanderer"
                ),
                "title": row["title"],
                "content": row["content"],
                "upvotes": int(row.get("upvotes") or 0),
                "downvotes": int(row.get("downvotes") or 0),
                "viewer_vote": votes.get(int(row["id"])),
                "created_at": row.get("created_at"),
            }
            for row in rows
        ]

    conn = sqlite3.connect(DB)
    try:
        if board_slug:
            rows = conn.execute(
                """
                SELECT id, board_slug, author_hash, author_name, title, content, upvotes, downvotes, created_at
                FROM board_posts WHERE board_slug=? ORDER BY created_at DESC LIMIT ?
                """,
                (board_slug, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT id, board_slug, author_hash, author_name, title, content, upvotes, downvotes, created_at
                FROM board_posts ORDER BY created_at DESC LIMIT ?
                """,
                (limit,),
            ).fetchall()
    finally:
        conn.close()

    post_ids = [int(row[0]) for row in rows]
    votes = _member_votes(viewer_hash, post_ids) if viewer_hash else {}
    return [
        {
            "id": int(row[0]),
            "board": row[1],
            "author_reference": row[2],
            "author": row[3],
            "title": row[4],
            "content": row[5],
            "upvotes": int(row[6] or 0),
            "downvotes": int(row[7] or 0),
            "viewer_vote": votes.get(int(row[0])),
            "created_at": row[8],
        }
        for row in rows
    ]


def set_post_vote(user_hash: str, post_id: int, vote_type: str | None) -> tuple[int, int]:
    """Set, switch, or remove the caller's vote and return updated totals."""
    if vote_type not in {"up", "down", None}:
        raise ValueError("vote_type must be up, down, or None")
    if _using_supabase_backend():
        return _supabase().set_board_post_vote(_resolve_auth_subject(user_hash), post_id, vote_type)

    conn = sqlite3.connect(DB)
    try:
        conn.execute(
            "DELETE FROM board_post_votes WHERE board_post_id=? AND user_hash=?",
            (int(post_id), user_hash),
        )
        if vote_type:
            conn.execute(
                "INSERT INTO board_post_votes (board_post_id, user_hash, vote_type) VALUES (?, ?, ?)",
                (int(post_id), user_hash, vote_type),
            )
        upvotes = conn.execute(
            "SELECT COUNT(*) FROM board_post_votes WHERE board_post_id=? AND vote_type='up'",
            (int(post_id),),
        ).fetchone()[0]
        downvotes = conn.execute(
            "SELECT COUNT(*) FROM board_post_votes WHERE board_post_id=? AND vote_type='down'",
            (int(post_id),),
        ).fetchone()[0]
        conn.execute(
            "UPDATE board_posts SET upvotes=?, downvotes=? WHERE id=?",
            (upvotes, downvotes, int(post_id)),
        )
        conn.commit()
        return int(upvotes), int(downvotes)
    finally:
        conn.close()


def _board_label(slug: str) -> str:
    return next((name for key, name, _ in DEFAULT_BOARDS if key == slug), "🌙 Discussion")


def _score(post: dict) -> int:
    return int(post.get("upvotes") or 0) - int(post.get("downvotes") or 0)


def _sort_posts(posts: list[dict], sort_mode: str) -> list[dict]:
    """Sort the current feed locally after applying privacy-safe vote totals."""
    if sort_mode == "Top":
        return sorted(posts, key=lambda post: (_score(post), str(post.get("created_at") or "")), reverse=True)
    if sort_mode == "Controversial":
        return sorted(
            posts,
            key=lambda post: (
                int(post.get("upvotes") or 0) + int(post.get("downvotes") or 0),
                -abs(_score(post)),
                str(post.get("created_at") or ""),
            ),
            reverse=True,
        )
    return sorted(posts, key=lambda post: str(post.get("created_at") or ""), reverse=True)


def _render_vote_controls(post: dict, user_hash: str) -> None:
    """Render one member's reversible vote controls for a board post."""
    member_reference = _current_member_reference(user_hash)
    is_own_post = str(post.get("author_reference") or "") == member_reference
    current_vote = post.get("viewer_vote")
    score = _score(post)
    vote_columns = st.columns([1, 1, 1.4, 4.6])
    with vote_columns[0]:
        if st.button(
            "▲",
            key=f"board_upvote_{post['id']}",
            type="primary" if current_vote == "up" else "secondary",
            help="Upvote this discussion" if not is_own_post else "You cannot vote on your own discussion.",
            disabled=is_own_post,
            use_container_width=True,
        ):
            set_post_vote(user_hash, int(post["id"]), None if current_vote == "up" else "up")
            st.rerun()
    with vote_columns[1]:
        if st.button(
            "▼",
            key=f"board_downvote_{post['id']}",
            type="primary" if current_vote == "down" else "secondary",
            help="Downvote this discussion" if not is_own_post else "You cannot vote on your own discussion.",
            disabled=is_own_post,
            use_container_width=True,
        ):
            set_post_vote(user_hash, int(post["id"]), None if current_vote == "down" else "down")
            st.rerun()
    with vote_columns[2]:
        st.caption(f"Score {score:+d}")
    with vote_columns[3]:
        st.caption(f"▲ {int(post.get('upvotes') or 0)}  ·  ▼ {int(post.get('downvotes') or 0)}")


def render_boards_tab(*, compact: bool = False) -> None:
    """Render a simple all-discussions feed with votes and flexible sorting.

    The Talk toggle uses the compact viewport so its selected board surface fits
    above mobile navigation; the feed itself remains independently scrollable.
    """
    init_boards_db()
    feed_height = 175 if compact else 275
    user_hash = st.session_state.get("user_hash", "anonymous")
    display_name = st.session_state.get("display_name", "Moon Wanderer")

    controls_left, controls_right = st.columns([2, 1])
    with controls_left:
        st.caption("Vote on conversations and sort the community signal.")
    with controls_right:
        sort_mode = st.selectbox(
            "Sort discussions", SORT_OPTIONS, label_visibility="collapsed", key="talk_board_sort"
        )

    with st.expander("Start a discussion", expanded=False):
        with st.form("lunatick_talk_board_post", clear_on_submit=True):
            title = st.text_input("Title", max_chars=120, placeholder="What is on your mind?")
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

    posts = _sort_posts(list_posts(limit=100, viewer_hash=user_hash), sort_mode)[:12]
    with st.container(height=feed_height, border=True):
        if not posts:
            st.caption("No discussions yet. Start the first thread.")
        for post in posts:
            board = html.escape(_board_label(str(post.get("board") or "")))
            author = html.escape(str(post.get("author") or "Moon Wanderer"))
            title = html.escape(str(post.get("title") or "Untitled"))
            content = html.escape(str(post.get("content") or "")).replace("\n", "<br>")
            created_at = html.escape(str(post.get("created_at") or "")[:16])
            st.markdown(
                f"<article style='border-bottom:1px solid #30363d;padding:.5rem 0 .18rem;'>"
                f"<div style='color:#8b949e;font-size:.65rem;'>{board} · @{author} · {created_at}</div>"
                f"<div style='color:#f0f6fc;font-weight:700;margin:.18rem 0;'>{title}</div>"
                f"<div style='color:#c9d1d9;font-size:.88rem;line-height:1.42;'>{content}</div>"
                f"</article>",
                unsafe_allow_html=True,
            )
            _render_vote_controls(post, user_hash)
