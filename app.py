import streamlit as st
import ephem
import math
from datetime import datetime, timezone, timedelta

# ---------------------------------------------------------------------------
# Page config & dark theme
# ---------------------------------------------------------------------------
st.set_page_config(page_title="🌙 Moon Management", page_icon="🌙", layout="wide")

DARK_CSS = """
<style>
    /* Dark background overrides */
    .stApp { background-color: #0e1117; color: #c9d1d9; }
    section[data-testid="stSidebar"] { background-color: #161b22; }

    /* Metric cards */
    .moon-card {
        background: linear-gradient(135deg, #1a1f36 0%, #0d1224 100%);
        border: 1px solid #30363d;
        border-radius: 16px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        text-align: center;
    }
    .moon-card h3 { color: #e6edf3; margin-bottom: 0.3rem; }
    .moon-card .big { font-size: 2.4rem; }
    .moon-card .sub { color: #8b949e; font-size: 0.9rem; }

    /* Event list */
    .event-row {
        background: #161b22;
        border-left: 4px solid #6e40c9;
        border-radius: 8px;
        padding: 0.8rem 1rem;
        margin-bottom: 0.6rem;
    }
    .event-row .date { color: #8b949e; font-size: 0.85rem; }
    .event-row .title { color: #e6edf3; font-weight: 600; }

    /* Vibes section */
    .vibes-box {
        background: linear-gradient(135deg, #1b1040 0%, #0e1117 100%);
        border: 1px solid #6e40c9;
        border-radius: 16px;
        padding: 1.5rem;
        margin-bottom: 1rem;
    }
    .vibes-box h4 { color: #d2a8ff; }

    /* Countdown */
    .countdown-box {
        background: linear-gradient(135deg, #0d1f3c 0%, #0e1117 100%);
        border: 1px solid #1f6feb;
        border-radius: 16px;
        padding: 1.5rem;
        text-align: center;
    }
    .countdown-box .number { font-size: 3rem; color: #58a6ff; font-weight: 700; }
    .countdown-box .label  { color: #8b949e; font-size: 0.85rem; }

    /* Full-moon table */
    .fm-table { width: 100%; border-collapse: collapse; }
    .fm-table th { color: #8b949e; text-align: left; padding: 0.4rem 0.6rem;
                   border-bottom: 1px solid #30363d; font-weight: 600; }
    .fm-table td { padding: 0.45rem 0.6rem; border-bottom: 1px solid #21262d; color: #c9d1d9; }
    .fm-table tr.past td { color: #484f58; }
    .fm-table tr.next td { color: #58a6ff; font-weight: 600; }
</style>
"""
st.markdown(DARK_CSS, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Helpers – ephem-based calculations
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

FULL_MOONS_2026 = [
    ("Jan 3", "Wolf Moon", "5:03 AM EST"),
    ("Feb 1", "Snow Moon", "5:09 PM EST"),
    ("Mar 3", "Worm Moon ★ Total Lunar Eclipse", "6:38 AM EST"),
    ("Apr 1", "Pink Moon", "10:12 PM EDT"),
    ("May 1", "Flower Moon", "1:23 PM EDT"),
    ("May 31", "Blue Moon", "4:45 AM EDT"),
    ("Jun 29", "Strawberry Moon", "7:57 PM EDT"),
    ("Jul 29", "Buck Moon", "10:36 AM EDT"),
    ("Aug 28", "Sturgeon Moon ★ Partial Lunar Eclipse", "12:18 AM EDT"),
    ("Sep 26", "Corn Moon", "12:49 PM EDT"),
    ("Oct 25", "Hunter's Moon", "11:12 PM EDT"),
    ("Nov 24", "Beaver Moon", "9:53 AM EST"),
    ("Dec 23", "Cold Moon", "8:28 PM EST"),
]

KEY_EVENTS_2026 = [
    ("March 3, 2026", "Total Lunar Eclipse",
     "Visible across the Americas, Europe, and Africa. The Worm Moon enters Earth's full shadow."),
    ("March 14, 2026", "Annular Solar Eclipse",
     "The 'ring of fire' eclipse visible across parts of Africa and southeastern Europe."),
    ("August 28, 2026", "Partial Lunar Eclipse",
     "The Sturgeon Moon dips partially into Earth's shadow. Visible from the Pacific region."),
    ("February 1, 2026", "Snow Moon (Micro Moon)",
     "Near apogee – the farthest and smallest-looking full moon of 2026."),
    ("May 31, 2026", "Blue Moon",
     "Second full moon in May – a rare Blue Moon. Next one isn't until 2029."),
    ("September 26, 2026", "Corn Moon (Supermoon)",
     "Closest full moon of the year – appears larger and brighter than usual."),
]


def get_moon_phase_name(phase_frac: float) -> tuple[str, str]:
    """Return (name, emoji) for a 0-1 phase fraction."""
    for i in range(len(PHASE_NAMES) - 1):
        lo = PHASE_NAMES[i][0]
        hi = PHASE_NAMES[i + 1][0]
        if lo <= phase_frac < hi:
            return PHASE_NAMES[i][1], PHASE_NAMES[i][2]
    return "New Moon", "🌑"


def get_moon_data(now_utc: datetime) -> dict:
    """Compute current moon info using ephem."""
    obs = ephem.Observer()
    obs.lat = "0"
    obs.lon = "0"
    obs.date = ephem.Date(now_utc)

    moon = ephem.Moon(obs)
    sun = ephem.Sun(obs)

    # Phase fraction: 0 = new, 0.5 = full, 1 = new
    # ephem.moon_phase returns illumination (0-1), not cycle position
    illumination = moon.phase / 100.0  # 0-1

    # Compute lunation fraction from elongation
    elong = float(moon.elong)  # radians, negative before new moon
    if elong < 0:
        elong += 2 * math.pi
    phase_frac = elong / (2 * math.pi)

    phase_name, phase_emoji = get_moon_phase_name(phase_frac)

    # Moon zodiac sign from ecliptic longitude
    ecl = ephem.Ecliptic(moon)
    lon_deg = math.degrees(float(ecl.lon)) % 360
    sign_index = int(lon_deg / 30)
    sign_name, sign_symbol, sign_vibe = ZODIAC_SIGNS[sign_index]
    sign_degree = lon_deg % 30

    # Next full moon
    next_full = ephem.next_full_moon(obs.date)
    next_full_dt = ephem.Date(next_full).datetime().replace(tzinfo=timezone.utc)

    # Next new moon
    next_new = ephem.next_new_moon(obs.date)
    next_new_dt = ephem.Date(next_new).datetime().replace(tzinfo=timezone.utc)

    return {
        "illumination": illumination,
        "phase_frac": phase_frac,
        "phase_name": phase_name,
        "phase_emoji": phase_emoji,
        "sign_name": sign_name,
        "sign_symbol": sign_symbol,
        "sign_vibe": sign_vibe,
        "sign_degree": sign_degree,
        "next_full_dt": next_full_dt,
        "next_new_dt": next_new_dt,
        "moon_age_days": phase_frac * 29.53059,
    }


# ---------------------------------------------------------------------------
# Main UI
# ---------------------------------------------------------------------------

now_utc = datetime.now(timezone.utc)
data = get_moon_data(now_utc)

# Header
st.markdown(
    f"""
    <div style="text-align:center; padding: 1rem 0 0.5rem 0;">
        <span style="font-size:4rem;">{data['phase_emoji']}</span>
        <h1 style="margin:0; color:#e6edf3;">Moon Management</h1>
        <p style="color:#8b949e; margin-top:0.2rem;">
            {now_utc.strftime('%A, %B %d, %Y')} &mdash; {now_utc.strftime('%H:%M')} UTC
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# --- Row 1: Phase / Illumination / Moon Age ---
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(
        f"""<div class="moon-card">
            <h3>Current Phase</h3>
            <div class="big">{data['phase_emoji']} {data['phase_name']}</div>
            <div class="sub">Cycle position {data['phase_frac']:.1%}</div>
        </div>""",
        unsafe_allow_html=True,
    )

with col2:
    pct = data["illumination"] * 100
    st.markdown(
        f"""<div class="moon-card">
            <h3>Illumination</h3>
            <div class="big">{pct:.1f}%</div>
            <div class="sub">Surface lit by the Sun</div>
        </div>""",
        unsafe_allow_html=True,
    )

with col3:
    age = data["moon_age_days"]
    st.markdown(
        f"""<div class="moon-card">
            <h3>Moon Age</h3>
            <div class="big">{age:.1f} days</div>
            <div class="sub">Since last New Moon (cycle ≈ 29.5 d)</div>
        </div>""",
        unsafe_allow_html=True,
    )

st.markdown("---")

# --- Row 2: Countdown + Moon Vibes ---
col_left, col_right = st.columns([1, 1])

with col_left:
    st.subheader("⏳ Countdown to Next Full Moon")
    delta = data["next_full_dt"] - now_utc
    total_seconds = int(delta.total_seconds())
    days = total_seconds // 86400
    hours = (total_seconds % 86400) // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60

    c1, c2, c3, c4 = st.columns(4)
    for col, val, lbl in [
        (c1, days, "DAYS"),
        (c2, hours, "HOURS"),
        (c3, minutes, "MINS"),
        (c4, seconds, "SECS"),
    ]:
        with col:
            st.markdown(
                f"""<div class="countdown-box">
                    <div class="number">{val}</div>
                    <div class="label">{lbl}</div>
                </div>""",
                unsafe_allow_html=True,
            )

    st.markdown(
        f"<p style='color:#8b949e; text-align:center; margin-top:0.5rem;'>"
        f"Next Full Moon: <b style='color:#58a6ff'>{data['next_full_dt'].strftime('%B %d, %Y at %H:%M UTC')}</b></p>",
        unsafe_allow_html=True,
    )

with col_right:
    st.subheader("✨ Moon Vibes – Astrological Insight")
    st.markdown(
        f"""<div class="vibes-box">
            <h4>{data['sign_symbol']} Moon in {data['sign_name']} ({data['sign_degree']:.1f}°)</h4>
            <p style="color:#c9d1d9; font-size:1.05rem;">{data['sign_vibe']}</p>
        </div>""",
        unsafe_allow_html=True,
    )
    # Quick tips based on element
    element_tips = {
        "Fire": "🔥 **Energy is high.** Channel it into action – start things, exercise, be bold.",
        "Earth": "🌿 **Steady and practical.** Good for finances, cooking, gardening, and self-care.",
        "Air": "💬 **Mind is active.** Write, talk, brainstorm, network. Avoid overthinking before bed.",
        "Water": "🌊 **Feelings run deep.** Journal, meditate, connect emotionally. Protect your energy.",
    }
    element = data["sign_vibe"].split("sign")[0].split()[-1]
    tip = element_tips.get(element, "")
    if tip:
        st.markdown(tip)

st.markdown("---")

# --- Row 3: 2026 Highlights ---
st.subheader("🗓️ 2026 Highlights")

tab_events, tab_full_moons = st.tabs(["Key Events", "Full Moon Calendar"])

with tab_events:
    # Sort by date
    sorted_events = sorted(KEY_EVENTS_2026, key=lambda e: datetime.strptime(e[0], "%B %d, %Y"))
    for date_str, title, desc in sorted_events:
        ev_date = datetime.strptime(date_str, "%B %d, %Y").replace(year=2026)
        past = ev_date.date() < now_utc.date()
        opacity = "0.5" if past else "1.0"
        st.markdown(
            f"""<div class="event-row" style="opacity:{opacity}">
                <span class="date">{date_str}</span><br/>
                <span class="title">{title}</span>
                <p style="color:#8b949e; margin:0.2rem 0 0 0; font-size:0.9rem;">{desc}</p>
            </div>""",
            unsafe_allow_html=True,
        )

with tab_full_moons:
    rows_html = ""
    for date_str, name, time_str in FULL_MOONS_2026:
        # Determine if past or next
        try:
            fm_date = datetime.strptime(f"{date_str} 2026", "%b %d %Y")
        except ValueError:
            fm_date = datetime(2026, 1, 1)
        css_class = ""
        if fm_date.date() < now_utc.date():
            css_class = "past"
        elif fm_date.date() <= (now_utc + timedelta(days=30)).date() and fm_date.date() >= now_utc.date():
            css_class = "next"
        star = " ⭐" if "★" in name else ""
        rows_html += f'<tr class="{css_class}"><td>{date_str}</td><td>{name}</td><td>{time_str}</td></tr>\n'

    st.markdown(
        f"""<table class="fm-table">
            <tr><th>Date</th><th>Name</th><th>Time</th></tr>
            {rows_html}
        </table>""",
        unsafe_allow_html=True,
    )

# --- Footer ---
st.markdown("---")
st.markdown(
    "<p style='text-align:center; color:#484f58; font-size:0.8rem;'>"
    "🌙 Moon Management • Powered by PyEphem • Data accurate to ±1 minute</p>",
    unsafe_allow_html=True,
)
