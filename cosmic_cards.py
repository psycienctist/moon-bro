"""LunaTicK Cosmic Cards: private birth inputs, share-safe collectible cards, and friend trades.

The active card is deliberately limited to six transparent fields. It is a visual
collectible, not a diagnostic or a substitute for professional astrology or
Human Design analysis.
"""

from __future__ import annotations

import hashlib
import html
import math
import sqlite3
import requests
import swisseph as swe
from timezonefinder import TimezoneFinder
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from collections import Counter
from datetime import date, datetime, time as dtime, timedelta, timezone

import ephem
import streamlit as st

import auth
import direct_messages
import supabase_store


def _cache_data(*args, **kwargs):
    cache = getattr(st, "cache_data", None)
    if cache is not None:
        return cache(*args, **kwargs)
    return lambda function: function


DB = "lunatick.db"
GEOCODER_URL = "https://nominatim.openstreetmap.org/search"
GEOCODER_USER_AGENT = "LunaTicK/1.0 (birth-location lookup; contact repository maintainer)"
_TIMEZONE_FINDER = TimezoneFinder()
# Bumped whenever a complete Cosmic Card module reload is required after a
# warm-worker deployment, not merely a check for an older helper symbol.
CARD_MODULE_VERSION = "birth_chart_svg_v2"


CARD_PROFILE_DEFAULTS = {
    "display_name": "Moon Wanderer",
    "avatar": None,
    "birth_date": None,
    "birth_time": None,
    "birth_place": None,
    "lat": None,
    "lon": None,
    "utc_offset": None,
    "public_card_values_visible": True,
}

ZODIAC = [
    ("Aries", "♈"), ("Taurus", "♉"), ("Gemini", "♊"), ("Cancer", "♋"),
    ("Leo", "♌"), ("Virgo", "♍"), ("Libra", "♎"), ("Scorpio", "♏"),
    ("Sagittarius", "♐"), ("Capricorn", "♑"), ("Aquarius", "♒"), ("Pisces", "♓"),
]

ZODIAC_COLORS = {
    "Aries": "#ff6b6b", "Taurus": "#51cf66", "Gemini": "#ffd43b",
    "Cancer": "#ced4da", "Leo": "#ff922b", "Virgo": "#94d82d",
    "Libra": "#f783ac", "Scorpio": "#e03131", "Sagittarius": "#9775fa",
    "Capricorn": "#adb5bd", "Aquarius": "#4dabf7", "Pisces": "#66d9e8",
}

# This mapping is intentionally used only for the clearly labelled LunaTicK
# "Dominant Planet" card highlight; it is not a professional chart assessment.
SIGN_RULERS = {
    "Aries": ("Mars", "♂"), "Taurus": ("Venus", "♀"), "Gemini": ("Mercury", "☿"),
    "Cancer": ("Moon", "☾"), "Leo": ("Sun", "☉"), "Virgo": ("Mercury", "☿"),
    "Libra": ("Venus", "♀"), "Scorpio": ("Pluto", "♇"), "Sagittarius": ("Jupiter", "♃"),
    "Capricorn": ("Saturn", "♄"), "Aquarius": ("Uranus", "♅"), "Pisces": ("Neptune", "♆"),
}

TERM_EXPLANATIONS = {
    "sun": {
        "title": "Sun sign",
        "what": "The zodiac sector containing the Sun at your recorded birth moment.",
        "how": "LunaTicK calculates the Sun’s tropical ecliptic position from your saved birth date and time.",
        "note": "A correct local time and UTC offset improve time-specific results.",
    },
    "moon": {
        "title": "Moon sign",
        "what": "The zodiac sector containing the Moon at your recorded birth moment.",
        "how": "LunaTicK calculates the Moon’s tropical ecliptic position from your saved birth date and time.",
        "note": "A correct local time and UTC offset improve time-specific results.",
    },
    "rising": {
        "title": "Rising sign",
        "what": "The zodiac sector rising on the eastern horizon at your recorded birth moment and location.",
        "how": "LunaTicK combines your birth time, UTC offset, latitude, and longitude to calculate the Ascendant.",
        "note": "Coordinates and the historical timezone are resolved from a confirmed city or postal/ZIP-code result.",
    },
    "birth_phase": {
        "title": "Birth phase",
        "what": "The Moon’s illumination phase at your recorded birth moment.",
        "how": "LunaTicK derives a user-friendly phase band from the Sun–Moon elongation and lunar illumination.",
        "note": "The named phase is a display band, not an exact timestamp of a lunar-phase event.",
    },
    "full_moons": {
        "title": "Full Moons Lived",
        "what": "An approximate count of synodic lunar cycles since your recorded birth date.",
        "how": "LunaTicK divides elapsed days by the mean 29.530588-day synodic month.",
        "note": "It is an approximation, not a count of individual full moons you observed.",
    },
    "dominant": {
        "title": "Dominant Planet",
        "what": "A LunaTicK card highlight based on the sign rulers of the displayed Sun, Moon, and Rising signs.",
        "how": "Sun sign receives three weights; Moon and available Rising sign each receive two. The most frequent mapped ruler is shown.",
        "note": "This is a card-design heuristic, not a professional natal-chart determination.",
    },
}


def _using_supabase_backend() -> bool:
    """Return whether the approved Supabase card-storage path is active."""
    return supabase_store.data_backend_from_streamlit_secrets() == "supabase"


def _supabase() -> supabase_store.SupabaseStore:
    """Create the server-only Supabase adapter on demand."""
    return supabase_store.SupabaseStore(supabase_store.SupabaseSettings.from_streamlit_secrets())


def _resolve_auth_subject(user_reference: str) -> str:
    """Resolve old user-hash call sites to the immutable Auth0 subject."""
    reference = str(user_reference or "").strip()
    current_subject = str(st.session_state.get("auth_subject", "")).strip()
    current_hash = str(st.session_state.get("user_hash", "")).strip()
    if current_subject and reference == current_hash:
        return current_subject
    if reference:
        return reference
    if current_subject:
        return current_subject
    raise ValueError("A signed-in LunaTicK identity is required for Cosmic Cards.")


def sign_color(sign: str | None) -> str:
    return ZODIAC_COLORS.get(str(sign or ""), "#f0f6fc")


def colored_sign(symbol: str, name: str, extra: str = "") -> str:
    label = f"{symbol} {name}" if not extra else f"{symbol} {extra} {name}"
    return f'<span style="color:{sign_color(name)};font-weight:700;">{html.escape(label)}</span>'


def _sign_from_lon(lon_deg: float) -> tuple[str, str]:
    return ZODIAC[int((lon_deg % 360) / 30) % 12]


def _has_actual_coordinates(lat: object, lon: object) -> bool:
    """Require actual submitted coordinates; a place label must never imply 0, 0."""
    if lat is None or lon is None:
        return False
    try:
        return not (float(lat) == 0.0 and float(lon) == 0.0)
    except (TypeError, ValueError):
        return False


@_cache_data(ttl=86400, show_spinner=False)
def _geocode_place(query: str) -> list[dict]:
    """Resolve one explicit city/postal-code search; never run as autocomplete."""
    normalized = " ".join(str(query or "").split())
    if not normalized:
        return []
    response = requests.get(
        GEOCODER_URL,
        params={"q": normalized, "format": "jsonv2", "addressdetails": 1, "limit": 5},
        headers={"User-Agent": GEOCODER_USER_AGENT, "Accept-Language": "en"},
        timeout=10,
    )
    response.raise_for_status()
    results = []
    for item in response.json():
        try:
            lat = float(item["lat"])
            lon = float(item["lon"])
        except (KeyError, TypeError, ValueError):
            continue
        timezone_name = _TIMEZONE_FINDER.timezone_at(lng=lon, lat=lat)
        if timezone_name:
            results.append({
                "label": str(item.get("display_name") or normalized),
                "lat": lat,
                "lon": lon,
                "timezone": timezone_name,
            })
    return results


def _local_to_utc(
    birth_date: str,
    birth_time: str | None,
    utc_offset: float | None = None,
    timezone_name: str | None = None,
) -> datetime:
    """Convert local wall time using historical IANA rules when available."""
    parsed_date = date.fromisoformat(birth_date[:10])
    if birth_time:
        try:
            parts = birth_time.strip().split(":")
            local_time = dtime(int(parts[0]) % 24, int(parts[1]) % 60 if len(parts) > 1 else 0)
        except (TypeError, ValueError):
            local_time = dtime(12, 0)
    else:
        local_time = dtime(12, 0)
    naive = datetime.combine(parsed_date, local_time)
    if timezone_name:
        try:
            return naive.replace(tzinfo=ZoneInfo(timezone_name)).astimezone(timezone.utc)
        except (ZoneInfoNotFoundError, ValueError):
            pass
    offset = float(utc_offset) if utc_offset is not None else 0.0
    return (naive - timedelta(hours=offset)).replace(tzinfo=timezone.utc)


def _chart(dt_utc: datetime, lat: float | None = None, lon: float | None = None) -> dict:
    """Calculate card astronomy from a UTC instant and optional actual coordinates."""
    observer = ephem.Observer()
    if lat is not None and lon is not None:
        observer.lat = str(lat)
        observer.lon = str(lon)
    else:
        observer.lat = observer.lon = "0"
    observer.date = ephem.Date(dt_utc)

    moon = ephem.Moon(observer)
    sun = ephem.Sun(observer)
    elong = float(moon.elong)
    if elong < 0:
        elong += 2 * math.pi
    phase_fraction = elong / (2 * math.pi)
    phases = [
        (0.00, "New Moon", "🌑"), (0.07, "Waxing Crescent", "🌒"),
        (0.25, "First Quarter", "🌓"), (0.43, "Waxing Gibbous", "🌔"),
        (0.50, "Full Moon", "🌕"), (0.57, "Waning Gibbous", "🌖"),
        (0.75, "Last Quarter", "🌗"), (0.93, "Waning Crescent", "🌘"),
        (1.00, "New Moon", "🌑"),
    ]
    phase_name, phase_emoji = "New Moon", "🌑"
    for index in range(len(phases) - 1):
        if phases[index][0] <= phase_fraction < phases[index + 1][0]:
            phase_name, phase_emoji = phases[index][1], phases[index][2]
            break

    moon_lon = math.degrees(float(ephem.Ecliptic(moon).lon)) % 360
    sun_lon = math.degrees(float(ephem.Ecliptic(sun).lon)) % 360
    moon_sign, moon_symbol = _sign_from_lon(moon_lon)
    sun_sign, sun_symbol = _sign_from_lon(sun_lon)
    out = {
        "moon_sign": moon_sign,
        "moon_symbol": moon_symbol,
        "sun_sign": sun_sign,
        "sun_symbol": sun_symbol,
        "phase_name": phase_name,
        "phase_emoji": phase_emoji,
        "illum": moon.phase / 100.0,
        "moon_lon": moon_lon,
        "has_rising": False,
        "rising_sign": None,
        "rising_symbol": None,
    }

    if lat is not None and lon is not None:
        try:
            # Swiss Ephemeris is the reference calculation for the Ascendant.
            jd_ut = swe.julday(
                dt_utc.year, dt_utc.month, dt_utc.day,
                dt_utc.hour + dt_utc.minute / 60 + dt_utc.second / 3600,
            )
            _cusps, ascmc = swe.houses_ex(jd_ut, float(lat), float(lon), b"P", 0)
            ascendant = float(ascmc[0]) % 360.0
            rising_sign, rising_symbol = _sign_from_lon(ascendant)
            out.update({"has_rising": True, "rising_sign": rising_sign, "rising_symbol": rising_symbol})
        except (TypeError, ValueError, OverflowError, swe.Error):
            pass
    return out


def init_cards_db() -> None:
    """Initialize legacy local card tables only when SQLite is selected."""
    if _using_supabase_backend():
        return
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_profiles (
            user_hash TEXT PRIMARY KEY,
            display_name TEXT,
            birth_date TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    for column, kind in [
        ("birth_time", "TEXT"), ("birth_place", "TEXT"), ("lat", "REAL"),
        ("lon", "REAL"), ("utc_offset", "REAL"),
        ("public_card_values_visible", "INTEGER NOT NULL DEFAULT 1"),
    ]:
        try:
            cursor.execute(f"ALTER TABLE user_profiles ADD COLUMN {column} {kind}")
        except sqlite3.OperationalError:
            pass
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS card_trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_hash TEXT,
            receiver_hash TEXT,
            message TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            resolved_at TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def get_or_create_profile(user_hash: str) -> dict:
    """Read the active card inputs from the selected backend."""
    if _using_supabase_backend():
        subject = _resolve_auth_subject(user_hash)
        row = _supabase().get_profile_by_auth_subject(subject) or {}
        profile = dict(CARD_PROFILE_DEFAULTS)
        profile.update({field: row.get(field) for field in CARD_PROFILE_DEFAULTS})
        profile["auth_subject"] = subject
        profile["user_hash"] = row.get("user_hash") or str(user_hash)
        return profile

    init_cards_db()
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT display_name, birth_date, birth_time, birth_place, lat, lon, utc_offset,
               public_card_values_visible
        FROM user_profiles WHERE user_hash=?
    """, (user_hash,))
    row = cursor.fetchone()
    conn.close()
    profile = dict(CARD_PROFILE_DEFAULTS)
    if row:
        profile.update({
            "display_name": row[0], "birth_date": row[1], "birth_time": row[2],
            "birth_place": row[3], "lat": row[4], "lon": row[5], "utc_offset": row[6],
            "public_card_values_visible": bool(row[7]),
            "user_hash": user_hash,
        })
    return profile


def save_profile(
    user_hash: str,
    display_name: str,
    birth_date: str,
    birth_time: str | None = None,
    birth_place: str | None = None,
    lat: float | None = None,
    lon: float | None = None,
    utc_offset: float | None = None,
) -> None:
    """Save private birth-chart inputs to the selected backend."""
    if _using_supabase_backend():
        subject = _resolve_auth_subject(user_hash)
        _supabase().update_profile_fields(subject, {
            "display_name": display_name,
            "birth_date": birth_date,
            "birth_time": birth_time,
            "birth_place": birth_place,
            "lat": lat,
            "lon": lon,
            "utc_offset": utc_offset,
        })
        return

    init_cards_db()
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT birth_time, birth_place, lat, lon, utc_offset FROM user_profiles WHERE user_hash=?
    """, (user_hash,))
    prior = cursor.fetchone()
    if prior:
        birth_time = prior[0] if birth_time is None else birth_time
        birth_place = prior[1] if birth_place is None else birth_place
        lat = prior[2] if lat is None else lat
        lon = prior[3] if lon is None else lon
        utc_offset = prior[4] if utc_offset is None else utc_offset
    cursor.execute("""
        INSERT INTO user_profiles (user_hash, display_name, birth_date, birth_time, birth_place, lat, lon, utc_offset)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_hash) DO UPDATE SET
            display_name=excluded.display_name, birth_date=excluded.birth_date,
            birth_time=excluded.birth_time, birth_place=excluded.birth_place,
            lat=excluded.lat, lon=excluded.lon, utc_offset=excluded.utc_offset
    """, (user_hash, display_name, birth_date, birth_time, birth_place, lat, lon, utc_offset))
    conn.commit()
    conn.close()


def public_card_values_visible(user_hash: str) -> bool:
    """Return the owner's default-on public Cosmic Card value visibility choice."""
    return bool(get_or_create_profile(user_hash).get("public_card_values_visible", True))


def set_public_card_values_visible(user_hash: str, visible: bool) -> None:
    """Persist the owner's value-display choice without changing card presence."""
    if _using_supabase_backend():
        _supabase().update_profile_fields(
            _resolve_auth_subject(user_hash), {"public_card_values_visible": bool(visible)}
        )
        return
    init_cards_db()
    conn = sqlite3.connect(DB)
    conn.execute(
        "UPDATE user_profiles SET public_card_values_visible=? WHERE user_hash=?",
        (1 if visible else 0, user_hash),
    )
    conn.commit()
    conn.close()


def _dominant_planet(sun: str, moon: str, rising: str | None) -> dict:
    weights: list[str] = []
    for sign, weight in ((sun, 3), (moon, 2), (rising, 2)):
        if sign and sign in SIGN_RULERS:
            weights.extend([SIGN_RULERS[sign][0]] * weight)
    if not weights:
        return {"name": "Sun", "symbol": "☉"}
    name = Counter(weights).most_common(1)[0][0]
    symbol = next((symbol for ruler, symbol in SIGN_RULERS.values() if ruler == name), "✦")
    return {"name": name, "symbol": symbol}


def _full_moons_lived(birth_date: str) -> int:
    try:
        born = datetime.combine(date.fromisoformat(birth_date[:10]), dtime(0, 0)).replace(tzinfo=timezone.utc)
        return max(0, int((datetime.now(timezone.utc) - born).days / 29.530588))
    except (TypeError, ValueError):
        return 0


def _timezone_for_coordinates(lat: float | None, lon: float | None) -> str | None:
    if lat is None or lon is None:
        return None
    try:
        return _TIMEZONE_FINDER.timezone_at(lng=float(lon), lat=float(lat))
    except (TypeError, ValueError):
        return None


def build_card(user_hash: str) -> dict | None:
    """Build the private owner card; callers must not render private inputs for contacts."""
    profile = get_or_create_profile(user_hash)
    if not profile.get("birth_date"):
        return None
    try:
        has_coordinates = _has_actual_coordinates(profile.get("lat"), profile.get("lon"))
        natal = _chart(
            _local_to_utc(
                profile["birth_date"],
                profile.get("birth_time"),
                profile.get("utc_offset"),
                _timezone_for_coordinates(profile.get("lat"), profile.get("lon")),
            ),
            float(profile["lat"]) if has_coordinates else None,
            float(profile["lon"]) if has_coordinates else None,
        )
        rising = natal.get("rising_sign") if natal.get("has_rising") else None
        return {
            "user_hash": profile.get("user_hash") or user_hash,
            "profile_auth_subject": profile.get("auth_subject"),
            "display_name": profile.get("display_name") or "Moon Wanderer",
            "avatar": profile.get("avatar"),
            "birth_date": profile["birth_date"],
            "birth_time": profile.get("birth_time"),
            "birth_place": profile.get("birth_place"),
            "natal": natal,
            "dominant": _dominant_planet(natal["sun_sign"], natal["moon_sign"], rising),
            "full_moons_lived": _full_moons_lived(profile["birth_date"]),
        }
    except (TypeError, ValueError, OverflowError):
        return None


def _safe_card_key(value: object) -> str:
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()[:16]


def shareable_card(card: dict) -> dict:
    """Return only approved public identity and derived card values for collection UI."""
    return {
        "card_key": _safe_card_key(card.get("profile_auth_subject") or card.get("user_hash")),
        "display_name": card.get("display_name") or "Moon Wanderer",
        "avatar": card.get("avatar"),
        "natal": dict(card["natal"]),
        "dominant": dict(card.get("dominant") or {"name": "Sun", "symbol": "☉"}),
        "full_moons_lived": int(card.get("full_moons_lived") or 0),
    }


def build_friend_card(viewer_reference: str, friend_auth_subject: str) -> dict | None:
    """Build a share-safe card only when the counterpart is an accepted contact."""
    viewer_subject = _resolve_auth_subject(viewer_reference)
    if str(friend_auth_subject) not in set(friends_of(viewer_subject)):
        return None
    card = build_card(str(friend_auth_subject))
    return shareable_card(card) if card else None


def _public_card_shell(source: dict, state: str) -> dict:
    """Return a visible public card shell with no derived personal values."""
    return {
        "card_key": _safe_card_key(source.get("auth_subject")),
        "display_name": source.get("display_name") or "Moon Wanderer",
        "avatar": source.get("avatar") or "✦",
        "public_card_state": state,
    }


def build_public_card_by_username(username: str) -> dict | None:
    """Build a visible public card with values shown only when its owner permits.

    Private birth inputs are resolved server-side and discarded before this
    function returns. A profile without inputs receives a base card; a member
    who hides values receives a privacy-state card with the same visual presence.
    """
    if not _using_supabase_backend():
        return None
    source = _supabase().get_card_profile_by_username_server_only(username)
    subject = str((source or {}).get("auth_subject") or "").strip()
    if not subject:
        return None
    if not source.get("birth_date"):
        return _public_card_shell(source, "awaiting")
    if not bool(source.get("public_card_values_visible", True)):
        return _public_card_shell(source, "private")
    card = build_card(subject)
    return shareable_card(card) if card else _public_card_shell(source, "awaiting")


def list_users_with_cards(exclude_hash: str) -> list[dict]:
    """Return derived discovery summaries for people eligible to receive a card trade."""
    if _using_supabase_backend():
        current_subject = _resolve_auth_subject(exclude_hash)
        out: list[dict] = []
        for profile in _supabase().list_card_profiles(current_subject):
            card = build_card(profile.get("auth_subject"))
            if card:
                out.append(shareable_card(card) | {"profile_auth_subject": profile.get("auth_subject")})
        return out

    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT user_hash FROM user_profiles WHERE birth_date IS NOT NULL AND user_hash != ?
    """, (exclude_hash,))
    rows = cursor.fetchall()
    conn.close()
    return [shareable_card(card) | {"profile_auth_subject": row[0]} for row in rows if (card := build_card(row[0]))]


def send_trade(sender: str, receiver: str, message: str = "") -> tuple[bool, str]:
    if _using_supabase_backend():
        sender_subject = _resolve_auth_subject(sender)
        receiver_subject = _resolve_auth_subject(receiver)
        if sender_subject == receiver_subject:
            return False, "You cannot send a card trade to yourself."
        store = _supabase()
        if store.has_pending_card_trade(sender_subject, receiver_subject):
            return False, "Already have a pending card trade with this person."
        store.create_card_trade(sender_subject, receiver_subject, message)
        return True, "Card trade sent!"

    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id FROM card_trades WHERE sender_hash=? AND receiver_hash=? AND status='pending'
    """, (sender, receiver))
    if cursor.fetchone():
        conn.close()
        return False, "Already have a pending card trade with this person."
    cursor.execute("""
        INSERT INTO card_trades (sender_hash, receiver_hash, message, status)
        VALUES (?, ?, ?, 'pending')
    """, (sender, receiver, message.strip() or None))
    conn.commit()
    conn.close()
    return True, "Card trade sent!"


def list_trades(user_hash: str, direction: str = "all") -> list[dict]:
    if _using_supabase_backend():
        return [
            {
                "id": row["id"], "sender": row["sender_auth_subject"],
                "receiver": row["receiver_auth_subject"], "message": row.get("message"),
                "status": row["status"], "created_at": row.get("created_at"),
            }
            for row in _supabase().list_card_trades(_resolve_auth_subject(user_hash), direction)
        ]

    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    if direction == "incoming":
        cursor.execute("""SELECT id, sender_hash, receiver_hash, message, status, created_at
            FROM card_trades WHERE receiver_hash=? ORDER BY created_at DESC""", (user_hash,))
    elif direction == "outgoing":
        cursor.execute("""SELECT id, sender_hash, receiver_hash, message, status, created_at
            FROM card_trades WHERE sender_hash=? ORDER BY created_at DESC""", (user_hash,))
    elif direction == "all":
        cursor.execute("""SELECT id, sender_hash, receiver_hash, message, status, created_at
            FROM card_trades WHERE sender_hash=? OR receiver_hash=? ORDER BY created_at DESC""", (user_hash, user_hash))
    else:
        conn.close()
        raise ValueError("Card-trade direction must be incoming, outgoing, or all.")
    rows = cursor.fetchall()
    conn.close()
    return [{"id": row[0], "sender": row[1], "receiver": row[2], "message": row[3], "status": row[4], "created_at": row[5]} for row in rows]


def resolve_trade(trade_id: int, user_hash: str, accept: bool) -> bool:
    if _using_supabase_backend():
        return _supabase().resolve_card_trade(trade_id, _resolve_auth_subject(user_hash), accept)

    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    cursor.execute("SELECT receiver_hash, status FROM card_trades WHERE id=?", (trade_id,))
    row = cursor.fetchone()
    if not row or row[0] != user_hash or row[1] != "pending":
        conn.close()
        return False
    cursor.execute("""UPDATE card_trades SET status=?, resolved_at=CURRENT_TIMESTAMP WHERE id=?""", ("accepted" if accept else "declined", trade_id))
    conn.commit()
    conn.close()
    return True


def friends_of(user_hash: str) -> list[str]:
    if _using_supabase_backend():
        return _supabase().list_accepted_card_contacts(_resolve_auth_subject(user_hash))

    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    cursor.execute("""SELECT sender_hash, receiver_hash FROM card_trades
        WHERE status='accepted' AND (sender_hash=? OR receiver_hash=?)""", (user_hash, user_hash))
    contacts: set[str] = set()
    for sender, receiver in cursor.fetchall():
        contacts.add(receiver if sender == user_hash else sender)
    conn.close()
    return sorted(contacts)


def _render_card_css() -> None:
    st.html("""
    <style>
    div[class*="st-key-cosmic_card_"] {
      background:linear-gradient(155deg,#090d18 0%,#11142b 48%,#0b203d 100%);
      border-radius:22px; padding:1rem 1rem 1.15rem; margin:0.7rem 0 1rem;
      box-shadow:inset 0 0 36px rgba(0,0,0,.36),0 0 25px rgba(88,166,255,.12);
      position:relative; overflow:hidden;
    }
    div[class*="st-key-cosmic_card_"]::before {
      content:""; position:absolute; inset:0; pointer-events:none; opacity:.38;
      background-image:radial-gradient(circle at 12% 18%,rgba(255,255,255,.48) 0 1px,transparent 1.4px),radial-gradient(circle at 76% 28%,rgba(88,166,255,.45) 0 1px,transparent 1.4px),radial-gradient(circle at 44% 72%,rgba(188,140,255,.36) 0 1px,transparent 1.4px);
      background-size:82px 91px,121px 109px,151px 137px;
    }
    /* Keep the two three-tile rows intact even on narrow phones. Streamlit
       otherwise collapses st.columns into a vertical list at mobile width. */
    div[class*="st-key-cosmic_card_"] [data-testid="stHorizontalBlock"] {
      flex-flow:row nowrap !important; gap:.42rem !important;
    }
    div[class*="st-key-cosmic_card_"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
      min-width:0 !important; width:calc((100% - .84rem) / 3) !important; flex:1 1 0 !important;
    }
    .cosmic-card-grid { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:.46rem; position:relative; z-index:1; }
    .cosmic-card-tile { min-height:102px; padding:.52rem .2rem .42rem; border:1.5px solid #7b8496; border-radius:13px; background:linear-gradient(145deg,rgba(27,34,61,.86),rgba(11,16,33,.88)); box-shadow:inset 0 0 18px rgba(255,255,255,.025); display:flex; flex-direction:column; align-items:center; justify-content:center; text-align:center; text-decoration:none!important; color:#edf5ff!important; overflow:hidden; }
    .cosmic-card-tile:hover { background:linear-gradient(145deg,rgba(42,59,99,.92),rgba(13,24,48,.94)); transform:translateY(-1px); }
    .cosmic-card-tile-label { font-size:.58rem; font-weight:700; letter-spacing:1.35px; color:#a9b3c6; line-height:1.15; text-transform:uppercase; }
    .cosmic-card-tile-symbol { font-size:1.55rem; line-height:1.05; margin:.22rem 0 .16rem; }
    .cosmic-card-tile-value { font-size:1rem; font-weight:800; line-height:1.08; letter-spacing:-.02em; overflow-wrap:anywhere; }
    .cosmic-card-tile--sun { border-color:#d8dee9; box-shadow:inset 0 0 18px rgba(216,222,233,.16),0 0 11px rgba(216,222,233,.18); }.cosmic-card-tile--sun .cosmic-card-tile-value { color:#d8dee9; }
    .cosmic-card-tile--moon { border-color:#66a8ff; box-shadow:inset 0 0 18px rgba(102,168,255,.16),0 0 11px rgba(102,168,255,.18); }.cosmic-card-tile--moon .cosmic-card-tile-value { color:#66a8ff; }
    .cosmic-card-tile--rising { border-color:#f7d25c; box-shadow:inset 0 0 18px rgba(247,210,92,.16),0 0 11px rgba(247,210,92,.18); }.cosmic-card-tile--rising .cosmic-card-tile-value { color:#f7d25c; }
    .cosmic-card-tile--birth_phase { border-color:#c5a6ff; box-shadow:inset 0 0 18px rgba(197,166,255,.14),0 0 11px rgba(197,166,255,.15); }.cosmic-card-tile--birth_phase .cosmic-card-tile-value { color:#c5a6ff; }
    .cosmic-card-tile--full_moons { border-color:#9c7bff; box-shadow:inset 0 0 18px rgba(156,123,255,.14),0 0 11px rgba(156,123,255,.15); }.cosmic-card-tile--full_moons .cosmic-card-tile-value { color:#9c7bff; }
    .cosmic-card-tile--dominant { border-color:#73dfbf; box-shadow:inset 0 0 18px rgba(115,223,191,.14),0 0 11px rgba(115,223,191,.15); }.cosmic-card-tile--dominant .cosmic-card-tile-value { color:#73dfbf; }
    .lunatick-birth-chart { max-width:760px; margin:.35rem auto .8rem; border:1px solid rgba(188,140,255,.42); border-radius:20px; background:radial-gradient(circle at center,rgba(54,31,96,.58),rgba(5,8,17,.95) 70%); overflow:hidden; box-shadow:0 0 28px rgba(188,140,255,.16),inset 0 0 36px rgba(96,165,250,.09); }
    .lunatick-birth-chart svg { display:block; width:100%; height:auto; }
    .astro-positions-table { margin:.45rem 0 .85rem; padding:.45rem; border:1px solid rgba(188,140,255,.32); border-radius:14px; background:linear-gradient(145deg,rgba(21,23,50,.88),rgba(8,13,27,.92)); box-shadow:inset 0 0 26px rgba(188,140,255,.06); }
    .astro-positions-table-row { display:grid; grid-template-columns:1fr 1fr; gap:.45rem; }
    .astro-position-row { margin:.2rem 0; padding:.58rem .68rem; min-height:3.35rem; border:1px solid rgba(188,140,255,.24); border-radius:10px; background:rgba(18,22,42,.74); color:#f0f6fc; line-height:1.35; }
    .astro-reading-card { margin:.65rem 0 .9rem; padding:.75rem .85rem; border:1px solid rgba(188,140,255,.35); border-radius:14px; background:linear-gradient(145deg,rgba(31,24,62,.78),rgba(9,14,28,.9)); box-shadow:inset 0 0 22px rgba(188,140,255,.08); }
    .astro-reading-kicker { color:#bc8cff; font-size:.62rem; font-weight:800; letter-spacing:1.6px; margin-bottom:.35rem; }
    .astro-reading-text { color:#f0f6fc; font-size:1rem; line-height:1.65; letter-spacing:.01em; }
    @media (max-width: 600px) {
      div[class*="st-key-cosmic_card_"] { padding:.62rem .58rem .68rem !important; margin:.28rem 0 .52rem !important; border-radius:18px !important; }
      .cosmic-card-grid { gap:.35rem; }
      .cosmic-card-tile { min-height:82px; padding:.35rem .08rem .3rem; border-radius:11px; }
      .cosmic-card-tile-label { font-size:.48rem; letter-spacing:.9px; }
      .cosmic-card-tile-symbol { font-size:1.25rem; margin:.16rem 0 .1rem; }
      .cosmic-card-tile-value { font-size:.78rem; line-height:1.04; }
    }
    </style>
    """)


def _detail_href(card_key: str, tile_key: str) -> str:
    """Create a non-sensitive in-app route for a card tile explanation."""
    return f"?cosmic_detail={card_key}__{tile_key}"


def _card_tile(card_key: str, tile_key: str, icon: str, label: str, value: str, color: str) -> str:
    """Render one compact visual card tile; all strings are escaped before HTML output."""
    return f'''<a class="cosmic-card-tile cosmic-card-tile--{html.escape(tile_key)}" href="{_detail_href(card_key, tile_key)}">
      <span class="cosmic-card-tile-label">{html.escape(label)}</span>
      <span class="cosmic-card-tile-symbol">{html.escape(icon)}</span>
      <span class="cosmic-card-tile-value">{html.escape(value)}</span>
    </a>'''


def _render_detail_panel(card_key: str) -> None:
    token = st.query_params.get("cosmic_detail")
    prefix = f"{card_key}__"
    if not isinstance(token, str) or not token.startswith(prefix):
        return
    selected = token.removeprefix(prefix)
    detail = TERM_EXPLANATIONS.get(selected)
    if not detail:
        return
    st.markdown("##### ✦ " + detail["title"])
    st.write(detail["what"])
    st.caption("**How LunaTicK gets it:** " + detail["how"])
    st.caption("**Note on precision:** " + detail["note"])
    if st.button("Close explanation", key=f"close_card_detail_{card_key}"):
        st.query_params.pop("cosmic_detail", None)
        st.rerun()


def _render_public_card_state(card: dict, key_prefix: str) -> None:
    """Render a compact public card presence without any derived personal values."""
    _render_card_css()
    safe_key = f"{key_prefix}_{card.get('card_key') or _safe_card_key(card.get('display_name'))}"
    is_private = card.get("public_card_state") == "private"
    title = "COSMIC DETAILS PRIVATE" if is_private else "COSMIC CARD READY"
    note = (
        "This member keeps their personal cosmic values private."
        if is_private
        else "Cosmic details appear here when this member activates their card."
    )
    value = "Private" if is_private else "Awaiting"
    icon = "🔒" if is_private else "✦"
    tiles = "".join(
        f'''<div class="cosmic-card-tile cosmic-card-tile--private">
          <span class="cosmic-card-tile-label">{label}</span>
          <span class="cosmic-card-tile-symbol">{icon}</span>
          <span class="cosmic-card-tile-value">{value}</span>
        </div>'''
        for label in ("Sun", "Moon", "Rising", "Birth Phase", "Full Moons", "Dominant")
    )
    with st.container(key=f"cosmic_card_{safe_key}", border=False):
        st.html(f"""
        <style>
        .st-key-cosmic_card_{safe_key}{{border:2px solid #bc8cff!important;padding:.45rem .48rem .5rem!important;margin:.42rem 0 .28rem!important;}}
        .st-key-cosmic_card_{safe_key} .cosmic-card-tile{{min-height:66px!important;padding:.25rem .06rem .2rem!important;border-color:#8d7aa8!important;}}
        .st-key-cosmic_card_{safe_key} .cosmic-card-tile-label{{font-size:.44rem!important;letter-spacing:.7px!important;}}
        .st-key-cosmic_card_{safe_key} .cosmic-card-tile-symbol{{font-size:1.08rem!important;margin:.1rem 0 .06rem!important;}}
        .st-key-cosmic_card_{safe_key} .cosmic-card-tile-value{{font-size:.70rem!important;line-height:1.02!important;color:#c5a6ff!important;}}
        </style>
        <div style="display:flex;justify-content:space-between;align-items:center;position:relative;z-index:1;margin:.05rem 0 .24rem;">
          <div style="font-size:.57rem;letter-spacing:2.2px;color:#83caff;font-weight:700;">{title}</div>
          <div style="font-size:.58rem;color:#8b949e;">PROFILE CARD</div>
        </div>
        <div style="position:relative;z-index:1;font-size:.62rem;color:#a9b3c6;margin-bottom:.32rem;">{note}</div>
        <div class="cosmic-card-grid">{tiles}</div>
        """)


def render_collectible_card(
    card: dict, *, is_owner: bool = True, key_prefix: str = "my", compact: bool = False
) -> None:
    """Render one non-flippable, public-safe Cosmic Card.

    ``compact`` retains the six direct card fields while omitting repeated identity
    treatment for a public profile that already renders the avatar, name, handle,
    and bio directly above it.
    """
    if card.get("public_card_state"):
        _render_public_card_state(card, key_prefix)
        return
    _render_card_css()
    safe_key = f"{key_prefix}_{card.get('card_key') or _safe_card_key(card.get('profile_auth_subject') or card.get('user_hash'))}"
    natal = card["natal"]
    accent = sign_color(natal["sun_sign"])
    display_name = html.escape(str(card.get("display_name") or "Moon Wanderer"))
    avatar = html.escape(str(card.get("avatar") or "✦"))
    rising_value = natal["rising_sign"] if natal.get("has_rising") else "Add coords"
    rising_icon = natal["rising_symbol"] if natal.get("has_rising") else "↑"
    dominant = card.get("dominant") or {"name": "Sun", "symbol": "☉"}

    tiles = "".join((
        _card_tile(safe_key, "sun", natal["sun_symbol"], "Sun", natal["sun_sign"], "#d8dee9"),
        _card_tile(safe_key, "moon", natal["moon_symbol"], "Moon", natal["moon_sign"], "#66a8ff"),
        _card_tile(safe_key, "rising", rising_icon, "Rising", rising_value, "#f7d25c"),
        _card_tile(safe_key, "birth_phase", natal["phase_emoji"], "Birth Phase", natal["phase_name"], "#c5a6ff"),
        _card_tile(safe_key, "full_moons", "◌", "Full Moons", str(card.get("full_moons_lived", 0)), "#9c7bff"),
        _card_tile(safe_key, "dominant", dominant["symbol"], "Dominant", dominant["name"], "#73dfbf"),
    ))

    card_label = "PUBLIC COSMIC CARD" if compact else ("MY CARD" if is_owner else "COLLECTED CARD")
    identity_html = "" if compact else f'''<div style="position:relative;z-index:1;display:flex;gap:.42rem;align-items:center;margin-bottom:.56rem;">
          <div style="width:1.7rem;height:1.7rem;border-radius:50%;border:1px solid {accent};display:flex;align-items:center;justify-content:center;color:{accent};font-size:.88rem;overflow:hidden;">{avatar}</div>
          <div style="font-size:1.05rem;font-weight:700;color:#f0f6fc;line-height:1.1;">{display_name}</div>
        </div>'''
    compact_css = "" if not compact else f"""
        .st-key-cosmic_card_{safe_key}{{padding:.45rem .48rem .5rem!important;margin:.42rem 0 .28rem!important;}}
        .st-key-cosmic_card_{safe_key} .cosmic-card-tile{{min-height:66px!important;padding:.25rem .06rem .2rem!important;}}
        .st-key-cosmic_card_{safe_key} .cosmic-card-tile-label{{font-size:.44rem!important;letter-spacing:.7px!important;}}
        .st-key-cosmic_card_{safe_key} .cosmic-card-tile-symbol{{font-size:1.08rem!important;margin:.1rem 0 .06rem!important;}}
        .st-key-cosmic_card_{safe_key} .cosmic-card-tile-value{{font-size:.70rem!important;line-height:1.02!important;}}
        """

    with st.container(key=f"cosmic_card_{safe_key}", border=False):
        st.html(f"""
        <style>.st-key-cosmic_card_{safe_key}{{border:2px solid {accent}!important;box-shadow:inset 0 0 36px rgba(0,0,0,.36),0 0 28px {accent}3d!important;}}{compact_css}</style>
        <div style="display:flex;justify-content:space-between;align-items:center;position:relative;z-index:1;margin:0.05rem 0 .4rem;">
          <div style="font-size:.57rem;letter-spacing:2.2px;color:#83caff;font-weight:700;">LUNATICK COSMIC CARD</div>
          <div style="font-size:.58rem;color:#8b949e;">{card_label}</div>
        </div>
        {identity_html}
        <div class="cosmic-card-grid">{tiles}</div>
        """)
    _render_detail_panel(safe_key)


def render_profile_form(user_hash: str, key_prefix: str = "cards") -> None:
    init_cards_db()
    profile = get_or_create_profile(user_hash)
    name = st.text_input("Display name", value=profile.get("display_name") or "Moon Wanderer", key=f"{key_prefix}_name")
    default_birth_date = date.fromisoformat(profile["birth_date"]) if profile.get("birth_date") else date(1990, 1, 1)
    birth_date = st.date_input("Birth date", value=default_birth_date, min_value=date(1920, 1, 1), max_value=date.today(), key=f"{key_prefix}_bd")

    st.caption("Enter a city and region/country or a postal/ZIP code. LunaTicK resolves the coordinates and historical timezone for you.")
    time_column, location_column = st.columns(2)
    with time_column:
        raw_time = profile.get("birth_time") or "12:00"
        try:
            hour, minute = [int(value) for value in raw_time.split(":")[:2]]
            time_value = dtime(hour % 24, minute % 60)
        except (TypeError, ValueError):
            time_value = dtime(12, 0)
        birth_time = st.time_input("Birth time (local)", value=time_value, key=f"{key_prefix}_bt")
    with location_column:
        location_query = st.text_input(
            "Birth city or postal/ZIP code",
            value=profile.get("birth_place") or "",
            placeholder="e.g. 10001 or New York, NY, USA",
            key=f"{key_prefix}_place",
        )

    results_key = f"{key_prefix}_geo_results"
    if st.button("Find birth location", key=f"{key_prefix}_find_location"):
        try:
            st.session_state[results_key] = _geocode_place(location_query)
        except requests.RequestException:
            st.session_state[results_key] = []
            st.error("The location service is temporarily unavailable. Please try again.")

    results = st.session_state.get(results_key, [])
    selected = None
    if results:
        labels = [f"{item['label']} — {item['timezone']}" for item in results]
        selected_index = st.selectbox("Confirm the matching birthplace", range(len(labels)), format_func=lambda index: labels[index], key=f"{key_prefix}_geo_choice")
        selected = results[selected_index]
        st.caption(f"Resolved coordinates: {selected['lat']:.4f}, {selected['lon']:.4f}. The timezone is determined from those coordinates.")
    elif location_query:
        st.info("Search for the birthplace, then select the matching result before saving.")

    if st.button("Save birth inputs", type="primary", key=f"{key_prefix}_save"):
        if not selected:
            st.error("Please search for and confirm a city or postal/ZIP-code match before saving.")
            return
        birth_datetime = datetime.combine(birth_date, birth_time).replace(tzinfo=ZoneInfo(selected["timezone"]))
        utc_offset = birth_datetime.utcoffset().total_seconds() / 3600
        save_profile(
            user_hash,
            name.strip() or "Moon Wanderer",
            birth_date.isoformat(),
            birth_time=f"{birth_time.hour:02d}:{birth_time.minute:02d}",
            birth_place=selected["label"],
            lat=selected["lat"],
            lon=selected["lon"],
            utc_offset=utc_offset,
        )
        st.session_state.display_name = name.strip() or "Moon Wanderer"
        st.session_state.birth_date = birth_date
        st.success("Birth inputs saved — Cosmic Card updated.")
        st.rerun()


def _friend_label(card: dict) -> str:
    natal = card["natal"]
    return f"{card['display_name']} ({natal['sun_symbol']} {natal['sun_sign']} · {natal['moon_symbol']} {natal['moon_sign']})"


def _render_trade_profile_lookup(user_hash: str) -> None:
    """Find a public member and send a privacy-safe direct card-trade request."""
    st.markdown("##### Find a LunaTicK member")
    st.caption("Enter a public @username to view their profile and send a card-trade request.")
    with st.form("card_profile_lookup_form", clear_on_submit=False):
        lookup_username = st.text_input(
            "Username",
            value=st.session_state.get("card_profile_lookup", ""),
            max_chars=24,
            placeholder="e.g. moon_orbit",
            label_visibility="collapsed",
        )
        search_profile = st.form_submit_button("Find member", use_container_width=True)
    if search_profile:
        st.session_state["card_profile_lookup"] = lookup_username.strip().lstrip("@")

    requested_handle = str(st.session_state.get("card_profile_lookup", "")).strip()
    if not requested_handle:
        return
    profile = auth.get_public_profile(requested_handle)
    if profile is None:
        st.info(f"No public LunaTicK profile was found for @{html.escape(requested_handle)}.")
    else:
        avatar = html.escape(str(profile.get("avatar") or "🌙"))
        display_name = html.escape(str(profile.get("display_name") or "Moon Wanderer"))
        username = html.escape(str(profile.get("username") or requested_handle))
        bio = html.escape(str(profile.get("bio") or "")).replace("\n", "<br>")
        st.markdown(
            f"<div style='border:1px solid rgba(188,140,255,.32);border-radius:12px;padding:.7rem;margin:.55rem 0;'>"
            f"<div style='color:#f0f6fc;font-weight:700;'>{avatar} {display_name}</div>"
            f"<div style='color:#bc8cff;font-size:.8rem;'>@{username}</div>"
            f"<div style='color:#c9d1d9;font-size:.84rem;margin-top:.28rem;'>{bio or 'No bio shared yet.'}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
        target_subject = ""
        if _using_supabase_backend():
            # Keep the immutable subject server-side; it is used only to create the request.
            source = _supabase().get_card_profile_by_username_server_only(str(profile.get("username") or requested_handle))
            target_subject = str((source or {}).get("auth_subject") or "").strip()
        if target_subject:
            st.caption("Send a request now; once accepted, this member is added to your collection.")
            if st.button(f"Send card trade to @{username}", key="send_lookup_card_trade", type="primary", use_container_width=True):
                ok, note = send_trade(user_hash, target_subject)
                (st.success if ok else st.warning)(note)
                if ok:
                    st.rerun()
        else:
            st.caption("Direct trades are available after this member’s public profile finishes syncing.")

        public_card = build_public_card_by_username(str(profile.get("username") or requested_handle))
        if public_card:
            render_collectible_card(public_card, is_owner=False, key_prefix=f"trade_lookup_{username}", compact=True)
        else:
            st.caption("This member has not activated a public Cosmic Card yet.")

    if st.button("Clear member search", key="clear_card_profile_lookup"):
        st.session_state.pop("card_profile_lookup", None)
        st.rerun()


def _render_trade_initiation(user_hash: str) -> None:
    """Compact top-of-screen trade action and public card discovery."""
    with st.popover("🤝 Trade Cards", help="Find a member or send a card-trade request"):
        _render_trade_profile_lookup(user_hash)
        st.markdown("---")
        st.caption("Send a card trade to add an accepted friend to your collection.")
        discoverable_cards = list_users_with_cards(user_hash)
        if not discoverable_cards:
            st.caption("No other cards are available yet. Share LunaTicK so friends can create theirs.")
            return
        options = {_friend_label(card): card["profile_auth_subject"] for card in discoverable_cards}
        selected = st.selectbox("Send card to", list(options), key="card_trade_target")
        message = st.text_input("Optional message", max_chars=200, key="card_trade_message")
        if st.button("Send card trade", key="send_card_trade", type="primary"):
            ok, note = send_trade(user_hash, options[selected], message)
            (st.success if ok else st.warning)(note)
            if ok:
                st.rerun()


def _render_profile_hub_css() -> None:
    """Style the dedicated social profile surface without exposing private fields."""
    st.html("""
    <style>
      .profile-hub-card {
        background: linear-gradient(145deg, rgba(26, 16, 57, .9), rgba(9, 12, 24, .96));
        border: 1px solid rgba(188, 140, 255, .46);
        border-radius: 14px;
        margin: .55rem 0;
        padding: .8rem .9rem;
      }
      .profile-hub-card__name { color: #f0f6fc; font-size: 1.04rem; font-weight: 750; }
      .profile-hub-card__handle { color: #bc8cff; font-size: .82rem; margin-top: .1rem; }
      .profile-hub-card__bio { color: #c9d1d9; font-size: .87rem; line-height: 1.42; margin: .38rem 0 0; }
      .profile-hub-kicker { color: #bc8cff; font-family: Orbitron, sans-serif; font-size: .59rem; font-weight: 800; letter-spacing: .15em; margin: .18rem 0; text-transform: uppercase; }
    </style>
    """)


def _render_profile_summary(profile: dict, *, heading: str | None = None) -> None:
    """Render only the safe public presence fields shared by a member."""
    avatar = html.escape(str(profile.get("avatar") or "🌙"))
    display_name = html.escape(str(profile.get("display_name") or "Moon Wanderer"))
    username = html.escape(str(profile.get("username") or "moon_wanderer"))
    bio = html.escape(str(profile.get("bio") or "")).replace("\n", "<br>")
    kicker = f"<div class='profile-hub-kicker'>{html.escape(heading)}</div>" if heading else ""
    st.markdown(
        f"<section class='profile-hub-card'>"
        f"{kicker}<div class='profile-hub-card__name'>{avatar} {display_name}</div>"
        f"<div class='profile-hub-card__handle'>@{username}</div>"
        f"<div class='profile-hub-card__bio'>{bio or 'No bio shared yet.'}</div>"
        f"</section>",
        unsafe_allow_html=True,
    )


def _profile_hub_target_subject(username: str) -> str:
    """Resolve a target only on the server; never surface its immutable subject."""
    if not _using_supabase_backend():
        return ""
    source = _supabase().get_card_profile_by_username_server_only(username)
    return str((source or {}).get("auth_subject") or "").strip()


def _render_profile_hub_member(user_hash: str, requested_handle: str) -> None:
    """Show one searched public profile with connection and card-trade actions."""
    profile = auth.get_public_profile(requested_handle)
    if profile is None:
        st.info(f"No public LunaTicK profile was found for @{html.escape(requested_handle)}.")
        return

    _render_profile_summary(profile, heading="Member profile")
    username = str(profile.get("username") or requested_handle).strip()
    current_username = str(st.session_state.get("username") or "").strip()
    target_subject = _profile_hub_target_subject(username)

    if username == current_username:
        st.caption("This is your public profile. Use Settings to edit your public details.")
    elif target_subject and target_subject in set(friends_of(user_hash)):
        st.success("✦ You are connected. Their card is in your collection when it is active.")
        direct_messages.render_member_direct_message(target_subject, profile)
    elif target_subject:
        st.caption("Send a card trade to connect. Your friend decides whether to accept it.")
        if st.button(
            f"Send card trade to @{username}",
            key=f"profile_hub_trade_{_safe_card_key(username)}",
            type="primary",
            use_container_width=True,
        ):
            ok, note = send_trade(user_hash, target_subject)
            (st.success if ok else st.warning)(note)
            if ok:
                st.rerun()
    else:
        st.caption("This member’s profile is still syncing. Try again shortly to send a card trade.")

    public_card = build_public_card_by_username(username)
    if public_card:
        st.caption("Public Cosmic Card")
        render_collectible_card(public_card, is_owner=False, key_prefix=f"profile_hub_{_safe_card_key(username)}", compact=True)


def _render_profile_hub_connections(user_hash: str) -> None:
    """List accepted public connections without revealing private profile data."""
    friend_subjects = friends_of(user_hash)
    st.subheader("Your Connections")
    if not friend_subjects:
        st.caption("Search a member above and send a card trade to start your collection.")
        return
    if _using_supabase_backend():
        profiles = _supabase().get_public_profile_summaries(friend_subjects)
        for subject in friend_subjects:
            profile = profiles.get(subject) or {}
            username = str(profile.get("username") or "").strip()
            label = str(profile.get("display_name") or username or "Moon Wanderer")
            avatar = str(profile.get("avatar") or "🌙")
            if username and st.button(
                f"{avatar} {label} · @{username}",
                key=f"profile_hub_connection_{_safe_card_key(subject)}",
                use_container_width=True,
            ):
                st.session_state["profile_hub_lookup"] = username
                st.rerun()
        return
    st.caption(f"{len(friend_subjects)} accepted card connection{'s' if len(friend_subjects) != 1 else ''}.")


def _render_profile_hub_search_form(*, key_suffix: str = "") -> None:
    """Search a public handle and rerun directly into the selected member view."""
    st.caption("Search an exact public @username to view their profile, connect, and trade Cosmic Cards.")
    with st.form(f"profile_hub_lookup_form_{key_suffix or 'owner'}", clear_on_submit=False):
        lookup_username = st.text_input(
            "Username", value="", max_chars=24, placeholder="e.g. moon_orbit",
            label_visibility="collapsed", key=f"profile_hub_lookup_input_{key_suffix or 'owner'}",
        )
        searched = st.form_submit_button("View profile", type="primary", use_container_width=True)
    if searched:
        requested_handle = lookup_username.strip().lstrip("@")
        if requested_handle:
            st.session_state["profile_hub_lookup"] = requested_handle
            st.rerun()
        st.warning("Enter a public @username to continue.")


def _render_profile_menu(*, viewing_member: bool) -> None:
    """Render a compact left-anchored owner menu without consuming page width."""
    with st.popover("☰", help="Open Profile navigation", type="secondary"):
        st.markdown("**Profile navigation**")
        st.caption("Your LunaTicK space")
        profile_clicked = st.button("✎  My Profile · Edit", key="profile_menu_my_profile", use_container_width=True)
        friends_clicked = st.button("♧  My Friends", key="profile_menu_friends", use_container_width=True)
        dms_clicked = st.button("✉  My DMs", key="profile_menu_dms", use_container_width=True)
        if profile_clicked:
            st.session_state.pop("profile_hub_lookup", None)
            st.session_state["profile_hub_section"] = "profile"
            st.rerun()
        if friends_clicked:
            st.session_state.pop("profile_hub_lookup", None)
            st.session_state["profile_hub_section"] = "friends"
            st.rerun()
        if dms_clicked:
            st.session_state.pop("profile_hub_lookup", None)
            st.session_state["profile_hub_section"] = "dms"
            st.rerun()
        if viewing_member:
            st.caption("You are viewing a member profile.")


def render_profile_hub() -> None:
    """Show the owner menu destinations or a selected public member profile directly."""
    init_cards_db()
    _render_card_css()
    _render_profile_hub_css()
    user_hash = str(st.session_state.get("user_hash") or "anonymous")
    own_username = str(st.session_state.get("username") or "").strip()
    requested_handle = str(st.session_state.get("profile_hub_lookup", "")).strip().lstrip("@")
    viewing_member = bool(requested_handle and requested_handle.lower() != own_username.lower())
    _render_profile_menu(viewing_member=viewing_member)

    if viewing_member:
        st.markdown("<div class='profile-hub-kicker'>LunaTic member</div><h2>Member Profile</h2>", unsafe_allow_html=True)
        _render_profile_hub_member(user_hash, requested_handle)
        st.markdown("---")
        st.markdown("<div class='profile-hub-kicker'>Discover</div><h3>Find another member</h3>", unsafe_allow_html=True)
        _render_profile_hub_search_form(key_suffix="member")
        return

    section = str(st.session_state.get("profile_hub_section") or "profile")
    if section == "friends":
        st.markdown("<div class='profile-hub-kicker'>LunaTicK social</div><h2>My Friends</h2>", unsafe_allow_html=True)
        _render_profile_hub_connections(user_hash)
        return
    if section == "dms":
        st.markdown("<div class='profile-hub-kicker'>LunaTicK social</div><h2>My DMs</h2>", unsafe_allow_html=True)
        direct_messages.render_owner_dm_inbox()
        return

    own_profile = auth.get_public_profile(own_username) if own_username else None
    title_column, edit_column = st.columns([7, 1])
    with title_column:
        st.markdown("<div class='profile-hub-kicker'>LunaTicK social</div><h2>My Profile</h2>", unsafe_allow_html=True)
    with edit_column:
        if st.button("✎", key="profile_hub_edit", help="Edit your public profile", type="secondary"):
            st.session_state.nav_page = "Settings"
            st.rerun()

    if own_profile:
        _render_profile_summary(own_profile, heading="Your public presence")
    else:
        st.info("Your public profile is being prepared. Complete your profile in Settings to share a username.")

    st.markdown("---")
    st.markdown("<div class='profile-hub-kicker'>Discover and connect</div><h3>Find a LunaTicK Member</h3>", unsafe_allow_html=True)
    _render_profile_hub_search_form()
    st.markdown("---")
    _render_profile_hub_connections(user_hash)


def render_cosmic_cards_tab() -> None:
    """Render the compact owner card, its detail panel, and accepted-card collection."""
    init_cards_db()
    user_hash = st.session_state.get("user_hash", "anonymous")
    profile = get_or_create_profile(user_hash)
    my_card = build_card(user_hash)

    st.caption("Use the profile button in the upper-left corner to find members, connect, and trade Cosmic Cards.")

    if my_card:
        # Preserve the existing Collect hierarchy: the Cosmic Card stays first.
        render_collectible_card(my_card, is_owner=True, key_prefix="owner")

    # The owner-only chart is rendered independently of card success. This keeps
    # the chart reachable without moving the established Cosmic Card to the
    # bottom of Collect.
    render_birth_chart_and_horoscope(profile)

    if not my_card:
        st.info("Add your birth date to unlock your Cosmic Card.")
        with st.expander("Add your private birth inputs", expanded=True):
            render_profile_form(user_hash, key_prefix="cards")
        return

    # The collection intentionally follows the owner-card explanation area.
    st.markdown("#### Your Collection")
    friend_subjects = friends_of(user_hash)
    if not friend_subjects:
        st.caption("Your collection is waiting. Send a card trade to start collecting.")
    else:
        for friend_subject in friend_subjects:
            friend_card = build_friend_card(user_hash, friend_subject)
            if friend_card:
                render_collectible_card(friend_card, is_owner=False, key_prefix="friend")

    st.markdown("---")
    st.subheader("Incoming Card Trades")
    incoming = [trade for trade in list_trades(user_hash, "incoming") if trade["status"] == "pending"]
    if not incoming:
        st.caption("No pending card trades.")
    for trade in incoming:
        sender_card = build_card(trade["sender"])
        sender_name = sender_card["display_name"] if sender_card else "A LunaTicK member"
        columns = st.columns([3, 1, 1])
        columns[0].write(f"**{sender_name}** wants to trade cards. {trade['message'] or ''}")
        if columns[1].button("Accept", key=f"accept_trade_{trade['id']}"):
            resolve_trade(trade["id"], user_hash, True)
            st.rerun()
        if columns[2].button("Decline", key=f"decline_trade_{trade['id']}"):
            resolve_trade(trade["id"], user_hash, False)
            st.rerun()

    with st.expander("Update private birth inputs", expanded=False):
        render_profile_form(user_hash, key_prefix="cards")


# ---------------------------------------------------------------------------
# Owner-only birth-chart and horoscope experience.
# These values are deliberately calculated from the private profile at render
# time and are never added to shareable_card().
# ---------------------------------------------------------------------------

_DETAILED_PLANETS = (
    ("Sun", swe.SUN, "☉", "#f6b73c"),
    ("Moon", swe.MOON, "☾", "#d8dee9"),
    ("Mercury", swe.MERCURY, "☿", "#66a8ff"),
    ("Venus", swe.VENUS, "♀", "#f783c2"),
    ("Mars", swe.MARS, "♂", "#ff6b6b"),
    ("Jupiter", swe.JUPITER, "♃", "#c5a6ff"),
    ("Saturn", swe.SATURN, "♄", "#9ba9bf"),
)

_DETAILED_ASPECTS = (
    (0, "Conjunction", "☌", "#f6b73c"),
    (60, "Sextile", "⚹", "#66a8ff"),
    (90, "Square", "□", "#ff6b6b"),
    (120, "Trine", "△", "#73dfbf"),
    (180, "Opposition", "☍", "#f783c2"),
)

_HOROSCOPE_ENERGIES = (
    "a quiet opening",
    "a threshold of courage",
    "a return to your center",
    "a clearing of old noise",
    "a spark of creative motion",
    "a patient rebalancing",
    "a wider view of what matters",
)
_HOROSCOPE_GUIDANCE = (
    "choose one honest next step instead of solving the whole path",
    "protect the first uninterrupted hour you can claim",
    "let curiosity lead before certainty makes the decision for you",
    "name the boundary that would make your energy feel more like your own",
    "finish one small thing that has been asking for your attention",
    "share your insight generously, without needing to control its reception",
    "make room for a conversation that leaves both people more understood",
    "return to the body through breath, water, walking, or deliberate rest",
    "notice what repeats today; repetition may be showing you a pattern",
    "write down the feeling before turning it into a conclusion",
)
_SIGN_TRAITS = {
    "Aries": "direct, initiating, and willing to turn an idea into motion",
    "Taurus": "grounded, patient, and attentive to what can endure",
    "Gemini": "curious, connective, and energized by living questions",
    "Cancer": "protective, intuitive, and deeply responsive to atmosphere",
    "Leo": "expressive, generous, and capable of warming a whole room",
    "Virgo": "observant, refining, and devoted to useful details",
    "Libra": "relational, discerning, and drawn toward meaningful balance",
    "Scorpio": "perceptive, focused, and unafraid of honest transformation",
    "Sagittarius": "searching, candid, and oriented toward a larger horizon",
    "Capricorn": "steady, strategic, and willing to build over time",
    "Aquarius": "independent, inventive, and attentive to collective possibility",
    "Pisces": "imaginative, empathic, and porous to the emotional field around you",
}


def _detailed_birth_chart(profile: dict) -> dict | None:
    """Return private planetary positions, aspects, and optional Ascendant."""
    birth_date = str(profile.get("birth_date") or "").strip()
    if not birth_date:
        return None
    try:
        has_coordinates = _has_actual_coordinates(profile.get("lat"), profile.get("lon"))
        timezone_name = _timezone_for_coordinates(profile.get("lat"), profile.get("lon"))
        dt_utc = _local_to_utc(birth_date, profile.get("birth_time"), profile.get("utc_offset"), timezone_name)
        jd_ut = swe.julday(
            dt_utc.year,
            dt_utc.month,
            dt_utc.day,
            dt_utc.hour + dt_utc.minute / 60 + dt_utc.second / 3600,
        )
        flags = swe.FLG_SWIEPH | swe.FLG_SPEED
        positions = []
        for name, planet_id, symbol, color in _DETAILED_PLANETS:
            values, _retflags, _ret_message = swe.calc_ut(jd_ut, planet_id, flags)
            longitude = float(values[0]) % 360.0
            sign, sign_symbol = _sign_from_lon(longitude)
            positions.append({
                "name": name,
                "symbol": symbol,
                "color": color,
                "longitude": longitude,
                "sign": sign,
                "sign_symbol": sign_symbol,
                "degree": longitude % 30.0,
            })

        aspects = []
        for left_index, left in enumerate(positions):
            for right in positions[left_index + 1:]:
                raw_delta = abs(left["longitude"] - right["longitude"]) % 360.0
                separation = min(raw_delta, 360.0 - raw_delta)
                for angle, label, symbol, color in _DETAILED_ASPECTS:
                    orb = abs(separation - angle)
                    if orb <= 6.0:
                        aspects.append({
                            "left": left["name"], "right": right["name"],
                            "label": label, "symbol": symbol, "color": color,
                            "angle": angle, "orb": orb,
                        })
                        break

        ascendant = None
        if has_coordinates:
            try:
                _cusps, ascmc = swe.houses_ex(jd_ut, float(profile["lat"]), float(profile["lon"]), b"P", 0)
                asc_longitude = float(ascmc[0]) % 360.0
                rising_sign, rising_symbol = _sign_from_lon(asc_longitude)
                ascendant = {"longitude": asc_longitude, "sign": rising_sign, "symbol": rising_symbol}
            except (TypeError, ValueError, OverflowError, swe.Error):
                ascendant = None
        return {"positions": positions, "aspects": aspects, "ascendant": ascendant, "birth_date": birth_date}
    except (TypeError, ValueError, OverflowError, swe.Error):
        return None


def _chart_point(longitude: float, radius: float, center: float = 320.0) -> tuple[float, float]:
    angle = math.radians(longitude - 90.0)
    return center + radius * math.cos(angle), center + radius * math.sin(angle)


def _chart_sector_path(start_longitude: float, end_longitude: float, outer: float = 292.0, inner: float = 226.0) -> str:
    start_outer = _chart_point(start_longitude, outer)
    end_outer = _chart_point(end_longitude, outer)
    end_inner = _chart_point(end_longitude, inner)
    start_inner = _chart_point(start_longitude, inner)
    large_arc = 1 if (end_longitude - start_longitude) > 180 else 0
    return (
        f"M {start_outer[0]:.1f},{start_outer[1]:.1f} "
        f"A {outer},{outer} 0 {large_arc} 1 {end_outer[0]:.1f},{end_outer[1]:.1f} "
        f"L {end_inner[0]:.1f},{end_inner[1]:.1f} "
        f"A {inner},{inner} 0 {large_arc} 0 {start_inner[0]:.1f},{start_inner[1]:.1f} Z"
    )


def _birth_chart_svg(chart: dict) -> str:
    """Render the owner-only SVG port of Emergent's BirthChart component."""
    view_size = 640.0
    center = view_size / 2
    outer_r = view_size * 0.465
    sign_r = view_size * 0.39
    track_r = view_size * 0.30
    inner_r = view_size * 0.14
    element_colors = {"Fire": "#EF4444", "Earth": "#10B981", "Air": "#60A5FA", "Water": "#A78BFA"}
    element_backgrounds = {"Fire": "rgba(239,68,68,0.24)", "Earth": "rgba(16,185,129,0.24)", "Air": "rgba(96,165,250,0.24)", "Water": "rgba(167,139,250,0.24)"}
    elements = {
        "Aries": "Fire", "Leo": "Fire", "Sagittarius": "Fire",
        "Taurus": "Earth", "Virgo": "Earth", "Capricorn": "Earth",
        "Gemini": "Air", "Libra": "Air", "Aquarius": "Air",
        "Cancer": "Water", "Scorpio": "Water", "Pisces": "Water",
    }
    brand_glow = "#C084FC"

    def point(longitude: float, radius: float) -> tuple[float, float]:
        return _chart_point(longitude, radius, center)

    def sector_path(start_longitude: float, end_longitude: float) -> str:
        start_outer = point(start_longitude, outer_r)
        end_outer = point(end_longitude, outer_r)
        end_inner = point(end_longitude, sign_r)
        start_inner = point(start_longitude, sign_r)
        return (
            f"M {start_outer[0]:.2f} {start_outer[1]:.2f} "
            f"A {outer_r:.2f} {outer_r:.2f} 0 0 1 {end_outer[0]:.2f} {end_outer[1]:.2f} "
            f"L {end_inner[0]:.2f} {end_inner[1]:.2f} "
            f"A {sign_r:.2f} {sign_r:.2f} 0 0 0 {start_inner[0]:.2f} {start_inner[1]:.2f} Z"
        )

    sun = next((item for item in chart["positions"] if item["name"] == "Sun"), None)
    sun_sign = sun["sign"] if sun else ""
    zodiac_segments = []
    for index, (sign, symbol) in enumerate(ZODIAC):
        start = index * 30.0
        mid = start + 15.0
        element = elements[sign]
        fill = element_backgrounds[element]
        border = element_colors[element]
        selected = sign == sun_sign
        if selected:
            fill = fill.replace("0.24", "0.46")
        label_x, label_y = point(mid, (outer_r + sign_r) / 2)
        tile_size = 17 if selected else 14
        zodiac_segments.append(
            f"<g><path d='{sector_path(start, start + 30.0)}' fill='{fill}' stroke='{border if selected else 'rgba(148,163,184,0.18)'}' stroke-width='{2.4 if selected else 1.0}'/>"
            f"<rect x='{label_x - tile_size - 2:.2f}' y='{label_y - tile_size - 2:.2f}' width='{(tile_size + 2) * 2:.2f}' height='{(tile_size + 2) * 2:.2f}' rx='8' fill='{border}' opacity='0.35' filter='url(#birthChartTileGlow)'/>"
            f"<rect x='{label_x - tile_size:.2f}' y='{label_y - tile_size:.2f}' width='{tile_size * 2:.2f}' height='{tile_size * 2:.2f}' rx='7' fill='rgba(170,75,235,0.86)' stroke='{border if selected else 'rgba(233,213,255,0.58)'}' stroke-width='{2.2 if selected else 1.1}'/>"
            f"<text x='{label_x:.2f}' y='{label_y + (7 if selected else 6):.2f}' font-size='{24 if selected else 20}' fill='#fffaff' stroke='rgba(59,16,95,0.42)' stroke-width='0.8' paint-order='stroke' text-anchor='middle' font-weight='bold'>{html.escape(symbol)}</text></g>"
        )

    stars = []
    for star_index in range(34):
        star_x = 34 + ((star_index * 137) % 572)
        star_y = 34 + ((star_index * 83) % 572)
        star_radius = 0.55 + (star_index % 4) * 0.35
        star_opacity = 0.24 + (star_index % 5) * 0.08
        stars.append(f"<circle cx='{star_x}' cy='{star_y}' r='{star_radius:.2f}' fill='#e9ddff' opacity='{star_opacity:.2f}'/>")

    ticks = []
    for degree in range(0, 360, 5):
        major = degree % 30 == 0
        tick_r1 = outer_r + (4 if major else 2)
        tick_r2 = outer_r - (3 if major else 1)
        x1, y1 = point(degree, tick_r1)
        x2, y2 = point(degree, tick_r2)
        ticks.append(
            f"<line x1='{x1:.2f}' y1='{y1:.2f}' x2='{x2:.2f}' y2='{y2:.2f}' stroke='{'rgba(148,163,184,0.3)' if major else 'rgba(148,163,184,0.12)'}' stroke-width='{1 if major else 0.5}'/>"
        )

    position_by_name = {item["name"]: item for item in chart["positions"]}
    marker_items = list(chart["positions"])
    if chart.get("ascendant"):
        marker_items.append({
            "name": "Ascendant", "symbol": "AC", "longitude": chart["ascendant"]["longitude"],
            "color": "#C084FC", "sign": chart["ascendant"]["sign"],
        })
        position_by_name["Ascendant"] = marker_items[-1]

    marker_state = []
    for item in marker_items:
        x, y = point(item["longitude"], track_r)
        marker_state.append({"item": item, "x": x, "y": y})
    for left_index in range(len(marker_state)):
        for right_index in range(left_index + 1, len(marker_state)):
            left = marker_state[left_index]
            right = marker_state[right_index]
            if math.hypot(left["x"] - right["x"], left["y"] - right["y"]) < 14:
                right["x"], right["y"] = point(right["item"]["longitude"], track_r - 16)

    aspect_lines = []
    for aspect in chart["aspects"][:8]:
        left = position_by_name.get(aspect["left"])
        right = position_by_name.get(aspect["right"])
        if not left or not right:
            continue
        x1, y1 = point(left["longitude"], track_r - 12)
        x2, y2 = point(right["longitude"], track_r - 12)
        dash = " stroke-dasharray='4,3'" if aspect["label"] == "Square" else " stroke-dasharray='6,3'" if aspect["label"] == "Opposition" else ""
        aspect_lines.append(
            f"<line x1='{x1:.2f}' y1='{y1:.2f}' x2='{x2:.2f}' y2='{y2:.2f}' stroke='{aspect['color']}' stroke-width='4.8' opacity='0.08' filter='url(#birthChartPlanetBloom)'{dash}/>"
            f"<line x1='{x1:.2f}' y1='{y1:.2f}' x2='{x2:.2f}' y2='{y2:.2f}' stroke='{aspect['color']}' stroke-width='2.15' opacity='0.20'{dash}/>"
            f"<line x1='{x1:.2f}' y1='{y1:.2f}' x2='{x2:.2f}' y2='{y2:.2f}' stroke='{aspect['color']}' stroke-width='0.95' opacity='0.68'{dash}/>"
        )

    planet_nodes = []
    for marker in marker_state:
        item = marker["item"]
        x, y = marker["x"], marker["y"]
        font_size = 12 if item["name"] == "Ascendant" else 17
        halo_radius = 22 if item["name"] == "Ascendant" else 25
        dot_radius = 9 if item["name"] == "Ascendant" else 11
        planet_nodes.append(
            f"<g><circle cx='{x:.2f}' cy='{y:.2f}' r='{halo_radius + 8}' fill='{item['color']}' opacity='0.16' filter='url(#birthChartPlanetBloom)'/>"
            f"<circle cx='{x:.2f}' cy='{y:.2f}' r='{halo_radius}' fill='{item['color']}' opacity='0.18'/>"
            f"<circle cx='{x:.2f}' cy='{y:.2f}' r='{dot_radius + 2}' fill='{item['color']}' opacity='0.26' stroke='{item['color']}' stroke-width='1.4'/>"
            f"<circle cx='{x:.2f}' cy='{y:.2f}' r='{dot_radius}' fill='{item['color']}' opacity='0.98' stroke='rgba(255,255,255,0.64)' stroke-width='1.3'/>"
            f"<text x='{x:.2f}' y='{y - (20 if item['name'] == 'Ascendant' else 18):.2f}' font-size='{font_size}' fill='{item['color']}' stroke='rgba(5,8,17,0.82)' stroke-width='1.8' paint-order='stroke' text-anchor='middle' font-weight='bold'>{html.escape(item['symbol'])}</text></g>"
        )

    center_label = sun["sign_symbol"] if sun else "✦"
    return f"""
    <div class='lunatick-birth-chart'>
      <svg viewBox='0 0 {view_size:.0f} {view_size:.0f}' role='img' aria-label='Private LunaTicK birth chart'>
        <defs>
          <radialGradient id='birthChartCenterGlow' cx='50%' cy='50%' r='50%'><stop offset='0%' stop-color='{brand_glow}' stop-opacity='0.46'/><stop offset='48%' stop-color='{brand_glow}' stop-opacity='0.18'/><stop offset='100%' stop-color='{brand_glow}' stop-opacity='0'/></radialGradient>
          <radialGradient id='birthChartOuterGlow' cx='50%' cy='50%' r='50%'><stop offset='76%' stop-color='transparent' stop-opacity='0'/><stop offset='94%' stop-color='{brand_glow}' stop-opacity='0.12'/><stop offset='100%' stop-color='{brand_glow}' stop-opacity='0.22'/></radialGradient>
          <radialGradient id='birthChartCenterMedallion' cx='35%' cy='28%' r='78%'><stop offset='0%' stop-color='#e9d5ff' stop-opacity='0.92'/><stop offset='24%' stop-color='#c084fc' stop-opacity='0.94'/><stop offset='68%' stop-color='#7e22ce' stop-opacity='0.96'/><stop offset='100%' stop-color='#35105f' stop-opacity='0.98'/></radialGradient>
          <filter id='birthChartPlanetBloom' x='-80%' y='-80%' width='260%' height='260%'><feGaussianBlur stdDeviation='5'/></filter>
          <filter id='birthChartTileGlow' x='-80%' y='-80%' width='260%' height='260%'><feGaussianBlur stdDeviation='3'/></filter>
        </defs>
        {''.join(stars)}
        <circle cx='{center:.0f}' cy='{center:.0f}' r='{outer_r + 7:.2f}' fill='url(#birthChartOuterGlow)'/>
        <circle cx='{center:.0f}' cy='{center:.0f}' r='{outer_r + 2:.2f}' fill='none' stroke='rgba(192,132,252,0.22)' stroke-width='3'/>
        <circle cx='{center:.0f}' cy='{center:.0f}' r='{outer_r:.2f}' fill='none' stroke='rgba(216,180,254,0.26)' stroke-width='1.4'/>
        <circle cx='{center:.0f}' cy='{center:.0f}' r='{sign_r + 3:.2f}' fill='none' stroke='rgba(148,163,184,0.20)' stroke-width='1.2'/>
        <circle cx='{center:.0f}' cy='{center:.0f}' r='{sign_r:.2f}' fill='none' stroke='rgba(148,163,184,0.16)' stroke-width='0.8'/>
        {''.join(ticks)}
        {''.join(zodiac_segments)}
        {''.join(f"<line x1='{point(i * 30.0, inner_r)[0]:.2f}' y1='{point(i * 30.0, inner_r)[1]:.2f}' x2='{point(i * 30.0, sign_r)[0]:.2f}' y2='{point(i * 30.0, sign_r)[1]:.2f}' stroke='rgba(148,163,184,0.12)' stroke-width='0.5'/>" for i in range(12))}
        <circle cx='{center:.0f}' cy='{center:.0f}' r='{track_r + 16:.2f}' fill='none' stroke='rgba(148,163,184,0.10)' stroke-width='0.8'/>
        <circle cx='{center:.0f}' cy='{center:.0f}' r='{track_r:.2f}' fill='none' stroke='rgba(148,163,184,0.13)' stroke-width='0.8' stroke-dasharray='3,3'/>
        {''.join(aspect_lines)}
        <circle cx='{center:.0f}' cy='{center:.0f}' r='{inner_r + 30:.2f}' fill='url(#birthChartCenterGlow)' opacity='0.78'/>
        <circle cx='{center:.0f}' cy='{center:.0f}' r='{inner_r + 11:.2f}' fill='none' stroke='rgba(192,132,252,0.28)' stroke-width='2.2'/>
        <circle cx='{center:.0f}' cy='{center:.0f}' r='{inner_r:.2f}' fill='url(#birthChartCenterMedallion)' stroke='rgba(245,231,255,0.72)' stroke-width='1.8'/>
        <circle cx='{center:.0f}' cy='{center:.0f}' r='{inner_r - 5:.2f}' fill='none' stroke='rgba(255,255,255,0.18)' stroke-width='1'/>
        <text x='{center:.0f}' y='{center + 18:.0f}' font-size='54' fill='#fffaff' stroke='rgba(77,24,118,0.48)' stroke-width='1.4' paint-order='stroke' text-anchor='middle' font-weight='bold'>{html.escape(center_label)}</text>
        {''.join(planet_nodes)}
      </svg>
    </div>
    """


def _daily_horoscope(chart: dict, category: str) -> str:
    """Generate a deterministic daily reading without requiring an external API."""
    today_key = date.today().isoformat()
    sun = next((item for item in chart["positions"] if item["name"] == "Sun"), chart["positions"][0])
    moon = next((item for item in chart["positions"] if item["name"] == "Moon"), chart["positions"][1])
    phase_name = _chart(datetime.now(timezone.utc), None, None).get("phase_name", "the current Moon")
    seed = hashlib.sha256(f"{today_key}|{sun['sign']}|{category}".encode("utf-8")).digest()
    energy = _HOROSCOPE_ENERGIES[seed[0] % len(_HOROSCOPE_ENERGIES)]
    guidance = _HOROSCOPE_GUIDANCE[seed[1] % len(_HOROSCOPE_GUIDANCE)]
    category_line = {
        "General": "Let the day be a conversation between your intention and what the world actually offers.",
        "Love & Connection": "Listen for the need beneath the first reaction, including your own.",
        "Work & Purpose": "Give the most important task a clear container instead of giving it your whole identity.",
        "Wellness & Reflection": "Treat restoration as a practice that makes honest action possible.",
    }.get(category, "Return to what is true, useful, and kind.")
    return (
        f"With your Sun in {sun['sign']} and your natal Moon in {moon['sign']}, today carries {energy}. "
        f"The {phase_name.lower()} context invites you to {guidance}. {category_line}"
    )


def _sign_traits_reading(chart: dict) -> str:
    sun = next((item for item in chart["positions"] if item["name"] == "Sun"), chart["positions"][0])
    moon = next((item for item in chart["positions"] if item["name"] == "Moon"), chart["positions"][1])
    rising = chart.get("ascendant")
    rising_text = f" Your Rising sign adds a {rising['sign']} way of meeting the world." if rising else " Add a confirmed birth time and location to calculate your Rising sign."
    return f"Your Sun sign is {sun['sign']}: { _SIGN_TRAITS.get(sun['sign'], 'distinctive and reflective') }. Your Moon in {moon['sign']} describes an emotional rhythm that deserves room to be heard.{rising_text}"


def render_birth_chart_and_horoscope(profile: dict) -> None:
    """Render detailed astrology only for the signed-in owner."""
    st.markdown("#### Your Birth Chart & Daily Horoscope")
    birth_date = str(profile.get("birth_date") or "").strip()
    if not birth_date:
        st.info("Your private birth chart will appear here after you save a birth date in Collect.")
        return
    chart = _detailed_birth_chart(profile)
    if not chart:
        st.warning("Your birth profile is saved, but the chart could not be calculated yet. Open Update private birth inputs below and save the confirmed birth details again.")
        return
    st.caption("Private owner view. Exact birth inputs remain server-side and are not included in shared Cosmic Cards.")
    # Markdown HTML is intentionally used here instead of st.html so the SVG
    # remains visible on Streamlit versions that sanitize st.html containers.
    st.markdown(_birth_chart_svg(chart), unsafe_allow_html=True)

    st.markdown("##### Planetary Positions")
    position_cells = []
    for item in chart["positions"]:
        position_cells.append(
            f"<div class='astro-position-row'><span style='color:{item['color']};font-size:1.45rem;line-height:1;'>{html.escape(item['symbol'])}</span> "
            f"<strong>{html.escape(item['name'])}</strong><br><span style='color:{sign_color(item['sign'])};'>{html.escape(item['sign_symbol'])} {html.escape(item['sign'])} {item['degree']:.1f}°</span></div>"
        )
    paired_rows = []
    for index in range(0, len(position_cells), 2):
        right = position_cells[index + 1] if index + 1 < len(position_cells) else "<div></div>"
        paired_rows.append(f"<div class='astro-positions-table-row'>{position_cells[index]}{right}</div>")
    st.markdown(f"<div class='astro-positions-table' role='table'>{''.join(paired_rows)}</div>", unsafe_allow_html=True)

    ascendant = chart.get("ascendant")
    if ascendant:
        st.caption(f"Rising / Ascendant: {ascendant['symbol']} {ascendant['sign']}")
    else:
        st.info("Rising sign is unavailable until a confirmed birthplace and birth time are saved.")

    if chart["aspects"]:
        st.markdown("##### Key Aspects")
        aspect_text = " · ".join(
            f"{item['symbol']} {item['left']}–{item['right']} {item['label']} ({item['orb']:.1f}° orb)"
            for item in chart["aspects"][:8]
        )
        st.caption(aspect_text)

    mode = st.radio("Reading", ("Today's Reading", "Sign Traits"), horizontal=True, key="cosmic_reading_mode")
    if mode == "Today's Reading":
        category = st.selectbox("Reading category", ("General", "Love & Connection", "Work & Purpose", "Wellness & Reflection"), key="cosmic_reading_category")
        st.markdown(f"<div class='astro-reading-card'><div class='astro-reading-kicker'>TODAY'S READING · {html.escape(category.upper())}</div><div class='astro-reading-text'>{html.escape(_daily_horoscope(chart, category))}</div></div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='astro-reading-card'><div class='astro-reading-kicker'>SIGN TRAITS</div><div class='astro-reading-text'>{html.escape(_sign_traits_reading(chart))}</div></div>", unsafe_allow_html=True)
