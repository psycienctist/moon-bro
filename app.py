import streamlit as st
import ephem
import math
from datetime import datetime, timezone, timedelta

# ---------------------------------------------------------------------------
# Page config & Lunatick Theme
# ---------------------------------------------------------------------------
st.set_page_config(page_title="🌑 Lunatick", page_icon="🌑", layout="wide")

LUNATICK_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Inter:wght@300;400;600&display=swap');

    .stApp {
        background-color: #05070a;
        color: #e6edf3;
        font-family: 'Inter', sans-serif;
    }

    /* Titles */
    h1, h2, h3, h4 {
        font-family: 'Orbitron', sans-serif;
        text-transform: uppercase;
        letter-spacing: 2px;
    }

    /* Main Glow Card */
    .glow-container {
        background: radial-gradient(circle at top right, #1b1040 0%, #05070a 100%);
        border: 1px solid #6e40c9;
        border-radius: 24px;
        padding: 2.5rem;
        margin-bottom: 2rem;
        box-shadow: 0 0 40px rgba(110, 64, 201, 0.2);
        text-align: center;
    }

    /* Countdown Styling */
    .countdown-display {
        display: flex;
        justify-content: center;
        gap: 1.5rem;
        margin: 1.5rem 0;
    }
    .unit-box {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 1rem;
        min-width: 100px;
        box-shadow: inset 0 0 10px rgba(0, 0, 0, 0.5);
    }
    .unit-box .num {
        font-family: 'Orbitron', sans-serif;
        font-size: 3.5rem;
        font-weight: 700;
        background: linear-gradient(180deg, #fff 30%, #58a6ff 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        line-height: 1;
    }
    .unit-box .label {
        font-size: 0.75rem;
        color: #8b949e;
        margin-top: 0.5rem;
        font-weight: 600;
    }

    /* Stats Cards */
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
        font-size: 2rem;
        font-weight: 700;
        margin: 0.5rem 0;
        color: #f0f6fc;
    }
    .stat-label {
        color: #8b949e;
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    /* Vibe Box */
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

    /* Events List */
    .event-item {
        background: #161b22;
        border-radius: 12px;
        padding: 1.2rem;
        margin-bottom: 1rem;
        border-left: 5px solid #ff7b72;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .event-info .etitle { font-weight: 600; color: #f0f6fc; }
    .event-info .edesc { color: #8b949e; font-size: 0.9rem; margin-top: 0.3rem; }
    .event-date { color: #ff7b72; font-family: 'Orbitron', sans-serif; font-size: 0.8rem; }

    /* Custom Scrollbar */
    ::-webkit-scrollbar { width: 8px; }
    ::-webkit-scrollbar-track { background: #05070a; }
    ::-webkit-scrollbar-thumb { background: #30363d; border-radius: 10px; }
    ::-webkit-scrollbar-thumb:hover { background: #484f58; }
</style>
"""
st.markdown(LUNATICK_CSS, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Logic – Same high-precision Ephem engine
# ---------------------------------------------------------------------------

ZODIAC_SIGNS = [
    ("Aries", "♈", "🔥 Fire sign – Bold, assertive energy. Great for starting new projects."),
    ("Taurus", "♉", "🌍 Earth sign – Grounded, sensual vibes. Focus on comfort and stability."),
    ("Gemini", "♊", "💨 Air sign – Curious, communicative mood. Ideal for learning and socialising."),
    ("Cancer", "♋", "💧 Water sign – Nurturing, emotional depth. Prioritise home and family."),
    ("Leo", "♌", "🔥 Fire sign – Creative, warm-hearted energy. Shine and express yourself."),
    ("Virgo", "♍", "🌍 Earth sign – Analytical, detail-oriented. Perfect for organising and health."),
    ("Libra", "♎", "💨 Air sign – Harmonious, balanced mood. Focus on relationships and beauty."),
    ("Scorpio", "♏", "💧 Water sign – Intense, transformative energy. Dive deep within."),
    ("Sagittarius", "♐", "🔥 Fire sign – Adventurous, optimistic vibes. Seek truth and explore."),
    ("Capricorn", "♑", "🌍 Earth sign – Disciplined, ambitious. Build towards long-term goals."),
    ("Aquarius", "♒", "💨 Air sign – Innovative, humanitarian energy. Think outside the box."),
    ("Pisces", "♓", "💧 Water sign – Dreamy, intuitive mood. Meditate and create art."),
]

PHASE_NAMES = [
    (0.00, "New Moon", "🌑"),
    (0.07, "Waxing Crescent", "🌒"),
    (0.25, "First Quarter", "🌓"),
    (0.43, "Waxing Gibbous", "🌔"),
    (0.50, "Full Moon", "🌕"),
    (0.57, "Waning Gibbous", "🌖"),
    (0.75, "Last Quarter", "🌗"),
    (0.93, "Waning Crescent", "🌘"),
    (1.00, "New Moon", "🌑"),
]

KEY_EVENTS_2026 = [
    ("March 3, 2026", "Total Lunar Eclipse", "Visible across the Americas, Europe, and Africa."),
    ("March 14, 2026", "Annular Solar Eclipse", "The 'ring of fire' eclipse visible in Africa."),
    ("August 12, 2026", "Total Solar Eclipse", "Major eclipse visible in Europe & Greenland."),
    ("August 28, 2026", "Partial Lunar Eclipse", "Visible from the Pacific region."),
    ("September 26, 2026", "Corn Moon (Supermoon)", "The largest full moon appearance of the year."),
]

def get_moon_phase_name(phase_frac: float) -> tuple[str, str]:
    for i in range(len(PHASE_NAMES) - 1):
        if PHASE_NAMES[i][0] <= phase_frac < PHASE_NAMES[i + 1][0]:
            return PHASE_NAMES[i][1], PHASE_NAMES[i][2]
    return "New Moon", "🌑"

def get_moon_data(now_utc: datetime) -> dict:
    obs = ephem.Observer()
    obs.lat, obs.lon = "0", "0"
    obs.date = ephem.Date(now_utc)
    moon = ephem.Moon(obs)
    
    illumination = moon.phase / 100.0
    elong = float(moon.elong)
    if elong < 0: elong += 2 * math.pi
    phase_frac = elong / (2 * math.pi)
    
    phase_name, phase_emoji = get_moon_phase_name(phase_frac)
    
    ecl = ephem.Ecliptic(moon)
    lon_deg = math.degrees(float(ecl.lon)) % 360
    sign_idx = int(lon_deg / 30)
    sign_name, sign_symbol, sign_vibe = ZODIAC_SIGNS[sign_idx]
    
    next_full = ephem.next_full_moon(obs.date)
    next_full_dt = ephem.Date(next_full).datetime().replace(tzinfo=timezone.utc)
    
    return {
        "illumination": illumination,
        "phase_frac": phase_frac,
        "phase_name": phase_name,
        "phase_emoji": phase_emoji,
        "sign_name": sign_name,
        "sign_symbol": sign_symbol,
        "sign_vibe": sign_vibe,
        "next_full_dt": next_full_dt,
        "moon_age_days": phase_frac * 29.53059,
    }

# ---------------------------------------------------------------------------
# UI Rendering
# ---------------------------------------------------------------------------

now_utc = datetime.now(timezone.utc)
data = get_moon_data(now_utc)

# 1. TOP & CENTER: COUNTDOWN
delta = data["next_full_dt"] - now_utc
total_sec = int(delta.total_seconds())
d, remainder = divmod(total_sec, 86400)
h, remainder = divmod(remainder, 3600)
m, s = divmod(remainder, 60)

st.markdown(
    f"""
    <div class="glow-container">
        <h1 style="color:#bc8cff; margin-bottom:0.5rem;">LUNATICK</h1>
        <p style="color:#8b949e; font-size:0.9rem; margin-bottom:2rem;">Next Full Moon Countdown</p>
        <div class="countdown-display">
            <div class="unit-box"><div class="num">{d}</div><div class="label">DAYS</div></div>
            <div class="unit-box"><div class="num">{h}</div><div class="label">HOURS</div></div>
            <div class="unit-box"><div class="num">{m}</div><div class="label">MINS</div></div>
            <div class="unit-box"><div class="num">{s}</div><div class="label">SECS</div></div>
        </div>
        <p style="color:#58a6ff; font-weight:600; margin-top:1.5rem;">
            {data['next_full_dt'].strftime('%B %d, %Y at %H:%M UTC')}
        </p>
    </div>
    """,
    unsafe_allow_html=True
)

# 2. CURRENT STATS
c1, c2, c3 = st.columns(3)
with c1:
    st.markdown(f"""<div class="stat-card">
        <div class="stat-label">Phase</div>
        <div class="stat-val">{data['phase_emoji']} {data['phase_name']}</div>
        <div class="stat-label" style="font-size:0.7rem;">{data['phase_frac']:.1%} Completion</div>
    </div>""", unsafe_allow_html=True)
with c2:
    st.markdown(f"""<div class="stat-card">
        <div class="stat-label">Illumination</div>
        <div class="stat-val">{data['illumination']*100:.1f}%</div>
        <div class="stat-label" style="font-size:0.7rem;">Current Surface Glow</div>
    </div>""", unsafe_allow_html=True)
with c3:
    st.markdown(f"""<div class="stat-card">
        <div class="stat-label">Moon Age</div>
        <div class="stat-val">{data['moon_age_days']:.1f} Days</div>
        <div class="stat-label" style="font-size:0.7rem;">In current cycle</div>
    </div>""", unsafe_allow_html=True)

st.write("")

# 3. MOON VIBES & EVENTS
vcol, ecol = st.columns([1, 1])

with vcol:
    st.markdown(f"""
    <div class="vibe-card">
        <div class="vibe-tag">COSMIC ENERGY</div>
        <h2 style="color:#fff; margin-bottom:1rem;">{data['sign_symbol']} Moon in {data['sign_name']}</h2>
        <p style="font-size:1.1rem; line-height:1.6; color:#c9d1d9;">{data['sign_vibe']}</p>
        <div style="margin-top:1.5rem; padding:1rem; background:rgba(0,0,0,0.2); border-radius:12px; border-left:3px solid #58a6ff;">
            <span style="color:#58a6ff; font-weight:600;">Brobot Tip:</span> 
            Focus on {data['sign_name'].lower()}-themed activities for maximum alignment today.
        </div>
    </div>
    """, unsafe_allow_html=True)

with ecol:
    st.subheader("🔭 2026 Cosmic Calendar")
    for d_str, title, desc in KEY_EVENTS_2026:
        st.markdown(f"""
        <div class="event-item">
            <div class="event-info">
                <div class="etitle">{title}</div>
                <div class="edesc">{desc}</div>
            </div>
            <div class="event-date">{d_str}</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("---")

st.markdown("<p style='text-align:center; color:#484f58;'>🌒 LUNATICK &mdash; Your Cosmic Moon Companion</p>", unsafe_allow_html=True)
