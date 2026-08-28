"""Connection-gated member-to-member Direct Messages for the Profile hub.

This is deliberately separate from Reading Requests: a member chat exists only
between two people with an accepted Cosmic Card trade. Immutable auth subjects
are used only inside server-side storage checks and never rendered in the UI.
"""

from __future__ import annotations

import html

import streamlit as st

import supabase_store


MESSAGE_REFRESH_SECONDS = 5
MESSAGE_MAX_CHARS = 1200


def _using_supabase_backend() -> bool:
    """Return whether the cloud-only member messaging backend is enabled."""
    return supabase_store.data_backend_from_streamlit_secrets() == "supabase"


def _store() -> supabase_store.SupabaseStore:
    """Create the server-only store on demand."""
    return supabase_store.SupabaseStore(supabase_store.SupabaseSettings.from_streamlit_secrets())


def _member_subject() -> str:
    """Read the active immutable identity only from the signed-in server session."""
    return str(st.session_state.get("auth_subject") or "").strip()


def _display_name() -> str:
    """Return a bounded public display name for the sender label."""
    return supabase_store.public_display_name(st.session_state.get("display_name"))


def _safe_key(value: str) -> str:
    """Build a stable widget-key suffix without putting an auth identity in a key."""
    return str(abs(hash(value)))


def can_message_member(member_auth_subject: str) -> bool:
    """Allow messages only to a distinct accepted Cosmic Card connection."""
    viewer = _member_subject()
    target = str(member_auth_subject or "").strip()
    if not _using_supabase_backend() or not viewer or not target or viewer == target:
        return False
    return target in set(_store().list_accepted_card_contacts(viewer))


def open_member_conversation(member_auth_subject: str) -> dict | None:
    """Create or reopen a two-person conversation after rechecking consent."""
    viewer = _member_subject()
    target = str(member_auth_subject or "").strip()
    if not can_message_member(target):
        return None
    return _store().get_or_create_direct_message_thread(viewer, target)


def list_member_messages(thread_id: int, member_auth_subject: str) -> list[dict]:
    """Read messages only when the active member remains an accepted connection."""
    viewer = _member_subject()
    if not can_message_member(member_auth_subject):
        return []
    return _store().list_direct_messages_for_participant(int(thread_id), viewer)


def send_member_message(thread_id: int, member_auth_subject: str, content: str) -> bool:
    """Send a bounded message only into the active participant-owned thread."""
    body = str(content or "").strip()
    viewer = _member_subject()
    if not body or len(body) > MESSAGE_MAX_CHARS or not can_message_member(member_auth_subject):
        return False
    try:
        _store().create_direct_message(int(thread_id), viewer, _display_name(), body)
    except (ValueError, supabase_store.SupabaseRequestError):
        return False
    return True


def render_owner_dm_inbox() -> None:
    """Render the owner’s connection-gated DM list and selected conversation."""
    viewer = _member_subject()
    if not _using_supabase_backend() or not viewer:
        st.info("Direct Messages are available after you connect with another member.")
        return
    threads = _store().list_direct_message_threads_for_participant(viewer)
    st.markdown("### My DMs")
    st.caption("Private conversations with accepted Cosmic Card connections.")
    if not threads:
        st.info("No direct messages yet. Open an accepted member connection to start one.")
        return

    partner_subjects = [thread.get("partner_auth_subject") for thread in threads if thread.get("partner_auth_subject")]
    profiles = _store().get_public_profile_summaries(partner_subjects)
    for thread in threads:
        partner_subject = str(thread.get("partner_auth_subject") or "")
        profile = profiles.get(partner_subject) or {}
        username = str(profile.get("username") or "member").strip().lstrip("@")
        label = supabase_store.public_display_name(profile.get("display_name"))
        if st.button(
            f"{profile.get('avatar') or '🌙'} {label} · @{username}",
            key=f"profile_dm_thread_{_safe_key(str(thread.get('id')))}",
            use_container_width=True,
        ):
            st.session_state["profile_direct_message_thread"] = int(thread["id"])
            st.session_state["profile_direct_message_target"] = partner_subject
            st.rerun()

    active_thread = st.session_state.get("profile_direct_message_thread")
    active_target = str(st.session_state.get("profile_direct_message_target") or "")
    if not active_thread or not active_target:
        return
    active_thread_record = next((thread for thread in threads if int(thread["id"]) == int(active_thread)), None)
    if not active_thread_record or str(active_thread_record.get("partner_auth_subject") or "") != active_target:
        st.session_state.pop("profile_direct_message_thread", None)
        st.session_state.pop("profile_direct_message_target", None)
        return
    profile = profiles.get(active_target) or {}
    label = supabase_store.public_display_name(profile.get("display_name"))
    st.markdown(f"#### Private chat with {html.escape(label)}")
    st.caption("Only accepted card-trade connections can view this conversation.")
    _render_message_panel(int(active_thread), active_target)


def _render_message_panel(thread_id: int, member_auth_subject: str) -> None:
    """Render the conversation with a small timed refresh, if Streamlit supports it."""
    widget_key = _safe_key(member_auth_subject)

    def _panel() -> None:
        with st.container(height=260, border=True):
            messages = list_member_messages(thread_id, member_auth_subject)
            if not messages:
                st.caption("Your private chat is ready. Say hello when you are comfortable.")
            for message in messages:
                sender = html.escape(str(message.get("sender_name") or "Moon Wanderer"))
                body = html.escape(str(message.get("content") or "")).replace("\n", "<br>")
                when = html.escape(str(message.get("created_at") or "")[11:16])
                st.markdown(
                    f"<div style='margin:0 0 .55rem;'><b style='color:#bc8cff;'>{sender}</b> "
                    f"<span style='color:#8b949e;font-size:.7rem;'>{when}</span><br>"
                    f"<span style='color:#e6edf3;'>{body}</span></div>",
                    unsafe_allow_html=True,
                )
        with st.form(f"profile_direct_message_form_{widget_key}", clear_on_submit=True):
            message = st.text_input(
                "Message", key=f"profile_direct_message_input_{widget_key}",
                label_visibility="collapsed", max_chars=MESSAGE_MAX_CHARS,
                placeholder="Write privately…",
            )
            send = st.form_submit_button("Send message", type="primary", use_container_width=True)
        if send:
            if send_member_message(thread_id, member_auth_subject, message):
                st.rerun()
            else:
                st.warning("Write a message of up to 1,200 characters. This chat is available only while you are connected.")

    fragment = getattr(st, "fragment", None)
    if fragment is None:
        _panel()
        return

    @fragment(run_every=MESSAGE_REFRESH_SECONDS)
    def _messages_fragment() -> None:
        _panel()

    _messages_fragment()


def render_member_direct_message(member_auth_subject: str, member_profile: dict) -> None:
    """Render a Profile-level message button and its connection-gated conversation."""
    target = str(member_auth_subject or "").strip()
    username = str(member_profile.get("username") or "member").strip().lstrip("@")
    display_name = supabase_store.public_display_name(member_profile.get("display_name"))
    key_suffix = _safe_key(username)

    if not can_message_member(target):
        return

    if st.button(
        f"💬 Message @{username}", key=f"profile_direct_message_open_{key_suffix}",
        type="primary", use_container_width=True,
    ):
        conversation = open_member_conversation(target)
        if conversation:
            st.session_state["profile_direct_message_thread"] = int(conversation["id"])
            st.session_state["profile_direct_message_target"] = target
            st.rerun()
        st.warning("This chat is available only while you are connected.")

    active_thread = st.session_state.get("profile_direct_message_thread")
    active_target = str(st.session_state.get("profile_direct_message_target") or "")
    if active_target != target or not active_thread:
        return

    st.markdown(f"#### Private chat with {html.escape(display_name)}")
    st.caption("Only accepted card-trade connections can open this chat. Keep sensitive personal information out of messages.")
    _render_message_panel(int(active_thread), target)
