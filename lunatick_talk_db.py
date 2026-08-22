# lunatick_talk_db.py
# Database schema + CRUD adapter for LunaTick Talk Message Board

from __future__ import annotations

import sqlite3
from datetime import datetime

import streamlit as st

import supabase_store


# --------------------------------------------------------------------------
# Backend and identity helpers
# --------------------------------------------------------------------------

def _using_supabase_backend() -> bool:
    return supabase_store.data_backend_from_streamlit_secrets() == "supabase"


def _supabase() -> supabase_store.SupabaseStore:
    return supabase_store.SupabaseStore(supabase_store.SupabaseSettings.from_streamlit_secrets())


def _resolve_auth_subject(user_reference: str | None = None) -> str:
    """Map legacy current-user hash callers to the authenticated canonical subject."""
    reference = str(user_reference or "").strip()
    subject = str(st.session_state.get("auth_subject", "")).strip()
    user_hash = str(st.session_state.get("user_hash", "")).strip()
    if subject and (not reference or reference == user_hash):
        return subject
    if reference:
        return reference
    raise ValueError("A signed-in LunaTicK identity is required to use LunaTicK Talk.")


def _summary_label(
    summaries: dict[str, dict], subject: str, is_anonymous: bool
) -> str:
    """Resolve the only author label that may be rendered into the Talk UI."""
    if is_anonymous:
        return "Anonymous"
    profile = summaries.get(subject, {})
    return str(profile.get("display_name") or profile.get("username") or "Moon Wanderer")


# --------------------------------------------------------------------------
# Database initialization
# --------------------------------------------------------------------------

def init_db() -> None:
    """Initialize legacy Talk tables only while the SQLite backend is selected."""
    if _using_supabase_backend():
        return

    conn = sqlite3.connect("lunatick.db")
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS lunatick_talk_posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_hash TEXT,
            display_name TEXT,
            user_moon_sign TEXT,
            current_moon_phase TEXT,
            content TEXT,
            image_path TEXT,
            upvotes INTEGER DEFAULT 0,
            downvotes INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_anonymous BOOLEAN DEFAULT TRUE,
            is_hidden BOOLEAN DEFAULT FALSE
        )
        """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS lunatick_talk_comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER,
            user_hash TEXT,
            display_name TEXT,
            content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            upvotes INTEGER DEFAULT 0,
            downvotes INTEGER DEFAULT 0,
            is_anonymous BOOLEAN DEFAULT TRUE,
            is_hidden BOOLEAN DEFAULT FALSE,
            FOREIGN KEY(post_id) REFERENCES lunatick_talk_posts(id)
        )
        """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS user_profiles (
            user_hash TEXT PRIMARY KEY,
            display_name TEXT,
            birth_date TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS user_votes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_hash TEXT,
            post_id INTEGER,
            vote_type TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_hash, post_id)
        )
        """
    )
    try:
        c.execute("ALTER TABLE user_profiles ADD COLUMN birth_date TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        c.execute("ALTER TABLE lunatick_talk_posts ADD COLUMN image_path TEXT")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()


# --------------------------------------------------------------------------
# Create
# --------------------------------------------------------------------------

def create_post(display_name, content, user_moon_sign, current_moon_phase, is_anonymous=True, image_path=None):
    if _using_supabase_backend():
        row = _supabase().create_talk_post(
            _resolve_auth_subject(),
            content.strip(),
            user_moon_sign,
            current_moon_phase,
            bool(is_anonymous),
            image_path,
        )
        return row["id"]

    conn = sqlite3.connect("lunatick.db")
    c = conn.cursor()
    user_hash = st.session_state.get("user_hash", "anonymous")
    c.execute(
        """
        INSERT INTO lunatick_talk_posts
            (user_hash, display_name, content, user_moon_sign, current_moon_phase, is_anonymous, image_path)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (user_hash, display_name, content, user_moon_sign, current_moon_phase, is_anonymous, image_path),
    )
    conn.commit()
    post_id = c.lastrowid
    conn.close()
    return post_id


def create_comment(post_id, display_name, content, is_anonymous=True):
    if _using_supabase_backend():
        _supabase().create_talk_comment(
            post_id, _resolve_auth_subject(), content.strip(), bool(is_anonymous)
        )
        return

    conn = sqlite3.connect("lunatick.db")
    c = conn.cursor()
    user_hash = st.session_state.get("user_hash", "anonymous")
    c.execute(
        """
        INSERT INTO lunatick_talk_comments (post_id, user_hash, display_name, content, is_anonymous)
        VALUES (?, ?, ?, ?, ?)
        """,
        (post_id, user_hash, display_name, content, is_anonymous),
    )
    conn.commit()
    conn.close()


# --------------------------------------------------------------------------
# Read
# --------------------------------------------------------------------------

def get_posts(limit=20, phase_filter=None):
    """Return the original Talk post tuple shape for the existing UI renderer."""
    if _using_supabase_backend():
        rows = _supabase().list_talk_posts(limit=limit, phase_filter=phase_filter)
        summaries = _supabase().get_public_profile_summaries(
            [row["profile_auth_subject"] for row in rows]
        )
        return [
            (
                row["id"],
                row["profile_auth_subject"],
                _summary_label(summaries, row["profile_auth_subject"], bool(row.get("is_anonymous"))),
                row.get("user_moon_sign") or "Unknown",
                row.get("current_moon_phase") or "Unknown",
                row["content"],
                row.get("image_path"),
                int(row.get("upvotes") or 0),
                int(row.get("downvotes") or 0),
                str(row.get("created_at") or ""),
                bool(row.get("is_anonymous")),
                bool(row.get("is_hidden")),
            )
            for row in rows
        ]

    conn = sqlite3.connect("lunatick.db")
    c = conn.cursor()
    query = "SELECT * FROM lunatick_talk_posts WHERE is_hidden = 0"
    params = []
    if phase_filter:
        query += " AND current_moon_phase = ?"
        params.append(phase_filter)
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    c.execute(query, params)
    posts = c.fetchall()
    conn.close()
    return posts


def get_comments(post_id):
    """Return the original Talk comment tuple shape for the existing UI renderer."""
    if _using_supabase_backend():
        rows = _supabase().list_talk_comments(post_id)
        summaries = _supabase().get_public_profile_summaries(
            [row["profile_auth_subject"] for row in rows]
        )
        return [
            (
                row["id"],
                row["post_id"],
                row["profile_auth_subject"],
                _summary_label(summaries, row["profile_auth_subject"], bool(row.get("is_anonymous"))),
                row["content"],
                str(row.get("created_at") or ""),
                int(row.get("upvotes") or 0),
                int(row.get("downvotes") or 0),
                bool(row.get("is_anonymous")),
                bool(row.get("is_hidden")),
            )
            for row in rows
        ]

    conn = sqlite3.connect("lunatick.db")
    c = conn.cursor()
    c.execute(
        "SELECT * FROM lunatick_talk_comments WHERE post_id = ? AND is_hidden = 0 ORDER BY created_at ASC",
        (post_id,),
    )
    comments = c.fetchall()
    conn.close()
    return comments


# --------------------------------------------------------------------------
# LunaTick Pulse (zero-token keyword analysis)
# --------------------------------------------------------------------------

def get_lunatick_pulse(phase_filter=None):
    posts = get_posts(limit=50, phase_filter=phase_filter)
    if not posts:
        return "The moon is quiet tonight. Be the first to share your reflection."

    themes = ["release", "gratitude", "overwhelm", "rest", "connection", "grief", "joy", "letting go", "beginning", "hope"]
    text = " ".join([post[5] for post in posts])
    theme_counts = {theme: text.lower().count(theme) for theme in themes}
    dominant_theme = max(theme_counts, key=theme_counts.get)
    total = len(posts)
    percentage = int((theme_counts[dominant_theme] / total) * 100) if total > 0 else 0
    return f"Tonight's {phase_filter or 'moon'} has {percentage}% of our community reflecting on {dominant_theme}. You are not alone."


# --------------------------------------------------------------------------
# Voting (with persistence)
# --------------------------------------------------------------------------

def get_user_vote(user_hash, post_id):
    if _using_supabase_backend():
        return _supabase().get_talk_vote(_resolve_auth_subject(user_hash), post_id)

    conn = sqlite3.connect("lunatick.db")
    c = conn.cursor()
    c.execute("SELECT vote_type FROM user_votes WHERE user_hash = ? AND post_id = ?", (user_hash, post_id))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None


def set_user_vote(user_hash, post_id, vote_type):
    if _using_supabase_backend():
        _supabase().set_talk_vote(_resolve_auth_subject(user_hash), post_id, vote_type)
        return

    conn = sqlite3.connect("lunatick.db")
    c = conn.cursor()
    c.execute("DELETE FROM user_votes WHERE user_hash = ? AND post_id = ?", (user_hash, post_id))
    if vote_type:
        c.execute("INSERT INTO user_votes (user_hash, post_id, vote_type) VALUES (?, ?, ?)", (user_hash, post_id, vote_type))
        if vote_type == "up":
            c.execute(
                "UPDATE lunatick_talk_posts SET upvotes = (SELECT COUNT(*) FROM user_votes WHERE post_id = ? AND vote_type = 'up'), downvotes = (SELECT COUNT(*) FROM user_votes WHERE post_id = ? AND vote_type = 'down') WHERE id = ?",
                (post_id, post_id, post_id),
            )
        elif vote_type == "down":
            c.execute(
                "UPDATE lunatick_talk_posts SET downvotes = (SELECT COUNT(*) FROM user_votes WHERE post_id = ? AND vote_type = 'down'), upvotes = (SELECT COUNT(*) FROM user_votes WHERE post_id = ? AND vote_type = 'up') WHERE id = ?",
                (post_id, post_id, post_id),
            )
    else:
        c.execute(
            "UPDATE lunatick_talk_posts SET upvotes = (SELECT COUNT(*) FROM user_votes WHERE post_id = ? AND vote_type = 'up'), downvotes = (SELECT COUNT(*) FROM user_votes WHERE post_id = ? AND vote_type = 'down') WHERE id = ?",
            (post_id, post_id, post_id),
        )
    conn.commit()
    conn.close()


# --------------------------------------------------------------------------
# Moderation and legacy profile compatibility
# --------------------------------------------------------------------------

def hide_post(post_id):
    if _using_supabase_backend():
        _supabase().hide_talk_post(post_id)
        return

    conn = sqlite3.connect("lunatick.db")
    c = conn.cursor()
    c.execute("UPDATE lunatick_talk_posts SET is_hidden = 1 WHERE id = ?", (post_id,))
    conn.commit()
    conn.close()


def get_user_profile(user_hash):
    if _using_supabase_backend():
        row = _supabase().get_profile_by_auth_subject(_resolve_auth_subject(user_hash))
        if not row:
            return None
        return {"display_name": row.get("display_name"), "birth_date": row.get("birth_date")}

    conn = sqlite3.connect("lunatick.db")
    c = conn.cursor()
    c.execute("SELECT display_name, birth_date FROM user_profiles WHERE user_hash = ?", (user_hash,))
    row = c.fetchone()
    conn.close()
    return {"display_name": row[0], "birth_date": row[1]} if row else None


def set_user_profile(user_hash, display_name, birth_date=None):
    if _using_supabase_backend():
        _supabase().update_profile_fields(
            _resolve_auth_subject(user_hash),
            {"display_name": display_name, "birth_date": birth_date},
        )
        return

    conn = sqlite3.connect("lunatick.db")
    c = conn.cursor()
    c.execute(
        """
        INSERT OR REPLACE INTO user_profiles (user_hash, display_name, birth_date, updated_at)
        VALUES (?, ?, ?, ?)
        """,
        (user_hash, display_name, birth_date, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()


# --------------------------------------------------------------------------
# Seed data
# --------------------------------------------------------------------------

def seed_talk_posts():
    """Keep the Supabase fresh start empty; retain legacy SQLite demo seeding only."""
    if _using_supabase_backend():
        return

    conn = sqlite3.connect("lunatick.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM lunatick_talk_posts")
    if c.fetchone()[0] == 0:
        demo_posts = [
            ("🌕 Full Moon Reflections", "Anyone else feeling extra emotional tonight? I've been crying at everything. The moon is so bright.", "Waxing Gibbous", "Pisces"),
            ("🌱 What are you planting this cycle?", "I'm setting an intention to release the need to control everything. The moon reminds me to trust the flow.", "Waxing Crescent", "Taurus"),
            ("💫 Question for the community", "How do you track your emotions across the lunar cycle? I'm new to this and would love tips.", "First Quarter", "Gemini"),
            ("🕊️ Gratitude under the Waning Moon", "Feeling grateful for the friends who understand my moon phases without explanation. You know who you are.", "Waning Gibbous", "Cancer"),
            ("🌑 New Moon Intentions", "Silence. Stillness. A new beginning. What are you calling in?", "New Moon", "Capricorn"),
        ]
        for display_name, content, phase, sign in demo_posts:
            c.execute(
                """
                INSERT INTO lunatick_talk_posts
                    (user_hash, display_name, content, current_moon_phase, user_moon_sign, is_anonymous)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                ("seed_user", display_name, content, phase, sign, False),
            )
        conn.commit()
        c.execute("SELECT id FROM lunatick_talk_posts LIMIT 1")
        post_id = c.fetchone()[0]
        c.execute(
            """
            INSERT INTO lunatick_talk_comments (post_id, user_hash, display_name, content, is_anonymous)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("seed_user", "LunaSeeker", "I feel this so deeply. The full moon always brings everything to the surface for me too. 🌕", False),
        )
        c.execute(
            """
            INSERT INTO lunatick_talk_comments (post_id, user_hash, display_name, content, is_anonymous)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("seed_user", "MoonChild42", "Same here. I've been journaling every night this week and it's been so healing.", False),
        )
        conn.commit()
    conn.close()
