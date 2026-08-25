"""Unified Community surface for LunaTicK.

This module intentionally combines the live chat and message boards into one
Community page. The former LunaTicK Talk surface is no longer rendered here.
"""

from __future__ import annotations

import html

import streamlit as st

import auth
import boards
import chat_room
import moderation
import cosmic_cards


# Keep this value compatible with app.py's warm-worker reload guard.
COMMUNITY_MODULE_VERSION = "public_profile_card_v1"


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

    .community-section {
        background: linear-gradient(145deg, rgba(20, 29, 52, 0.54), rgba(63, 35, 107, 0.20));
        border: 1px solid rgba(188, 140, 255, 0.20);
        border-radius: 16px;
        box-shadow: 0 0 22px rgba(110, 64, 201, 0.08);
        margin: 0 0 1rem;
        padding: 0.95rem 1rem 0.45rem;
    }

    .community-section-title {
        color: #f0f6fc;
        font-family: 'Orbitron', sans-serif;
        font-size: 1.05rem;
        letter-spacing: 0.04em;
        margin: 0;
        text-transform: uppercase;
    }

    .community-section-caption {
        color: #8b949e;
        font-size: 0.82rem;
        margin: 0.25rem 0 0.8rem;
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

    @media (max-width: 480px) {
        .community-shell { padding: 0.85rem 0.7rem 0.25rem; }
        .community-section { padding: 0.85rem 0.7rem 0.25rem; }
        .public-profile-card { padding: 0.85rem; }
    }
</style>
"""


def _set_profile_lookup(username: str) -> None:
    """Store a requested public handle in the current Community session."""
    st.session_state["public_profile_lookup"] = username.strip().lstrip("@")


def _clear_profile_lookup() -> None:
    st.session_state.pop("public_profile_lookup", None)


def _render_public_profile_lookup() -> None:
    """Render a direct username lookup with a minimal public card."""
    with st.expander("🔭 View a LunaTicK profile", expanded=False):
        st.caption(
            "Look up a public profile by @username. Email, birth data, and account details remain private."
        )
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
                st.warning("Enter a username to view a profile.")

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

        avatar = html.escape(str(profile.get("avatar") or "🌙"))
        display_name = html.escape(str(profile.get("display_name") or "Moon Wanderer"))
        username = html.escape(str(profile.get("username") or requested_handle))
        bio = html.escape(str(profile.get("bio") or "")).replace("\n", "<br>")
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

        # The card is derived server-side and contains only share-safe values.
        featured_card = cosmic_cards.build_public_card_by_username(profile["username"])
        if featured_card:
            cosmic_cards.render_collectible_card(
                featured_card,
                is_owner=False,
                key_prefix=f"public_{profile['username']}",
                compact=True,
            )

        if st.button("Close profile", key="close_public_profile"):
            _clear_profile_lookup()
            st.rerun()


def _render_unified_community() -> None:
    """Render live chat and message boards together on one Community surface."""
    st.markdown(
        '<div class="community-section">'
        '<h2 class="community-section-title">💬 Live chat</h2>'
        '<p class="community-section-caption">A quick-moving lounge for the community. Refresh to see new messages.</p>'
        '</div>',
        unsafe_allow_html=True,
    )
    chat_room.render_chat_tab()

    st.markdown(
        '<div class="community-section">'
        '<h2 class="community-section-title">📋 Message boards</h2>'
        '<p class="community-section-caption">Start a lasting conversation in a topic-specific board.</p>'
        '</div>',
        unsafe_allow_html=True,
    )
    boards.render_boards_tab()


def render_community() -> None:
    """Render the Community page without the former LunaTicK Talk section."""
    auth.init_auth_db()
    boards.init_boards_db()
    chat_room.init_chat_db()

    st.markdown(COMMUNITY_CSS, unsafe_allow_html=True)
    with st.container(key="community-page"):
        st.markdown(
            '<div class="community-shell">'
            '<div class="community-kicker">Lunatick social orbit</div>'
            '<h1 class="community-title">Community</h1>'
            '<p class="community-subtitle">Chat in the moment. Share lasting thoughts. Find your people.</p>'
            '</div>',
            unsafe_allow_html=True,
        )
        _render_public_profile_lookup()
        moderation.render_moderation_console()

    _render_unified_community()


__all__ = ["render_community"]
