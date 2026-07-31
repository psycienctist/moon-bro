# chat_room.py
# Lightweight chat for Streamlit (refresh-based, no websockets)

import streamlit as st
import sqlite3

DB = "lunatick.db"


def init_chat_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            author_hash TEXT,
            author_name TEXT,
            content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def post_message(author_hash: str, author_name: str, content: str):
    content = content.strip()
    if not content or len(content) > 1000:
        return False
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
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
        SELECT author_name, content, created_at FROM chat_messages
        ORDER BY id DESC LIMIT ?
    """, (limit,))
    rows = list(reversed(c.fetchall()))
    conn.close()
    return [{"author": r[0], "content": r[1], "created_at": r[2]} for r in rows]


def render_chat_tab():
    init_chat_db()
    user_hash = st.session_state.get("user_hash", "anonymous")
    display_name = st.session_state.get("display_name", "Moon Wanderer")

    st.markdown("### 💬 LunaTick Chat")
    st.caption("Community lounge — refresh to see new messages.")

    if st.button("🔄 Refresh"):
        st.rerun()

    msgs = recent_messages(40)
    box = st.container(height=360)
    with box:
        if not msgs:
            st.caption("Silence under the moon… say something.")
        for m in msgs:
            ts = str(m["created_at"])[11:16] if m["created_at"] else ""
            st.markdown(
                f"**{m['author']}** "
                f"<span style='color:#484f58;font-size:0.7rem'>{ts}</span>  \n"
                f"{m['content']}",
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
