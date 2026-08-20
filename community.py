"""Unified Community surface for Lunatick.

This module is intentionally isolated from app.py. It can be reviewed and
validated independently before Community is wired into the top-level route.
"""

import streamlit as st

import boards
import chat_room
import lunatick_talk_ui


COMMUNITY_VIEWS = (
    ("Chat", "💬", "Chat"),
    ("Boards", "📋", "Boards"),
    ("Lunatick Talk", "🗣️", "Talk"),
)
DEFAULT_VIEW = "Boards"


COMMUNITY_CSS = """
<style>
    .community-shell {
        background: linear-gradient(145deg, rgba(13, 31, 60, 0.68), rgba(45, 27, 105, 0.42));
        border: 1px solid rgba(188, 140, 255, 0.30);
        border-radius: 18px;
        box-shadow: 0 0 28px rgba(110, 64, 201, 0.12), inset 0 0 24px rgba(0, 0, 0, 0.16);
        margin-bottom: 1rem;
        padding: 1rem 1rem 0.35rem;
    }

    .community-kicker {
        color: #bc8cff;
        font-family: 'Orbitron', sans-serif;
        font-size: 0.62rem;
        font-weight: 700;
        letter-spacing: 0.20em;
        margin-bottom: 0.3rem;
        text-transform: uppercase;
    }

    .community-title {
        color: #f0f6fc;
        font-family: 'Orbitron', sans-serif;
        font-size: clamp(1.25rem, 4vw, 1.7rem);
        letter-spacing: 0.06em;
        margin: 0;
        text-transform: uppercase;
    }

    .community-subtitle {
        color: #8b949e;
        font-size: 0.88rem;
        line-height: 1.45;
        margin: 0.45rem 0 1rem;
    }

    .st-key-community-subnav [data-testid="stButton"] > button {
        background: rgba(255, 255, 255, 0.045);
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 0.8rem;
        color: #aab6ca;
        font-size: 0.78rem;
        min-height: 2.7rem;
        transition: background 160ms ease, border-color 160ms ease, color 160ms ease, transform 160ms ease;
    }

    .st-key-community-subnav [data-testid="stButton"] > button:hover,
    .st-key-community-subnav [data-testid="stButton"] > button:focus-visible {
        border-color: rgba(188, 140, 255, 0.72);
        color: #f0e6ff;
        outline: none;
        transform: translateY(-1px);
    }

    .st-key-community-subnav [data-testid="stButton"] > button[kind="primary"] {
        background: linear-gradient(135deg, #7841c7, #aa70f0);
        border-color: #bc8cff;
        color: #ffffff;
        box-shadow: 0 0 16px rgba(188, 140, 255, 0.20);
    }

    @media (max-width: 480px) {
        .community-shell { padding: 0.85rem 0.7rem 0.25rem; }
        .st-key-community-subnav [data-testid="stButton"] > button {
            font-size: 0.67rem;
            padding-left: 0.2rem;
            padding-right: 0.2rem;
        }
    }
</style>
"""


def _set_community_view(view_name: str) -> None:
    """Persist the selected in-page Community view across Streamlit reruns."""
    st.session_state["community_view"] = view_name


def _render_community_nav(active_view: str) -> None:
    """Render the non-sticky, page-local Community subnavigation."""
    with st.container(key="community-subnav"):
        columns = st.columns(len(COMMUNITY_VIEWS), gap="small")
        for column, (view_name, icon, short_label) in zip(columns, COMMUNITY_VIEWS):
            with column:
                button_type = "primary" if view_name == active_view else "secondary"
                st.button(
                    f"{icon} {short_label}",
                    key=f"community_view_{short_label.lower().replace(' ', '_')}",
                    type=button_type,
                    use_container_width=True,
                    on_click=_set_community_view,
                    args=(view_name,),
                )


def render_community() -> None:
    """Render the unified Community page without changing top-level routing."""
    boards.init_boards_db()
    chat_room.init_chat_db()

    active_view = st.session_state.get("community_view", DEFAULT_VIEW)
    valid_views = {view_name for view_name, _, _ in COMMUNITY_VIEWS}
    if active_view not in valid_views:
        active_view = DEFAULT_VIEW
        st.session_state["community_view"] = active_view

    st.markdown(COMMUNITY_CSS, unsafe_allow_html=True)
    with st.container(key="community-page"):
        st.markdown(
            '<div class="community-shell">'
            '<div class="community-kicker">Lunatick social orbit</div>'
            '<h1 class="community-title">Community</h1>'
            '<p class="community-subtitle">Share openly. Listen deeply. Find your people.</p>'
            '</div>',
            unsafe_allow_html=True,
        )
        _render_community_nav(active_view)

    if active_view == "Chat":
        chat_room.render_chat_tab()
    elif active_view == "Lunatick Talk":
        lunatick_talk_ui.render_talk_tab()
    else:
        boards.render_boards_tab()


__all__ = ["render_community"]