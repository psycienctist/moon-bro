"""Private, deterministic Daily Reflection companion for LunaTicK.

The renderer intentionally makes no external model calls. It never sends or reads
journal entry content to construct a prompt, and it stores no reflection text of
its own. Journal-practice progress is calculated from owner-only date metadata.
"""

from __future__ import annotations

import hashlib
import html
import sqlite3
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import streamlit as st

import cosmic_cards
import supabase_store


PRACTICE_BADGES = (
    {
        "title": "Mooned",
        "threshold": 1,
        "symbol": "🌙",
        "description": "You sealed your first private reflection.",
    },
    {
        "title": "Moon Lit",
        "threshold": 3,
        "symbol": "✨",
        "description": "You kept a three-day reflection rhythm.",
    },
    {
        "title": "Moonwalker",
        "threshold": 7,
        "symbol": "🌗",
        "description": "You carried your practice through a full week.",
    },
    {
        "title": "Over the Moon",
        "threshold": 14,
        "symbol": "🌕",
        "description": "You sustained two weeks of private reflection.",
    },
)


PROMPT_FAMILIES = (
    (
        "Notice",
        (
            "With the Moon in {moon_sign}, what are you noticing before you decide what it means?",
            "What is asking for your honest attention today, even if it does not need an immediate answer?",
            "Name one feeling, pattern, or moment you can observe with curiosity rather than judgment.",
        ),
    ),
    (
        "Integrate",
        (
            "Your {sun_sign} Sun can offer a steady center. What part of yourself would you like to meet with more respect today?",
            "Your {moon_sign} Moon points toward your inner weather. What would help you make room for it without letting it steer everything?",
            "What is one truth you can hold alongside one uncertainty, without forcing either one to disappear?",
        ),
    ),
    (
        "Release",
        (
            "What can you set down for tonight without needing to settle its final outcome?",
            "Where might a smaller expectation make more room for breath, rest, or clarity?",
            "What are you ready to stop rehearsing in your mind for the rest of this day?",
        ),
    ),
    (
        "Relate",
        (
            "Where could you be more direct while remaining kind—to someone else or to yourself?",
            "What boundary, request, or appreciation would make one relationship feel more honest today?",
            "How can you honor your own perspective without assuming it is the only perspective in the room?",
        ),
    ),
    (
        "Act",
        (
            "Name one action small enough to complete today that would honor what you have noticed.",
            "What is the next grounded step—not the entire solution—you can take before the day ends?",
            "If you gave this insight fifteen quiet minutes of support, what would you do first?",
        ),
    ),
)

_SQLITE_DB = Path("lunatick.db")


def _using_supabase() -> bool:
    return supabase_store.data_backend_from_streamlit_secrets() == "supabase"


def _store() -> supabase_store.SupabaseStore:
    return supabase_store.SupabaseStore(supabase_store.SupabaseSettings.from_streamlit_secrets())


def _auth_subject() -> str:
    return str(st.session_state.get("auth_subject", "")).strip()


def _private_practice_days() -> set[date]:
    """Return only this owner's practice dates; never retrieve journal content."""
    subject = _auth_subject()
    if _using_supabase() and subject:
        rows = _store().list_journal_practice_days(subject)
        raw_dates = (row.get("practice_date") for row in rows)
    else:
        user_hash = str(st.session_state.get("user_hash", "anonymous"))
        if not _SQLITE_DB.exists():
            return set()
        conn = sqlite3.connect(_SQLITE_DB)
        try:
            rows = conn.execute(
                "SELECT DISTINCT date(created_at) FROM journal_entries WHERE user_hash=?",
                (user_hash,),
            ).fetchall()
        except sqlite3.Error:
            rows = []
        finally:
            conn.close()
        raw_dates = (row[0] for row in rows)

    days: set[date] = set()
    for raw_value in raw_dates:
        try:
            days.add(date.fromisoformat(str(raw_value)[:10]))
        except (TypeError, ValueError):
            continue
    return days


def record_practice_day(practice_day: date | None = None) -> None:
    """Persist one owner-only UTC practice date after a private journal save."""
    if not _using_supabase():
        # The SQLite fallback derives practice dates directly from journal entry
        # timestamps, preserving the same no-content tracking behavior.
        return
    subject = _auth_subject()
    if not subject:
        raise ValueError("A signed-in LunaTicK identity is required to record journal practice.")
    _store().record_journal_practice_day(
        subject, (practice_day or datetime.now(timezone.utc).date()).isoformat()
    )


def practice_summary(today: date | None = None) -> dict[str, Any]:
    """Calculate owner-only current and longest practice rhythms from dates alone."""
    current_day = today or datetime.now(timezone.utc).date()
    days = _private_practice_days()
    current_streak = 0
    cursor = current_day
    while cursor in days:
        current_streak += 1
        cursor -= timedelta(days=1)

    longest_streak = 0
    running_streak = 0
    previous: date | None = None
    for practice_day in sorted(days):
        if previous and practice_day == previous + timedelta(days=1):
            running_streak += 1
        else:
            running_streak = 1
        longest_streak = max(longest_streak, running_streak)
        previous = practice_day

    earned = [badge for badge in PRACTICE_BADGES if longest_streak >= badge["threshold"]]
    next_badge = next((badge for badge in PRACTICE_BADGES if longest_streak < badge["threshold"]), None)
    return {
        "practice_days": len(days),
        "practiced_today": current_day in days,
        "current_streak": current_streak,
        "longest_streak": longest_streak,
        "earned_badges": earned,
        "next_badge": next_badge,
    }


def _derived_reflection_context(today: date) -> dict[str, str]:
    """Build display-safe context from current sky and optional derived card labels."""
    sky = cosmic_cards._chart(datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc))
    context = {
        "phase": str(sky.get("phase_name") or st.session_state.get("current_phase") or "Moon phase"),
        "moon_sign": str(sky.get("moon_sign") or "the current sky"),
        "moon_symbol": str(sky.get("moon_symbol") or "🌙"),
        "sun_sign": "inner compass",
        "rising_sign": "",
    }
    user_reference = str(st.session_state.get("user_hash") or _auth_subject()).strip()
    if not user_reference:
        return context
    try:
        card = cosmic_cards.build_card(user_reference)
        natal = dict(card.get("natal") or {}) if card else {}
        context["sun_sign"] = str(natal.get("sun_sign") or context["sun_sign"])
        context["rising_sign"] = str(natal.get("rising_sign") or "")
    except Exception:
        # Daily Reflection must remain available even if a card has not been saved
        # or a card-specific astronomy calculation cannot run.
        pass
    return context


def _prompt_for_today(context: dict[str, str], rotation: int = 0) -> tuple[str, str]:
    """Choose a stable daily prompt with an optional user-requested local rotation."""
    subject = _auth_subject() or str(st.session_state.get("user_hash", "anonymous"))
    seed = hashlib.sha256(f"{subject}:{datetime.now(timezone.utc).date().isoformat()}".encode("utf-8")).digest()
    family_index = (int.from_bytes(seed[:2], "big") + rotation) % len(PROMPT_FAMILIES)
    family, templates = PROMPT_FAMILIES[family_index]
    prompt_index = (int.from_bytes(seed[2:4], "big") + rotation) % len(templates)
    return family, templates[prompt_index].format(**context)


def _badge_markup(summary: dict[str, Any]) -> str:
    earned = summary["earned_badges"]
    if not earned:
        next_badge = summary["next_badge"]
        if next_badge:
            remaining = max(0, next_badge["threshold"] - summary["longest_streak"])
            return (
                "<div style='color:#8b949e;font-size:.72rem;margin-top:.55rem;'>"
                f"Private practice · {remaining} more day{'s' if remaining != 1 else ''} toward "
                f"{html.escape(str(next_badge['title']))} {html.escape(str(next_badge['symbol']))}</div>"
            )
        return ""
    chips = "".join(
        "<span style='display:inline-block;margin:.22rem .32rem 0 0;padding:.24rem .48rem;"
        "border:1px solid rgba(188,140,255,.42);border-radius:999px;color:#e4d0ff;font-size:.67rem;'>"
        f"{html.escape(str(badge['symbol']))} {html.escape(str(badge['title']))}</span>"
        for badge in earned
    )
    return (
        "<div style='color:#aab6c9;font-size:.67rem;margin-top:.55rem;'>"
        "Private milestones earned</div>"
        f"<div>{chips}</div>"
    )


def render_daily_reflection() -> None:
    """Render a finished no-API reflection prompt and private practice status."""
    today = datetime.now(timezone.utc).date()
    rotation_key = f"daily_reflection_rotation_{today.isoformat()}"
    st.session_state.setdefault(rotation_key, 0)
    context = _derived_reflection_context(today)
    summary = practice_summary(today)
    family, prompt = _prompt_for_today(context, int(st.session_state[rotation_key]))

    st.markdown(
        "<div style='font-family:Orbitron,sans-serif;font-size:.76rem;letter-spacing:2px;"
        "color:#bc8cff;text-transform:uppercase;margin:.1rem 0 .35rem;'>"
        "🌙 Today’s Reflection</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<div style='border:1px solid rgba(188,140,255,.35);border-radius:12px;"
        "padding:.82rem .9rem;background:linear-gradient(135deg,rgba(45,27,105,.23),rgba(13,31,60,.32));'>"
        f"<div style='color:#9bbcff;font-size:.66rem;letter-spacing:1.2px;text-transform:uppercase;'>"
        f"{html.escape(context['moon_symbol'])} {html.escape(context['phase'])} · {html.escape(context['moon_sign'])}</div>"
        f"<div style='color:#eef3ff;font-size:1rem;line-height:1.48;margin-top:.45rem;'>"
        f"{html.escape(prompt)}</div>"
        f"<div style='color:#8b949e;font-size:.62rem;margin-top:.52rem;'>Today’s lens · {html.escape(family)}</div>"
        f"{_badge_markup(summary)}"
        "</div>",
        unsafe_allow_html=True,
    )

    status = (
        "You have sealed a reflection today."
        if summary["practiced_today"]
        else "A sealed entry today begins or continues your private rhythm."
    )
    st.caption(
        f"{status} {summary['current_streak']}-day current rhythm · "
        f"{summary['practice_days']} private practice day{'s' if summary['practice_days'] != 1 else ''}."
    )
    left, right = st.columns(2)
    with left:
        if st.button("Try another lens", key=f"daily_reflection_rotate_{today.isoformat()}", use_container_width=True):
            st.session_state[rotation_key] = int(st.session_state[rotation_key]) + 1
            st.rerun()
    with right:
        if st.button("Write today’s reflection", key=f"daily_reflection_write_{today.isoformat()}", type="primary", use_container_width=True):
            st.session_state["journal_prompt_mode"] = "🌙 Phase Reflection"
            st.session_state["daily_reflection_write_intent"] = True
            st.rerun()


__all__ = [
    "PRACTICE_BADGES",
    "record_practice_day",
    "practice_summary",
    "render_daily_reflection",
]
