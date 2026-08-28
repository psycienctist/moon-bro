"""The compact LunaTicK Talk surface for the Connect destination."""

from __future__ import annotations

import streamlit as st

import boards
import chat_room


# Required by app.py to replace Community pages retained by warm Streamlit workers.
COMMUNITY_MODULE_VERSION = "talk_surface_toggle_v2"


TALK_CSS = """
<style>
    .talk-page-header {
        margin: 0 0 0.48rem;
        text-align: center;
    }
    .talk-page-kicker {
        color: #bc8cff;
        font-family: 'Orbitron', sans-serif;
        font-size: 0.56rem;
        font-weight: 700;
        letter-spacing: 0.19em;
        text-transform: uppercase;
    }
    .talk-page-title {
        color: #f0f6fc;
        font-family: 'Orbitron', sans-serif;
        font-size: clamp(1.22rem, 5vw, 1.65rem);
        letter-spacing: 0.08em;
        margin: 0.12rem 0 0;
        text-transform: uppercase;
    }
    .talk-section-heading {
        align-items: baseline;
        display: flex;
        justify-content: space-between;
        margin: 0.08rem 0 0.34rem;
    }
    .talk-section-heading h2 {
        color: #f0f6fc;
        font-family: 'Orbitron', sans-serif;
        font-size: 0.82rem;
        letter-spacing: 0.07em;
        margin: 0;
        text-transform: uppercase;
    }
    .talk-section-heading span {
        color: #8b949e;
        font-size: 0.68rem;
    }
    .talk-surface-toggle {
        margin: 0.12rem 0 0.48rem;
    }
    @media (max-width: 480px) {
        .talk-page-header { margin-bottom: 0.38rem; }
        .talk-surface-toggle { margin-bottom: 0.36rem; }
        .talk-section-heading { margin-bottom: 0.26rem; }
        /* The app reserves space for its fixed rail. The selected board uses
           that clearance and gives internal feed content room above the rail. */
        [data-testid="stMain"]:has(.st-key-talk-board-feed) [data-testid="stMainBlockContainer"] {
            padding-bottom: calc(4.425rem + env(safe-area-inset-bottom)) !important;
        }
        .st-key-talk-board-feed {
            margin-bottom: -4rem;
            padding-bottom: calc(4rem + 0.9375rem) !important;
        }
    }
</style>
"""


def _section_heading(title: str, caption: str) -> None:
    st.markdown(
        f'<div class="talk-section-heading"><h2>{title}</h2><span>{caption}</span></div>',
        unsafe_allow_html=True,
    )


def render_community() -> None:
    """Render one compact Talk surface at a time for phone-sized screens."""
    boards.init_boards_db()
    chat_room.init_chat_db()

    st.html(TALK_CSS)
    st.markdown(
        """
        <div class="talk-page-header">
          <div class="talk-page-kicker">LunaTicK Community</div>
          <h1 class="talk-page-title">LunaTicK Talk</h1>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.container(key="talk-surface-toggle"):
        active_surface = st.radio(
            "Choose LunaTicK Talk surface",
            ("Live Chat", "Message Board"),
            key="talk_active_surface",
            index=1,
            horizontal=True,
            label_visibility="collapsed",
        )

    if active_surface == "Live Chat":
        _section_heading("Live chat", "Updates automatically")
        chat_room.render_chat_tab()
    else:
        boards.render_boards_tab(compact=True)


__all__ = ["render_community"]
