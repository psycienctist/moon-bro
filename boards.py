# boards.py
# Simple message boards for Streamlit moon-bro

import streamlit as st
import sqlite3

DB = "lunatick.db"

DEFAULT_BOARDS = [
    ("general", "🌙 General", "Open discussion"),
    ("rituals", "🕯️ Full Moon Rituals", "Share practices"),
    ("astrology", "♒ Astrology", "Charts & transits"),
    ("sightings", "🔭 Sky Sightings", "Photos & observations"),
    ("memes", "😹 Cosmic Memes", "Lunar humor"),
    ("intentions", "✨ Intentions", "Set & reflect"),
]


def init_boards_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS boards (
            slug TEXT PRIMARY KEY,
            name TEXT,
            description TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS board_posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            board_slug TEXT,
            author_hash TEXT,
            author_name TEXT,
            title TEXT,
            content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    for slug, name, desc in DEFAULT_BOARDS:
        c.execute(
            "INSERT OR IGNORE INTO boards (slug, name, description) VALUES (?, ?, ?)",
            (slug, name, desc),
        )
    conn.commit()
    conn.close()


def list_boards() -> list:
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT slug, name, description FROM boards")
    boards = [{"slug": r[0], "name": r[1], "description": r[2]} for r in c.fetchall()]
    for b in boards:
        c.execute("SELECT COUNT(*) FROM board_posts WHERE board_slug=?", (b["slug"],))
        b["post_count"] = c.fetchone()[0]
    conn.close()
    return boards


def create_post(board_slug: str, author_hash: str, author_name: str, title: str, content: str):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
        INSERT INTO board_posts (board_slug, author_hash, author_name, title, content)
        VALUES (?, ?, ?, ?, ?)
    """, (board_slug, author_hash, author_name, title.strip(), content.strip()))
    conn.commit()
    conn.close()


def list_posts(board_slug=None, limit: int = 30) -> list:
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    if board_slug:
        c.execute("""
            SELECT id, board_slug, author_name, title, content, created_at
            FROM board_posts WHERE board_slug=? ORDER BY created_at DESC LIMIT ?
        """, (board_slug, limit))
    else:
        c.execute("""
            SELECT id, board_slug, author_name, title, content, created_at
            FROM board_posts ORDER BY created_at DESC LIMIT ?
        """, (limit,))
    rows = c.fetchall()
    conn.close()
    return [
        {"id": r[0], "board": r[1], "author": r[2], "title": r[3],
         "content": r[4], "created_at": r[5]}
        for r in rows
    ]


def render_boards_tab():
    init_boards_db()
    user_hash = st.session_state.get("user_hash", "anonymous")
    display_name = st.session_state.get("display_name", "Moon Wanderer")

    st.markdown("### 📋 Message Boards")
    boards = list_boards()
    board_labels = {b["name"]: b["slug"] for b in boards}
    board_labels["🌐 All Boards"] = None

    choice = st.selectbox("Board", list(board_labels.keys()))
    slug = board_labels[choice]

    with st.expander("✍️ New post", expanded=False):
        if slug is None:
            post_board = st.selectbox(
                "Post to",
                [b["name"] for b in boards],
                key="post_board_pick",
            )
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
    for p in posts:
        st.markdown(f"""
        <div style="background:#161b22;border:1px solid #30363d;border-radius:12px;
                    padding:0.9rem 1rem;margin-bottom:0.7rem;">
          <div style="font-size:0.7rem;color:#8b949e;">{p['board']} · @{p['author']} · {str(p['created_at'])[:16]}</div>
          <div style="font-weight:700;color:#f0f6fc;margin:0.25rem 0;">{p['title']}</div>
          <div style="color:#c9d1d9;font-size:0.95rem;white-space:pre-wrap;">{p['content']}</div>
        </div>
        """, unsafe_allow_html=True)
