# lunatick_talk_db.py
# Database Schema + CRUD API for LunaTick Talk Message Board
# Built together by The Founder, The Mirror AI, and our AI Ally

import sqlite3
from datetime import datetime
import streamlit as st

# --------------------------------------------------------------------------
# Database Initialization
# --------------------------------------------------------------------------

def init_db():
    conn = sqlite3.connect("lunatick.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS lunatick_talk_posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_hash TEXT,
            display_name TEXT,
            user_moon_sign TEXT,
            current_moon_phase TEXT,
            content TEXT,
            upvotes INTEGER DEFAULT 0,
            downvotes INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_anonymous BOOLEAN DEFAULT TRUE,
            is_hidden BOOLEAN DEFAULT FALSE
        )
    """)
    c.execute("""
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
    """)
    conn.commit()
    conn.close()

# --------------------------------------------------------------------------
# Create
# --------------------------------------------------------------------------

def create_post(display_name, content, user_moon_sign, current_moon_phase, is_anonymous=True):
    conn = sqlite3.connect("lunatick.db")
    c = conn.cursor()
    user_hash = st.session_state.get("user_hash", "anonymous")
    c.execute("""
        INSERT INTO lunatick_talk_posts (user_hash, display_name, content, user_moon_sign, current_moon_phase, is_anonymous)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_hash, display_name, content, user_moon_sign, current_moon_phase, is_anonymous))
    conn.commit()
    post_id = c.lastrowid
    conn.close()
    return post_id

def create_comment(post_id, display_name, content, is_anonymous=True):
    conn = sqlite3.connect("lunatick.db")
    c = conn.cursor()
    user_hash = st.session_state.get("user_hash", "anonymous")
    c.execute("""
        INSERT INTO lunatick_talk_comments (post_id, user_hash, display_name, content, is_anonymous)
        VALUES (?, ?, ?, ?, ?)
    """, (post_id, user_hash, display_name, content, is_anonymous))
    conn.commit()
    conn.close()

# --------------------------------------------------------------------------
# Read
# --------------------------------------------------------------------------

def get_posts(limit=20, phase_filter=None):
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
    conn = sqlite3.connect("lunatick.db")
    c = conn.cursor()
    c.execute("SELECT * FROM lunatick_talk_comments WHERE post_id = ? AND is_hidden = 0 ORDER BY created_at ASC", (post_id,))
    comments = c.fetchall()
    conn.close()
    return comments

# --------------------------------------------------------------------------
# LunaTick Pulse (Community Pulse)
# --------------------------------------------------------------------------

def get_lunatick_pulse(phase_filter=None):
    """
    Returns a simple aggregated insight from the community.
    """
    posts = get_posts(limit=50, phase_filter=phase_filter)
    if not posts:
        return "The moon is quiet tonight. Be the first to share your reflection."

    themes = ["release", "gratitude", "overwhelm", "rest", "connection", "grief", "joy", "letting go", "beginning", "hope"]
    text = " ".join([post[5] for post in posts])  # content is at index 5
    theme_counts = {t: text.lower().count(t) for t in themes}
    dominant_theme = max(theme_counts, key=theme_counts.get)
    total = len(posts)
    percentage = int((theme_counts[dominant_theme] / total) * 100) if total > 0 else 0

    return f"Tonight's {phase_filter or 'moon'} has {percentage}% of our community reflecting on {dominant_theme}. You are not alone."

# --------------------------------------------------------------------------
# Vote (Upvote / Downvote)
# --------------------------------------------------------------------------

def vote_post(post_id, vote_type):
    conn = sqlite3.connect("lunatick.db")
    c = conn.cursor()
    if vote_type == "up":
        c.execute("UPDATE lunatick_talk_posts SET upvotes = upvotes + 1 WHERE id = ?", (post_id,))
    elif vote_type == "down":
        c.execute("UPDATE lunatick_talk_posts SET downvotes = downvotes + 1 WHERE id = ?", (post_id,))
    conn.commit()
    conn.close()

# --------------------------------------------------------------------------
# Moderation
# --------------------------------------------------------------------------

def hide_post(post_id):
    conn = sqlite3.connect("lunatick.db")
    c = conn.cursor()
    c.execute("UPDATE lunatick_talk_posts SET is_hidden = 1 WHERE id = ?", (post_id,))
    conn.commit()
    conn.close()