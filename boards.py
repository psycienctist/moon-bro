"""Compact Reddit-style discussion board for the LunaTicK Talk screen."""

from __future__ import annotations

from collections import Counter
import html
import sqlite3
from urllib.parse import quote

import streamlit as st

import supabase_store


DB = "lunatick.db"
# Required by app.py to replace a board renderer retained by a warm Streamlit worker.
BOARD_MODULE_VERSION = "compact_feed_v3"

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

PINNED_FEATURE_GUIDE = """
### 📌 LunaTicK Feature Field Guide

Welcome to LunaTicK Social. This pinned guide explains what each destination is for and how to get the most from it. Use **Connect** for community conversation, **Correct** for personal binaural-beat listening, **Inspect** for lunar and astronomical planning, **Reflect** for private writing, **Collect** for share-safe Cosmic Cards and connections, and **Prospect** for community reading matches.

## Connect · Message Board and Live Chat

**Live Chat** is the quick-moving room for greetings, short observations, timely questions, and friendly conversation. Use it when your message benefits from an immediate exchange. **Message Board** is for lasting discussions that should remain useful after the live chat moves on: questions, sky observations, practices, resources, and reflective topics.

To start a board thread, open **Start a discussion**, write a specific title, and provide enough context for another member to understand what you mean without guessing. Keep one main idea per thread when possible. Use **Newest** for recent activity, **Top** for posts the community has found useful, and **Controversial** for threads with substantial but divided engagement. Voting is a community signal: use ▲ for constructive, helpful, or insightful posts and ▼ for content that is misleading, off-topic, or less useful. You can change or remove your vote, but you cannot vote on your own discussion.

Public usernames in board posts and chat may be clickable. Open them to view the appropriate public member information and available connection options. Keep contact details, exact locations, private birth information, and identifying information out of public conversation. Disagree with ideas without attacking people, avoid flooding threads, and use the moderation path for harassment, spam, impersonation, or privacy violations.

## Correct · Binaural Beats

Correct is LunaTicK’s personal listening space for binaural-beat experimentation, relaxation, and focused reflection. Use headphones so the left and right channels can be heard separately. Choose a tone preset or set the available beat difference to suit your listening intention; the beat difference is the frequency gap between the two channels, not a diagnosis or a promise of a particular result.

The page uses sine-wave binaural playback with the automatic **11-second tone shift**. You can keep the default beat setting, use a meaningful value such as the Schumann-resonance setting if that is part of your personal practice, or explore the available random chakra sequence. Start at a comfortable volume, listen for a short period first, and stop if the sound causes discomfort. This feature is for personal relaxation and reflection only; it is not medical treatment or a substitute for professional care.

## Inspect · Calendar

Inspect is your planning view for the lunar cycle and notable skywatching moments. The calendar grid helps you orient yourself by date, while **Upcoming Events:** provides the fuller event detail below the grid, including lunar phases and other notable astronomical events when available. Use the event detail to decide which dates deserve a reminder, observation session, or personal reflection.

The compact **Private event** control near the legend is for your own planning notes. Add a clear title, date, and useful context, and remember that private entries are not community posts. When following an astronomical event, confirm the date and local conditions independently if precise observation timing matters; the calendar is an informational planning aid rather than a guarantee of visibility from every location.

## Reflect · Journal

Reflect is your private free-writing space. Use it for observations, intentions, dream notes, emotional check-ins, creative writing, or a record of what you noticed during another LunaTicK feature. A dated entry with a short title or opening sentence is easier to revisit than an unstructured block of text.

Write honestly and at your own pace. You can return to earlier entries to notice patterns, but the journal is not a diagnostic tool and its prompts are not professional medical or mental-health advice. Keep highly sensitive information limited to what you genuinely want stored, and never assume a journal entry is public simply because it relates to a public card or community conversation.

## Collect · Cosmic Cards

Collect turns selected, share-safe chart results into a visual Cosmic Card. Begin with your private birth inputs, search for your birthplace when available, and confirm the resolved place and historical timezone before saving. This confirmation step matters because an incorrect location or daylight-saving offset can change the calculated chart result.

The public card is intentionally limited to approved derived fields such as Sun, Moon, Rising, birth phase, full-moon count, and dominant-planet presentation. Exact birth date, birth time, birthplace, coordinates, timezone details, email address, and immutable account identifiers remain private. Search for another member by exact public username to view their public profile, send a card-trade request, and become connected only after the other member accepts. Accepted connections can support private member messaging under the app’s consent rules.

## Prospect · Reading Requests

Prospect is the community matching space for free astrology-reading requests. If you want a reading, describe what kind of reflection or chart discussion you are seeking and provide only the context you are comfortable sharing. If you volunteer as a reader, describe your approach honestly and set expectations about availability and scope.

A match is a mutual community arrangement, not a professional guarantee. Wait for the relevant request or match state before using its private conversation, communicate respectfully, and do not request unnecessary personal information. Astrology readings should be treated as reflective or entertainment-oriented community exchanges rather than medical, legal, financial, or mental-health advice. End a conversation clearly if either person is uncomfortable, and never share another member’s private details outside the matched exchange.

**A simple LunaTicK habit:** use Connect to exchange ideas, Correct to settle into listening, Inspect to notice timing, Reflect to write privately, Collect to share only what you approve, and Prospect to seek or offer a respectful reading match. Across every feature, protect consent, privacy, and the autonomy of other members.
"""


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
                "profile_username": profiles.get(row["profile_auth_subject"], {}).get("username") or "",
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
            "profile_username": "",
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
    # 255 px fills the Talk viewport down to the fixed mobile navigation while
    # preserving a small visual buffer and keeping the page itself unscrollable.
    feed_height = 255 if compact else 275
    user_hash = st.session_state.get("user_hash", "anonymous")
    display_name = st.session_state.get("display_name", "Moon Wanderer")

    _, controls_right = st.columns([2, 1])
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
    with st.container(
        height=feed_height,
        border=True,
        key="talk-board-feed" if compact else None,
    ):
        with st.expander("📌 Pinned LunaTicK Feature Guide", expanded=False):
            st.caption("Correct · Calendar · Journal · Cosmic Cards · Reading Requests")
            st.markdown(PINNED_FEATURE_GUIDE)
        if not posts:
            st.caption("No discussions yet. Start the first thread.")
        for post in posts:
            board = html.escape(_board_label(str(post.get("board") or "")))
            author = html.escape(str(post.get("author") or "Moon Wanderer"))
            profile_username = str(post.get("profile_username") or "").strip()
            profile_label = html.escape(profile_username or str(post.get("author") or "Moon Wanderer"))
            author_markup = (
                f"<a href='?profile={quote(profile_username, safe='')}' style='color:#bc8cff;text-decoration:none;'>@{profile_label}</a>"
                if profile_username else f"@{profile_label}"
            )
            title = html.escape(str(post.get("title") or "Untitled"))
            content = html.escape(str(post.get("content") or "")).replace("\n", "<br>")
            created_at = html.escape(str(post.get("created_at") or "")[:16])
            st.markdown(
                f"<article style='border-bottom:1px solid #30363d;padding:.5rem 0 .18rem;'>"
                f"<div style='color:#8b949e;font-size:.65rem;'>{board} · {author_markup} · {created_at}</div>"
                f"<div style='color:#f0f6fc;font-weight:700;margin:.18rem 0;'>{title}</div>"
                f"<div style='color:#c9d1d9;font-size:.88rem;line-height:1.42;'>{content}</div>"
                f"</article>",
                unsafe_allow_html=True,
            )
            _render_vote_controls(post, user_hash)
