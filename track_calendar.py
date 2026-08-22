"""Phone-first lunar Track calendar with owner-only personal entries.

The public astronomical layer is deliberately separate from personal notes and
observed cycle markers. All persistence uses the server-only Supabase adapter.
"""

from __future__ import annotations

import calendar as calendar_module
import html
import sqlite3
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any

import streamlit as st

import cosmic_cards
import supabase_store

TRACK_MODULE_VERSION = "mobile_grid_private_entries_v2"
_SQLITE_DB = Path("lunatick.db")

# NASA Eclipse Web Site 2026 catalog dates/times (UT). Descriptions deliberately
# do not claim local visibility because that depends on the observer's location.
LUNAR_EVENTS: dict[date, dict[str, str]] = {
    date(2026, 2, 17): {
        "title": "Annular Solar Eclipse",
        "kind": "solar_eclipse",
        "utc": "20260217T121200Z",
        "source": "NASA eclipse catalog · UT",
    },
    date(2026, 3, 3): {
        "title": "Total Lunar Eclipse",
        "kind": "lunar_eclipse",
        "utc": "20260303T113400Z",
        "source": "NASA eclipse catalog · UT",
    },
    date(2026, 8, 12): {
        "title": "Total Solar Eclipse",
        "kind": "solar_eclipse",
        "utc": "20260812T174600Z",
        "source": "NASA eclipse catalog · UT",
    },
    date(2026, 8, 28): {
        "title": "Partial Lunar Eclipse",
        "kind": "lunar_eclipse",
        "utc": "20260828T041300Z",
        "source": "NASA eclipse catalog · UT",
    },
}


def _using_supabase() -> bool:
    return supabase_store.data_backend_from_streamlit_secrets() == "supabase"


def _store() -> supabase_store.SupabaseStore:
    return supabase_store.SupabaseStore(supabase_store.SupabaseSettings.from_streamlit_secrets())


def _subject() -> str:
    subject = str(st.session_state.get("auth_subject", "")).strip()
    if not subject:
        raise ValueError("A signed-in LunaTicK identity is required for private Track entries.")
    return subject


def _init_sqlite() -> None:
    conn = sqlite3.connect(_SQLITE_DB)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS calendar_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_hash TEXT NOT NULL,
            entry_date TEXT NOT NULL,
            note TEXT NOT NULL DEFAULT '',
            cycle_marker TEXT,
            severity INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_hash, entry_date)
        )
        """
    )
    conn.commit()
    conn.close()


def list_private_entries(month_start: date, month_end: date) -> dict[str, dict[str, Any]]:
    """Return only the signed-in owner's date notes and cycle markers."""
    start_iso, end_iso = month_start.isoformat(), month_end.isoformat()
    if _using_supabase():
        rows = _store().list_calendar_entries(_subject(), start_iso, end_iso)
    else:
        _init_sqlite()
        conn = sqlite3.connect(_SQLITE_DB)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT entry_date,note,cycle_marker,severity,updated_at
            FROM calendar_entries
            WHERE user_hash=? AND entry_date>=? AND entry_date<?
            ORDER BY entry_date ASC
            """,
            (str(st.session_state.get("user_hash", "anonymous")), start_iso, end_iso),
        ).fetchall()
        conn.close()
    return {str(row["entry_date"]): dict(row) for row in rows}


def save_private_entry(entry_date: date, note: str, cycle_marker: str | None, severity: int | None) -> None:
    """Save one owner's private note/observed marker for a date."""
    clean_note = (note or "").strip()[:2000]
    normalized_marker = cycle_marker if cycle_marker in {"started", "ended"} else None
    normalized_severity = int(severity) if severity in {1, 2, 3, 4, 5} else None
    if not clean_note and not normalized_marker and normalized_severity is None:
        delete_private_entry(entry_date)
        return
    if _using_supabase():
        _store().upsert_calendar_entry(
            _subject(), entry_date.isoformat(), clean_note, normalized_marker, normalized_severity
        )
        return
    _init_sqlite()
    conn = sqlite3.connect(_SQLITE_DB)
    conn.execute(
        """
        INSERT INTO calendar_entries (user_hash,entry_date,note,cycle_marker,severity)
        VALUES (?,?,?,?,?)
        ON CONFLICT(user_hash,entry_date) DO UPDATE SET
          note=excluded.note,cycle_marker=excluded.cycle_marker,severity=excluded.severity,
          updated_at=CURRENT_TIMESTAMP
        """,
        (str(st.session_state.get("user_hash", "anonymous")), entry_date.isoformat(), clean_note, normalized_marker, normalized_severity),
    )
    conn.commit()
    conn.close()


def delete_private_entry(entry_date: date) -> None:
    """Remove only the signed-in owner's selected private date entry."""
    if _using_supabase():
        _store().delete_calendar_entry(_subject(), entry_date.isoformat())
        return
    _init_sqlite()
    conn = sqlite3.connect(_SQLITE_DB)
    conn.execute(
        "DELETE FROM calendar_entries WHERE user_hash=? AND entry_date=?",
        (str(st.session_state.get("user_hash", "anonymous")), entry_date.isoformat()),
    )
    conn.commit()
    conn.close()


def _phase_for_day(day: date) -> dict[str, Any]:
    # Noon UTC avoids a local-midnight boundary changing the calendar's daily icon.
    return cosmic_cards._chart(datetime.combine(day, time(12, 0), tzinfo=timezone.utc))


def _event_ics(day: date, event: dict[str, str]) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    start = event["utc"]
    end = (datetime.strptime(start, "%Y%m%dT%H%M%SZ") + timedelta(hours=1)).strftime("%Y%m%dT%H%M%SZ")
    title = event["title"].replace(",", "\\,")
    return "\r\n".join(
        (
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//LunaTicK//Track//EN",
            "BEGIN:VEVENT",
            f"UID:lunatick-{day.isoformat()}-{event['kind']}@lunatick",
            f"DTSTAMP:{stamp}",
            f"DTSTART:{start}",
            f"DTEND:{end}",
            f"SUMMARY:{title}",
            "DESCRIPTION:Source: NASA eclipse catalog. Time shown in UTC; local visibility varies by location.",
            "BEGIN:VALARM",
            "TRIGGER:-P1D",
            "ACTION:DISPLAY",
            f"DESCRIPTION:Tomorrow: {title}",
            "END:VALARM",
            "END:VEVENT",
            "END:VCALENDAR",
            "",
        )
    )


def _selected_day(month_start: date) -> date:
    raw = str(st.query_params.get("track_day", "")).strip()
    try:
        chosen = date.fromisoformat(raw)
        if chosen.year == month_start.year and chosen.month == month_start.month:
            return chosen
    except ValueError:
        pass
    return date.today() if date.today().year == month_start.year and date.today().month == month_start.month else month_start


def _set_month(delta: int) -> None:
    year = int(st.session_state.get("track_calendar_year", date.today().year))
    month = int(st.session_state.get("track_calendar_month", date.today().month)) + delta
    if month < 1:
        month, year = 12, year - 1
    elif month > 12:
        month, year = 1, year + 1
    st.session_state.track_calendar_month = month
    st.session_state.track_calendar_year = year
    st.query_params.pop("track_day", None)


def _month_grid_html(month_start: date, entries: dict[str, dict[str, Any]]) -> str:
    weekday_labels = ("M", "T", "W", "T", "F", "S", "S")
    days = [f'<div class="track-weekday">{label}</div>' for label in weekday_labels]
    matrix = calendar_module.monthcalendar(month_start.year, month_start.month)
    today = date.today()
    for week in matrix:
        for day_number in week:
            if not day_number:
                days.append('<div class="track-day track-day--empty" aria-hidden="true"></div>')
                continue
            day = date(month_start.year, month_start.month, day_number)
            phase = _phase_for_day(day)
            entry = entries.get(day.isoformat(), {})
            event = LUNAR_EVENTS.get(day)
            flags: list[str] = []
            if event:
                flags.append('<span class="track-dot track-dot--event" title="Notable lunar event">✦</span>')
            if entry.get("note"):
                flags.append('<span class="track-dot track-dot--note" title="Private note">•</span>')
            if entry.get("cycle_marker") == "started":
                flags.append('<span class="track-dot track-dot--cycle-start" title="Private observed cycle start">•</span>')
            if entry.get("cycle_marker") == "ended":
                flags.append('<span class="track-dot track-dot--cycle-end" title="Private observed cycle end">•</span>')
            state = " track-day--today" if day == today else ""
            event_class = " track-day--event" if event else ""
            days.append(
                f'''<a class="track-day{state}{event_class}" href="?track_day={day.isoformat()}" aria-label="{day.isoformat()}">
                    <span class="track-date">{day_number}</span>
                    <span class="track-moon">{phase['phase_emoji']}</span>
                    <span class="track-dots">{''.join(flags)}</span>
                </a>'''
            )
    return "".join(days)


def _render_css() -> None:
    st.html(
        """
        <style>
        .track-grid { display:grid; grid-template-columns:repeat(7,minmax(0,1fr)); gap:4px; width:100%; }
        .track-weekday { text-align:center; color:#8591a5; font-size:.56rem; font-weight:700; letter-spacing:.04em; padding:.08rem 0 .16rem; }
        .track-day { position:relative; aspect-ratio:1/1; min-height:43px; display:flex; flex-direction:column; align-items:center; justify-content:center; gap:0; text-decoration:none!important; border:1px solid rgba(178,190,225,.20); border-radius:8px; background:linear-gradient(145deg,rgba(25,31,50,.94),rgba(12,16,28,.94)); color:#e9eefb!important; overflow:hidden; }
        .track-day:active,.track-day:focus { transform:scale(.97); outline:1px solid #bc8cff; background:rgba(74,54,120,.44); }
        .track-day--today { border-color:#bc8cff; box-shadow:0 0 13px rgba(188,140,255,.28); }
        .track-day--event { border-color:rgba(255,207,91,.72); }
        .track-day--empty { border-color:transparent; background:transparent; pointer-events:none; }
        .track-date { position:absolute; top:3px; left:5px; font-size:.54rem; font-weight:700; color:#dfe6f7; }
        .track-moon { font-size:1.1rem; line-height:1; transform:translateY(3px); }
        .track-dots { position:absolute; right:4px; bottom:2px; display:flex; align-items:center; gap:1px; min-height:8px; }
        .track-dot { font-size:.6rem; line-height:1; }
        .track-dot--event { color:#ffd36e; font-size:.62rem; }
        .track-dot--note { color:#bc8cff; font-size:.85rem; }
        .track-dot--cycle-start { color:#f05d6e; font-size:.85rem; }
        .track-dot--cycle-end { color:#63d99d; font-size:.85rem; }
        .track-selected { border:1px solid rgba(188,140,255,.35); border-radius:11px; background:rgba(30,22,52,.58); padding:.72rem .76rem; margin:.7rem 0; }
        .track-event-strip { border:1px solid rgba(255,211,110,.52); border-radius:8px; background:rgba(112,82,23,.20); color:#f6dda2; font-size:.68rem; padding:.35rem .5rem; margin:.28rem 0 .32rem; }
        .st-key-track_previous_month button, .st-key-track_next_month button { min-height:1.72rem!important; height:1.72rem!important; min-width:1.72rem!important; width:1.72rem!important; padding:0!important; border-radius:.48rem!important; font-size:.66rem!important; line-height:1!important; }
        .track-legend { display:flex; flex-wrap:wrap; gap:.42rem .78rem; color:#9ba9bf; font-size:.62rem; margin:.42rem 0 .08rem; }
        @media (max-width: 480px) {
          .track-day { min-height:42px; border-radius:7px; }
          .track-moon { font-size:1.04rem; }
          .track-date { font-size:.52rem; left:4px; }
        }
        </style>
        """
    )


def _render_selected_day(day: date, entry: dict[str, Any]) -> None:
    phase = _phase_for_day(day)
    event = LUNAR_EVENTS.get(day)
    marker = str(entry.get("cycle_marker") or "")
    existing_note = str(entry.get("note") or "")
    existing_severity = entry.get("severity")
    st.markdown(
        f'''<div class="track-selected">
          <div style="font-size:.64rem;letter-spacing:1.5px;color:#9bbcff;font-weight:700;">{day.strftime('%A · %B')} {day.day}</div>
          <div style="font-size:1.1rem;color:#f1f5ff;margin:.14rem 0;">{phase['phase_emoji']} {html.escape(str(phase['phase_name']))}</div>
          <div style="font-size:.7rem;color:#9ba9bf;">Daily phase estimate · {float(phase['illum']) * 100:.0f}% illuminated</div>
        </div>''',
        unsafe_allow_html=True,
    )
    if event:
        st.markdown(f"#### ✦ {event['title']}")
        st.caption(f"{event['source']}. Time is shown in UTC; local visibility varies by location.")
        st.download_button(
            "Add to device calendar",
            data=_event_ics(day, event),
            file_name=f"lunatick-{event['kind']}-{day.isoformat()}.ics",
            mime="text/calendar",
            use_container_width=True,
            key=f"track_ics_{day.isoformat()}",
        )

    st.markdown("#### 🔒 Private note")
    st.caption("Only you can see these notes and observed cycle markers. They are not medical predictions.")
    marker_labels = {"": "No cycle marker", "started": "Period started", "ended": "Period ended"}
    options = list(marker_labels)
    current_marker = marker if marker in marker_labels else ""
    severity_options: list[str] = ["Not set", "1", "2", "3", "4", "5"]
    current_severity = str(existing_severity) if existing_severity in {1, 2, 3, 4, 5} else "Not set"
    with st.form(f"track_entry_{day.isoformat()}", clear_on_submit=False):
        note = st.text_area(
            "Personal note",
            value=existing_note,
            max_chars=2000,
            height=94,
            placeholder="Anything you want to remember about this day…",
        )
        left, right = st.columns(2)
        with left:
            cycle_choice = st.selectbox(
                "Observed cycle marker",
                options=options,
                index=options.index(current_marker),
                format_func=lambda value: marker_labels[value],
            )
        with right:
            severity_choice = st.selectbox("Optional severity", severity_options, index=severity_options.index(current_severity))
        save = st.form_submit_button("Save private date entry", type="primary", use_container_width=True)
    if save:
        save_private_entry(day, note, cycle_choice or None, None if severity_choice == "Not set" else int(severity_choice))
        st.toast("Private date entry saved.")
        st.rerun()
    if existing_note or current_marker or existing_severity is not None:
        if st.button("Remove this private date entry", key=f"delete_track_{day.isoformat()}"):
            delete_private_entry(day)
            st.toast("Private date entry removed.")
            st.rerun()


def render_track_tab() -> None:
    """Render the compact lunar calendar, events, and owner-only personal layer."""
    _render_css()
    today = date.today()
    st.session_state.setdefault("track_calendar_month", today.month)
    st.session_state.setdefault("track_calendar_year", today.year)
    year = int(st.session_state.track_calendar_year)
    month = int(st.session_state.track_calendar_month)
    month_start = date(year, month, 1)
    next_month = date(year + (month == 12), 1 if month == 12 else month + 1, 1)

    month_events = [
        (event_day, event)
        for event_day, event in LUNAR_EVENTS.items()
        if event_day.year == year and event_day.month == month
    ]
    selected = _selected_day(month_start)
    entries = list_private_entries(month_start, next_month)

    st.markdown(
        "<div style=\"font-family:Orbitron,sans-serif;font-size:.76rem;letter-spacing:2.6px;color:#bc8cff;text-transform:uppercase;margin-bottom:.08rem;\">📅 Track</div>",
        unsafe_allow_html=True,
    )
    left, center, right = st.columns([0.32, 2.1, 0.32], vertical_alignment="center")
    with left:
        st.button("◀", key="track_previous_month", on_click=_set_month, args=(-1,))
    with center:
        st.markdown(
            f"<div style='text-align:center;font-family:Orbitron,sans-serif;font-size:.72rem;color:#f1f5ff;padding:.1rem 0;'>{month_start.strftime('%B %Y')}</div>",
            unsafe_allow_html=True,
        )
    with right:
        st.button("▶", key="track_next_month", on_click=_set_month, args=(1,))

    if month_events:
        event_day, event = month_events[0]
        st.markdown(
            f"<div class='track-event-strip'>✦ {event_day.strftime('%b')} {event_day.day} · {html.escape(event['title'])}</div>",
            unsafe_allow_html=True,
        )
    else:
        st.caption("Daily moon phases and your private calendar.")

    with st.expander(f"✎ Add a private note · {selected.strftime('%b')} {selected.day}", expanded=False):
        _render_selected_day(selected, entries.get(selected.isoformat(), {}))

    st.markdown(f'<div class="track-grid">{_month_grid_html(month_start, entries)}</div>', unsafe_allow_html=True)
    st.markdown(
        "<div class='track-legend'>"
        "<span>✦ lunar event</span><span style='color:#bc8cff'>• private note</span>"
        "<span style='color:#f05d6e'>• cycle start</span><span style='color:#63d99d'>• cycle end</span>"
        "</div>",
        unsafe_allow_html=True,
    )
