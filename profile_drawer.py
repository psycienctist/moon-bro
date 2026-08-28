"""Non-breaking fixed Profile drawer overlay.

This module intentionally depends only on Streamlit and receives the already-loaded
Cosmic Cards module from app.py. Missing optional renderers fail closed so the main
application and bottom navigation can still launch.
"""

from __future__ import annotations

import html
from typing import Any

import streamlit as st


DRAWER_MODULE_VERSION = "profile_drawer_isolated_v1"


def _render_css() -> None:
    st.html(
        """
        <style>
        .st-key-profile-drawer-overlay {
          position: fixed !important;
          z-index: 1000000 !important;
          top: .75rem !important;
          left: .75rem !important;
          width: min(50vw, 30rem) !important;
          max-width: calc(100vw - 1.5rem) !important;
          height: calc(100dvh - 1.5rem) !important;
          overflow-y: auto !important;
          padding: 1rem !important;
          border: 1px solid rgba(197,166,255,.72) !important;
          border-radius: 16px !important;
          background: linear-gradient(150deg, rgba(17,12,39,.98), rgba(5,8,18,.98)) !important;
          box-shadow: 0 18px 54px rgba(0,0,0,.62), 0 0 32px rgba(156,123,255,.22) !important;
          backdrop-filter: blur(14px) !important;
        }
        @media (max-width: 600px) {
          .st-key-profile-drawer-overlay {
            left: .5rem !important;
            top: .5rem !important;
            width: calc(100vw - 1rem) !important;
            max-width: none !important;
            height: calc(100dvh - 1rem) !important;
          }
        }
        </style>
        """
    )


def _safe_public_profile() -> dict[str, str]:
    return {
        "username": str(st.session_state.get("username") or "").strip(),
        "display_name": str(st.session_state.get("display_name") or "Moon Wanderer").strip(),
        "avatar": str(st.session_state.get("avatar") or "🌙"),
        "bio": str(st.session_state.get("bio") or "").strip(),
    }


def render_profile_drawer(cosmic_module: Any) -> None:
    """Render the drawer only when explicitly opened; never raise into app.py."""
    if not st.session_state.get("profile_drawer_open"):
        return
    try:
        _render_css()
        profile = _safe_public_profile()
        user_hash = str(st.session_state.get("user_hash") or "anonymous")
        with st.container(key="profile-drawer-overlay", border=True):
            close_col, title_col = st.columns([1, 8])
            with close_col:
                if st.button("×", key="profile_drawer_close", help="Close profile drawer", type="secondary"):
                    st.session_state["profile_drawer_open"] = False
                    st.rerun()
            with title_col:
                st.markdown("### My Profile")
            st.markdown(
                f"**{html.escape(profile['avatar'])} {html.escape(profile['display_name'])}**  "
                f"<span style='color:#bc8cff'>@{html.escape(profile['username'] or 'username')}</span>",
                unsafe_allow_html=True,
            )
            if profile["bio"]:
                st.caption(profile["bio"])

            build_card = getattr(cosmic_module, "build_card", None)
            render_card = getattr(cosmic_module, "render_collectible_card", None)
            if callable(build_card) and callable(render_card):
                card = build_card(user_hash)
                if card:
                    st.caption("My Cosmic Card")
                    render_card(card, is_owner=True, key_prefix="drawer_owner", compact=True)

            st.markdown("---")
            st.markdown("#### My Friends")
            render_friends = getattr(cosmic_module, "_render_profile_hub_connections", None)
            if callable(render_friends):
                render_friends(user_hash)
            else:
                st.caption("Friends are temporarily unavailable.")

            st.markdown("---")
            st.markdown("#### My DMs")
            try:
                from direct_messages import render_owner_dm_inbox
                render_owner_dm_inbox()
            except Exception:
                st.caption("Direct messages are temporarily unavailable.")
    except Exception:
        # Drawer-only failure must never remove bottom navigation or stop app launch.
        st.session_state["profile_drawer_open"] = False
        return
