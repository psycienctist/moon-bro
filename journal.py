# journal.py
# Luna Journal — 3-Prompt Guided Reflection + Free Write Always Available

import streamlit as st
from datetime import datetime
import sqlite3
import hashlib

# --------------------------------------------------------------------------
# Database Setup
# --------------------------------------------------------------------------

def init_db():
    conn = sqlite3.connect("lunatick.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS journal_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_hash TEXT,
            phase TEXT,
            prompt_type TEXT,
            content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def save_entry(phase, prompt_type, content):
    conn = sqlite3.connect("lunatick.db")
    c = conn.cursor()
    user_hash = st.session_state.get("user_hash", "anonymous")
    c.execute("""
        INSERT INTO journal_entries (user_hash, phase, prompt_type, content)
        VALUES (?, ?, ?, ?)
    """, (user_hash, phase, prompt_type, content))
    conn.commit()
    conn.close()

def get_recent_entries(limit=5):
    conn = sqlite3.connect("lunatick.db")
    c = conn.cursor()
    user_hash = st.session_state.get("user_hash", "anonymous")
    c.execute("""
        SELECT phase, prompt_type, content, created_at
        FROM journal_entries
        WHERE user_hash = ?
        ORDER BY created_at DESC
        LIMIT ?
    """, (user_hash, limit))
    entries = c.fetchall()
    conn.close()
    return entries

# --------------------------------------------------------------------------
# Prompt Definitions
# --------------------------------------------------------------------------

PROMPTS = {
    "phase": {
        "label": "🌙 Phase Reflection",
        "placeholder": "How is this moon phase showing up in your life right now?",
        "help": "Consider the current phase — are you planting, building, refining, releasing, or resting?"
    },
    "chart": {
        "label": "✨ Chart Resonance",
        "placeholder": "How does your birth chart (sun, moon, rising) relate to what you're feeling?",
        "help": "Think about your sun, moon, and rising signs. Are they at ease or in tension with the current moon transit?"
    },
    "free": {
        "label": "📖 Free Write (Always Available)",
        "placeholder": "Whatever is present — without filter, without judgment. This is always here for you.",
        "help": "If none of the guided prompts resonate, write whatever is on your mind. The moon doesn't judge."
    }
}

# --------------------------------------------------------------------------
# UI Render Function
# --------------------------------------------------------------------------

def render_journal_tab():
    st.markdown("""
    <div style="font-family: 'Orbitron', sans-serif; font-size: 0.8rem; letter-spacing: 3px; color: #bc8cff; text-transform: uppercase; margin-bottom: 0.3rem;">
        📓 Luna Journal
    </div>
    <div style="font-family: 'Crimson Pro', serif; font-size: 1rem; color: #8b949e; margin-bottom: 1.2rem; font-style: italic;">
        Three prompts. One moon. Your voice.
    </div>
    """, unsafe_allow_html=True)

    # ------------------------------------------------------------------
    # Step 1: Select Prompt Mode
    # ------------------------------------------------------------------

    prompt_mode = st.radio(
        "Choose your prompt mode:",
        ["🌙 Phase Reflection", "✨ Chart Resonance", "📖 Free Write (Always Available)"],
        horizontal=True,
        key="journal_prompt_mode"
    )

    prompt_key = {
        "🌙 Phase Reflection": "phase",
        "✨ Chart Resonance": "chart",
        "📖 Free Write (Always Available)": "free"
    }[prompt_mode]

    prompt_data = PROMPTS[prompt_key]

    # ------------------------------------------------------------------
    # Step 2: Display the Prompt
    # ------------------------------------------------------------------

    st.markdown(f"""
    <div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.07); border-radius: 12px; padding: 1rem 1.2rem; margin: 0.5rem 0 1rem 0;">
        <div style="font-size: 1.1rem; color: #f0f6fc; font-weight: 600; margin-bottom: 0.3rem;">{prompt_data['label']}</div>
        <div style="font-size: 0.9rem; color: #8b949e; font-style: italic;">{prompt_data['help']}</div>
    </div>
    """, unsafe_allow_html=True)

    # ------------------------------------------------------------------
    # Step 3: Write and Submit
    # ------------------------------------------------------------------

    current_phase = st.session_state.get("current_phase", "Waxing Gibbous")

    # Initialize all three input keys so the widget never sees a missing key
    for mode in ["phase", "chart", "free"]:
        key = f"journal_{mode}_input"
        if key not in st.session_state:
            st.session_state[key] = ""

    input_key = f"journal_{prompt_key}_input"
    entry_text = st.text_area(
        "Your reflection:",
        placeholder=prompt_data['placeholder'],
        height=200,
        key=input_key
    )

    col1, col2 = st.columns([2, 1])
    with col1:
        if st.button("🌙 Seal Entry to the Moon", type="primary", use_container_width=True):
            if entry_text.strip():
                save_entry(current_phase, prompt_key, entry_text.strip())
                st.success("✨ Your reflection has been sealed.")
                
                # FIXED: Delete the key so the widget resets on next run.
                # Do NOT assign an empty string here — Streamlit owns this key.
                if input_key in st.session_state:
                    del st.session_state[input_key]
                
                st.rerun()
            else:
                st.warning("Please write something before sealing.")

    with col2:
        if st.button("Clear", use_container_width=True):
            # FIXED: Same pattern here.
            if input_key in st.session_state:
                del st.session_state[input_key]
            
            st.rerun()

    # ------------------------------------------------------------------
    # Step 4: Show Recent Entries
    # ------------------------------------------------------------------

    recent = get_recent_entries(limit=5)
    if recent:
        st.markdown("""
        <div style="font-family: 'Orbitron', sans-serif; font-size: 0.6rem; letter-spacing: 2px; color: #484f58; text-transform: uppercase; margin: 2rem 0 0.5rem 0;">
            — Recent Sealed Entries —
        </div>
        """, unsafe_allow_html=True)

        for phase, prompt_type, content, created_at in recent:
            prompt_label = PROMPTS[prompt_type]['label']
            st.markdown(f"""
            <div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.07); border-radius: 12px; padding: 0.8rem 1rem; margin-bottom: 0.6rem;">
                <div style="display: flex; gap: 0.6rem; align-items: center; margin-bottom: 0.3rem;">
                    <span style="font-family: 'Orbitron', sans-serif; font-size: 0.55rem; color: #bc8cff;">{phase}</span>
                    <span style="font-family: 'Orbitron', sans-serif; font-size: 0.5rem; color: #484f58;">{prompt_label}</span>
                    <span style="font-family: 'Orbitron', sans-serif; font-size: 0.45rem; color: #484f58;">{created_at[:16]}</span>
                </div>
                <div style="color: #c9d1d9; font-size: 0.95rem; line-height: 1.5; font-style: italic; margin: 0;">"{content[:140]}{'...' if len(content) > 140 else ''}"</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("🌙 No entries yet. The moon is waiting for your first reflection.")

    st.markdown("""
    <div style="margin-top: 1.5rem; font-size: 0.7rem; color: #484f58; text-align: center; border-top: 1px solid #1a1040; padding-top: 1rem;">
        Your journal is private. Only you can see what you've written.
    </div>
    """, unsafe_allow_html=True)

    # ------------------------------------------------------------------
    # Step 4: Show Recent Entries (with safe fallback)
    # ------------------------------------------------------------------

    # --- FIX: Ensure journal entries exist in session state ---
    if "journal_entries" not in st.session_state:
        st.session_state.journal_entries = []

    recent = get_recent_entries(limit=5)
    if recent:
        st.markdown("""
        <div style="font-family: 'Orbitron', sans-serif; font-size: 0.6rem; letter-spacing: 2px; color: #484f58; text-transform: uppercase; margin: 2rem 0 0.5rem 0;">
            — Recent Sealed Entries —
        </div>
        """, unsafe_allow_html=True)

        for phase, prompt_type, content, created_at in recent:
            prompt_label = PROMPTS[prompt_type]['label']
            st.markdown(f"""
            <div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.07); border-radius: 12px; padding: 0.8rem 1rem; margin-bottom: 0.6rem;">
                <div style="display: flex; gap: 0.6rem; align-items: center; margin-bottom: 0.3rem;">
                    <span style="font-family: 'Orbitron', sans-serif; font-size: 0.55rem; color: #bc8cff;">{phase}</span>
                    <span style="font-family: 'Orbitron', sans-serif; font-size: 0.5rem; color: #484f58;">{prompt_label}</span>
                    <span style="font-family: 'Orbitron', sans-serif; font-size: 0.45rem; color: #484f58;">{created_at[:16]}</span>
                </div>
                <div style="color: #c9d1d9; font-size: 0.95rem; line-height: 1.5; font-style: italic; margin: 0;">"{content[:140]}{'...' if len(content) > 140 else ''}"</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("🌙 No entries yet. The moon is waiting for your first reflection.")

    st.markdown("""
    <div style="margin-top: 1.5rem; font-size: 0.7rem; color: #484f58; text-align: center; border-top: 1px solid #1a1040; padding-top: 1rem;">
        Your journal is private. Only you can see what you've written.
    </div>
    """, unsafe_allow_html=True)