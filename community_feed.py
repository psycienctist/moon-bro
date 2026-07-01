# community_feed.py
# Lunatic Community Feed — Full Implementation
# Includes: Image Uploads · Moderation Dashboard · Privacy Integration · Lunar Pulse Banner

import streamlit as st
import sqlite3
import hashlib
import os
import re
from datetime import datetime
from PIL import Image

# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------

UPLOAD_DIR = "community_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

FLAG_THRESHOLD = 5  # Auto-hide posts with this many flags

# --------------------------------------------------------------------------
# Database Setup
# --------------------------------------------------------------------------

def init_db():
    conn = sqlite3.connect("lunatick.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS community_posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_hash TEXT,
            display_name TEXT,
            title TEXT,
            content TEXT,
            phase TEXT,
            tag TEXT,
            image_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            upvotes INTEGER DEFAULT 0,
            downvotes INTEGER DEFAULT 0,
            is_anonymous BOOLEAN DEFAULT TRUE,
            is_hidden BOOLEAN DEFAULT FALSE,
            flag_count INTEGER DEFAULT 0
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS community_comments (
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
            flag_count INTEGER DEFAULT 0,
            FOREIGN KEY(post_id) REFERENCES community_posts(id)
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS community_flags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_hash TEXT,
            post_id INTEGER,
            comment_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_hash, post_id, comment_id)
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS community_consent (
            user_hash TEXT PRIMARY KEY,
            consent_given BOOLEAN DEFAULT FALSE,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def get_user_hash():
    if "user_id" not in st.session_state:
        st.session_state.user_id = "anonymous_" + hashlib.md5(str(datetime.now()).encode()).hexdigest()[:8]
    return hashlib.sha256(st.session_state.user_id.encode()).hexdigest()[:16]

def get_display_name():
    if "display_name" not in st.session_state:
        st.session_state.display_name = "Moon Wanderer"
    return st.session_state.display_name

def get_phase():
    return st.session_state.get("current_phase", "Waxing Gibbous")

def get_tag_options():
    return ["Reflection", "Question", "Insight", "Connection", "Gratitude", "Letting Go", "Other"]

def is_moderator():
    return st.session_state.get("user_role") == "admin"

# --------------------------------------------------------------------------
# Consent
# --------------------------------------------------------------------------

def has_community_consent():
    conn = sqlite3.connect("lunatick.db")
    c = conn.cursor()
    user_hash = get_user_hash()
    c.execute("SELECT consent_given FROM community_consent WHERE user_hash = ?", (user_hash,))
    row = c.fetchone()
    conn.close()
    return row and row[0]

def set_community_consent(consent):
    conn = sqlite3.connect("lunatick.db")
    c = conn.cursor()
    user_hash = get_user_hash()
    c.execute("""
        INSERT OR REPLACE INTO community_consent (user_hash, consent_given, updated_at)
        VALUES (?, ?, ?)
    """, (user_hash, consent, datetime.now().isoformat()))
    conn.commit()
    conn.close()

# --------------------------------------------------------------------------
# Moderation
# --------------------------------------------------------------------------

def flag_post(post_id):
    conn = sqlite3.connect("lunatick.db")
    c = conn.cursor()
    user_hash = get_user_hash()
    try:
        c.execute("INSERT INTO community_flags (user_hash, post_id) VALUES (?, ?)", (user_hash, post_id))
        c.execute("UPDATE community_posts SET flag_count = flag_count + 1 WHERE id = ?", (post_id,))
        c.execute("UPDATE community_posts SET is_hidden = 1 WHERE id = ? AND flag_count >= ?", (post_id, FLAG_THRESHOLD))
        conn.commit()
    except sqlite3.IntegrityError:
        st.warning("You already flagged this post.")
    conn.close()

def flag_comment(comment_id):
    conn = sqlite3.connect("lunatick.db")
    c = conn.cursor()
    user_hash = get_user_hash()
    try:
        c.execute("INSERT INTO community_flags (user_hash, comment_id) VALUES (?, ?)", (user_hash, comment_id))
        c.execute("UPDATE community_comments SET flag_count = flag_count + 1 WHERE id = ?", (comment_id,))
        c.execute("UPDATE community_comments SET is_hidden = 1 WHERE id = ? AND flag_count >= ?", (comment_id, FLAG_THRESHOLD))
        conn.commit()
    except sqlite3.IntegrityError:
        st.warning("You already flagged this comment.")
    conn.close()

def approve_post(post_id):
    conn = sqlite3.connect("lunatick.db")
    c = conn.cursor()
    c.execute("UPDATE community_posts SET flag_count = 0, is_hidden = 0 WHERE id = ?", (post_id,))
    conn.commit()
    conn.close()

def hide_post(post_id):
    conn = sqlite3.connect("lunatick.db")
    c = conn.cursor()
    c.execute("UPDATE community_posts SET is_hidden = 1 WHERE id = ?", (post_id,))
    conn.commit()
    conn.close()

def delete_post(post_id):
    conn = sqlite3.connect("lunatick.db")
    c = conn.cursor()
    c.execute("DELETE FROM community_posts WHERE id = ?", (post_id,))
    c.execute("DELETE FROM community_comments WHERE post_id = ?", (post_id,))
    conn.commit()
    conn.close()

# --------------------------------------------------------------------------
# Create / Retrieve
# --------------------------------------------------------------------------

def create_post(title, content, phase, tag, is_anonymous, image_file=None):
    conn = sqlite3.connect("lunatick.db")
    c = conn.cursor()
    user_hash = get_user_hash()
    display_name = "Anonymous" if is_anonymous else get_display_name()
    image_path = None
    if image_file:
        ext = image_file.name.split(".")[-1]
        filename = f"{user_hash}_{datetime.now().timestamp()}.{ext}"
        image_path = os.path.join(UPLOAD_DIR, filename)
        with open(image_path, "wb") as f:
            f.write(image_file.getbuffer())
    c.execute("""
        INSERT INTO community_posts (user_hash, display_name, title, content, phase, tag, image_path, is_anonymous)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (user_hash, display_name, title, content, phase, tag, image_path, is_anonymous))
    conn.commit()
    conn.close()

def get_posts(phase_filter=None, tag_filter=None, limit=20, show_hidden=False):
    conn = sqlite3.connect("lunatick.db")
    c = conn.cursor()
    query = "SELECT * FROM community_posts"
    conditions = []
    params = []
    if not show_hidden:
        conditions.append("is_hidden = 0")
    if phase_filter and phase_filter != "All Phases":
        conditions.append("phase = ?")
        params.append(phase_filter)
    if tag_filter and tag_filter != "All Tags":
        conditions.append("tag = ?")
        params.append(tag_filter)
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    c.execute(query, params)
    posts = c.fetchall()
    conn.close()
    return posts

def get_flagged_posts(threshold=FLAG_THRESHOLD):
    conn = sqlite3.connect("lunatick.db")
    c = conn.cursor()
    c.execute("SELECT * FROM community_posts WHERE flag_count >= ? ORDER BY flag_count DESC", (threshold,))
    posts = c.fetchall()
    conn.close()
    return posts

def add_comment(post_id, content, is_anonymous):
    conn = sqlite3.connect("lunatick.db")
    c = conn.cursor()
    user_hash = get_user_hash()
    display_name = "Anonymous" if is_anonymous else get_display_name()
    c.execute("""
        INSERT INTO community_comments (post_id, user_hash, display_name, content, is_anonymous)
        VALUES (?, ?, ?, ?, ?)
    """, (post_id, user_hash, display_name, content, is_anonymous))
    conn.commit()
    conn.close()

def get_comments(post_id):
    conn = sqlite3.connect("lunatick.db")
    c = conn.cursor()
    c.execute("SELECT * FROM community_comments WHERE post_id = ? AND is_hidden = 0 ORDER BY created_at ASC", (post_id,))
    comments = c.fetchall()
    conn.close()
    return comments

# --------------------------------------------------------------------------
# Lunar Pulse
# --------------------------------------------------------------------------

def get_lunar_pulse(phase):
    conn = sqlite3.connect("lunatick.db")
    c = conn.cursor()
    c.execute("SELECT content FROM community_posts WHERE phase = ? AND is_hidden = 0", (phase,))
    posts = c.fetchall()
    conn.close()
    if not posts:
        return f"🌕 Lunar Pulse — The {phase} moon is quiet tonight. Your reflection matters. Share something."

    themes = ["release", "gratitude", "overwhelm", "rest", "connection", "grief", "joy", "letting go", "beginning", "hope"]
    text = " ".join([p[0] for p in posts]).lower()
    theme_counts = {t: text.count(t) for t in themes}
    dominant_theme = max(theme_counts, key=theme_counts.get)
    total = len(posts)
    percentage = int((theme_counts[dominant_theme] / total) * 100) if total > 0 else 0
    return f"🌕 Lunar Pulse — Tonight's {phase} moon has {percentage}% of our community reflecting on {dominant_theme}. You are not alone."

# --------------------------------------------------------------------------
# UI: Moderation Dashboard
# --------------------------------------------------------------------------

def render_moderation_dashboard():
    st.markdown("### 🛡️ Moderation Dashboard")
    if not is_moderator():
        st.warning("Access restricted to moderators.")
        return

    flagged = get_flagged_posts()
    if not flagged:
        st.info("No flagged posts.")
        return

    for post in flagged:
        post_id, user_hash, display_name, title, content, phase, tag, img_path, created_at, upvotes, downvotes, is_anon, is_hidden, flag_count = post
        with st.container():
            st.markdown(f"""
            <div style="background: rgba(255,0,0,0.05); border: 1px solid rgba(255,0,0,0.3); border-radius: 12px; padding: 0.8rem; margin-bottom: 0.8rem;">
                <strong>{title}</strong><br>
                <span style="color: #8b949e; font-size: 0.8rem;">{content[:200]}...</span><br>
                <span style="color: #ff7b72; font-size: 0.75rem;">🚩 {flag_count} flags</span>
            </div>
            """, unsafe_allow_html=True)
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("✅ Approve", key=f"mod_approve_{post_id}"):
                    approve_post(post_id)
                    st.rerun()
            with col2:
                if st.button("🔒 Hide", key=f"mod_hide_{post_id}"):
                    hide_post(post_id)
                    st.rerun()
            with col3:
                if st.button("🗑️ Delete", key=f"mod_delete_{post_id}"):
                    delete_post(post_id)
                    st.rerun()

# --------------------------------------------------------------------------
# UI: Main Community Feed
# --------------------------------------------------------------------------

def render_community_tab():
    st.markdown("""
    <div style="font-family: 'Orbitron', sans-serif; font-size: 0.8rem; letter-spacing: 3px; color: #bc8cff; text-transform: uppercase; margin-bottom: 0.3rem;">
        🌐 Lunatic Community Feed
    </div>
    <div style="font-family: 'Crimson Pro', serif; font-size: 1rem; color: #8b949e; margin-bottom: 1.2rem; font-style: italic;">
        Share your reflections. Read what others are feeling. You are not alone under the moon.
    </div>
    """, unsafe_allow_html=True)

    # -- Lunar Pulse Banner --
    phase = get_phase()
    pulse = get_lunar_pulse(phase)
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #1b1040, #2d1b69); border-radius: 16px; padding: 1rem 1.5rem; margin-bottom: 1.5rem; border-left: 4px solid #bc8cff;">
        <div style="font-family: 'Orbitron', sans-serif; font-size: 0.7rem; color: #bc8cff; letter-spacing: 2px; margin-bottom: 0.2rem;">🌕 LUNAR PULSE</div>
        <div style="font-size: 1.1rem; color: #fff; line-height: 1.5;">{pulse}</div>
    </div>
    """, unsafe_allow_html=True)

    # -- Consent Check --
    if not has_community_consent():
        st.warning("🔒 You haven't opted in to community participation. Your posts and comments will remain private.")
        if st.button("✅ Opt in to community sharing"):
            set_community_consent(True)
            st.rerun()
        return

    # -- New Post --
    with st.expander("🌙 Share something with the community"):
        if not has_community_consent():
            st.warning("Please opt in above first.")
        else:
            title = st.text_input("Title", max_chars=100, placeholder="A thought, a question, a reflection...")
            content = st.text_area("Your post", max_chars=1000, placeholder="What's on your mind under tonight's moon?")
            uploaded_image = st.file_uploader("Attach an image (optional)", type=["jpg", "jpeg", "png", "webp"])
            phase = st.selectbox("Moon Phase", ["New Moon", "Waxing Crescent", "First Quarter", "Waxing Gibbous", "Full Moon", "Waning Gibbous", "Last Quarter", "Waning Crescent"], index=0)
            tag = st.selectbox("Tag", get_tag_options(), index=0)
            is_anonymous = st.checkbox("Post anonymously", value=True)

            if st.button("Share with the community"):
                if title.strip() and content.strip():
                    create_post(title, content, phase, tag, is_anonymous, uploaded_image)
                    st.success("🌙 Your post has been shared.")
                    st.rerun()
                else:
                    st.warning("Please fill in both title and content.")

    # -- Moderation Dashboard (Admin Only) --
    if is_moderator():
        render_moderation_dashboard()

    # -- Filters --
    col_filters = st.columns([2, 2, 1])
    with col_filters[0]:
        phase_filter = st.selectbox("Filter by Phase", ["All Phases", "New Moon", "Waxing Crescent", "First Quarter", "Waxing Gibbous", "Full Moon", "Waning Gibbous", "Last Quarter", "Waning Crescent"], index=0)
    with col_filters[1]:
        tag_filter = st.selectbox("Filter by Tag", ["All Tags"] + get_tag_options(), index=0)
    with col_filters[2]:
        st.write("")
        st.write("")
        if st.button("🔄 Refresh"):
            st.rerun()

    # -- Feed --
    posts = get_posts(phase_filter, tag_filter)
    if not posts:
        st.info("No posts yet under this phase or tag. Be the first to share!")
        return

    for post in posts:
        post_id, user_hash, display_name, title, content, phase, tag, img_path, created_at, upvotes, downvotes, is_anon, is_hidden, flag_count = post

        with st.container():
            st.markdown(f"""
            <div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.07); border-radius: 12px; padding: 1rem 1.2rem; margin-bottom: 1rem;">
                <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                    <div>
                        <span style="font-weight: 700; color: #f0f6fc; font-size: 1rem;">{title}</span>
                        <span style="margin-left: 0.5rem; font-size: 0.6rem; background: rgba(110,64,201,0.2); padding: 0.1rem 0.5rem; border-radius: 12px; color: #bc8cff;">{phase}</span>
                        <span style="margin-left: 0.3rem; font-size: 0.6rem; background: rgba(88,166,255,0.1); padding: 0.1rem 0.5rem; border-radius: 12px; color: #58a6ff;">{tag}</span>
                    </div>
                    <div style="font-size: 0.55rem; color: #8b949e; font-family: 'Orbitron', sans-serif;">{created_at[:16]}</div>
                </div>
            """, unsafe_allow_html=True)

            if img_path and os.path.exists(img_path):
                st.image(img_path, use_container_width=True)

            st.markdown(f"""
                <div style="color: #c9d1d9; line-height: 1.6; font-size: 0.95rem; margin: 0.5rem 0;">{content}</div>
                <div style="display: flex; gap: 1rem; align-items: center; margin-top: 0.3rem;">
                    <span style="font-size: 0.7rem; color: #8b949e;">by {display_name}</span>
                    <span style="font-size: 0.7rem; color: #8b949e;">❤️ {upvotes} · 💔 {downvotes}</span>
            """, unsafe_allow_html=True)

            if not is_moderator():
                if st.button("🚩 Flag", key=f"flag_{post_id}"):
                    flag_post(post_id)
                    st.success("Post flagged for review.")
                    st.rerun()

            st.markdown("</div></div>", unsafe_allow_html=True)

            # -- Comments --
            with st.expander(f"💬 Comments ({len(get_comments(post_id))})"):
                for comment in get_comments(post_id):
                    cid, c_post_id, c_user_hash, c_display_name, c_content, c_created_at, c_upvotes, c_downvotes, c_anon, c_hidden, c_flag_count = comment
                    st.markdown(f"""
                    <div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.07); border-radius: 8px; padding: 0.5rem 0.8rem; margin-bottom: 0.4rem;">
                        <div style="display: flex; justify-content: space-between;">
                            <span style="font-size: 0.7rem; color: #8b949e;">{c_display_name}</span>
                            <span style="font-size: 0.55rem; color: #484f58;">{c_created_at[:16]}</span>
                        </div>
                        <div style="font-size: 0.9rem; color: #c9d1d9;">{c_content}</div>
                    </div>
                    """, unsafe_allow_html=True)

                    if not is_moderator():
                        if st.button("🚩 Flag comment", key=f"flag_comment_{cid}"):
                            flag_comment(cid)
                            st.success("Comment flagged for review.")
                            st.rerun()

                with st.form(key=f"comment_form_{post_id}"):
                    comment_content = st.text_area("Add a comment", max_chars=500, placeholder="Share your thoughts...", key=f"comment_{post_id}")
                    comment_anon = st.checkbox("Comment anonymously", value=True, key=f"comment_anon_{post_id}")
                    if st.form_submit_button("Reply"):
                        if comment_content.strip():
                            add_comment(post_id, comment_content, comment_anon)
                            st.success("Comment added.")
                            st.rerun()
                        else:
                            st.warning("Please write something.")

# --------------------------------------------------------------------------
# Seed Demo Data
# --------------------------------------------------------------------------

def seed_demo_posts():
    conn = sqlite3.connect("lunatick.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM community_posts")
    if c.fetchone()[0] == 0:
        demo_posts = [
            ("Feeling the pull of the full moon", "Anyone else feeling extra emotional tonight? I've been crying at everything.", "Full Moon", "Reflection"),
            ("What are you letting go of this month?", "I'm releasing the need to control everything. The moon reminds me to trust the flow.", "Waning Gibbous", "Gratitude"),
            ("Question for the community", "How do you track your emotions across the lunar cycle? I'm new to this.", "First Quarter", "Question")
        ]
        for title, content, phase, tag in demo_posts:
            c.execute("""
                INSERT INTO community_posts (user_hash, display_name, title, content, phase, tag, is_anonymous)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, ("demo_user", "Lunatic Pioneer", title, content, phase, tag, True))
        conn.commit()
    conn.close()