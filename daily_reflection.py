# daily_reflection.py
# Context Engine + Prompt Builder for LunaTick's Daily Reflection
# Built together by The Founder, The Mirror AI, and our AI Ally

import streamlit as st
from datetime import datetime
import lunatick_talk_db as talk_db
import journal as journal_ui

# --------------------------------------------------------------------------
# Gather Context (includes live Pulse)
# --------------------------------------------------------------------------

def gather_context():
    current_phase = st.session_state.get("current_phase", "Waxing Gibbous")
    user_hash = st.session_state.get("user_hash", "anonymous")

    # --- Get live Pulse from community ---
    pulse = talk_db.get_lunatick_pulse(current_phase)

    # --- Get recent journal entries ---
    recent_entries = journal_ui.get_recent_entries(limit=3)
    journal_summary = "\n".join([f"- {entry[2][:100]}..." for entry in recent_entries]) if recent_entries else "No recent journal entries yet."

    # --- Chart data (from session_state) ---
    sun_sign = st.session_state.get("sun_sign", "Unknown")
    moon_sign = st.session_state.get("moon_sign", "Unknown")

    return {
        "phase": current_phase,
        "sun_sign": sun_sign,
        "moon_sign": moon_sign,
        "journal_summary": journal_summary,
        "pulse": pulse
    }

# --------------------------------------------------------------------------
# Build Prompt (includes Pulse)
# --------------------------------------------------------------------------

def build_reflection_prompt(context):
    prompt = f"""
You are a grounded, reflective companion for someone exploring their inner world through the lunar cycle.

**Current Moon:** {context['phase']}
**Their Chart:** Sun in {context['sun_sign']}, Moon in {context['moon_sign']}
**Recent Journal Entries:**
{context['journal_summary']}

**Community Pulse (from LunaTick Talk):**
{context['pulse']}

Based on this, write a short, personal reflection for the user. Be grounding, humble, and reflective. Do not predict the future. Remind them they are not alone.

End with one open question to carry through the day.
"""
    return prompt

# --------------------------------------------------------------------------
# UI Render Function
# --------------------------------------------------------------------------

def render_daily_reflection():
    """
    A simple Streamlit UI block to display the daily reflection.
    """
    st.markdown("### 🌙 Your Daily Reflection")

    # Gather context and build prompt
    context = gather_context()
    prompt = build_reflection_prompt(context)

    # For now, display the prompt for testing
    # In the next step, we'll send this to the AI
    with st.expander("📝 Reflection Prompt (Preview)"):
        st.text(prompt)

    # Placeholder for the AI's response
    st.info("✨ Your reflection will appear here once the AI is connected.")

    # Optional: Show the raw context for debugging
    with st.expander("🔍 Raw Context"):
        st.json(context)