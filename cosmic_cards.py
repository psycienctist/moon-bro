# cosmic_cards.py
# Collectible birth-chart cosmic cards + trade-as-friend-request
# Includes: Clickable term explanations, refined Sun sign archetypes.

import streamlit as st
import sqlite3
import ephem
import math
from datetime import datetime, timezone, timedelta, date, time as dtime
from collections import Counter

DB = "lunatick.db"

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

SIGN_RULERS = {
    "Aries": ("Mars", "♂"), "Taurus": ("Venus", "♀"), "Gemini": ("Mercury", "☿"),
    "Cancer": ("Moon", "☾"), "Leo": ("Sun", "☉"), "Virgo": ("Mercury", "☿"),
    "Libra": ("Venus", "♀"), "Scorpio": ("Pluto", "♇"), "Sagittarius": ("Jupiter", "♃"),
    "Capricorn": ("Saturn", "♄"), "Aquarius": ("Uranus", "♅"), "Pisces": ("Neptune", "♆"),
}

RARITY_STYLE = {
    "Common": ("#8b949e", "COMMON"), "Uncommon": ("#3fb950", "UNCOMMON"),
    "Rare": ("#58a6ff", "RARE"), "Epic": ("#bc8cff", "EPIC"),
    "Legendary": ("#ffd700", "LEGENDARY"),
}

HD_BY_RISING = {
    "Aries": "Manifestor", "Taurus": "Generator", "Gemini": "Manifesting Generator",
    "Cancer": "Generator", "Leo": "Manifestor", "Virgo": "Projector",
    "Libra": "Projector", "Scorpio": "Manifesting Generator", "Sagittarius": "Manifestor",
    "Capricorn": "Generator", "Aquarius": "Projector", "Pisces": "Reflector",
}

HD_FLAVOR_MAPPING = {
    "Manifestor": "Initiate and Inform", "Generator": "Respond and Satisfy",
    "Manifesting Generator": "Respond, Visualize, then Initiate", "Projector": "Wait for the Invitation",
    "Reflector": "Wait a Lunar Cycle",
}

# --- REFINED SUN SIGN ARCHETYPES (No "You are") ---
SUN_SIGN_DESCRIPTIONS = {
    "Aries": "Fiery, pioneering, and fiercely independent, you charge headfirst into new horizons with unstoppable courage. Primary purposes include ignite fresh initiatives, blaze trails for othe[...]",
    "Taurus": "Disciplined, patient, and dedicated, you build slowly but with lasting impact. Primary purposes include master your craft, build enduring structures, and mentor others.",
    "Gemini": "Curious, adaptable, and intellectually lightning-fast, you weave connections between diverse ideas and people. Primary purposes include translate complex concepts, bridge communitie[...]",
    "Cancer": "Deeply intuitive, nurturing, and protective, you create emotional sanctuaries where others feel truly seen and safe. Primary purposes include foster emotional healing, cultivate sac[...]",
    "Leo": "Radiant, generous, and naturally magnetic, you light up every room with heartfelt warmth and creative vision. Primary purposes include inspire authentic self-expression, lead with cour[...]",
    "Virgo": "Meticulous, analytical, and devotedly service-oriented, you refine chaos into elegant, highly efficient systems. Primary purposes include optimize collective workflows, heal through [...]",
    "Libra": "Harmonious, diplomatic, and aesthetically refined, you restore equilibrium and foster graceful collaboration. Primary purposes include bridge opposing perspectives, cultivate exquisi[...]",
    "Scorpio": "Intense, transformative, and unblinkingly profound, you pierce beneath surface illusions to uncover deeper truths. Primary purposes include facilitate deep psychological healing, m[...]",
    "Sagittarius": "Expansive, philosophical, and endlessly adventurous, you seek wisdom across distant horizons and grand paradigms. Primary purposes include inspire higher learning, expand cultu[...]",
    "Capricorn": "Strategic, resilient, and masterfully disciplined, you turn ambitious visions into enduring, tangible monuments. Primary purposes include architect sustainable organizations, ste[...]",
    "Aquarius": "Visionary, eccentric, and humanitarian-minded, you channel revolutionary insights for the collective future. Primary purposes include invent progressive paradigms, champion univer[...]",
    "Pisces": "Boundlessly compassionate, imaginative, and spiritually attuned, you dissolve rigid boundaries to connect with universal empathy. Primary purposes include channel divine inspiration[...]",
}

# --- TERM EXPLANATIONS (For Clickable Toggles) ---
TERM_EXPLANATIONS = {
    "Sun": {
        "title": "Sun Sign",
        "body": "Your core identity — the energy you radiate most consistently. It shapes your ego, willpower, and life purpose.",
        "matters": "It defines your fundamental sense of self and the conscious creative force you bring to the world."
    },
    "Moon": {
        "title": "Moon Sign",
        "body": "Your emotional inner world — how you feel, nurture, and process. It reveals what you need to feel safe and whole.",
        "matters": "It governs your subconscious reactions, emotional resilience, and private sanctuary needs."
    },
    "Rising": {
        "title": "Rising Sign (Ascendant)",
        "body": "The mask you wear and the first impression you make. It is the lens through which the world sees you and you see the world.",
        "matters": "It dictates your spontaneous outward demeanor and the physical vitality filtering your chart."
    },
    "Birth Phase": {
        "title": "Birth Phase",
        "body": "The lunar phase at the exact moment you were born. It reveals your soul's innate rhythm — whether you are here to initiate, build, refine, or release.",
        "matters": "It aligns your natural energetic cadence with cosmic timing and developmental cycles."
    },
    "Full Moons Lived": {
        "title": "Full Moons Lived",
        "body": "The number of complete lunar cycles you have witnessed since birth. Each one is a chapter — a cycle of culmination and release you have lived through.",
        "matters": "It acts as a profound chronological milestone of emotional wisdom and maturational chapters."
    },
    "Dominant": {
        "title": "Dominant Planet",
        "body": "The celestial body with the strongest influence over your chart, based on your Sun, Moon, and Rising rulers. It colors your motivations and default mode of operating.",
        "matters": "It acts as the primary planetary lens focusing your astrological signature and behavioral instincts."
    },
    "HD Type": {
        "title": "HD Type (Human Design)",
        "body": "Your Human Design energy type — Manifestor, Generator, Manifesting Generator, Projector, or Reflector. It defines how you are designed to interact with the world and make decis[...]",
        "matters": "It removes resistance by showing you how your aura naturally functions and exchanges energy."
    },
    "HD Flavor": {
        "title": "HD Flavor (Strategy & Authority)",
        "body": "Your Strategy and Authority in Human Design — the specific way your type is meant to navigate life. It is your personal decision-making compass.",
        "matters": "It provides the precise mechanical instructions for making correct choices without burnout."
    }
}

def sign_color(sign: str | None) -> str:
    if not sign: return "#ffffff"
    return ZODIAC_COLORS.get(sign, "#ffffff")

def colored_sign(symbol: str, name: str, extra: str = "") -> str:
    c = sign_color(name)
    label = f"{symbol} {name}" if not extra else f"{symbol} {extra} {name}"
    return f'<span style="color:{c};font-weight:700;">{label}</span>'

def _dominant_planet(sun: str, moon: str, rising: str | None) -> dict:
    weights: list[str] = []
    for sign, w in ((sun, 3), (moon, 2), (rising, 2)):
        if not sign: continue
        ruler = SIGN_RULERS.get(sign)
        if ruler: weights.extend([ruler[0]] * w)
    if not weights: return {"name": "Sun", "symbol": "☉"}
    name = Counter(weights).most_common(1)[0][0]
    sym = next((s for n, s in SIGN_RULERS.values() if n == name), "✦")
    for sign_name, (rn, rs) in SIGN_RULERS.items():
        if rn == name:
            sym = rs
            break
    return {"name": name, "symbol": sym}

def _rarity(sun: str, moon: str, rising: str | None, phase: str) -> str:
    signs = [s for s in (sun, moon, rising) if s]
    unique = len(set(signs))
    triple = rising and sun == moon == rising
    double = sun == moon
    new_or_full = phase in ("New Moon", "Full Moon")

    if triple and new_or_full: return "Legendary"
    if triple: return "Epic"
    if double and rising and rising in (sun, moon) and new_or_full: return "Epic"
    if double and rising: return "Rare"
    if double or (rising and unique == 2 and new_or_full): return "Rare"
    if rising and unique == 3 and new_or_full: return "Uncommon"
    if rising: return "Uncommon"
    if double: return "Uncommon"
    return "Common"

def _full_moons_lived(birth_date: str) -> int:
    try:
        d = date.fromisoformat(birth_date[:10])
        birth_utc = datetime.combine(d, dtime(0, 0)).replace(tzinfo=timezone.utc)
        days = (datetime.now(timezone.utc) - birth_utc).days
        return max(0, int(days / 29.530588))
    except Exception: return 0

def _human_design_type(rising: str | None, sun: str) -> str:
    if rising and rising in HD_BY_RISING: return HD_BY_RISING[rising]
    return HD_BY_RISING.get(sun, "Generator")

def init_cards_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS user_profiles (
            user_hash TEXT PRIMARY KEY,
            display_name TEXT,
            birth_date TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    for col, typ in [("birth_time", "TEXT"), ("birth_place", "TEXT"), ("lat", "REAL"), ("lon", "REAL"), ("utc_offset", "REAL")]:
        try: c.execute(f"ALTER TABLE user_profiles ADD COLUMN {col} {typ}")
        except sqlite3.OperationalError: pass
    c.execute("""
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

def _sign_from_lon(lon_deg: float):
    idx = int((lon_deg % 360) / 30) % 12
    return ZODIAC[idx][0], ZODIAC[idx][1]

def _chart(dt_utc: datetime, lat: float | None = None, lon: float | None = None) -> dict:
    obs = ephem.Observer()
    if lat is not None and lon is not None:
        obs.lat = str(lat); obs.lon = str(lon)
    else:
        obs.lat = obs.lon = "0"
    obs.date = ephem.Date(dt_utc)
    moon, sun = ephem.Moon(obs), ephem.Sun(obs)
    elong = float(moon.elong)
    if elong < 0: elong += 2 * math.pi
    phase_frac = elong / (2 * math.pi)
    phases = [
        (0.00, "New Moon", "🌑"), (0.07, "Waxing Crescent", "🌒"),
        (0.25, "First Quarter", "🌓"), (0.43, "Waxing Gibbous", "🌔"),
        (0.50, "Full Moon", "🌕"), (0.57, "Waning Gibbous", "🌖"),
        (0.75, "Last Quarter", "🌗"), (0.93, "Waning Crescent", "🌘"),
        (1.00, "New Moon", "🌑"),
    ]
    phase_name, phase_emoji = "New Moon", "🌑"
    for i in range(len(phases) - 1):
        if phases[i][0] <= phase_frac < phases[i + 1][0]:
            phase_name, phase_emoji = phases[i][1], phases[i][2]
            break
    moon_lon = math.degrees(float(ephem.Ecliptic(moon).lon)) % 360
    sun_lon = math.degrees(float(ephem.Ecliptic(sun).lon)) % 360
    mi, si = int(moon_lon / 30) % 12, int(sun_lon / 30) % 12
    out = {
        "moon_sign": ZODIAC[mi][0], "moon_symbol": ZODIAC[mi][1],
        "sun_sign": ZODIAC[si][0], "sun_symbol": ZODIAC[si][1],
        "phase_name": phase_name, "phase_emoji": phase_emoji,
        "illum": moon.phase / 100.0, "moon_lon": moon_lon,
        "has_rising": False, "rising_sign": None, "rising_symbol": None,
    }
    if lat is not None and lon is not None:
        try:
            lst = float(obs.sidereal_time())
            lat_r = math.radians(float(lat))
            eps = math.radians(23.4392911)
            y = -math.cos(lst)
            x = math.sin(lst) * math.cos(eps) + math.tan(lat_r) * math.sin(eps)
            asc = math.degrees(math.atan2(y, x)) % 360
            r_sign, r_sym = _sign_from_lon(asc)
            out["has_rising"] = True
            out["rising_sign"] = r_sign
            out["rising_symbol"] = r_sym
        except Exception: pass
    return out

def _local_to_utc(birth_date: str, birth_time: str | None, utc_offset: float | None) -> datetime:
    d = date.fromisoformat(birth_date[:10])
    if birth_time:
        try:
            parts = birth_time.strip().split(":")
            hh, mm = int(parts[0]), int(parts[1]) if len(parts) > 1 else 0
            t = dtime(hh % 24, mm % 60)
        except Exception: t = dtime(12, 0)
    else: t = dtime(12, 0)
    local_naive = datetime.combine(d, t)
    offset = float(utc_offset) if utc_offset is not None else 0.0
    utc_naive = local_naive - timedelta(hours=offset)
    return utc_naive.replace(tzinfo=timezone.utc)

def get_or_create_profile(user_hash: str) -> dict:
    init_cards_db()
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute(
        "SELECT display_name, birth_date, birth_time, birth_place, lat, lon, utc_offset "
        "FROM user_profiles WHERE user_hash=?", (user_hash,)
    )
    row = c.fetchone()
    conn.close()
    if row:
        return {"display_name": row[0], "birth_date": row[1], "birth_time": row[2],
                "birth_place": row[3], "lat": row[4], "lon": row[5], "utc_offset": row[6]}
    return {"display_name": "Moon Wanderer", "birth_date": None, "birth_time": None,
            "birth_place": None, "lat": None, "lon": None, "utc_offset": None}

def save_profile(user_hash: str, display_name: str, birth_date: str | None, birth_time: str | None = None,
                 birth_place: str | None = None, lat: float | None = None, lon: float | None = None,
                 utc_offset: float | None = None):
    init_cards_db()
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT birth_time, birth_place, lat, lon, utc_offset FROM user_profiles WHERE user_hash=?", (user_hash,))
    prev = c.fetchone()
    if prev:
        if birth_time is None: birth_time = prev[0]
        if birth_place is None: birth_place = prev[1]
        if lat is None: lat = prev[2]
        if lon is None: lon = prev[3]
        if utc_offset is None: utc_offset = prev[4]
    c.execute("""
        CREATE TABLE IF NOT EXISTS user_profiles (
            user_hash TEXT PRIMARY KEY,
            display_name TEXT,
            birth_date TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )