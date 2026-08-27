"""The compact LunaTicK Talk surface for the Connect destination."""

from __future__ import annotations

import streamlit as st

import boards
import chat_room


# Required by app.py to replace Community pages retained by warm Streamlit workers.
COMMUNITY_MODULE_VERSION = "talk_split_surface_v1"


TALK_CSS = """
<style>
    .talk-page-header {
        margin: 0 0 0.65rem;
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
        margin: 0.05rem 0 0.42rem;
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
    .talk-divider {
        border-top: 1px solid rgba(188, 140, 255, 0.25);
        margin: 0.62rem 0;
    }
    @media (max-width: 480px) {
        .talk-page-header { margin-bottom: 0.52rem; }
        .talk-section-heading { margin-bottom: 0.3rem; }
    }
</style>
"""


def _section_heading(title: str, caption: str) -> None:
    st.markdown(
        f'<div class="talk-section-heading"><h2>{title}</h2><span>{caption}</span></div>',
        unsafe_allow_html=True,
    )


def render_community() -> None:
    """Render only the lightweight Talk chat and lasting discussion board."""
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

    _section_heading("Live chat", "Updates automatically")
    chat_room.render_chat_tab()

    st.markdown('<div class="talk-divider"></div>', unsafe_allow_html=True)
    _section_heading("Message board", "Lasting conversations")
    boards.render_boards_tab()


__all__ = ["render_community"]
