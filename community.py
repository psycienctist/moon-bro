"""Unified Community surface for LunaTicK."""

from __future__ import annotations

import html

import streamlit as st

import auth
import boards
import chat_room
import lunatick_talk_ui
import moderation


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

    .public-profile-card {
        background: linear-gradient(145deg, rgba(20, 29, 52, 0.92), rgba(63, 35, 107, 0.55));
        border: 1px solid rgba(188, 140, 255, 0.42);
        border-radius: 16px;
        box-shadow: 0 0 22px rgba(110, 64, 201, 0.12);
        margin: 0.85rem 0 0.35rem;
        padding: 1rem;
    }

    .public-profile-head {
        align-items: center;
        display: flex;
        gap: 0.8rem;
    }

    .public-profile-avatar {
        align-items: center;
        background: rgba(188, 140, 255, 0.13);
        border: 1px solid rgba(188, 140, 255, 0.34);
        border-radius: 50%;
        display: flex;
        font-size: 2rem;
        height: 3.35rem;
        justify-content: center;
        width: 3.35rem;
    }

    .public-profile-name {
        color: #f0f6fc;
        font-size: 1.02rem;
        font-weight: 700;
        line-height: 1.2;
    }

    .public-profile-handle {
        color: #bc8cff;
        font-size: 0.82rem;
        margin-top: 0.12rem;
    }

    .public-profile-bio {
        color: #c9d1d9;
        font-size: 0.9rem;
        line-height: 1.5;
        margin: 0.85rem 0 0;
        white-space: normal;
    }

    .public-profile-note {
        color: #7d8794;
        font-size: 0.7rem;
        letter-spacing: 0.02em;
        margin-top: 0.85rem;
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
        .public-profile-card { padding: 0.85rem; }
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


def _set_profile_lookup(username: str) -> None:
    """Store a requested public handle in the current Community session."""
    st.session_state["public_profile_lookup"] = username.strip().lstrip("@")


def _clear_profile_lookup() -> None:
    st.session_state.pop("public_profile_lookup", None)


def _render_public_profile_lookup() -> None:
    """Render a direct username lookup with a deliberately minimal public card."""
    with st.expander("🔭 View a LunaTicK profile", expanded=False):
        st.caption("Look up a public profile by @username. Email, birth data, and account details remain private.")
        with st.form("public_profile_lookup_form", clear_on_submit=False):
            lookup_username = st.text_input(
                "Username",
                value=st.session_state.get("public_profile_lookup", ""),
                max_chars=24,
                placeholder="e.g. moon_orbit",
                label_visibility="collapsed",
            )
            search_profile = st.form_submit_button("View profile", use_container_width=True)

        if search_profile:
            requested_handle = lookup_username.strip().lstrip("@")
            if requested_handle:
                _set_profile_lookup(requested_handle)
            else:
                st.warning("Enter a username to view a public profile.")

        requested_handle = st.session_state.get("public_profile_lookup", "")
        if not requested_handle:
            return

        profile = auth.get_public_profile(requested_handle)
        if profile is None:
            st.info(f"No public LunaTicK profile was found for @{html.escape(requested_handle)}.")
            if st.button("Clear search", key="clear_missing_public_profile"):
                _clear_profile_lookup()
                st.rerun()
            return

        avatar = html.escape(profile["avatar"])
        display_name = html.escape(profile["display_name"])
        username = html.escape(profile["username"])
        bio = html.escape(profile["bio"]).replace("\n", "<br>")
        bio_html = (
            f'<p class="public-profile-bio">{bio}</p>'
            if bio
            else '<p class="public-profile-bio" style="color:#7d8794;font-style:italic;">No bio shared yet.</p>'
        )
        st.markdown(
            f"""
            <div class="public-profile-card">
              <div class="public-profile-head">
                <div class="public-profile-avatar">{avatar}</div>
                <div>
                  <div class="public-profile-name">{display_name}</div>
                  <div class="public-profile-handle">@{username}</div>
                </div>
              </div>
              {bio_html}
              <div class="public-profile-note">PUBLIC LUNATICK PROFILE</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Close profile", key="close_public_profile"):
            _clear_profile_lookup()
            st.rerun()


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
    auth.init_auth_db()

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
        _render_public_profile_lookup()
        moderation.render_moderation_console()
        _render_community_nav(active_view)

    if active_view == "Chat":
        chat_room.render_chat_tab()
    elif active_view == "Lunatick Talk":
        lunatick_talk_ui.render_talk_tab()
    else:
        boards.render_boards_tab()


__all__ = ["render_community"]
