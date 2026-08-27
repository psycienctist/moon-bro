"""Private, free Reading Requests matching for LunaTicK members."""

from __future__ import annotations

import html
import sqlite3
from typing import Any

import streamlit as st

import supabase_store


DB = "lunatick.db"
READING_REQUESTS_MODULE_VERSION = "reader_requests_private_messages_v1"
MESSAGE_REFRESH_SECONDS = 5


def _using_supabase_backend() -> bool:
    return supabase_store.data_backend_from_streamlit_secrets() == "supabase"


def _store() -> supabase_store.SupabaseStore:
    return supabase_store.SupabaseStore(supabase_store.SupabaseSettings.from_streamlit_secrets())


def _member_id() -> str:
    subject = str(st.session_state.get("auth_subject", "")).strip()
    user_hash = str(st.session_state.get("user_hash", "")).strip()
    if _using_supabase_backend():
        if not subject:
            raise ValueError("Please sign in again to use Reading Requests.")
        return subject
    return user_hash or "anonymous"


def _display_name() -> str:
    return str(st.session_state.get("display_name") or "Moon Wanderer").strip()[:48] or "Moon Wanderer"


def _avatar() -> str:
    return str(st.session_state.get("avatar") or "🌙").strip()[:8] or "🌙"


def init_reading_requests_db() -> None:
    """Create the private matching tables for the legacy SQLite fallback."""
    if _using_supabase_backend():
        return
    conn = sqlite3.connect(DB)
    try:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS reading_readers (
                member_id TEXT PRIMARY KEY,
                display_name TEXT NOT NULL,
                avatar TEXT NOT NULL,
                focus TEXT NOT NULL DEFAULT '',
                intro TEXT NOT NULL DEFAULT '',
                is_available INTEGER NOT NULL DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS reading_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                requester_id TEXT NOT NULL,
                requester_name TEXT NOT NULL,
                topic TEXT NOT NULL,
                private_context TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','matched','closed','cancelled')),
                reader_id TEXT,
                reader_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS reading_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reading_request_id INTEGER NOT NULL,
                sender_id TEXT NOT NULL,
                sender_name TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (reading_request_id) REFERENCES reading_requests(id) ON DELETE CASCADE
            )"""
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_reading_requests_status ON reading_requests(status, created_at DESC)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_reading_messages_request ON reading_messages(reading_request_id, created_at ASC)")
        conn.commit()
    finally:
        conn.close()


def save_reader_profile(focus: str, intro: str, is_available: bool) -> None:
    member_id = _member_id()
    if _using_supabase_backend():
        _store().upsert_reading_reader(member_id, _display_name(), _avatar(), focus.strip(), intro.strip(), is_available)
        return
    conn = sqlite3.connect(DB)
    try:
        conn.execute(
            """INSERT INTO reading_readers (member_id, display_name, avatar, focus, intro, is_available, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
               ON CONFLICT(member_id) DO UPDATE SET display_name=excluded.display_name, avatar=excluded.avatar,
               focus=excluded.focus, intro=excluded.intro, is_available=excluded.is_available, updated_at=CURRENT_TIMESTAMP""",
            (member_id, _display_name(), _avatar(), focus.strip(), intro.strip(), int(is_available)),
        )
        conn.commit()
    finally:
        conn.close()


def get_reader_profile(member_id: str | None = None) -> dict[str, Any] | None:
    target = member_id or _member_id()
    if _using_supabase_backend():
        return _store().get_reading_reader(target)
    conn = sqlite3.connect(DB)
    try:
        row = conn.execute(
            "SELECT member_id, display_name, avatar, focus, intro, is_available FROM reading_readers WHERE member_id=?",
            (target,),
        ).fetchone()
    finally:
        conn.close()
    return (
        {"member_id": row[0], "display_name": row[1], "avatar": row[2], "focus": row[3], "intro": row[4], "is_available": bool(row[5])}
        if row
        else None
    )


def list_available_readers(limit: int = 50) -> list[dict[str, Any]]:
    if _using_supabase_backend():
        return _store().list_available_reading_readers(limit)
    conn = sqlite3.connect(DB)
    try:
        rows = conn.execute(
            "SELECT member_id, display_name, avatar, focus, intro FROM reading_readers WHERE is_available=1 ORDER BY updated_at DESC LIMIT ?",
            (max(1, min(limit, 100)),),
        ).fetchall()
    finally:
        conn.close()
    return [{"member_id": row[0], "display_name": row[1], "avatar": row[2], "focus": row[3], "intro": row[4]} for row in rows]


def create_request(topic: str, private_context: str) -> int:
    topic = topic.strip()
    private_context = private_context.strip()
    if not topic or len(topic) > 120 or len(private_context) > 1200:
        raise ValueError("Add a short topic and optional private context within the stated limits.")
    member_id = _member_id()
    if _using_supabase_backend():
        row = _store().create_reading_request(member_id, _display_name(), topic, private_context)
        return int(row["id"])
    conn = sqlite3.connect(DB)
    try:
        cursor = conn.execute(
            "INSERT INTO reading_requests (requester_id, requester_name, topic, private_context) VALUES (?, ?, ?, ?)",
            (member_id, _display_name(), topic, private_context),
        )
        conn.commit()
        return int(cursor.lastrowid)
    finally:
        conn.close()


def list_open_requests(limit: int = 50) -> list[dict[str, Any]]:
    if _using_supabase_backend():
        return _store().list_open_reading_requests(limit)
    conn = sqlite3.connect(DB)
    try:
        rows = conn.execute(
            "SELECT id, requester_id, requester_name, topic, created_at FROM reading_requests WHERE status='open' ORDER BY created_at DESC LIMIT ?",
            (max(1, min(limit, 100)),),
        ).fetchall()
    finally:
        conn.close()
    return [{"id": int(row[0]), "requester_id": row[1], "requester_name": row[2], "topic": row[3], "created_at": row[4]} for row in rows]


def list_member_requests() -> list[dict[str, Any]]:
    member_id = _member_id()
    if _using_supabase_backend():
        return _store().list_member_reading_requests(member_id)
    conn = sqlite3.connect(DB)
    try:
        rows = conn.execute(
            """SELECT id, requester_id, requester_name, topic, private_context, status, reader_id, reader_name, created_at
               FROM reading_requests WHERE requester_id=? OR reader_id=? ORDER BY updated_at DESC""",
            (member_id, member_id),
        ).fetchall()
    finally:
        conn.close()
    return [
        {"id": int(row[0]), "requester_id": row[1], "requester_name": row[2], "topic": row[3], "private_context": row[4], "status": row[5], "reader_id": row[6], "reader_name": row[7], "created_at": row[8]}
        for row in rows
    ]


def get_request(request_id: int) -> dict[str, Any] | None:
    if _using_supabase_backend():
        return _store().get_reading_request(int(request_id))
    conn = sqlite3.connect(DB)
    try:
        row = conn.execute(
            """SELECT id, requester_id, requester_name, topic, private_context, status, reader_id, reader_name, created_at
               FROM reading_requests WHERE id=?""",
            (int(request_id),),
        ).fetchone()
    finally:
        conn.close()
    return (
        {"id": int(row[0]), "requester_id": row[1], "requester_name": row[2], "topic": row[3], "private_context": row[4], "status": row[5], "reader_id": row[6], "reader_name": row[7], "created_at": row[8]}
        if row
        else None
    )


def accept_request(request_id: int) -> bool:
    member_id = _member_id()
    profile = get_reader_profile(member_id)
    if not profile or not profile.get("is_available"):
        return False
    if _using_supabase_backend():
        return _store().accept_reading_request(int(request_id), member_id, _display_name())
    conn = sqlite3.connect(DB)
    try:
        cursor = conn.execute(
            """UPDATE reading_requests SET status='matched', reader_id=?, reader_name=?, updated_at=CURRENT_TIMESTAMP
               WHERE id=? AND status='open' AND requester_id<>?""",
            (member_id, _display_name(), int(request_id), member_id),
        )
        conn.commit()
        return cursor.rowcount == 1
    finally:
        conn.close()


def close_request(request_id: int) -> bool:
    request = get_request(request_id)
    member_id = _member_id()
    if not request or member_id not in {request["requester_id"], request.get("reader_id")}:
        return False
    if _using_supabase_backend():
        return _store().close_reading_request(int(request_id), member_id)
    conn = sqlite3.connect(DB)
    try:
        cursor = conn.execute(
            "UPDATE reading_requests SET status='closed', updated_at=CURRENT_TIMESTAMP WHERE id=? AND status='matched'",
            (int(request_id),),
        )
        conn.commit()
        return cursor.rowcount == 1
    finally:
        conn.close()


def _is_participant(request: dict[str, Any]) -> bool:
    return _member_id() in {request.get("requester_id"), request.get("reader_id")}


def list_messages(request_id: int) -> list[dict[str, Any]]:
    request = get_request(request_id)
    if not request or not _is_participant(request):
        return []
    if _using_supabase_backend():
        return _store().list_reading_messages(int(request_id))
    conn = sqlite3.connect(DB)
    try:
        rows = conn.execute(
            "SELECT id, sender_id, sender_name, content, created_at FROM reading_messages WHERE reading_request_id=? ORDER BY created_at ASC LIMIT 200",
            (int(request_id),),
        ).fetchall()
    finally:
        conn.close()
    return [{"id": int(row[0]), "sender_id": row[1], "sender_name": row[2], "content": row[3], "created_at": row[4]} for row in rows]


def send_message(request_id: int, content: str) -> bool:
    content = content.strip()
    if not content or len(content) > 1200:
        return False
    request = get_request(request_id)
    if not request or request.get("status") != "matched" or not _is_participant(request):
        return False
    if _using_supabase_backend():
        _store().create_reading_message(int(request_id), _member_id(), _display_name(), content)
        return True
    conn = sqlite3.connect(DB)
    try:
        conn.execute(
            "INSERT INTO reading_messages (reading_request_id, sender_id, sender_name, content) VALUES (?, ?, ?, ?)",
            (int(request_id), _member_id(), _display_name(), content),
        )
        conn.commit()
        return True
    finally:
        conn.close()


def _set_active_conversation(request_id: int) -> None:
    st.session_state["active_reading_request_id"] = int(request_id)


def _render_conversation(request: dict[str, Any]) -> None:
    member_id = _member_id()
    partner = request["reader_name"] if member_id == request["requester_id"] else request["requester_name"]
    st.markdown(f"### Private reading with {html.escape(str(partner or 'LunaTicK member'))}")
    st.caption("Only you and the matched reader/requester can view this conversation. Keep sensitive personal information out of messages.")
    if request.get("private_context"):
        st.info(f"Private request context: {request['private_context']}")

    def _message_panel() -> None:
        with st.container(height=260, border=True):
            messages = list_messages(int(request["id"]))
            if not messages:
                st.caption("Your private conversation is ready. Start when you are comfortable.")
            for message in messages:
                sender = html.escape(str(message.get("sender_name") or "Moon Wanderer"))
                body = html.escape(str(message.get("content") or "")).replace("\n", "<br>")
                when = html.escape(str(message.get("created_at") or "")[11:16])
                st.markdown(f"<div style='margin:0 0 .55rem;'><b style='color:#bc8cff;'>{sender}</b> <span style='color:#8b949e;font-size:.7rem;'>{when}</span><br><span style='color:#e6edf3;'>{body}</span></div>", unsafe_allow_html=True)
        with st.form(f"reading_message_form_{request['id']}", clear_on_submit=True):
            message = st.text_input("Message", key=f"reading_message_{request['id']}", label_visibility="collapsed", max_chars=1200, placeholder="Write privately…")
            send = st.form_submit_button("Send private message", type="primary", use_container_width=True)
        if send:
            if send_message(int(request["id"]), message):
                st.rerun()
            else:
                st.warning("Write a message of up to 1,200 characters.")

    fragment = getattr(st, "fragment", None)
    if fragment is None:
        _message_panel()
    else:
        @fragment(run_every=MESSAGE_REFRESH_SECONDS)
        def _private_messages_fragment() -> None:
            _message_panel()
        _private_messages_fragment()

    close_col, back_col = st.columns(2)
    with close_col:
        if st.button("Mark reading complete", key=f"close_reading_{request['id']}", use_container_width=True):
            if close_request(int(request["id"])):
                st.success("Reading marked complete.")
                st.session_state.pop("active_reading_request_id", None)
                st.rerun()
    with back_col:
        if st.button("Back to requests", key="back_to_readings", use_container_width=True):
            st.session_state.pop("active_reading_request_id", None)
            st.rerun()


def render_reading_requests() -> None:
    """Render reader volunteering, private requests, matching, and conversations."""
    init_reading_requests_db()
    if st.button("← Home", key="readings_back_home"):
        st.session_state.nav_page = "Home"
        st.query_params.pop("reading_requests", None)
        st.rerun()
    st.markdown("## ✦ Reading Requests")
    st.caption("Free community readings in private, matched conversations. Readers volunteer their own time; no payment or booking is involved.")

    active_id = st.session_state.get("active_reading_request_id")
    if active_id:
        active_request = get_request(int(active_id))
        if active_request and active_request.get("status") == "matched" and _is_participant(active_request):
            _render_conversation(active_request)
            return
        st.session_state.pop("active_reading_request_id", None)

    my_reader_profile = get_reader_profile()
    with st.expander("Volunteer as a reader", expanded=not bool(my_reader_profile)):
        with st.form("reader_volunteer_form"):
            focus = st.text_input("Reading focus", value=str((my_reader_profile or {}).get("focus") or ""), max_chars=120, placeholder="e.g. natal charts, transits, general reflection")
            intro = st.text_area("Reader introduction", value=str((my_reader_profile or {}).get("intro") or ""), max_chars=360, height=88, placeholder="Share your approach and boundaries.")
            available = st.toggle("Available for free requests", value=bool((my_reader_profile or {}).get("is_available")))
            save_reader = st.form_submit_button("Save reader profile", type="primary", use_container_width=True)
        if save_reader:
            save_reader_profile(focus, intro, available)
            st.success("Your reader availability was updated.")
            st.rerun()

    with st.expander("Request a reading", expanded=False):
        st.caption("Your topic is visible to volunteer readers. The optional context is private until a reader accepts your request.")
        with st.form("create_reading_request_form", clear_on_submit=True):
            topic = st.text_input("What would you like a reading about?", max_chars=120, placeholder="e.g. Understanding a current transit")
            private_context = st.text_area("Private context (optional)", max_chars=1200, height=110, placeholder="Only your matched reader will see this.")
            submit_request = st.form_submit_button("Post reading request", type="primary", use_container_width=True)
        if submit_request:
            try:
                request_id = create_request(topic, private_context)
                st.success("Your request is open to volunteer readers.")
                st.session_state["active_reading_request_id"] = request_id
                st.rerun()
            except ValueError as error:
                st.warning(str(error))

    st.markdown("### Your private readings")
    my_requests = list_member_requests()
    if not my_requests:
        st.caption("No active reading requests or matched conversations yet.")
    for request in my_requests:
        other_name = request.get("reader_name") or "Waiting for a reader" if _member_id() == request.get("requester_id") else request.get("requester_name")
        st.markdown(f"**{html.escape(str(request.get('topic') or 'Reading request'))}** · {html.escape(str(request.get('status') or 'open').title())} · {html.escape(str(other_name or ''))}")
        if request.get("status") == "matched":
            if st.button("Open private conversation", key=f"open_reading_{request['id']}", use_container_width=True):
                _set_active_conversation(int(request["id"]))
                st.rerun()

    if my_reader_profile and my_reader_profile.get("is_available"):
        st.markdown("### Open community requests")
        open_requests = [item for item in list_open_requests() if item.get("requester_id") != _member_id()]
        if not open_requests:
            st.caption("No open requests right now.")
        for request in open_requests:
            st.markdown(f"<div style='border:1px solid #30363d;border-radius:12px;padding:.65rem;margin:.45rem 0;'><div style='color:#f0f6fc;font-weight:700;'>{html.escape(str(request.get('topic') or 'Reading request'))}</div><div style='color:#8b949e;font-size:.78rem;'>Requested by {html.escape(str(request.get('requester_name') or 'Moon Wanderer'))}</div></div>", unsafe_allow_html=True)
            if st.button("Offer this reading", key=f"accept_reading_{request['id']}", type="primary", use_container_width=True):
                if accept_request(int(request["id"])):
                    _set_active_conversation(int(request["id"]))
                    st.rerun()
                st.warning("This request is no longer available.")

    st.markdown("### Available volunteer readers")
    readers = [reader for reader in list_available_readers() if reader.get("member_id") != _member_id()]
    if not readers:
        st.caption("No readers are currently available. You can volunteer above to help build the circle.")
    for reader in readers:
        focus = html.escape(str(reader.get("focus") or "General reflection"))
        intro = html.escape(str(reader.get("intro") or "")).replace("\n", "<br>")
        st.markdown(f"<div style='border-left:3px solid #bc8cff;padding:.48rem .7rem;margin:.45rem 0;'><b style='color:#f0f6fc;'>{html.escape(str(reader.get('avatar') or '🌙'))} {html.escape(str(reader.get('display_name') or 'Moon Wanderer'))}</b><br><span style='color:#bc8cff;font-size:.82rem;'>{focus}</span><br><span style='color:#c9d1d9;font-size:.84rem;'>{intro}</span></div>", unsafe_allow_html=True)
