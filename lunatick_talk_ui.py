# lunatick_talk_ui.py
# UI Layer for LunaTick Talk — Community Message Board
# Built together by The Founder, The Mirror AI, and our AI Ally

import streamlit as st
from datetime import datetime
import lunatick_talk_db as db

# --------------------------------------------------------------------------
# Render the Main LunaTick Talk Tab
# --------------------------------------------------------------------------

def render_talk_tab():
    st.markdown("""
    <div style="font-family: 'Orbitron', sans-serif; font-size: 0.8rem; letter-spacing: 3px; color: #bc8cff; text-transform: uppercase; margin-bottom: 0.3rem;">
        💬 LunaTick Talk
    </div>
    <div style="font-family: 'Crimson Pro', serif; font-size: 1rem; color: #8b949e; margin-bottom: 1.2rem; font-style: italic;">
        Share your reflections. Read what others are feeling. You are not alone under the moon.
    </div>
    """, unsafe_allow_html=True)

    # --- LunaTick Pulse Banner ---
    phase = st.session_state.get("current_phase", "Waxing Gibbous")
    pulse = db.get_lunatick_pulse(phase)
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #1b1040, #2d1b69); border-radius: 16px; padding: 1rem 1.5rem; margin-bottom: 1.5rem; border-left: 4px solid #bc8cff;">
        <div style="font-family: 'Orbitron', sans-serif; font-size: 0.7rem; color: #bc8cff; letter-spacing: 2px; margin-bottom: 0.2rem;">🌕 LUNATICK PULSE</div>
        <div style="font-size: 1.1rem; color: #fff; line-height: 1.5;">{pulse}</div>
    </div>
    """, unsafe_allow_html=True)

    # --- Create a New Post ---
    with st.expander("🌙 Share something with the community"):
        display_name = st.text_input("Your display name", value=st.session_state.get("display_name", "Moon Wanderer"))
        content = st.text_area("Your post", max_chars=1000, placeholder="What's on your mind under tonight's moon?")
        is_anonymous = st.checkbox("Post anonymously", value=True)

        if st.button("Share"):
            if content.strip():
                user_moon_sign = st.session_state.get("user_moon_sign", "Unknown")
                current_moon_phase = st.session_state.get("current_phase", "Waxing Gibbous")
                db.create_post(display_name, content, user_moon_sign, current_moon_phase, is_anonymous)
                st.success("🌙 Your post has been shared with the community.")
                st.rerun()
            else:
                st.warning("Please write something before sharing.")

    # --- Filters ---
    col_filters = st.columns([2, 1])
    with col_filters[0]:
        phase_filter = st.selectbox(
            "Filter by Phase",
            ["All Phases", "New Moon", "Waxing Crescent", "First Quarter", "Waxing Gibbous", "Full Moon", "Waning Gibbous", "Last Quarter", "Waning Crescent"],
            index=0
        )
    with col_filters[1]:
        if st.button("🔄 Refresh Feed"):
            st.rerun()

    # --- Feed ---
    posts = db.get_posts(limit=20, phase_filter=None if phase_filter == "All Phases" else phase_filter)

    if not posts:
        st.info("No posts yet. Be the first to share!")
        return

    for post in posts:
        post_id, user_hash, display_name, user_moon_sign, current_moon_phase, content, upvotes, downvotes, created_at, is_anon, is_hidden = post

        # Display each post
        st.markdown(f"""
        <div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.07); border-radius: 12px; padding: 1rem 1.2rem; margin-bottom: 1rem;">
            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                <div>
                    <span style="font-weight: 700; color: #f0f6fc; font-size: 1rem;">{display_name}</span>
                    <span style="margin-left: 0.5rem; font-size: 0.6rem; background: rgba(110,64,201,0.2); padding: 0.1rem 0.5rem; border-radius: 12px; color: #bc8cff;">{current_moon_phase}</span>
                    <span style="margin-left: 0.3rem; font-size: 0.6rem; background: rgba(88,166,255,0.1); padding: 0.1rem 0.5rem; border-radius: 12px; color: #58a6ff;">{user_moon_sign}</span>
                </div>
                <div style="font-size: 0.55rem; color: #8b949e; font-family: 'Orbitron', sans-serif;">{created_at[:16]}</div>
            </div>
            <div style="color: #c9d1d9; line-height: 1.6; font-size: 0.95rem; margin: 0.5rem 0;">{content}</div>
            <div style="display: flex; gap: 1rem; align-items: center; margin-top: 0.3rem;">
                <span style="font-size: 0.7rem; color: #8b949e;">❤️ {upvotes} · 💔 {downvotes}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # -- Comments --
        with st.expander(f"💬 Comments ({len(db.get_comments(post_id))})"):
            for comment in db.get_comments(post_id):
                cid, c_post_id, c_user_hash, c_display_name, c_content, c_created_at, c_upvotes, c_downvotes, c_anon, c_hidden = comment
                st.markdown(f"""
                <div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.07); border-radius: 8px; padding: 0.5rem 0.8rem; margin-bottom: 0.4rem;">
                    <div style="display: flex; justify-content: space-between;">
                        <span style="font-size: 0.7rem; color: #8b949e;">{c_display_name}</span>
                        <span style="font-size: 0.55rem; color: #484f58;">{c_created_at[:16]}</span>
                    </div>
                    <div style="font-size: 0.9rem; color: #c9d1d9;">{c_content}</div>
                </div>
                """, unsafe_allow_html=True)

            # --- Add a Comment ---
            with st.form(key=f"comment_form_{post_id}"):
                comment_content = st.text_area("Add a comment", max_chars=500, placeholder="Share your thoughts...", key=f"comment_{post_id}")
                comment_anon = st.checkbox("Comment anonymously", value=True, key=f"comment_anon_{post_id}")
                if st.form_submit_button("Reply"):
                    if comment_content.strip():
                        db.create_comment(post_id, "Anonymous" if comment_anon else st.session_state.get("display_name", "Moon Wanderer"), comment_content, comment_anon)
                        st.success("Comment added.")
                        st.rerun()
                    else:
                        st.warning("Please write something.")