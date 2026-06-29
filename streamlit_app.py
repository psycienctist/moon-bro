import streamlit as st
import ephem
import math
import json
import datetime as dt
from datetime import datetime, timezone, timedelta
import calendar as cal

# ---------------------------------------------------------------------------
# Page config & Lunatick Theme
# ---------------------------------------------------------------------------
st.set_page_config(page_title="🌙 Lunatick", page_icon="🌙", layout="wide")

LUNATICK_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Crimson+Pro:ital,wght@0,300;0,400;1,300;1,400&display=swap');

    .stApp {
        background-color: #05070a;
        color: #e6edf3;
        font-family: 'Crimson Pro', serif;
    }

    h1, h2, h3, h4 {
        font-family: 'Orbitron', sans-serif;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

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
        font-size: 0.5rem;
        color: #8b949e;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

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

    .event-date {
        color: #ff7b72;
        font-family: 'Orbitron', sans-serif;
        font-size: 0.65rem;
    }

    .journal-container {
        background: linear-gradient(160deg, #0a0d16 0%, #05070a 100%);
        border: 1px solid #2a2060;
        border-radius: 20px;
        padding: 1.5rem;
        margin-bottom: 1rem;
    }

    .journal-header {
        font-family: 'Orbitron', sans-serif;
        font-size: 0.75rem;
        letter-spacing: 3px;
        color: #bc8cff;
        text-transform: uppercase;
        margin-bottom: 1rem;
        border-bottom: 1px solid #1a1040;
        padding-bottom: 0.5rem;
    }

    .journal-entry {
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.07);
        border-radius: 12px;
        padding: 1rem 1.2rem;
        margin-bottom: 0.8rem;
        position: relative;
        transition: border-color 0.2s;
    }

    .journal-entry:hover {
        border-color: rgba(188, 140, 255, 0.3);
    }

    .entry-meta {
        display: flex;
        gap: 0.6rem;
        align-items: center;
        margin-bottom: 0.5rem;
        flex-wrap: wrap;
    }

    .entry-date {
        font-family: 'Orbitron', sans-serif;
        font-size: 0.55rem;
        color: #58a6ff;
        letter-spacing: 1px;
    }

    .entry-phase-badge {
        background: rgba(110, 64, 201, 0.25);
        border: 1px solid rgba(110, 64, 201, 0.5);
        color: #bc8cff;
        padding: 0.1rem 0.5rem;
        border-radius: 20px;
        font-size: 0.6rem;
        font-family: 'Orbitron', sans-serif;
        letter-spacing: 0.5px;
    }

    .entry-moon-sign {
        background: rgba(88, 166, 255, 0.1);
        border: 1px solid rgba(88, 166, 255, 0.3);
        color: #58a6ff;
        padding: 0.1rem 0.5rem;
        border-radius: 20px;
        font-size: 0.6rem;
        font-family: 'Orbitron', sans-serif;
    }

    .entry-text {
        font-family: 'Crimson Pro', serif;
        font-size: 1rem;
        color: #c9d1d9;
        line-height: 1.7;
        font-style: italic;
        margin: 0;
    }

    .pattern-card {
        background: linear-gradient(135deg, #0d1f0d 0%, #05070a 100%);
        border: 1px solid #238636;
        border-radius: 16px;
        padding: 1rem 1.2rem;
        margin-bottom: 0.8rem;
    }

    .pattern-title {
        font-family: 'Orbitron', sans-serif;
        font-size: 0.6rem;
        color: #3fb950;
        letter-spacing: 2px;
        margin-bottom: 0.5rem;
    }

    .calendar-day {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 8px;
        padding: 0.5rem;
        text-align: center;
        min-height: 80px;
        transition: border-color 0.2s;
    }

    .calendar-day:hover {
        border-color: rgba(188, 140, 255, 0.4);
    }

    .calendar-today {
        border: 2px solid #6e40c9;
        background: rgba(110, 64, 201, 0.1);
    }

    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-track { background: #05070a; }
    ::-webkit-scrollbar-thumb { background: #2a2060; border-radius: 3px; }
</style>
"""
st.markdown(LUNATICK_CSS, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Logic Functions
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

PHASE_PROMPTS = {
    "New Moon": [
        "What am I planting today?",
        "What intention do I set for this cycle?",
        "What am I ready to begin?",
    ],
    "Waxing Crescent": [
        "What small step did I take today?",
        "What feels like it's building?",
        "Where am I finding momentum?",
    ],
    "First Quarter": [
        "What challenge am I facing?",
        "What decision needs to be made?",
        "What am I committed to?",
    ],
    "Waxing Gibbous": [
        "What am I refining?",
        "What's almost ready?",
        "What do I need to adjust?",
    ],
    "Full Moon": [
        "What has come to fruition?",
        "What am I feeling most intensely right now?",
        "What am I ready to release?",
    ],
    "Waning Gibbous": [
        "What wisdom did this cycle bring?",
        "What am I grateful for?",
        "What am I sharing with others?",
    ],
    "Last Quarter": [
        "What am I letting go of?",
        "What no longer serves me?",
        "What patterns am I breaking?",
    ],
    "Waning Crescent": [
        "What do I need to rest from?",
        "What am I surrendering to the universe?",
        "What silence is asking to be heard?",
    ],
}

def get_zodiac_sign(lon_deg):
    idx = int(lon_deg / 30) % 12
    return ZODIAC_SIGNS[idx]

def get_moon_phase_name(phase_frac: float) -> tuple[str, str]:
    phases = [
        (0.00, "New Moon", "🌑"), (0.07, "Waxing Crescent", "🌒"),
        (0.25, "First Quarter", "🌓"), (0.43, "Waxing Gibbous", "🌔"),
        (0.50, "Full Moon", "🌕"), (0.57, "Waning Gibbous", "🌖"),
        (0.75, "Last Quarter", "🌗"), (0.93, "Waning Crescent", "🌘"),
        (1.00, "New Moon", "🌑"),
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
    if elong < 0:
        elong += 2 * math.pi
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
        "moon_sign": moon_sign, "moon_symbol": moon_symbol,
        "moon_vibe": moon_vibe, "moon_lon": moon_lon,
        "sun_sign": sun_sign, "sun_symbol": sun_symbol,
        "phase_frac": phase_frac, "phase_name": phase_name,
        "phase_emoji": phase_emoji, "illum": illum,
        "next_full_dt": nfm_dt, "age_days": phase_frac * 29.53
    }

def get_phase_patterns(entries):
    """Analyse which phases appear most in journal entries."""
    counts = {}
    for e in entries:
        p = e.get("phase", "Unknown")
        counts[p] = counts.get(p, 0) + 1
    if not counts:
        return None
    top = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    return top

# ---------------------------------------------------------------------------
# State Initialization
# ---------------------------------------------------------------------------

now_utc = datetime.now(timezone.utc)
current = get_celestial_data(now_utc)

query_params = st.query_params
initial_date = datetime(1990, 1, 1)
if "dob" in query_params:
    try:
        initial_date = datetime.strptime(query_params["dob"], "%Y-%m-%d")
    except:
        pass

if 'birth_date' not in st.session_state:
    st.session_state.birth_date = initial_date

if 'journal_entries' not in st.session_state:
    st.session_state.journal_entries = []

if 'journal_draft' not in st.session_state:
    st.session_state.journal_draft = ""

if 'calendar_month' not in st.session_state:
    st.session_state.calendar_month = now_utc.month

if 'calendar_year' not in st.session_state:
    st.session_state.calendar_year = now_utc.year

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown("### 🧬 Personal Cosmic Profile")
    birth_date_input = st.date_input(
        "When were you born?",
        value=st.session_state.birth_date,
        min_value=datetime(1920, 1, 1),
        max_value=now_utc
    )
    if birth_date_input != st.session_state.birth_date:
        st.session_state.birth_date = birth_date_input
        st.query_params["dob"] = birth_date_input.strftime("%Y-%m-%d")
        st.rerun()
    st.success("🔒 Private: Insights are only visible to you.")

    st.markdown("---")

    # Journal export
    if st.session_state.journal_entries:
        st.markdown("### 📓 Journal")
        export_data = json.dumps(st.session_state.journal_entries, indent=2)
        st.download_button(
            label="⬇️ Export Journal (JSON)",
            data=export_data,
            file_name=f"lunatick_journal_{now_utc.strftime('%Y%m%d')}.json",
            mime="application/json"
        )
        if st.button("🗑️ Clear All Entries", type="secondary"):
            st.session_state.journal_entries = []
            st.rerun()

# ---------------------------------------------------------------------------
# TABS
# ---------------------------------------------------------------------------

tab1, tab2, tab3, tab4 = st.tabs(["🏠 Main", "📓 Journal", "📅 Calendar", "⚙️ Settings"])

# ===========================================================================
# TAB 1: MAIN PAGE (Keep Exactly As-Is)
# ===========================================================================

with tab1:
    # 1. HEADER + COUNTDOWN
    delta = current["next_full_dt"] - now_utc
    d_count, rem = divmod(int(delta.total_seconds()), 86400)
    h_count, m_total = divmod(rem, 3600)
    m_count, _ = divmod(m_total, 60)

    st.markdown(f"""
        <div class="glow-container">
            <h1 style="color:#bc8cff; margin-bottom:0rem; font-size:3.2rem; letter-spacing:4px;">🌙 LUNATICK</h1>
            <div style="color:#8b949e; font-size:0.8rem; letter-spacing:3px; margin-bottom:1rem; font-weight:700;">MOON MONITOR</div>
            <p style="color:#8b949e; font-size:0.75rem; margin-bottom:0.6rem; letter-spacing:1.5px;">NEXT FULL MOON</p>
            <div class="countdown-display">
                <div class="unit-box"><div class="num">{d_count}</div><div class="label">Days</div></div>
                <div class="unit-box"><div class="num">{h_count}</div><div class="label">Hours</div></div>
                <div class="unit-box"><div class="num">{m_count}</div><div class="label">Mins</div></div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # 2. PERSONAL INSIGHTS
    birth_utc = datetime.combine(st.session_state.birth_date, datetime.min.time()).replace(tzinfo=timezone.utc)
    natal = get_celestial_data(birth_utc)
    total_moons = (now_utc - birth_utc).days / 29.53
    diff = (current["moon_lon"] - natal["moon_lon"]) % 360

    if diff < 10 or diff > 350:
        aspect, guidance = "Lunar Return", "High intuition today. Your birth rhythm is peaking."
    elif 170 < diff < 190:
        aspect, guidance = "Opposition", "Emotions might feel like a tug-of-war. Balance yourself."
    elif 80 < diff < 100 or 260 < diff < 280:
        aspect, guidance = "Square", "Tension in the air. The universe is pushing you to grow."
    elif 110 < diff < 130 or 230 < diff < 250:
        aspect, guidance = "Trine", "Harmony! Today's cosmic tide flows perfectly with you."
    else:
        aspect, guidance = "Cycle", "Steady growth. Build on the intentions you set recently."

    st.markdown(f"""
    <div class="personal-card">
        <div style="color:#58a6ff; font-size:0.85rem; font-weight:700; text-align:center; margin-bottom:0.8rem; letter-spacing:2px; font-family:'Orbitron', sans-serif;">
            YOUR COSMIC CHART
        </div>
        <div style="display:flex; justify-content:space-around; text-align:center; gap:0.5rem;">
            <div><div style="color:#8b949e; font-size:0.5rem;">SUN SIGN</div><div style="font-size:1.1rem; font-weight:700; color:#fff;">{natal['sun_symbol']} {natal['sun_sign']}</div></div>
            <div><div style="color:#8b949e; font-size:0.5rem;">BIRTH MOON</div><div style="font-size:1.1rem; font-weight:700; color:#fff;">{natal['moon_symbol']} {natal['moon_sign']}</div></div>
            <div><div style="color:#8b949e; font-size:0.5rem;">BORN UNDER</div><div style="font-size:1.1rem; font-weight:700; color:#fff;">{natal['phase_emoji']}</div></div>
            <div><div style="color:#8b949e; font-size:0.5rem;">FULL MOONS LIVED</div><div style="font-size:1.1rem; font-weight:700; color:#bc8cff;">{int(total_moons)}</div></div>
        </div>
        <div style="margin-top:0.8rem; background:rgba(0,0,0,0.3); padding:0.8rem; border-radius:10px; border:1px solid #1f6feb;">
            <div style="color:#58a6ff; font-weight:700; font-size:0.8rem; margin-bottom:0.2rem;">✨ {aspect.upper()} FORECAST</div>
            <div style="color:#e6edf3; line-height:1.4; font-size:0.95rem; font-family:'Crimson Pro', serif;">{guidance}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 3. CURRENT STATS
    st.markdown(f"""
    <div class="stats-row">
        <div class="stat-card">
            <div class="stat-label">Phase</div>
            <div class="stat-val" style="font-size:1.5rem;">{current["phase_emoji"]}</div>
            <div class="stat-label" style="font-size:0.55rem;">{current["phase_name"]}</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Glow</div>
            <div class="stat-val">{current["illum"]*100:.1f}%</div>
            <div class="stat-label" style="font-size:0.55rem;">Illuminated</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Age</div>
            <div class="stat-val">{current["age_days"]:.1f}d</div>
            <div class="stat-label" style="font-size:0.55rem;">This Cycle</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.write("")

    # 4. MOON VIBES & COSMIC CALENDAR
    vcol, ecol = st.columns([1, 1])

    with vcol:
        st.markdown(f"""
        <div class="vibe-card">
            <div class="vibe-tag">ENERGY</div>
            <h3 style="color:#fff; margin-bottom:0.5rem; font-size:1.1rem;">{current['moon_symbol']} Moon in {current['moon_sign']}</h3>
            <p style="font-size:1rem; line-height:1.6; color:#c9d1d9; font-family:'Crimson Pro', serif;">{current['moon_vibe']}</p>
        </div>
        """, unsafe_allow_html=True)

    with ecol:
        st.subheader("🔭 2026 Cosmic Calendar")
        for d_str, title, desc in [
            ("March 3", "Total Lunar Eclipse", "Visible across the Americas, Europe, and Africa."),
            ("August 12", "Total Solar Eclipse", "Major eclipse visible in Europe & Greenland."),
            ("August 28", "Partial Lunar Eclipse", "Visible from the Pacific region."),
            ("September 26", "Corn Moon (Supermoon)", "The largest full moon appearance of the year."),
        ]:
            st.markdown(
                f'<div class="event-item"><div class="event-date">{d_str}</div>'
                f'<div style="font-weight:700; font-size:0.9rem; color:#f0f6fc;">{title}</div>'
                f'<div style="color:#8b949e; font-size:0.8rem;">{desc}</div></div>',
                unsafe_allow_html=True
            )

# ===========================================================================
# TAB 2: JOURNAL
# ===========================================================================

with tab2:
    st.markdown("""
    <div style="font-family:'Orbitron', sans-serif; font-size:0.8rem; letter-spacing:3px; color:#bc8cff; text-transform:uppercase; margin-bottom:0.3rem;">
        📓 Lunar Journal
    </div>
    <div style="font-family:'Crimson Pro', serif; font-size:1rem; color:#8b949e; margin-bottom:1.2rem; font-style:italic;">
        Your private record, written in the light of the moon.
    </div>
    """, unsafe_allow_html=True)

    jcol, pcol = st.columns([3, 2])

    with jcol:
        # Phase-specific writing prompts
        current_phase_name = current["phase_name"]
        prompts = PHASE_PROMPTS.get(current_phase_name, ["What are you feeling right now?"])

        st.markdown(f"""
        <div style="margin-bottom:0.8rem;">
            <span style="font-family:'Orbitron', sans-serif; font-size:0.6rem; color:#6e40c9; letter-spacing:2px;">
                {current['phase_emoji']} {current_phase_name.upper()} PROMPTS
            </span>
        </div>
        """, unsafe_allow_html=True)

        prompt_cols = st.columns(len(prompts))
        for i, prompt in enumerate(prompts):
            with prompt_cols[i]:
                if st.button(f'"{prompt}"', key=f"prompt_{i}", use_container_width=True):
                    st.session_state.journal_draft = prompt + " "
                    st.rerun()

        # Journal text area
        entry_text = st.text_area(
            "Write your entry...",
            value=st.session_state.journal_draft,
            height=160,
            placeholder=f"Under the {current_phase_name}, in {current['moon_symbol']} {current['moon_sign']}...",
            label_visibility="collapsed",
            key="journal_input"
        )

        col_save, col_clear = st.columns([2, 1])
        with col_save:
            if st.button("✦ Seal this entry to the moon", type="primary", use_container_width=True):
                if entry_text and entry_text.strip():
                    new_entry = {
                        "id": len(st.session_state.journal_entries),
                        "text": entry_text.strip(),
                        "date": now_utc.strftime("%Y-%m-%d %H:%M UTC"),
                        "phase": current_phase_name,
                        "phase_emoji": current["phase_emoji"],
                        "moon_sign": current["moon_sign"],
                        "moon_symbol": current["moon_symbol"],
                        "illumination": round(current["illum"] * 100, 1),
                        "aspect": aspect,
                    }
                    st.session_state.journal_entries.insert(0, new_entry)
                    st.session_state.journal_draft = ""
                    st.success("Entry sealed. The moon witnessed it. 🌙")
                    st.rerun()
                else:
                    st.warning("Write something first.")
        with col_clear:
            if st.button("Clear", use_container_width=True):
                st.session_state.journal_draft = ""
                st.rerun()

    with pcol:
        # Pattern recognition
        if len(st.session_state.journal_entries) >= 3:
            patterns = get_phase_patterns(st.session_state.journal_entries)
            if patterns:
                st.markdown("""
                <div class="pattern-card">
                    <div class="pattern-title">🔮 Your Pattern Emerging</div>
                """, unsafe_allow_html=True)

                top_phase_name, top_count = patterns[0]
                top_emoji = next((e["phase_emoji"] for e in st.session_state.journal_entries if e["phase"] == top_phase_name), "🌙")
                total = len(st.session_state.journal_entries)

                st.markdown(f"""
                    <div style="font-family:'Crimson Pro', serif; font-size:0.95rem; color:#c9d1d9; line-height:1.6;">
                        You write most under the <strong style="color:#3fb950;">{top_phase_name}</strong> {top_emoji} —
                        {top_count} of your {total} entries. Something stirs in you at this phase.
                        Pay attention to it.
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="pattern-card">
                <div class="pattern-title">🔮 Pattern Recognition</div>
                <div style="font-family:'Crimson Pro', serif; font-size:0.9rem; color:#8b949e; font-style:italic; line-height:1.6;">
                    Write at least 3 entries and your lunar patterns will begin to reveal themselves.
                    The moon remembers everything.
                </div>
            </div>
            """, unsafe_allow_html=True)

        # Entry count by phase mini chart
        if st.session_state.journal_entries:
            all_phases = [e["phase"] for e in st.session_state.journal_entries]
            phase_order = ["New Moon", "Waxing Crescent", "First Quarter", "Waxing Gibbous",
                           "Full Moon", "Waning Gibbous", "Last Quarter", "Waning Crescent"]
            emojis = {"New Moon": "🌑", "Waxing Crescent": "🌒", "First Quarter": "🌓",
                      "Waxing Gibbous": "🌔", "Full Moon": "🌕", "Waning Gibbous": "🌖",
                      "Last Quarter": "🌗", "Waning Crescent": "🌘"}

            st.markdown("<div style='margin-top:0.8rem;'>", unsafe_allow_html=True)
            for phase in phase_order:
                count = all_phases.count(phase)
                if count > 0:
                    bar_width = min(count * 20, 100)
                    st.markdown(f"""
                    <div style="margin-bottom:0.3rem;">
                        <div style="display:flex; align-items:center; gap:0.4rem;">
                            <span style="font-size:0.8rem; width:1.2rem;">{emojis[phase]}</span>
                            <div style="flex:1; background:rgba(255,255,255,0.05); border-radius:4px; height:6px;">
                                <div style="width:{bar_width}%; background:linear-gradient(90deg, #6e40c9, #bc8cff); height:6px; border-radius:4px;"></div>
                            </div>
                            <span style="font-family:'Orbitron', sans-serif; font-size:0.5rem; color:#8b949e; width:1rem;">{count}</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

    # PAST ENTRIES
    if st.session_state.journal_entries:
        st.markdown(f"""
        <div style="font-family:'Orbitron', sans-serif; font-size:0.65rem; letter-spacing:2px; color:#484f58; text-transform:uppercase; margin: 1rem 0 0.5rem 0;">
            — {len(st.session_state.journal_entries)} entries in the archive —
        </div>
        """, unsafe_allow_html=True)

        # Filter by phase
        all_phases_in_journal = list(dict.fromkeys([e["phase"] for e in st.session_state.journal_entries]))
        filter_options = ["All Phases"] + all_phases_in_journal
        selected_filter = st.selectbox("Filter by phase", filter_options, label_visibility="collapsed")

        entries_to_show = st.session_state.journal_entries
        if selected_filter != "All Phases":
            entries_to_show = [e for e in entries_to_show if e["phase"] == selected_filter]

        for entry in entries_to_show:
            st.markdown(f"""
            <div class="journal-entry">
                <div class="entry-meta">
                    <span class="entry-date">{entry['date']}</span>
                    <span class="entry-phase-badge">{entry.get('phase_emoji','')} {entry['phase']}</span>
                    <span class="entry-moon-sign">{entry.get('moon_symbol','')} {entry['moon_sign']}</span>
                    <span style="font-family:'Orbitron', sans-serif; font-size:0.5rem; color:#484f58;">
                        {entry.get('illumination', '')}% lit
                    </span>
                </div>
                <p class="entry-text">"{entry['text']}"</p>
            </div>
            """, unsafe_allow_html=True)

# ===========================================================================
# TAB 3: CALENDAR
# ===========================================================================

with tab3:
    st.markdown("""
    <div style="font-family:'Orbitron', sans-serif; font-size:0.8rem; letter-spacing:3px; color:#bc8cff; text-transform:uppercase; margin-bottom:0.3rem;">
        📅 Lunar Calendar
    </div>
    <div style="font-family:'Crimson Pro', serif; font-size:1rem; color:#8b949e; margin-bottom:1.2rem; font-style:italic;">
        Track moon phases throughout the month.
    </div>
    """, unsafe_allow_html=True)

    # Month navigation
    nav_col1, nav_col2, nav_col3 = st.columns([1, 2, 1])
    
    with nav_col1:
        if st.button("◀ Previous", use_container_width=True):
            if st.session_state.calendar_month == 1:
                st.session_state.calendar_month = 12
                st.session_state.calendar_year -= 1
            else:
                st.session_state.calendar_month -= 1
            st.rerun()
    
    with nav_col2:
        month_name = datetime(st.session_state.calendar_year, st.session_state.calendar_month, 1).strftime("%B %Y")
        st.markdown(f"<h3 style='text-align:center; color:#fff;'>{month_name}</h3>", unsafe_allow_html=True)
    
    with nav_col3:
        if st.button("Next ▶", use_container_width=True):
            if st.session_state.calendar_month == 12:
                st.session_state.calendar_month = 1
                st.session_state.calendar_year += 1
            else:
                st.session_state.calendar_month += 1
            st.rerun()

    # Calendar grid
    month_cal = cal.monthcalendar(st.session_state.calendar_year, st.session_state.calendar_month)
    weekdays = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    
    # Weekday headers
    header_cols = st.columns(7)
    for i, day in enumerate(weekdays):
        with header_cols[i]:
            st.markdown(f"<div style='text-align:center; color:#8b949e; font-size:0.7rem; font-weight:700; margin-bottom:0.5rem;'>{day}</div>", unsafe_allow_html=True)
    
    # Calendar days
    today = datetime.now()
    for week in month_cal:
        day_cols = st.columns(7)
        for i, day in enumerate(week):
            with day_cols[i]:
                if day == 0:
                    st.markdown("<div style='min-height:80px;'></div>", unsafe_allow_html=True)
                else:
                    # Calculate moon phase for this day
                    date_obj = datetime(st.session_state.calendar_year, st.session_state.calendar_month, day)
                    day_data = get_celestial_data(date_obj.replace(tzinfo=timezone.utc))
                    
                    is_today = (day == today.day and 
                               st.session_state.calendar_month == today.month and 
                               st.session_state.calendar_year == today.year)
                    
                    today_class = "calendar-today" if is_today else ""
                    
                    st.markdown(f"""
                    <div class="calendar-day {today_class}">
                        <div style="font-size:0.9rem; font-weight:700; color:#fff; margin-bottom:0.3rem;">{day}</div>
                        <div style="font-size:1.5rem; margin-bottom:0.2rem;">{day_data['phase_emoji']}</div>
                        <div style="font-size:0.6rem; color:#8b949e;">{day_data['illum']*100:.0f}%</div>
                    </div>
                    """, unsafe_allow_html=True)

# ===========================================================================
# TAB 4: SETTINGS
# ===========================================================================

with tab4:
    st.markdown("""
    <div style="font-family:'Orbitron', sans-serif; font-size:0.8rem; letter-spacing:3px; color:#bc8cff; text-transform:uppercase; margin-bottom:0.3rem;">
        ⚙️ Settings
    </div>
    <div style="font-family:'Crimson Pro', serif; font-size:1rem; color:#8b949e; margin-bottom:1.2rem; font-style:italic;">
        Customize your lunar experience.
    </div>
    """, unsafe_allow_html=True)

    st.subheader("Personal Information")
    st.info(f"📅 Current Birth Date: {st.session_state.birth_date.strftime('%B %d, %Y')}")
    st.markdown("*Update your birth date in the sidebar to recalculate your cosmic chart.*")
    
    st.markdown("---")
    
    st.subheader("Journal Management")
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("Total Entries", len(st.session_state.journal_entries))
    
    with col2:
        if st.session_state.journal_entries:
            latest_entry = st.session_state.journal_entries[0]
            st.metric("Latest Entry", latest_entry['phase'])
    
    if st.session_state.journal_entries:
        st.markdown("**📥 Import/Export**")
        export_data = json.dumps(st.session_state.journal_entries, indent=2)
        st.download_button(
            label="📥 Download Journal Data",
            data=export_data,
            file_name=f"lunatick_journal_{now_utc.strftime('%Y%m%d')}.json",
            mime="application/json",
            use_container_width=True
        )
    
    st.markdown("---")
    
    st.subheader("About LUNATICK")
    st.markdown("""
    **Version:** 2.0  
    **Moon Data:** Calculated using PyEphem astronomical library  
    **Lunar Cycle:** 29.53 days  
    **Time Zone:** UTC  
    
    LUNATICK provides real-time moon phase tracking, personalized cosmic insights, 
    and a private lunar journal to help you connect with the rhythms of the moon.
    """)
    
    st.markdown("---")
    st.markdown("<p style='text-align:center; color:#484f58; font-size:0.65rem;'>🌙 LUNATICK — YOUR COSMIC MOON COMPANION</p>", unsafe_allow_html=True)
