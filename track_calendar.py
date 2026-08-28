"""Phone-first lunar Track calendar with owner-only personal entries.

The public astronomical layer is deliberately separate from personal notes and
observed cycle markers. All persistence uses the server-only Supabase adapter.
"""

from __future__ import annotations

import calendar as calendar_module
import html
import sqlite3

import ephem
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any

import streamlit as st

import cosmic_cards
import supabase_store

TRACK_MODULE_VERSION = "upcoming_events_v1"
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
        "title": "Deep Partial Lunar Eclipse · Full Moon",
        "kind": "lunar_eclipse",
        "utc": "20260828T041300Z",
        "source": "NASA eclipse catalog · UT",
    },
}

# Selected annual events are limited to high-interest public skywatching dates.
# Their public dates/descriptions are taken from NASA's 2026 Watch the Skies
# calendar; viewing conditions and exact clock times still depend on location.
NOTABLE_ASTRONOMICAL_EVENTS: tuple[dict[str, str], ...] = (
    {
        "date": "2026-08-28",
        "date_label": "Aug 27–28",
        "title": "Deep Partial Lunar Eclipse · Full Moon",
        "kind": "lunar_eclipse",
        "icon": "🌕",
        "eyebrow": "ECLIPSE · FULL MOON · BLOOD MOON",
        "detail": "The Full Moon passes deep through Earth’s umbra. At greatest eclipse, 96.3% of the lunar disk is in the dark central shadow and may appear copper-red.",
        "timing": "Partial phase begins 10:34 p.m. EDT Aug. 27 · greatest eclipse 12:13 a.m. EDT Aug. 28 · 4:13 UTC.",
        "source": "NASA eclipse guidance · visibility varies by location",
    },
    {
        "date": "2026-09-23",
        "date_label": "Sep 23",
        "title": "September Equinox",
        "kind": "seasonal",
        "icon": "🍂",
        "eyebrow": "SEASONAL MARKER",
        "detail": "The Sun crosses the celestial equator, marking the September equinox.",
        "timing": "Exact timing depends on the observer’s timezone.",
        "source": "NASA 2026 sky-events calendar",
    },
    {
        "date": "2026-09-25",
        "date_label": "Sep 25",
        "title": "Neptune at Opposition",
        "kind": "planetary",
        "icon": "🔵",
        "eyebrow": "PLANETARY OBSERVING",
        "detail": "Neptune is opposite the Sun in Earth’s sky, placing it at its closest and brightest annual viewing period.",
        "timing": "A telescope and dark sky are generally needed to observe Neptune.",
        "source": "NASA 2026 sky-events calendar",
    },
    {
        "date": "2026-10-04",
        "date_label": "Oct 4",
        "title": "Saturn at Opposition",
        "kind": "planetary",
        "icon": "🪐",
        "eyebrow": "PLANETARY OBSERVING",
        "detail": "Saturn reaches opposition, rising around sunset and remaining visible much of the night.",
        "timing": "Best viewed after dark; binoculars or a telescope reveal more detail.",
        "source": "NASA 2026 sky-events calendar",
    },
    {
        "date": "2026-10-21",
        "date_label": "Oct 21–22",
        "title": "Orionids Meteor Shower Peak",
        "kind": "meteor",
        "icon": "☄️",
        "eyebrow": "METEOR SHOWER",
        "detail": "Fast meteors from Halley’s Comet debris peak overnight, with roughly 10–20 meteors per hour under dark skies.",
        "timing": "Look after midnight through dawn; clear, dark skies improve viewing.",
        "source": "NASA Orionids guidance",
    },
    {
        "date": "2026-11-17",
        "date_label": "Nov 16–17",
        "title": "Leonids Meteor Shower Peak",
        "kind": "meteor",
        "icon": "☄️",
        "eyebrow": "METEOR SHOWER",
        "detail": "The Leonids peak overnight as Earth moves through material shed by Comet Tempel–Tuttle.",
        "timing": "Look after midnight through dawn from a dark location.",
        "source": "NASA Leonids guidance",
    },
    {
        "date": "2026-11-24",
        "date_label": "Nov 24",
        "title": "Supermoon",
        "kind": "lunar",
        "icon": "🌕",
        "eyebrow": "LUNAR HIGHLIGHT",
        "detail": "A Full Moon occurs near perigee, its closest approach to Earth, and can appear larger and brighter than usual.",
        "timing": "Moonrise timing varies by location.",
        "source": "NASA 2026 sky-events calendar",
    },
    {
        "date": "2026-12-13",
        "date_label": "Dec 13–14",
        "title": "Geminids Meteor Shower Peak",
        "kind": "meteor",
        "icon": "☄️",
        "eyebrow": "METEOR SHOWER",
        "detail": "The Geminids, one of the year’s strongest annual meteor displays, peak overnight.",
        "timing": "Observe after midnight from a dark, open location.",
        "source": "NASA 2026 sky-events calendar",
    },
)


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


def _next_lunar_phase_events(start_day: date, limit: int = 5) -> list[dict[str, str]]:
    """Return the next primary lunar phases as public UTC events."""
    phase_functions = (
        ("New Moon", "🌑", ephem.next_new_moon),
        ("First Quarter", "🌓", ephem.next_first_quarter_moon),
        ("Full Moon", "🌕", ephem.next_full_moon),
        ("Last Quarter", "🌗", ephem.next_last_quarter_moon),
    )
    cursor = ephem.Date(datetime.combine(start_day, time.min, tzinfo=timezone.utc).replace(tzinfo=None))
    events: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for _ in range(limit):
        candidates = []
        for title, icon, phase_function in phase_functions:
            moment = phase_function(cursor)
            moment_utc = moment.datetime().replace(tzinfo=timezone.utc)
            candidates.append((moment_utc, title, icon, moment))
        moment_utc, title, icon, moment = min(candidates, key=lambda item: item[0])
        event_day = moment_utc.date()
        identifier = (event_day.isoformat(), title)
        if identifier not in seen:
            seen.add(identifier)
            events.append(
                {
                    "date": event_day.isoformat(),
                    "date_label": moment_utc.strftime("%b %d"),
                    "title": title,
                    "kind": "lunar_phase",
                    "icon": icon,
                    "eyebrow": "LUNAR PHASE",
                    "detail": f"{title} occurs at {moment_utc.strftime('%H:%M')} UTC.",
                    "timing": "Local clock time and Moon visibility vary by location.",
                    "source": "LunaTicK astronomical calculation · UTC",
                }
            )
        cursor = moment + ephem.minute
    return events


def _upcoming_event_feed(today: date, limit: int = 14) -> list[dict[str, str]]:
    """Merge lunar-phase calculations with curated notable 2026 public events."""
    static_events = [event for event in NOTABLE_ASTRONOMICAL_EVENTS if event["date"] >= today.isoformat()]
    phase_events = _next_lunar_phase_events(today, limit=6)
    eclipse_days = {event["date"] for event in static_events if event["kind"] == "lunar_eclipse"}
    # The eclipse detail card already includes its coincident Full Moon.
    merged = static_events + [
        event for event in phase_events
        if not (event["title"] == "Full Moon" and event["date"] in eclipse_days)
    ]
    return sorted(merged, key=lambda event: (event["date"], event["title"]))[:limit]


def _render_upcoming_events(today: date) -> None:
    events = _upcoming_event_feed(today)
    st.markdown("<div class='track-upcoming-title'>✦ Upcoming Events:</div>", unsafe_allow_html=True)
    if not events:
        st.caption("No curated skywatching events are currently available in this calendar window.")
        return
    event_cards = []
    for event in events:
        event_cards.append(
            f"""<article class='track-upcoming-card track-upcoming-card--{html.escape(event['kind'])}'>
              <div class='track-upcoming-date'>{html.escape(event['date_label'])}</div>
              <div class='track-upcoming-icon' aria-hidden='true'>{html.escape(event['icon'])}</div>
              <div class='track-upcoming-copy'>
                <div class='track-upcoming-eyebrow'>{html.escape(event['eyebrow'])}</div>
                <div class='track-upcoming-name'>{html.escape(event['title'])}</div>
                <div class='track-upcoming-detail'>{html.escape(event['detail'])}</div>
                <div class='track-upcoming-timing'>{html.escape(event['timing'])}</div>
                <div class='track-upcoming-source'>{html.escape(event['source'])}</div>
              </div>
            </article>"""
        )
    st.markdown("<section class='track-upcoming-list'>" + "".join(event_cards) + "</section>", unsafe_allow_html=True)


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
        .st-key-track-month-nav [data-testid="stHorizontalBlock"] { display:flex!important; flex-direction:row!important; flex-wrap:nowrap!important; align-items:center!important; gap:.2rem!important; width:100%!important; }
        .st-key-track-month-nav [data-testid="stColumn"] { min-width:0!important; }
        .st-key-track-month-nav .st-key-track_previous_month, .st-key-track-month-nav .st-key-track_next_month { flex:0 0 1.72rem!important; width:1.72rem!important; }
        .st-key-track_previous_month button, .st-key-track_next_month button { min-height:1.72rem!important; height:1.72rem!important; min-width:1.72rem!important; width:1.72rem!important; padding:0!important; border-radius:.48rem!important; font-size:.66rem!important; line-height:1!important; }
        .st-key-track-calendar-footer { margin:.42rem 0 .08rem; }
        .st-key-track-calendar-footer [data-testid="stHorizontalBlock"] { display:flex!important; flex-direction:row!important; flex-wrap:nowrap!important; align-items:center!important; gap:.35rem!important; width:100%!important; }
        .st-key-track-calendar-footer [data-testid="stColumn"] { min-width:0!important; }
        .track-legend { display:flex; flex-wrap:wrap; gap:.42rem .78rem; color:#9ba9bf; font-size:.62rem; margin:0; }
        .st-key-track-private-event-control button { min-height:1.78rem!important; padding:.24rem .38rem!important; border:1px solid rgba(188,140,255,.82)!important; border-radius:.5rem!important; background:linear-gradient(135deg,rgba(85,54,139,.74),rgba(32,22,65,.94))!important; box-shadow:0 0 10px rgba(188,140,255,.16)!important; color:#f0e6ff!important; font-size:.57rem!important; font-weight:700!important; line-height:1!important; white-space:nowrap!important; }
        .st-key-track-private-event-control button:hover { border-color:#e0c6ff!important; background:linear-gradient(135deg,rgba(111,72,174,.80),rgba(47,30,88,.98))!important; }
        .track-upcoming-title { margin:1rem 0 .48rem; color:#f0e6ff; font-family:Orbitron,sans-serif; font-size:.72rem; font-weight:700; letter-spacing:1.5px; text-transform:uppercase; }
        .track-upcoming-list { display:grid; gap:.5rem; margin:0 0 1rem; }
        .track-upcoming-card { display:grid; grid-template-columns:3.25rem 2.15rem minmax(0,1fr); gap:.55rem; align-items:start; border:1px solid rgba(188,140,255,.38); border-radius:10px; background:linear-gradient(145deg,rgba(31,22,56,.82),rgba(10,15,29,.95)); box-shadow:inset 0 0 17px rgba(188,140,255,.07); padding:.62rem .68rem; }
        .track-upcoming-card--lunar_eclipse { border-color:rgba(255,211,110,.78); background:linear-gradient(145deg,rgba(85,49,27,.48),rgba(27,16,28,.94)); box-shadow:inset 0 0 18px rgba(255,173,72,.11),0 0 13px rgba(255,181,79,.08); }
        .track-upcoming-date { color:#d8c7ff; font-family:Orbitron,sans-serif; font-size:.6rem; font-weight:700; line-height:1.25; padding-top:.14rem; }
        .track-upcoming-card--lunar_eclipse .track-upcoming-date { color:#ffe2a4; }
        .track-upcoming-icon { font-size:1.36rem; line-height:1.12; text-align:center; }
        .track-upcoming-copy { min-width:0; }
        .track-upcoming-eyebrow { color:#a9b9dd; font-size:.53rem; font-weight:700; letter-spacing:.85px; line-height:1.2; }
        .track-upcoming-card--lunar_eclipse .track-upcoming-eyebrow { color:#ffd98b; }
        .track-upcoming-name { color:#f2f5ff; font-size:.82rem; font-weight:750; line-height:1.24; margin:.08rem 0 .18rem; }
        .track-upcoming-detail { color:#c5cfdf; font-size:.68rem; line-height:1.38; }
        .track-upcoming-timing { color:#dfe8ff; font-size:.63rem; line-height:1.35; margin-top:.25rem; }
        .track-upcoming-source { color:#8796b2; font-size:.56rem; line-height:1.25; margin-top:.2rem; }
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

    selected = _selected_day(month_start)
    entries = list_private_entries(month_start, next_month)

    st.markdown(
        "<div style=\"font-family:Orbitron,sans-serif;font-size:.76rem;letter-spacing:2.6px;color:#bc8cff;text-transform:uppercase;margin-bottom:.08rem;\">📅 Track</div>",
        unsafe_allow_html=True,
    )
    with st.container(key="track-month-nav"):
        left, center, right = st.columns([0.32, 2.1, 0.32], vertical_alignment="center")
        with left:
            st.button("◀", key="track_previous_month", on_click=_set_month, args=(-1,))
        with center:
            st.markdown(
                f"<div style='text-align:center;font-family:Orbitron,sans-serif;font-size:.72rem;color:#f1f5ff;padding:.1rem 0;white-space:nowrap;'>{month_start.strftime('%B %Y')}</div>",
                unsafe_allow_html=True,
            )
        with right:
            st.button("▶", key="track_next_month", on_click=_set_month, args=(1,))

    st.markdown(f'<div class="track-grid">{_month_grid_html(month_start, entries)}</div>', unsafe_allow_html=True)
    with st.container(key="track-calendar-footer"):
        legend_column, private_event_column = st.columns([4.2, 1.35], vertical_alignment="center")
        with legend_column:
            st.markdown(
                "<div class='track-legend'>"
                "<span>✦ lunar event</span><span style='color:#bc8cff'>• private note</span>"
                "<span style='color:#f05d6e'>• cycle start</span><span style='color:#63d99d'>• cycle end</span>"
                "</div>",
                unsafe_allow_html=True,
            )
        with private_event_column:
            with st.container(key="track-private-event-control"):
                with st.popover("✎ Private event", help="Add or edit a private note for the selected date", use_container_width=True):
                    _render_selected_day(selected, entries.get(selected.isoformat(), {}))
    _render_upcoming_events(today)
