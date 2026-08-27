"""Founder and delegated moderation for LunaTicK public Community content only."""

from __future__ import annotations

import html
from typing import Any

import streamlit as st

import supabase_store


CONTENT_TYPES = {
    "Message board": "board_post",
    "Live chat": "chat_message",
}


def _using_supabase_backend() -> bool:
    return supabase_store.data_backend_from_streamlit_secrets() == "supabase"


def _store() -> supabase_store.SupabaseStore:
    return supabase_store.SupabaseStore(supabase_store.SupabaseSettings.from_streamlit_secrets())


def _current_subject() -> str:
    subject = str(st.session_state.get("auth_subject", "")).strip()
    if not subject:
        raise ValueError("A signed-in LunaTicK identity is required for moderation.")
    return subject


def _configured_founder_email() -> str:
    try:
        return str(st.secrets.get("backup", {}).get("owner_email", "")).strip().lower()
    except Exception:
        return ""


def _is_configured_founder() -> bool:
    configured_email = _configured_founder_email()
    current_email = str(st.session_state.get("email", "")).strip().lower()
    return bool(configured_email and current_email and configured_email == current_email)


def current_role() -> str | None:
    """Resolve a role server-side, bootstrapping only the configured founder."""
    if not _using_supabase_backend():
        return None

    store = _store()
    subject = _current_subject()
    if _is_configured_founder():
        existing = store.get_moderator_role(subject)
        if not existing or existing.get("role") != "founder":
            store.upsert_moderator_role(subject, "founder", subject)
        return "founder"

    role = store.get_moderator_role(subject)
    return str(role.get("role")) if role else None


def is_moderator() -> bool:
    return current_role() in {"founder", "moderator"}


def _public_labels(store: supabase_store.SupabaseStore, subjects: list[str]) -> dict[str, str]:
    summaries = store.get_public_profile_summaries(subjects)
    return {
        subject: str(summary.get("display_name") or summary.get("username") or "Moon Wanderer")
        for subject, summary in summaries.items()
    }


def _record_title(target_type: str, row: dict[str, Any], author_label: str) -> str:
    if target_type == "board_post":
        return f"Board post · {row.get('board_slug') or 'board'} · {author_label}"
    if target_type == "chat_message":
        return f"Chat message · {author_label}"
    if target_type == "talk_post":
        label = "Anonymous" if row.get("is_anonymous") else author_label
        return f"Talk post · {label}"
    label = "Anonymous" if row.get("is_anonymous") else author_label
    return f"Talk comment · {label}"


def _record_preview(target_type: str, row: dict[str, Any]) -> str:
    if target_type == "board_post":
        title = str(row.get("title") or "Untitled")
        return f"{title}\n\n{row.get('content') or ''}"
    return str(row.get("content") or "")


def _act_on_content(
    store: supabase_store.SupabaseStore,
    actor_subject: str,
    target_type: str,
    row: dict[str, Any],
    action: str,
    reason: str,
) -> None:
    target_id = int(row["id"])
    if action == "hide":
        store.set_moderation_visibility(target_type, target_id, True)
    elif action == "restore":
        store.set_moderation_visibility(target_type, target_id, False)
    elif action == "delete":
        store.delete_moderation_content(target_type, target_id)
    else:
        raise ValueError("Unsupported public-content moderation action.")

    store.log_moderation_action(
        actor_subject,
        target_type,
        action,
        target_id=target_id,
        target_auth_subject=str(row.get("profile_auth_subject") or "") or None,
        reason=reason,
        details={"was_hidden": bool(row.get("is_hidden"))},
    )


def _render_content_review(store: supabase_store.SupabaseStore, role: str, actor_subject: str) -> None:
    st.caption("Review public Community records only. Hidden items stay available here for restoration; Journals never enter this view.")
    selected_label = st.selectbox("Content type", tuple(CONTENT_TYPES), key="moderation_content_type")
    target_type = CONTENT_TYPES[selected_label]
    records = store.list_moderation_content(target_type, limit=100)
    if not records:
        st.info("No records in this public-content review queue.")
        return

    labels = _public_labels(
        store,
        [str(row.get("profile_auth_subject") or "") for row in records if row.get("profile_auth_subject")],
    )
    for row in records:
        record_id = int(row["id"])
        author_label = labels.get(str(row.get("profile_auth_subject") or ""), "Moon Wanderer")
        hidden = bool(row.get("is_hidden"))
        state = "HIDDEN" if hidden else "VISIBLE"
        with st.expander(f"{_record_title(target_type, row, author_label)} · {state}", expanded=False):
            st.caption(f"Created {str(row.get('created_at') or '')[:16]}")
            st.markdown(html.escape(_record_preview(target_type, row)).replace("\n", "  \n"))
            reason = st.text_input(
                "Moderation reason (optional)",
                max_chars=240,
                key=f"moderation_reason_{target_type}_{record_id}",
            )
            primary_label = "Restore public visibility" if hidden else "Hide from Community"
            primary_action = "restore" if hidden else "hide"
            action_col, delete_col = st.columns(2)
            with action_col:
                if st.button(primary_label, key=f"moderation_{primary_action}_{target_type}_{record_id}", use_container_width=True):
                    _act_on_content(store, actor_subject, target_type, row, primary_action, reason)
                    st.success("Content restored." if primary_action == "restore" else "Content hidden.")
                    st.rerun()
            with delete_col:
                if role == "founder":
                    confirmation = st.checkbox(
                        "Confirm permanent deletion",
                        key=f"moderation_confirm_delete_{target_type}_{record_id}",
                    )
                    if st.button(
                        "Delete permanently",
                        key=f"moderation_delete_{target_type}_{record_id}",
                        use_container_width=True,
                        disabled=not confirmation,
                    ):
                        _act_on_content(store, actor_subject, target_type, row, "delete", reason)
                        st.success("Content permanently deleted and audited.")
                        st.rerun()
                else:
                    st.caption("Only the founder can permanently delete content.")


def _render_team_management(store: supabase_store.SupabaseStore, actor_subject: str) -> None:
    st.caption("Founder-only delegation. Grant by a user’s public @username; no email or private profile fields are shown.")
    with st.form("grant_moderator_form", clear_on_submit=True):
        handle = st.text_input("Moderator username", placeholder="e.g. moon_orbit", max_chars=24)
        grant = st.form_submit_button("Grant moderator role", use_container_width=True)
    if grant:
        profile = store.find_profile_for_moderation(handle)
        if not profile:
            st.warning("No LunaTicK profile was found for that username.")
        elif str(profile.get("auth_subject")) == actor_subject:
            st.warning("Your founder role is already active.")
        else:
            subject = str(profile["auth_subject"])
            store.upsert_moderator_role(subject, "moderator", actor_subject)
            store.log_moderation_action(
                actor_subject,
                "moderator_role",
                "grant_role",
                target_auth_subject=subject,
                reason="Founder granted moderator role",
                details={"role": "moderator"},
            )
            st.success(f"Moderator role granted to @{profile.get('username') or profile.get('display_name')}.")
            st.rerun()

    roles = store.list_moderator_roles()
    labels = _public_labels(store, [str(row.get("auth_subject") or "") for row in roles])
    st.markdown("#### Current moderation roles")
    for role_record in roles:
        subject = str(role_record.get("auth_subject") or "")
        role = str(role_record.get("role") or "moderator")
        active = bool(role_record.get("is_active"))
        label = labels.get(subject, "Moon Wanderer")
        status = "active" if active else "revoked"
        role_col, action_col = st.columns([3, 2])
        with role_col:
            st.caption(f"{label} · {role} · {status}")
        with action_col:
            if role == "moderator" and active:
                if st.button("Revoke", key=f"revoke_moderator_{subject}", use_container_width=True):
                    store.revoke_moderator_role(subject)
                    store.log_moderation_action(
                        actor_subject,
                        "moderator_role",
                        "revoke_role",
                        target_auth_subject=subject,
                        reason="Founder revoked moderator role",
                        details={"role": "moderator"},
                    )
                    st.success("Moderator role revoked.")
                    st.rerun()


def _render_audit_log(store: supabase_store.SupabaseStore) -> None:
    st.caption("Accountability metadata only. The log records actions and reasons, never a copy of Community or Journal content.")
    actions = store.list_moderation_actions(limit=100)
    if not actions:
        st.info("No moderation actions have been recorded yet.")
        return
    for action in actions:
        target = (
            f"{action.get('target_type')} #{action.get('target_id')}"
            if action.get("target_id") is not None
            else str(action.get("target_type"))
        )
        reason = str(action.get("reason") or "No reason supplied")
        st.caption(
            f"{str(action.get('created_at') or '')[:16]} · {action.get('action')} · {target} · {reason}"
        )


def visible_console_sections(role: str) -> tuple[str, ...]:
    """Return the protected console views allowed for a moderation role."""
    return ("Review", "Moderation team", "Audit") if role == "founder" else ("Review",)


def render_moderation_console() -> None:
    """Render a role-gated public-content console; no private Journal access exists here."""
    role = current_role()
    if role not in {"founder", "moderator"}:
        return

    store = _store()
    actor_subject = _current_subject()
    with st.expander("🛡️ Community moderation", expanded=False):
        st.caption(
            "Review public LunaTicK Talk board posts and live-chat messages. "
            "Private Journals and private profile data are not available here."
        )
        if role == "founder":
            review_tab, team_tab, audit_tab = st.tabs(visible_console_sections(role))
            with review_tab:
                _render_content_review(store, role, actor_subject)
            with team_tab:
                _render_team_management(store, actor_subject)
            with audit_tab:
                _render_audit_log(store)
        else:
            st.caption("Moderator access is limited to reviewing, hiding, and restoring public Community content.")
            _render_content_review(store, role, actor_subject)
