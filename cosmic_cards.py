# cosmic_cards.py
# Collectible birth-chart cosmic cards + trade-as-friend-request

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

# Simplified, deterministic Human Design-style lookups for the Cosmic Card.
# These are a Lunatick card heuristic based on the natal Sun and Moon signs,
# not a replacement for a full Human Design bodygraph calculation.
HD_PROFILE_LINE_BY_SUN = {
    "Aries": 1, "Taurus": 2, "Gemini": 3, "Cancer": 4,
    "Leo": 5, "Virgo": 6, "Libra": 1, "Scorpio": 2,
    "Sagittarius": 3, "Capricorn": 4, "Aquarius": 5, "Pisces": 6,
}

HD_PROFILE_LINE_BY_MOON = {
    "Aries": 3, "Taurus": 4, "Gemini": 5, "Cancer": 6,
    "Leo": 1, "Virgo": 2, "Libra": 3, "Scorpio": 4,
    "Sagittarius": 5, "Capricorn": 6, "Aquarius": 1, "Pisces": 2,
}

HD_AUTHORITY_BY_TYPE = {
    "Manifestor": "Emotional Authority",
    "Generator": "Sacral Authority",
    "Manifesting Generator": "Sacral Authority",
    "Projector": "Emotional Authority",
    "Reflector": "Lunar Authority",
}

SUN_SIGN_DESCRIPTIONS = {
    "Aries": "Fiery, pioneering, and fiercely independent, you charge headfirst into new horizons with unstoppable courage. Primary purposes include ignite fresh initiatives, blaze trails for others, and champion bold new ideas.",
    "Taurus": "Disciplined, patient, and dedicated, you build slowly but with lasting impact. Primary purposes include master your craft, build enduring structures, and mentor others.",
    "Gemini": "Curious, adaptable, and intellectually lightning-fast, you weave connections between diverse ideas and people. Primary purposes include translate complex concepts, bridge communities, and spark vibrant dialogue.",
    "Cancer": "Deeply intuitive, nurturing, and protective, you create emotional sanctuaries where others feel truly seen and safe. Primary purposes include foster emotional healing, cultivate sacred spaces, and anchor supportive communities.",
    "Leo": "Radiant, generous, and naturally magnetic, you light up every room with heartfelt warmth and creative vision. Primary purposes include inspire authentic self-expression, lead with courage, and champion joyful celebration.",
    "Virgo": "Meticulous, analytical, and devotedly service-oriented, you refine chaos into elegant, highly efficient systems. Primary purposes include optimize collective workflows, heal through practical care, and elevate standards of excellence.",
    "Libra": "Harmonious, diplomatic, and aesthetically refined, you restore equilibrium and foster graceful collaboration. Primary purposes include bridge opposing perspectives, cultivate exquisite beauty, and architect fair partnerships.",
    "Scorpio": "Intense, transformative, and unblinkingly profound, you pierce beneath surface illusions to uncover deeper truths. Primary purposes include facilitate deep psychological healing, master hidden mysteries, and catalyze personal rebirth.",
    "Sagittarius": "Expansive, philosophical, and endlessly adventurous, you seek wisdom across distant horizons and grand paradigms. Primary purposes include inspire higher learning, expand cultural horizons, and transmit uplifting truths.",
    "Capricorn": "Strategic, resilient, and masterfully disciplined, you turn ambitious visions into enduring, tangible monuments. Primary purposes include architect sustainable organizations, steward vital resources, and model unwavering integrity.",
    "Aquarius": "Visionary, eccentric, and humanitarian-minded, you channel revolutionary insights for the collective future. Primary purposes include invent progressive paradigms, champion universal freedom, and unite communities around noble ideals.",
    "Pisces": "Boundlessly compassionate, imaginative, and spiritually attuned, you dissolve rigid boundaries to connect with universal empathy. Primary purposes include channel divine inspiration, offer unconditional sanctuary, and awaken collective imagination."
}

TERM_EXPLANATIONS = {
    "Sun": {"title": "Sun Sign", "body": "Your core identity — the energy you radiate most consistently.", "matters": "It defines your fundamental sense of self."},
    "Moon": {"title": "Moon Sign", "body": "Your emotional inner world — how you feel, nurture, and process.", "matters": "It governs your subconscious reactions."},
    "Rising": {"title": "Rising Sign (Ascendant)", "body": "The mask you wear and the first impression you make.", "matters": "It dictates your spontaneous outward demeanor."},
    "Birth Phase": {"title": "Birth Phase", "body": "The lunar phase at the exact moment you were born.", "matters": "It aligns your natural energetic cadence with cosmic timing."},
    "Full Moons Lived": {"title": "Full Moons Lived", "body": "The number of complete lunar cycles you have witnessed since birth.", "matters": "It acts as a profound chronological milestone."},
    "Dominant": {"title": "Dominant Planet", "body": "The celestial body with the strongest influence over your chart.", "matters": "It colors your motivations and default mode of operating."},
    "HD Type": {"title": "HD Type (Human Design)", "body": "Your Human Design energy type.", "matters": "It removes resistance by showing you how your aura naturally functions."},
    "HD Flavor": {"title": "HD Flavor (Strategy & Authority)", "body": "Your Strategy and Authority in Human Design.", "matters": "It provides the precise mechanical instructions for making correct choices."}
}

def sign_color(sign):
    if not sign:
        return "#ffffff"
    return ZODIAC_COLORS.get(sign, "#ffffff")

def colored_sign(symbol, name, extra=""):
    c = sign_color(name)
    label = f"{symbol} {name}" if not extra else f"{symbol} {extra} {name}"
    return f'<span style="color:{c};font-weight:700;">{label}</span>'

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
    for col, typ in [
        ("birth_time", "TEXT"), ("birth_place", "TEXT"), ("lat", "REAL"),
        ("lon", "REAL"), ("utc_offset", "REAL"), ("hd_profile", "TEXT"),
        ("hd_authority", "TEXT"),
    ]:
        try:
            c.execute(f"ALTER TABLE user_profiles ADD COLUMN {col} {typ}")
        except sqlite3.OperationalError:
            pass
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

def _sign_from_lon(lon_deg):
    idx = int((lon_deg % 360) / 30) % 12
    return ZODIAC[idx][0], ZODIAC[idx][1]

def _chart(dt_utc, lat=None, lon=None):
    obs = ephem.Observer()
    if lat is not None and lon is not None:
        obs.lat = str(lat)
        obs.lon = str(lon)
    else:
        obs.lat = obs.lon = "0"
    obs.date = ephem.Date(dt_utc)
    moon, sun = ephem.Moon(obs), ephem.Sun(obs)
    elong = float(moon.elong)
    if elong < 0:
        elong += 2 * math.pi
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
        except Exception:
            pass
    return out

def _local_to_utc(birth_date, birth_time, utc_offset):
    d = date.fromisoformat(birth_date[:10])
    if birth_time:
        try:
            parts = birth_time.strip().split(":")
            hh, mm = int(parts[0]), int(parts[1]) if len(parts) > 1 else 0
            t = dtime(hh % 24, mm % 60)
        except Exception:
            t = dtime(12, 0)
    else:
        t = dtime(12, 0)
    local_naive = datetime.combine(d, t)
    offset = float(utc_offset) if utc_offset is not None else 0.0
    utc_naive = local_naive - timedelta(hours=offset)
    return utc_naive.replace(tzinfo=timezone.utc)

def get_or_create_profile(user_hash):
    init_cards_db()
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
        SELECT display_name, birth_date, birth_time, birth_place, lat, lon,
               utc_offset, hd_profile, hd_authority
        FROM user_profiles WHERE user_hash=?
    """, (user_hash,))
    row = c.fetchone()
    conn.close()
    if row:
        return {
            "display_name": row[0], "birth_date": row[1], "birth_time": row[2],
            "birth_place": row[3], "lat": row[4], "lon": row[5], "utc_offset": row[6],
            "hd_profile": row[7], "hd_authority": row[8],
        }
    return {
        "display_name": "Moon Wanderer", "birth_date": None, "birth_time": None,
        "birth_place": None, "lat": None, "lon": None, "utc_offset": None,
        "hd_profile": None, "hd_authority": None,
    }

def save_profile(user_hash, display_name, birth_date, birth_time=None, birth_place=None, lat=None, lon=None, utc_offset=None):
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
        INSERT INTO user_profiles (user_hash, display_name, birth_date, birth_time, birth_place, lat, lon, utc_offset)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_hash) DO UPDATE SET display_name=excluded.display_name, birth_date=excluded.birth_date,
            birth_time=excluded.birth_time, birth_place=excluded.birth_place, lat=excluded.lat,
            lon=excluded.lon, utc_offset=excluded.utc_offset
    """, (user_hash, display_name, birth_date, birth_time, birth_place, lat, lon, utc_offset))
    conn.commit()
    conn.close()

def build_card(user_hash):
    profile = get_or_create_profile(user_hash)
    if not profile["birth_date"]:
        return None
    try:
        has_loc = profile["lat"] is not None and profile["lon"] is not None
        dt_utc = _local_to_utc(profile["birth_date"], profile.get("birth_time"), profile.get("utc_offset"))
        natal = _chart(dt_utc, float(profile["lat"]) if has_loc else None, float(profile["lon"]) if has_loc else None)
        rising = natal.get("rising_sign") if natal.get("has_rising") else None
        dominant = _dominant_planet(natal["sun_sign"], natal["moon_sign"], rising)
        rarity = _rarity(natal["sun_sign"], natal["moon_sign"], rising, natal["phase_name"])
        full_moons = _full_moons_lived(profile["birth_date"])
        hd_type = _human_design_type(rising, natal["sun_sign"])
        hd_profile = _human_design_profile(natal["sun_sign"], natal["moon_sign"])
        hd_authority = _human_design_authority(hd_type)

        # Persist the computed card attributes. Existing databases are upgraded
        # by init_cards_db() before this function reaches the update.
        _save_hd_details(user_hash, hd_profile, hd_authority)

        return {
            "user_hash": user_hash, "display_name": profile["display_name"],
            "birth_date": profile["birth_date"], "birth_time": profile.get("birth_time"),
            "birth_place": profile.get("birth_place"), "natal": natal, "dominant": dominant,
            "rarity": rarity, "full_moons_lived": full_moons, "hd_type": hd_type,
            "hd_profile": hd_profile, "hd_authority": hd_authority,
        }
    except Exception:
        return None

def _dominant_planet(sun, moon, rising):
    weights = []
    for sign, w in ((sun, 3), (moon, 2), (rising, 2)):
        if not sign:
            continue
        ruler = SIGN_RULERS.get(sign)
        if ruler:
            weights.extend([ruler[0]] * w)
    if not weights:
        return {"name": "Sun", "symbol": "☉"}
    name = Counter(weights).most_common(1)[0][0]
    sym = next((s for n, s in SIGN_RULERS.values() if n == name), "✦")
    for sign_name, (rn, rs) in SIGN_RULERS.items():
        if rn == name:
            sym = rs
            break
    return {"name": name, "symbol": sym}

def _rarity(sun, moon, rising, phase):
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

def _full_moons_lived(birth_date):
    try:
        d = date.fromisoformat(birth_date[:10])
        birth_utc = datetime.combine(d, dtime(0, 0)).replace(tzinfo=timezone.utc)
        days = (datetime.now(timezone.utc) - birth_utc).days
        return max(0, int(days / 29.530588))
    except Exception:
        return 0

def _human_design_type(rising, sun):
    if rising and rising in HD_BY_RISING:
        return HD_BY_RISING[rising]
    return HD_BY_RISING.get(sun, "Generator")

def _human_design_profile(sun, moon):
    """Return a simplified six-line profile from natal Sun and Moon signs."""
    sun_line = HD_PROFILE_LINE_BY_SUN.get(sun, 1)
    moon_line = HD_PROFILE_LINE_BY_MOON.get(moon, 4)
    return f"{sun_line}/{moon_line}"


def _human_design_authority(hd_type):
    """Return the card's simplified authority from its computed HD Type."""
    return HD_AUTHORITY_BY_TYPE.get(hd_type, "Sacral Authority")


def _save_hd_details(user_hash, hd_profile, hd_authority):
    """Persist the computed simplified HD details for the user's card."""
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute(
        "UPDATE user_profiles SET hd_profile=?, hd_authority=? WHERE user_hash=?",
        (hd_profile, hd_authority, user_hash),
    )
    conn.commit()
    conn.close()


def show_term_explanation(term_key):
    info = TERM_EXPLANATIONS.get(term_key)
    if not info:
        return
    with st.expander(f"📖 {info['title']} — What does this mean?"):
        st.markdown(f"**{info['title']}**")
        st.markdown(info["body"])
        st.markdown(f"*Why it matters:* {info['matters']}")

def render_collectible_card(card):
    n = card["natal"]
    sun_c = sign_color(n["sun_sign"])
    moon_c = sign_color(n["moon_sign"])
    rise_c = sign_color(n.get("rising_sign")) if n.get("has_rising") else "#8b949e"
    rarity = card.get("rarity", "Common")
    r_color, r_label = RARITY_STYLE.get(rarity, RARITY_STYLE["Common"])
    dom = card.get("dominant") or {"name": "—", "symbol": "✦"}
    moons = card.get("full_moons_lived", 0)
    hd = card.get("hd_type", "—")
    time_line = card.get("birth_time") or "—"
    place = card.get("birth_place") or "Location unknown"

    if n.get("has_rising"):
        rising_block = f"""
        <div style="text-align:center;flex:1;">
          <div style="font-size:0.55rem;color:#8b949e;letter-spacing:1px;">RISING</div>
          <div style="font-size:1.15rem;font-weight:700;color:{rise_c};">{n['rising_symbol']}</div>
          <div style="font-size:1.15rem;font-weight:700;color:{rise_c};">{n['rising_sign']}</div>
        </div>"""
    else:
        rising_block = """
        <div style="text-align:center;flex:1;">
          <div style="font-size:0.55rem;color:#8b949e;letter-spacing:1px;">RISING</div>
          <div style="font-size:0.85rem;color:#484f58;">Add time & place</div>
        </div>"""

    col1, col2 = st.columns([4, 1])
    with col2:
        if st.button("🔄 Flip", key=f"flip_{card['user_hash']}"):
            st.session_state.show_card_back = not st.session_state.get("show_card_back", False)
            st.rerun()

    st.html(f"""
    <div style="background: linear-gradient(160deg, #0a0e17 0%, #12101f 40%, #0d1f3c 100%); border: 2px solid {sun_c}; border-radius: 20px; padding: 1.25rem 1.35rem 1.4rem; margin: 0.8rem 0 1.2rem; box-shadow: 0 0 32px {sun_c}44, inset 0 0 40px rgba(0,0,0,0.35); position: relative; overflow: hidden;">
      <div style="position:absolute;top:-30px;right:-30px;width:120px;height:120px; background:radial-gradient(circle,{sun_c}33,transparent 70%);pointer-events:none;"></div>
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.7rem;">
        <div style="font-family:Orbitron,sans-serif;font-size:0.65rem;letter-spacing:3px;color:#58a6ff;">COSMIC CARD</div>
        <div style="font-family:Orbitron,sans-serif;font-size:0.55rem;letter-spacing:2px; color:{r_color};border:1px solid {r_color};border-radius:999px; padding:0.2rem 0.65rem;background:{r_color}22;">{r_label}</div>
      </div>
      <div style="font-size:1.35rem;font-weight:700;color:#f0f6fc;margin-bottom:0.15rem;">{card['display_name']}</div>
      <div style="color:#8b949e;font-size:0.8rem;margin-bottom:1rem;">📍 {place} · 🕐 {time_line}</div>
      <div style="display:flex;gap:0.4rem;justify-content:space-between;margin-bottom:1rem; background:rgba(0,0,0,0.35);border-radius:12px;padding:0.75rem 0.5rem; border:1px solid rgba(255,255,255,0.06);">
        <div style="text-align:center;flex:1;"><div style="font-size:0.55rem;color:#8b949e;letter-spacing:1px;">SUN</div><div style="font-size:1.15rem;font-weight:700;color:{sun_c};">{n['sun_symbol']} {n['sun_sign']}</div></div>
        <div style="text-align:center;flex:1;"><div style="font-size:0.55rem;color:#8b949e;letter-spacing:1px;">MOON</div><div style="font-size:1.15rem;font-weight:700;color:{moon_c};">{n['moon_symbol']} {n['moon_sign']}</div></div>
        {rising_block}
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.55rem;">
        <div style="background:rgba(255,255,255,0.04);border-radius:10px;padding:0.55rem 0.7rem;border:1px solid rgba(255,255,255,0.07);"><div style="font-size:0.5rem;color:#8b949e;letter-spacing:1px;">BIRTH PHASE</div><div style="font-size:0.95rem;font-weight:600;color:#e6edf3;">{n['phase_emoji']} {n['phase_name']}</div></div>
        <div style="background:rgba(255,255,255,0.04);border-radius:10px;padding:0.55rem 0.7rem;border:1px solid rgba(255,255,255,0.07);"><div style="font-size:0.5rem;color:#8b949e;letter-spacing:1px;">FULL MOONS LIVED</div><div style="font-size:0.95rem;font-weight:700;color:#bc8cff;">{moons}</div></div>
        <div style="background:rgba(255,255,255,0.04);border-radius:10px;padding:0.55rem 0.7rem;border:1px solid rgba(255,255,255,0.07);"><div style="font-size:0.5rem;color:#8b949e;letter-spacing:1px;">DOMINANT</div><div style="font-size:0.95rem;font-weight:600;color:#f0f6fc;">{dom['symbol']} {dom['name']}</div></div>
        <div style="background:rgba(255,255,255,0.04);border-radius:10px;padding:0.55rem 0.7rem;border:1px solid rgba(255,255,255,0.07);"><div style="font-size:0.5rem;color:#8b949e;letter-spacing:1px;">HD TYPE</div><div style="font-size:0.95rem;font-weight:600;color:#d2a8ff;">{hd}</div></div>
      </div>
      <div style="margin-top:0.9rem;text-align:center;font-size:0.65rem;color:#484f58;letter-spacing:1px;">LUNATICK COLLECTIBLE · TAP TO LEARN</div>
    </div>
    """)

    st.markdown("##### 🔍 Tap any term below to explore its cosmic meaning:")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        if st.button("☀️ Sun", use_container_width=True): show_term_explanation("Sun")
        if st.button("🌙 Birth Phase", use_container_width=True): show_term_explanation("Birth Phase")
    with c2:
        if st.button("🌑 Moon", use_container_width=True): show_term_explanation("Moon")
        if st.button("🌕 Full Moons", use_container_width=True): show_term_explanation("Full Moons Lived")
    with c3:
        if st.button("⬆️ Rising", use_container_width=True): show_term_explanation("Rising")
        if st.button("⭐ Dominant", use_container_width=True): show_term_explanation("Dominant")
    with c4:
        if st.button("🧬 HD Type", use_container_width=True): show_term_explanation("HD Type")
        if st.button("🌀 HD Flavor", use_container_width=True): show_term_explanation("HD Flavor")

    st.markdown("---")
    st.markdown("##### ✨ Cosmic Archetype & Purpose")
    desc = SUN_SIGN_DESCRIPTIONS.get(n["sun_sign"], "Radiant and purposeful, you embody unique cosmic gifts.")
    st.info(f"**{n['sun_sign']} Sun Archetype:** {desc}")

def render_card_back(card):
    n = card["natal"]
    sun_c = sign_color(n["sun_sign"])
    moon_c = sign_color(n["moon_sign"])
    rise_c = sign_color(n.get("rising_sign")) if n.get("has_rising") else "#8b949e"
    rarity = card.get("rarity", "Common")
    r_color, r_label = RARITY_STYLE.get(rarity, RARITY_STYLE["Common"])
    dom = card.get("dominant") or {"name": "—", "symbol": "✦"}
    hd = card.get("hd_type", "—")
    hd_profile = card.get("hd_profile", "—")
    hd_authority = card.get("hd_authority", "—")
    phase = n.get("phase_name", "")

    col1, col2 = st.columns([4, 1])
    with col2:
        if st.button("🔄 Flip", key=f"flipback_{card['user_hash']}"):
            st.session_state.show_card_back = False
            st.rerun()

    st.html(f"""
    <div style="background: linear-gradient(160deg, #0a0e17 0%, #12101f 40%, #0d1f3c 100%); border: 2px solid {sun_c}; border-radius: 20px; padding: 1.25rem 1.35rem 1.4rem; margin: 0.8rem 0 1.2rem; box-shadow: 0 0 32px {sun_c}44, inset 0 0 40px rgba(0,0,0,0.35); position: relative; overflow: hidden;">
      <div style="position:absolute;top:-30px;right:-30px;width:120px;height:120px; background:radial-gradient(circle,{sun_c}33,transparent 70%);pointer-events:none;"></div>
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.7rem;">
        <div style="font-family:Orbitron,sans-serif;font-size:0.65rem;letter-spacing:3px;color:#58a6ff;">COSMIC BREAKDOWN</div>
        <div style="font-family:Orbitron,sans-serif;font-size:0.55rem;letter-spacing:2px; color:{r_color};border:1px solid {r_color};border-radius:999px; padding:0.2rem 0.65rem;background:{r_color}22;">{r_label}</div>
      </div>
      <div style="font-size:1.35rem;font-weight:700;color:#f0f6fc;margin-bottom:0.15rem;">{card['display_name']}</div>
      <div style="color:#8b949e;font-size:0.8rem;margin-bottom:0.8rem;">📍 {card.get('birth_place') or 'Location unknown'} · 🕐 {card.get('birth_time') or '—'}</div>
      <div style="background:rgba(255,255,255,0.03);border-radius:12px;padding:0.7rem;margin-bottom:0.6rem;border:1px solid rgba(255,255,255,0.06);">
        <div style="font-size:0.65rem;color:#8b949e;font-weight:700;letter-spacing:1px;">⭐ DOMINANT PLANET — {dom['symbol']} {dom['name']}</div>
        <div style="font-size:0.9rem;color:#e6edf3;line-height:1.5;margin-top:0.2rem;">Driven by {dom['name']} energy.</div>
      </div>
      <div style="background:rgba(255,255,255,0.03);border-radius:12px;padding:0.7rem;margin-bottom:0.6rem;border:1px solid rgba(255,255,255,0.06);">
        <div style="font-size:0.65rem;color:#8b949e;font-weight:700;letter-spacing:1px;">🧬 HD TYPE — {hd}</div>
        <div style="font-size:0.9rem;color:#e6edf3;line-height:1.5;margin-top:0.2rem;">You operate best by following your HD strategy.</div>
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.6rem;margin-bottom:0.6rem;">
        <div style="background:rgba(188,140,255,0.09);border-radius:12px;padding:0.7rem;border:1px solid rgba(188,140,255,0.24);">
          <div style="font-size:0.55rem;color:#8b949e;font-weight:700;letter-spacing:1px;">◈ HD PROFILE</div>
          <div style="font-size:1.05rem;font-weight:700;color:#d2a8ff;line-height:1.35;margin-top:0.2rem;">{hd_profile}</div>
        </div>
        <div style="background:rgba(88,166,255,0.08);border-radius:12px;padding:0.7rem;border:1px solid rgba(88,166,255,0.23);">
          <div style="font-size:0.55rem;color:#8b949e;font-weight:700;letter-spacing:1px;">✦ HD AUTHORITY</div>
          <div style="font-size:0.85rem;font-weight:700;color:#a8d3ff;line-height:1.35;margin-top:0.2rem;">{hd_authority}</div>
        </div>
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.6rem;margin-bottom:0.6rem;">
        <div style="background:rgba(255,255,255,0.03);border-radius:12px;padding:0.7rem;border:1px solid rgba(255,255,255,0.06);">
          <div style="font-size:0.55rem;color:#8b949e;font-weight:700;letter-spacing:1px;">🌙 BIRTH PHASE — {n['phase_emoji']} {phase}</div>
          <div style="font-size:0.8rem;color:#e6edf3;line-height:1.4;margin-top:0.2rem;">Born under the {phase}.</div>
        </div>
        <div style="background:rgba(255,255,255,0.03);border-radius:12px;padding:0.7rem;border:1px solid rgba(255,255,255,0.06);">
          <div style="font-size:0.55rem;color:#8b949e;font-weight:700;letter-spacing:1px;">💎 RARITY — {rarity}</div>
          <div style="font-size:0.8rem;color:#e6edf3;line-height:1.4;margin-top:0.2rem;">Based on your chart's alignments.</div>
        </div>
      </div>
      <div style="margin-top:0.9rem;text-align:center;font-size:0.65rem;color:#484f58;letter-spacing:1px;">LUNATICK COLLECTIBLE · FLIP TO CONNECT</div>
    </div>
    """)

def list_users_with_cards(exclude_hash):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
        SELECT user_hash, display_name, birth_date FROM user_profiles
        WHERE birth_date IS NOT NULL AND user_hash != ?
    """, (exclude_hash,))
    rows = c.fetchall()
    conn.close()
    out = []
    for h, name, bd in rows:
        card = build_card(h)
        if card:
            out.append(card)
    return out

def send_trade(sender, receiver, message=""):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
        SELECT id FROM card_trades
        WHERE sender_hash=? AND receiver_hash=? AND status='pending'
    """, (sender, receiver))
    if c.fetchone():
        conn.close()
        return False, "Already have a pending trade with this person."
    c.execute("""
        INSERT INTO card_trades (sender_hash, receiver_hash, message, status)
        VALUES (?, ?, ?, 'pending')
    """, (sender, receiver, message.strip() or None))
    conn.commit()
    conn.close()
    return True, "Trade (friend request) sent!"

def list_trades(user_hash, direction="all"):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    if direction == "incoming":
        c.execute("""
            SELECT id, sender_hash, receiver_hash, message, status, created_at
            FROM card_trades WHERE receiver_hash=? ORDER BY created_at DESC
        """, (user_hash,))
    elif direction == "outgoing":
        c.execute("""
            SELECT id, sender_hash, receiver_hash, message, status, created_at
            FROM card_trades WHERE sender_hash=? ORDER BY created_at DESC
        """, (user_hash,))
    else:
        c.execute("""
            SELECT id, sender_hash, receiver_hash, message, status, created_at
            FROM card_trades
            WHERE sender_hash=? OR receiver_hash=?
            ORDER BY created_at DESC
        """, (user_hash, user_hash))
    rows = c.fetchall()
    conn.close()
    return [{"id": r[0], "sender": r[1], "receiver": r[2], "message": r[3],
             "status": r[4], "created_at": r[5]} for r in rows]

def resolve_trade(trade_id, user_hash, accept):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT receiver_hash, status FROM card_trades WHERE id=?", (trade_id,))
    row = c.fetchone()
    if not row or row[0] != user_hash or row[1] != "pending":
        conn.close()
        return False
    status = "accepted" if accept else "declined"
    c.execute("""
        UPDATE card_trades SET status=?, resolved_at=CURRENT_TIMESTAMP WHERE id=?
    """, (status, trade_id))
    conn.commit()
    conn.close()
    return True

def friends_of(user_hash):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
        SELECT sender_hash, receiver_hash FROM card_trades
        WHERE status='accepted' AND (sender_hash=? OR receiver_hash=?)
    """, (user_hash, user_hash))
    friends = set()
    for s, r in c.fetchall():
        friends.add(r if s == user_hash else s)
    conn.close()
    return list(friends)

def render_profile_form(user_hash, key_prefix="cards"):
    init_cards_db()
    profile = get_or_create_profile(user_hash)

    name = st.text_input("Display name", value=profile["display_name"] or "Moon Wanderer", key=f"{key_prefix}_name")
    default_bd = date.fromisoformat(profile["birth_date"]) if profile["birth_date"] else date(1990, 1, 1)
    bd = st.date_input("Birth date", value=default_bd, min_value=date(1920, 1, 1), max_value=date.today(), key=f"{key_prefix}_bd")

    st.caption("Birth time + place unlock Rising, Dominant precision, and higher rarity.")
    c1, c2 = st.columns(2)
    with c1:
        bt_default = profile.get("birth_time") or "12:00"
        try:
            hh, mm = [int(x) for x in bt_default.split(":")[:2]]
            t_val = dtime(hh % 24, mm % 60)
        except Exception:
            t_val = dtime(12, 0)
        bt = st.time_input("Birth time (local)", value=t_val, key=f"{key_prefix}_bt")
    with c2:
        off_default = float(profile["utc_offset"]) if profile.get("utc_offset") is not None else 0.0
        utc_off = st.number_input("UTC offset (hours)", min_value=-12.0, max_value=14.0, value=off_default, step=0.5, help="e.g. -5 for US Eastern, +1 for Central Europe", key=f"{key_prefix}_off")

    place = st.text_input("Birth place (city / label)", value=profile.get("birth_place") or "", placeholder="e.g. New York, NY", key=f"{key_prefix}_place")
    c3, c4 = st.columns(2)
    with c3:
        lat_default = float(profile["lat"]) if profile.get("lat") is not None else 0.0
        lat = st.number_input("Latitude", min_value=-90.0, max_value=90.0, value=lat_default, step=0.0001, format="%.4f", key=f"{key_prefix}_lat")
    with c4:
        lon_default = float(profile["lon"]) if profile.get("lon") is not None else 0.0
        lon = st.number_input("Longitude", min_value=-180.0, max_value=180.0, value=lon_default, step=0.0001, format="%.4f", key=f"{key_prefix}_lon")

    if st.button("💾 Save birth chart", type="primary", key=f"{key_prefix}_save"):
        bt_str = f"{bt.hour:02d}:{bt.minute:02d}"
        use_loc = place.strip() or (lat != 0.0 or lon != 0.0)
        save_profile(user_hash, name.strip() or "Moon Wanderer", bd.isoformat(), birth_time=bt_str, birth_place=place.strip() or None, lat=float(lat) if use_loc else None, lon=float(lon) if use_loc else None, utc_offset=float(utc_off))
        st.session_state.display_name = name.strip() or "Moon Wanderer"
        st.session_state.birth_date = bd
        st.success("Birth chart saved — Cosmic Card updated.")
        st.rerun()

def render_cosmic_cards_tab():
    init_cards_db()
    user_hash = st.session_state.get("user_hash", "anonymous")

    if "show_card_back" not in st.session_state:
        st.session_state.show_card_back = False

    st.markdown("### 🃏 Cosmic Cards & Friend Trades")
    st.caption("Your birth-chart card is a collectible identity. Trade it as a friend request.")

    profile = get_or_create_profile(user_hash)
    with st.expander("🧬 Your Cosmic Profile", expanded=not profile["birth_date"]):
        render_profile_form(user_hash, key_prefix="cards")

    my_card = build_card(user_hash)
    if my_card:
        if st.session_state.get("show_card_back", False):
            render_card_back(my_card)
        else:
            render_collectible_card(my_card)
    else:
        st.info("Add your birth date above to unlock your Cosmic Card.")

    st.markdown("---")
    st.subheader("Send a Card Trade (Friend Request)")
    others = list_users_with_cards(user_hash)
    if not others:
        st.caption("No other cards yet. Share the app so friends can create theirs.")
    else:
        options = {f"{c['display_name']} ({c['natal']['sun_symbol']}{c['natal']['sun_sign']} · {c['natal']['moon_symbol']}{c['natal']['moon_sign']} · {c.get('rarity', '')})": c["user_hash"] for c in others}
        pick = st.selectbox("Send card to", list(options.keys()))
        msg = st.text_input("Optional message", max_chars=200)
        if st.button("🃏 Send Trade"):
            ok, note = send_trade(user_hash, options[pick], msg)
            (st.success if ok else st.warning)(note)
            if ok:
                st.rerun()

    st.markdown("---")
    st.subheader("Incoming Trades")
    incoming = [t for t in list_trades(user_hash, "incoming") if t["status"] == "pending"]
    if not incoming:
        st.caption("No pending requests.")
    for t in incoming:
        sender_card = build_card(t["sender"])
        label = sender_card["display_name"] if sender_card else t["sender"][:8]
        cols = st.columns([3, 1, 1])
        cols[0].write(f"**{label}** wants to trade cards. {t['message'] or ''}")
        if cols[1].button("Accept", key=f"acc_{t['id']}"):
            resolve_trade(t["id"], user_hash, True)
            st.rerun()
        if cols[2].button("Decline", key=f"dec_{t['id']}"):
            resolve_trade(t["id"], user_hash, False)
            st.rerun()

    st.markdown("---")
    st.subheader("Friends (accepted trades)")
    friends = friends_of(user_hash)
    if not friends:
        st.caption("No friends yet — send or accept a card trade.")
    for fh in friends:
        fc = build_card(fh)
        if fc:
            n = fc["natal"]
            parts = [colored_sign(n["sun_symbol"], n["sun_sign"]), colored_sign(n["moon_symbol"], n["moon_sign"])]
            if n.get("has_rising"):
                parts.append(colored_sign(n["rising_symbol"], n["rising_sign"]))
            rarity = fc.get("rarity", "")
            st.markdown(f"• **{fc['display_name']}** — " + " · ".join(parts) + f" · *{rarity}*", unsafe_allow_html=True)