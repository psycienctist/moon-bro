import streamlit as st
import ephem
import math
import json
import os
from datetime import datetime, timezone, timedelta

# ---------------------------------------------------------------------------
# Page config & Lunatick Theme
# ---------------------------------------------------------------------------
st.set_page_config(page_title="🌑 Lunatick", page_icon="🌑", layout="wide")

CONFIG_FILE = "user_config.json"

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f)

LUNATICK_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Inter:wght@300;400;600&display=swap');

    .stApp {
        background-color: #05070a;
        color: #e6edf3;
        font-family: 'Inter', sans-serif;
    }

    h1, h2, h3, h4 {
        font-family: 'Orbitron', sans-serif;
        text-transform: uppercase;
        letter-spacing: 2px;
    }

    .glow-container {
        background: radial-gradient(circle at top right, #1b1040 0%, #05070a 100%);
        border: 1px solid #6e40c9;
        border-radius: 24px;
        padding: 2.5rem;
        margin-bottom: 2rem;
        box-shadow: 0 0 40px rgba(110, 64, 201, 0.2);
        text-align: center;
    }

    .countdown-display {
        display: flex;
        flex-direction: row;
        justify-content: center;
        align-items: center;
        gap: 1rem;
        margin: 1.5rem 0;
        flex-wrap: nowrap;
    }
    .unit-box {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 1rem 0.5rem;
        flex: 1;
        max-width: 120px;
        min-width: 80px;
        box-shadow: inset 0 0 10px rgba(0, 0, 0, 0.5);
    }
    .unit-box .num {
        font-family: 'Orbitron', sans-serif;
        font-size: 2.2rem;
        font-weight: 700;
        background: linear-gradient(180deg, #fff 30%, #58a6ff 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        line-height: 1;
    }
    .unit-box .label {
        font-size: 0.6rem;
        color: #8b949e;
        margin-top: 0.4rem;
        font-weight: 600;
        text-transform: uppercase;
    }

    .stat-card {
        background: #0d1117;
        border: 1px solid #30363d;
        border-radius: 20px;
        padding: 1.5rem;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
        text-align: center;
    }
    .stat-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 30px rgba(88, 166, 255, 0.1);
        border-color: #58a6ff;
    }
    .stat-val {
        font-size: 1.6rem;
        font-weight: 700;
        margin: 0.5rem 0;
        color: #f0f6fc;
    }
    .stat-label {
        color: #8b949e;
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    .personal-card {
        background: linear-gradient(135deg, #0d1f3c 0%, #05070a 100%);
        border: 1px solid #1f6feb;
        border-radius: 20px;
        padding: 1.5rem;
        margin-top: 2rem;
        box-shadow: 0 10px 40px rgba(31, 111, 235, 0.15);
    }

    .vibe-card {
        background: linear-gradient(135deg, #2d1b69 0%, #1a1f36 100%);
        border-radius: 20px;
        padding: 2rem;
        border: 1px solid #bc8cff;
        box-shadow: 0 10px 40px rgba(188, 140, 255, 0.15);
    }
    .vibe-tag {
        background: rgba(210, 168, 255, 0.2);
        color: #d2a8ff;
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        display: inline-block;
        margin-bottom: 1rem;
    }

    .event-item {
        background: #161b22;
        border-radius: 12px;
        padding: 1rem;
        margin-bottom: 1rem;
        border-left: 5px solid #ff7b72;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .event-info .etitle { font-weight: 600; color: #f0f6fc; font-size: 0.9rem; }
    .event-info .edesc { color: #8b949e; font-size: 0.8rem; margin-top: 0.2rem; }
    .event-date { color: #ff7b72; font-family: 'Orbitron', sans-serif; font-size: 0.7rem; }

    ::-webkit-scrollbar { width: 8px; }
    ::-webkit-scrollbar-track { background: #05070a; }
    ::-webkit-scrollbar-thumb { background: #30363d; border-radius: 10px; }
</style>
"""
st.markdown(LUNATICK_CSS, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Logic – Same high-precision Ephem engine
# ---------------------------------------------------------------------------

ZODIAC_SIGNS = [
    ("Aries", "♈", "Bold, assertive energy. Great for starting new projects."),
    ("Taurus", "♉", "Grounded, sensual vibes. Focus on comfort and stability."),
    ("Gemini", "♊", "Curious, communicative mood. Ideal for learning and socialising."),
    ("Cancer", "♋", "Nurturing, emotional depth. Prioritise home and family."),
    ("Leo", "♌", "Creative, warm-hearted energy. Shine and express yourself."),
    ("Virgo", "♍", "Analytical, detail-oriented. Perfect for organising and health."),
    ("Libra", "♎", "Harmonious, balanced mood. Focus on relationships and beauty."),
    ("Scorpio", "♏", "Intense, transformative energy. Dive deep within."),
    ("Sagittarius", "♐", "Adventurous, optimistic vibes. Seek truth and explore."),
    ("Capricorn", "♑", "Disciplined, ambitious. Build towards long-term goals."),
    ("Aquarius", "♒", "Innovative, humanitarian energy. Think outside the box."),
    ("Pisces", "♓", "Dreamy, intuitive mood. Meditate and create art."),
]

def get_zodiac_sign(lon_deg):
    idx = int(lon_deg / 30) % 12
    return ZODIAC_SIGNS[idx]

def get_moon_phase_name(phase_frac: float) -> tuple[str, str]:
    phases = [
        (0.00, "New Moon", "🌑"), (0.07, "Waxing Crescent", "🌒"), (0.25, "First Quarter", "🌓"),
        (0.43, "Waxing Gibbous", "🌔"), (0.50, "Full Moon", "🌕"), (0.57, "Waning Gibbous", "🌖"),
        (0.75, "Last Quarter", "🌗"), (0.93, "Waning Crescent", "🌘"), (1.00, "New Moon", "🌑"),
    ]
    for i in range(len(phases) - 1):
        if phases[i][0] <= phase_frac < phases[i+1][0]:
            return phases[i][1], phases[i][2]
    return "New Moon", "🌑"

def get_celestial_data(date_utc: datetime):
    obs = ephem.Observer()
    obs.lat, obs.lon = "0", "0"
    obs.date = ephem.Date(date_utc)
    
    moon = ephem.Moon(obs)
    sun = ephem.Sun(obs)
    
    # Moon Calculations
    illum = moon.phase / 100.0
    elong = float(moon.elong)
    if elong < 0: elong += 2 * math.pi
    phase_frac = elong / (2 * math.pi)
    phase_name, phase_emoji = get_moon_phase_name(phase_frac)
    
    moon_ecl = ephem.Ecliptic(moon)
    moon_lon = math.degrees(float(moon_ecl.lon)) % 360
    moon_sign, moon_symbol, moon_vibe = get_zodiac_sign(moon_lon)
    
    # Sun Calculations
    sun_ecl = ephem.Ecliptic(sun)
    sun_lon = math.degrees(float(sun_ecl.lon)) % 360
    sun_sign, sun_symbol, _ = get_zodiac_sign(sun_lon)
    
    # Next Full Moon (only relevant for current date)
    nfm = ephem.next_full_moon(obs.date)
    nfm_dt = ephem.Date(nfm).datetime().replace(tzinfo=timezone.utc)
    
    return {
        "moon_sign": moon_sign, "moon_symbol": moon_symbol, "moon_vibe": moon_vibe, "moon_lon": moon_lon,
        "sun_sign": sun_sign, "sun_symbol": sun_symbol,
        "phase_frac": phase_frac, "phase_name": phase_name, "phase_emoji": phase_emoji, "illum": illum,
        "next_full_dt": nfm_dt, "age_days": phase_frac * 29.53
    }

# ---------------------------------------------------------------------------
# UI Rendering
# ---------------------------------------------------------------------------

now_utc = datetime.now(timezone.utc)
current = get_celestial_data(now_utc)

# Persistence
config = load_config()
persisted_birthdate = config.get("birthdate")

with st.sidebar:
    st.markdown("### 🧬 Personal Cosmic Profile")
    default_date = datetime.fromisoformat(persisted_birthdate) if persisted_birthdate else datetime(1990, 1, 1)
    birth_date_input = st.date_input("Enter your birthdate once:", value=default_date, min_value=datetime(1920, 1, 1), max_value=now_utc)
    
    if not persisted_birthdate or birth_date_input.isoformat() != persisted_birthdate:
        save_config({"birthdate": birth_date_input.isoformat()})
        st.success("Cosmic profile locked! 🔒")
        st.rerun()
    
    st.markdown("---")
    st.markdown("#### About Lunatick")
    st.info("Lunatick uses the PyEphem engine for high-precision celestial calculations.")

# 1. COUNTDOWN
delta = current["next_full_dt"] - now_utc
d, rem = divmod(int(delta.total_seconds()), 86400)
h, m_total = divmod(rem, 3600)
m, _ = divmod(m_total, 60)

st.markdown(f"""
    <div class="glow-container">
        <h1 style="color:#bc8cff; margin-bottom:0.5rem;">LUNATICK</h1>
        <p style="color:#8b949e; font-size:0.9rem; margin-bottom:1rem;">Next Full Moon Countdown</p>
        <div class="countdown-display">
            <div class="unit-box"><div class="num">{d}</div><div class="label">Days</div></div>
            <div class="unit-box"><div class="num">{h}</div><div class="label">Hours</div></div>
            <div class="unit-box"><div class="num">{m}</div><div class="label">Minutes</div></div>
        </div>
        <p style="color:#58a6ff; font-weight:600; margin-top:1.5rem; font-size: 0.9rem;">
            {current['next_full_dt'].strftime('%B %d, %Y at %H:%M UTC')}
        </p>
    </div>
""", unsafe_allow_html=True)

# 2. CURRENT STATS
c1, c2, c3 = st.columns(3)
with c1: st.markdown(f'<div class="stat-card"><div class="stat-label">Phase</div><div class="stat-val">{current["phase_emoji"]} {current["phase_name"]}</div><div class="stat-label" style="font-size:0.7rem;">{current["phase_frac"]:.1%} Completion</div></div>', unsafe_allow_html=True)
with c2: st.markdown(f'<div class="stat-card"><div class="stat-label">Illumination</div><div class="stat-val">{current["illum"]*100:.1f}%</div><div class="stat-label" style="font-size:0.7rem;">Current Glow</div></div>', unsafe_allow_html=True)
with c3: st.markdown(f'<div class="stat-card"><div class="stat-label">Moon Age</div><div class="stat-val">{current["age_days"]:.1f} Days</div><div class="stat-label" style="font-size:0.7rem;">In current cycle</div></div>', unsafe_allow_html=True)

# 3. PERSONAL INSIGHTS (ENHANCED)
birth_utc = datetime.combine(birth_date_input, datetime.min.time()).replace(tzinfo=timezone.utc)
natal = get_celestial_data(birth_utc)
total_moons = (now_utc - birth_utc).days / 29.53

# Personal Guidance Logic
aspect = ""
guidance = ""
diff = (current["moon_lon"] - natal["moon_lon"]) % 360

if diff < 10 or diff > 350:
    aspect = "Your Lunar Return"
    guidance = "The moon is in the exact spot it was when you were born. This is an emotional 'New Year' for you. High intuition, high sensitivity."
elif 170 < diff < 190:
    aspect = "Lunar Opposition"
    guidance = "The moon is opposite your natal position. Emotions might feel like a tug-of-war. Balance your needs with those around you."
elif 80 < diff < 100 or 260 < diff < 280:
    aspect = "Square Aspect"
    guidance = "Tension in the air today. The universe is pushing you to resolve a lingering emotional hurdle. Don't hide from it."
elif 110 < diff < 130 or 230 < diff < 250:
    aspect = "Trine Aspect"
    guidance = "Harmony! Today's cosmic tide flows perfectly with your internal rhythm. A great day for creativity and manifesting."
else:
    aspect = "Developing Cycle"
    guidance = "A steady day for emotional growth. Use the current moon vibes to build on the intentions you set during the New Moon."

st.markdown(f"""
<div class="personal-card">
    <h3 style="color:#58a6ff; font-size:1.1rem; margin-bottom:1.5rem;">🧬 YOUR COSMIC PROFILE & GUIDANCE</h3>
    <div style="display:flex; justify-content:space-around; text-align:center; flex-wrap:wrap; gap:1rem;">
        <div><div style="color:#8b949e; font-size:0.65rem;">Natal Sun Sign</div><div style="font-size:1.2rem; font-weight:700; color:#fff;">{natal['sun_symbol']} {natal['sun_sign']}</div></div>
        <div><div style="color:#8b949e; font-size:0.65rem;">Natal Moon Sign</div><div style="font-size:1.2rem; font-weight:700; color:#fff;">{natal['moon_symbol']} {natal['moon_sign']}</div></div>
        <div><div style="color:#8b949e; font-size:0.65rem;">Natal Moon Phase</div><div style="font-size:1.2rem; font-weight:700; color:#fff;">{natal['phase_emoji']} {natal['phase_name']}</div></div>
        <div><div style="color:#8b949e; font-size:0.65rem;">Full Moons Experienced</div><div style="font-size:1.2rem; font-weight:700; color:#fff;">{int(total_moons)}</div></div>
    </div>
    <div style="margin-top:1.5rem; background:rgba(0,0,0,0.3); padding:1.2rem; border-radius:12px; border:1px solid #1f6feb;">
        <div style="color:#58a6ff; font-weight:700; font-size:0.9rem; margin-bottom:0.5rem;">✨ TODAY'S PERSONAL FORECAST: {aspect.upper()}</div>
        <div style="color:#e6edf3; line-height:1.6; font-size:0.95rem;">{guidance}</div>
    </div>
</div>
""", unsafe_allow_html=True)

st.write("")

# 4. MOON VIBES & EVENTS
vcol, ecol = st.columns([1, 1])
with vcol:
    st.markdown(f"""
    <div class="vibe-card">
        <div class="vibe-tag">TODAY'S COSMIC ENERGY</div>
        <h2 style="color:#fff; margin-bottom:1rem; font-size:1.5rem;">{current['moon_symbol']} Moon in {current['moon_sign']}</h2>
        <p style="font-size:1rem; line-height:1.6; color:#c9d1d9;">{current['moon_vibe']}</p>
        <div style="margin-top:1.5rem; padding:1rem; background:rgba(0,0,0,0.2); border-radius:12px; border-left:3px solid #bc8cff;">
            <span style="color:#bc8cff; font-weight:600;">Brobot Tip:</span> 
            Focus on {current['moon_sign'].lower()}-themed activities for maximum alignment today.
        </div>
    </div>
    """, unsafe_allow_html=True)

with ecol:
    st.subheader("🔭 2026 Cosmic Calendar")
    for d_str, title, desc in [
        ("March 3, 2026", "Total Lunar Eclipse", "Visible across the Americas, Europe, and Africa."),
        ("August 12, 2026", "Total Solar Eclipse", "Major eclipse visible in Europe & Greenland."),
        ("August 28, 2026", "Partial Lunar Eclipse", "Visible from the Pacific region."),
        ("September 26, 2026", "Corn Moon (Supermoon)", "The largest full moon appearance of the year."),
    ]:
        st.markdown(f'<div class="event-item"><div class="event-info"><div class="etitle">{title}</div><div class="edesc">{desc}</div></div><div class="event-date">{d_str}</div></div>', unsafe_allow_html=True)

st.markdown("---")
st.markdown("<p style='text-align:center; color:#484f58; font-size:0.8rem;'>🌒 LUNATICK &mdash; Your Cosmic Moon Companion</p>", unsafe_allow_html=True)
