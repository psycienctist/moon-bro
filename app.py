import streamlit as st
import ephem
import math
from datetime import datetime, timezone, timedelta

# ---------------------------------------------------------------------------
# Page config & Lunatick Theme
# ---------------------------------------------------------------------------
st.set_page_config(page_title="🌙 Lunatick", page_icon="🌙", layout="wide")

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
        letter-spacing: 1px;
    }

    /* COMPACT HEADER & COUNTDOWN */
    .glow-container {
        background: radial-gradient(circle at top right, #1b1040 0%, #05070a 100%);
        border: 1px solid #6e40c9;
        border-radius: 16px;
        padding: 0.8rem 1rem;
        margin-bottom: 0.5rem;
        box-shadow: 0 0 30px rgba(110, 64, 201, 0.15);
        text-align: center;
    }

    .countdown-display, .stats-row {
        display: flex;
        flex-direction: row;
        justify-content: center;
        align-items: center;
        gap: 0.8rem;
        margin: 0.5rem 0;
        flex-wrap: nowrap;
    }

    .unit-box, .stat-card {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 10px;
        padding: 0.5rem;
        flex: 1;
        min-width: 60px;
        text-align: center;
    }

    .unit-box .num {
        font-family: 'Orbitron', sans-serif;
        font-size: 1.8rem;
        font-weight: 700;
        background: linear-gradient(180deg, #fff 30%, #58a6ff 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        line-height: 1.1;
    }

    .stat-card {
        background: #0d1117;
        border-color: #30363d;
    }
    
    .stat-val {
        font-size: 1.2rem;
        font-weight: 700;
        color: #f0f6fc;
        margin: 0.2rem 0;
    }

    .label, .stat-label {
        font-size: 0.55rem;
        color: #8b949e;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    /* COMPACT PERSONAL CARD */
    .personal-card {
        background: linear-gradient(135deg, #0d1f3c 0%, #05070a 100%);
        border: 1px solid #1f6feb;
        border-radius: 16px;
        padding: 1rem;
        margin-bottom: 1rem;
        box-shadow: 0 10px 30px rgba(31, 111, 235, 0.1);
    }

    .vibe-card {
        background: linear-gradient(135deg, #2d1b69 0%, #1a1f36 100%);
        border-radius: 16px;
        padding: 1.5rem;
        border: 1px solid #bc8cff;
    }
    .vibe-tag {
        background: rgba(210, 168, 255, 0.2);
        color: #d2a8ff;
        padding: 0.2rem 0.6rem;
        border-radius: 12px;
        font-size: 0.7rem;
        font-weight: 600;
        display: inline-block;
        margin-bottom: 0.5rem;
    }

    .event-item {
        background: #161b22;
        border-radius: 10px;
        padding: 0.8rem;
        margin-bottom: 0.8rem;
        border-left: 4px solid #ff7b72;
    }
    .event-date { color: #ff7b72; font-family: 'Orbitron', sans-serif; font-size: 0.65rem; }

    ::-webkit-scrollbar { width: 6px; }
</style>
"""
st.markdown(LUNATICK_CSS, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Logic
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
    illum = moon.phase / 100.0
    elong = float(moon.elong)
    if elong < 0: elong += 2 * math.pi
    phase_frac = elong / (2 * math.pi)
    phase_name, phase_emoji = get_moon_phase_name(phase_frac)
    moon_ecl = ephem.Ecliptic(moon)
    moon_lon = math.degrees(float(moon_ecl.lon)) % 360
    moon_sign, moon_symbol, moon_vibe = get_zodiac_sign(moon_lon)
    sun_ecl = ephem.Ecliptic(sun)
    sun_lon = math.degrees(float(sun_ecl.lon)) % 360
    sun_sign, sun_symbol, _ = get_zodiac_sign(sun_lon)
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

# PRIVACY PATCH
query_params = st.query_params
initial_date = datetime(1990, 1, 1)
if "dob" in query_params:
    try: initial_date = datetime.strptime(query_params["dob"], "%Y-%m-%d")
    except: pass

if 'birth_date' not in st.session_state:
    st.session_state.birth_date = initial_date

with st.sidebar:
    st.markdown("### 🧬 Personal Cosmic Profile")
    birth_date_input = st.date_input("When were you born?", value=st.session_state.birth_date, min_value=datetime(1920, 1, 1), max_value=now_utc)
    if birth_date_input != st.session_state.birth_date:
        st.session_state.birth_date = birth_date_input
        st.query_params["dob"] = birth_date_input.strftime("%Y-%m-%d")
        st.rerun()
    st.success("🔒 Private: Insights are only visible to you.")

# 1. TOP: COMPACT COUNTDOWN
delta = current["next_full_dt"] - now_utc
d, rem = divmod(int(delta.total_seconds()), 86400)
h, m_total = divmod(rem, 3600)
m, _ = divmod(m_total, 60)

st.markdown(f"""
    <div class="glow-container">
        <h2 style="color:#bc8cff; margin-bottom:0.1rem; font-size:1.2rem;">🌙 LUNATICK</h2>
        <div style="color:#8b949e; font-size:0.65rem; letter-spacing:2px; margin-bottom:0.5rem; font-weight:700;">MOON MONITOR</div>
        <p style="color:#8b949e; font-size:0.7rem; margin-bottom:0.5rem; letter-spacing:1px;">NEXT FULL MOON</p>
        <div class="countdown-display">
            <div class="unit-box"><div class="num">{d}</div><div class="label">Days</div></div>
            <div class="unit-box"><div class="num">{h}</div><div class="label">Hours</div></div>
            <div class="unit-box"><div class="num">{m}</div><div class="label">Mins</div></div>
        </div>
    </div>
""", unsafe_allow_html=True)

# 2. PERSONAL INSIGHTS
birth_utc = datetime.combine(st.session_state.birth_date, datetime.min.time()).replace(tzinfo=timezone.utc)
natal = get_celestial_data(birth_utc)
total_moons = (now_utc - birth_utc).days / 29.53
diff = (current["moon_lon"] - natal["moon_lon"]) % 360

if diff < 10 or diff > 350: aspect, guidance = "Lunar Return", "High intuition today. Your birth rhythm is peaking."
elif 170 < diff < 190: aspect, guidance = "Opposition", "Emotions might feel like a tug-of-war. Balance yourself."
elif 80 < diff < 100 or 260 < diff < 280: aspect, guidance = "Square", "Tension in the air. The universe is pushing you to grow."
elif 110 < diff < 130 or 230 < diff < 250: aspect, guidance = "Trine", "Harmony! Today's cosmic tide flows perfectly with you."
else: aspect, guidance = "Cycle", "Steady growth. Build on the intentions you set recently."

st.markdown(f"""
<div class="personal-card">
    <div style="color:#58a6ff; font-size:0.8rem; font-weight:700; text-align:center; margin-bottom:0.8rem; letter-spacing:2px; font-family:'Orbitron', sans-serif;">
        YOUR COSMIC CHART
    </div>
    <div style="display:flex; justify-content:space-around; text-align:center; gap:0.5rem;">
        <div><div style="color:#8b949e; font-size:0.55rem;">SUN</div><div style="font-size:1rem; font-weight:700; color:#fff;">{natal['sun_symbol']} {natal['sun_sign']}</div></div>
        <div><div style="color:#8b949e; font-size:0.55rem;">MOON</div><div style="font-size:1rem; font-weight:700; color:#fff;">{natal['moon_symbol']} {natal['moon_sign']}</div></div>
        <div><div style="color:#8b949e; font-size:0.55rem;">PHASE</div><div style="font-size:1rem; font-weight:700; color:#fff;">{natal['phase_emoji']}</div></div>
        <div><div style="color:#8b949e; font-size:0.55rem;">MOONS</div><div style="font-size:1rem; font-weight:700; color:#fff;">{int(total_moons)}</div></div>
    </div>
    <div style="margin-top:0.8rem; background:rgba(0,0,0,0.3); padding:0.8rem; border-radius:10px; border:1px solid #1f6feb;">
        <div style="color:#58a6ff; font-weight:700; font-size:0.75rem; margin-bottom:0.2rem;">✨ {aspect.upper()} FORECAST</div>
        <div style="color:#e6edf3; line-height:1.4; font-size:0.85rem;">{guidance}</div>
    </div>
</div>
""", unsafe_allow_html=True)

# 3. CURRENT STATS (FORCED HORIZONTAL ROW)
st.markdown(f"""
<div class="stats-row">
    <div class="stat-card">
        <div class="stat-label">Phase</div>
        <div class="stat-val" style="font-size:1.5rem;">{current["phase_emoji"]}</div>
        <div class="stat-label" style="font-size:0.5rem;">{current["phase_name"]}</div>
    </div>
    <div class="stat-card">
        <div class="stat-label">Glow</div>
        <div class="stat-val">{current["illum"]*100:.1f}%</div>
        <div class="stat-label" style="font-size:0.5rem;">Surface</div>
    </div>
    <div class="stat-card">
        <div class="stat-label">Age</div>
        <div class="stat-val">{current["age_days"]:.1f}d</div>
        <div class="stat-label" style="font-size:0.5rem;">Cycle</div>
    </div>
</div>
""", unsafe_allow_html=True)

st.write("")

# 4. MOON VIBES & EVENTS
vcol, ecol = st.columns([1, 1])
with vcol:
    st.markdown(f"""
    <div class="vibe-card">
        <div class="vibe-tag">ENERGY</div>
        <h3 style="color:#fff; margin-bottom:0.5rem; font-size:1rem;">{current['moon_symbol']} Moon in {current['moon_sign']}</h3>
        <p style="font-size:0.85rem; line-height:1.4; color:#c9d1d9;">{current['moon_vibe']}</p>
    </div>
    """, unsafe_allow_html=True)

with ecol:
    st.markdown("<h4 style='font-size:0.8rem; margin-bottom:0.5rem;'>🔭 2026 CALENDAR</h4>", unsafe_allow_html=True)
    for d_str, title, desc in [
        ("March 3", "Total Lunar Eclipse", "Americas, Europe, Africa."),
        ("Aug 12", "Total Solar Eclipse", "Europe & Greenland."),
        ("Aug 28", "Partial Lunar Eclipse", "Pacific region."),
    ]:
        st.markdown(f'<div class="event-item" style="padding:0.5rem;"><div class="event-info"><div class="etitle" style="font-size:0.8rem;">{title}</div></div><div class="event-date" style="font-size:0.6rem;">{d_str}</div></div>', unsafe_allow_html=True)

st.markdown("---")
st.markdown("<p style='text-align:center; color:#484f58; font-size:0.6rem; margin-top:1rem;'>🌙 LUNATICK &mdash; Your Cosmic Moon Companion</p>", unsafe_allow_html=True)
