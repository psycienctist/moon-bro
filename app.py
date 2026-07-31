import streamlit as st
import ephem
import math
import requests
from datetime import datetime, timezone, timedelta

# ---------------------------------------------------------------------------
# Import modules
# ---------------------------------------------------------------------------
import journal as journal_ui
import lunatick_talk_ui as talk_ui
import lunatick_talk_db as talk_db
import daily_reflection as reflection_ui
import cosmic_cards
import boards
import chat_room
import auth


def init_session_state():
    defaults = {
        "user_hash": "anonymous",
        "is_authenticated": False,
        "current_phase": "Waxing Gibbous",
        "current_tab": "Journal",
        "journal_prompt_mode": "🌙 Phase Reflection",
        "journal_phase_input": "",
        "journal_chart_input": "",
        "journal_free_input": "",
        "display_name": "Moon Wanderer",
        # Navigation
        "nav_view": "home",
        "nav_popup": None,
        "show_profile_menu": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


init_session_state()

# ---------------------------------------------------------------------------
# Page config & Lunatick Theme (+ bottom nav / chrome)
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
    .event-info { display: flex; flex-direction: column; }
    .etitle { color: #fff; font-weight: 600; font-size: 0.9rem; }
    .edesc { color: #8b949e; font-size: 0.75rem; line-height: 1.2; }
    .event-date { color: #ff7b72; font-family: 'Orbitron', sans-serif; font-size: 0.6rem; margin-top: 0.3rem; }

    /* ---- App chrome: leave room for fixed bottom nav ---- */
    .main .block-container {
        padding-bottom: 7.5rem !important;
        max-width: 900px;
        padding-top: 1rem;
    }

    .nav-popup-panel {
        background: #0d1117;
        border: 1px solid #6e40c9;
        border-radius: 14px;
        padding: 0.75rem 0.9rem;
        margin: 0.4rem 0 0.6rem 0;
        box-shadow: 0 0 24px rgba(110, 64, 201, 0.25);
    }
    .nav-popup-title {
        font-family: 'Orbitron', sans-serif;
        font-size: 0.65rem;
        letter-spacing: 2px;
        color: #bc8cff;
        text-transform: uppercase;
        margin-bottom: 0.5rem;
    }

    .profile-chip {
        display: inline-flex;
        align-items: center;
        gap: 0.45rem;
        background: rgba(110, 64, 201, 0.2);
        border: 1px solid #6e40c9;
        border-radius: 999px;
        padding: 0.25rem 0.75rem 0.25rem 0.3rem;
        color: #e6edf3;
        font-size: 0.85rem;
    }
    .profile-avatar {
        width: 28px; height: 28px;
        border-radius: 50%;
        background: linear-gradient(135deg, #6e40c9, #58a6ff);
        display: flex; align-items: center; justify-content: center;
        font-size: 0.85rem; font-weight: 700; color: #fff;
    }

    /* Bottom nav styling helpers */
    .bottom-nav-hint {
        font-family: 'Orbitron', sans-serif;
        font-size: 0.55rem;
        letter-spacing: 1px;
        color: #8b949e;
        text-align: center;
        margin-top: 0.15rem;
    }

    ::-webkit-scrollbar { width: 6px; }

    /* Hide default Streamlit footer clutter */
    footer { visibility: hidden; }
</style>
"""
st.markdown(LUNATICK_CSS, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Init DBs early (needed for auth profiles)
# ---------------------------------------------------------------------------
journal_ui.init_db()
talk_db.init_db()
cosmic_cards.init_cards_db()
boards.init_boards_db()
chat_room.init_chat_db()
auth.init_auth_db()

# ---------------------------------------------------------------------------
# AUTH GATE — must log in before using the app
# ---------------------------------------------------------------------------
if not auth.render_login_page():
    st.stop()

# ---------------------------------------------------------------------------
# Logic Functions (unchanged)
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


def get_moon_phase_name(phase_frac: float):
    phases = [
        (0.00, "New Moon", "🌑"), (0.07, "Waxing Crescent", "🌒"), (0.25, "First Quarter", "🌓"),
        (0.43, "Waxing Gibbous", "🌔"), (0.50, "Full Moon", "🌕"), (0.57, "Waning Gibbous", "🌖"),
        (0.75, "Last Quarter", "🌗"), (0.93, "Waning Crescent", "🌘"), (1.00, "New Moon", "🌑"),
    ]
    for i in range(len(phases) - 1):
        if phases[i][0] <= phase_frac < phases[i + 1][0]:
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
        "moon_sign": moon_sign, "moon_symbol": moon_symbol, "moon_vibe": moon_vibe, "moon_lon": moon_lon,
        "sun_sign": sun_sign, "sun_symbol": sun_symbol,
        "phase_frac": phase_frac, "phase_name": phase_name, "phase_emoji": phase_emoji, "illum": illum,
        "next_full_dt": nfm_dt, "age_days": phase_frac * 29.53,
    }


@st.cache_data(ttl=3600)
def get_ai_insight(natal, current, aspect):
    api_key = st.secrets.get("DEEPSEEK_API_KEY")
    if not api_key:
        return None

    prompt = f"""
    As a cosmic guide, provide a short, poetic, and encouraging astrology insight (max 3 sentences).
    User Natal: Sun in {natal['sun_sign']}, Moon in {natal['moon_sign']}.
    Current Sky: Moon in {current['moon_sign']} ({current['phase_name']}).
    Natal-Current Aspect: {aspect}.
    Tone: Mystical, empowering, and modern.
    """

    try:
        response = requests.post(
            "https://api.deepseek.com/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": "You are a mystical cosmic guide for the Lunatick app."},
                    {"role": "user", "content": prompt},
                ],
                "stream": False,
            },
            timeout=10,
        )
        return response.json()["choices"][0]["message"]["content"]
    except Exception:
        return None


def render_home():
    """Home dashboard — DO NOT change content, layout, or styling."""
    now_utc = datetime.now(timezone.utc)
    current = get_celestial_data(now_utc)

    if "birth_date" not in st.session_state:
        st.session_state.birth_date = datetime(1990, 1, 1).date()

    with st.sidebar:
        st.markdown("### 🧬 Personal Cosmic Profile")
        birth_date_input = st.date_input(
            "When were you born?",
            value=st.session_state.birth_date,
            min_value=datetime(1920, 1, 1),
            max_value=now_utc,
        )
        if birth_date_input != st.session_state.birth_date:
            st.session_state.birth_date = birth_date_input
            bd_str = birth_date_input.isoformat() if hasattr(birth_date_input, "isoformat") else str(birth_date_input)
            bd_str = bd_str[:10]
            cosmic_cards.save_profile(
                st.session_state.get("user_hash", "anonymous"),
                st.session_state.get("display_name", "Moon Wanderer"),
                bd_str,
            )
            if st.session_state.get("username"):
                auth.update_user_profile(
                    st.session_state.username,
                    st.session_state.get("display_name", "Moon Wanderer"),
                    bd_str,
                )
            st.rerun()
        st.success("🔒 Private: Insights are only visible to you.")

    delta = current["next_full_dt"] - now_utc
    d, rem = divmod(int(delta.total_seconds()), 86400)
    h, m_total = divmod(rem, 3600)
    m, _ = divmod(m_total, 60)

    st.markdown(f"""
    <div class="glow-container">
        <h1 style="color:#bc8cff; margin-bottom:0rem; font-size:3.2rem; letter-spacing:4px;">🌙 LUNATICK</h1>
        <div style="color:#8b949e; font-size:0.8rem; letter-spacing:3px; margin-bottom:1rem; font-weight:700;">MOON MONITOR</div>
        <p style="color:#8b949e; font-size:0.75rem; margin-bottom:0.6rem; letter-spacing:1.5px;">NEXT FULL MOON</p>
        <div class="countdown-display">
            <div class="unit-box"><div class="num">{d}</div><div class="label">Days</div></div>
            <div class="unit-box"><div class="num">{h}</div><div class="label">Hours</div></div>
            <div class="unit-box"><div class="num">{m}</div><div class="label">Mins</div></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    birth_raw = st.session_state.birth_date
    if hasattr(birth_raw, "date") and not isinstance(birth_raw, datetime):
        birth_day = birth_raw
    elif isinstance(birth_raw, datetime):
        birth_day = birth_raw.date()
    else:
        birth_day = birth_raw

    birth_utc = datetime.combine(birth_day, datetime.min.time()).replace(tzinfo=timezone.utc)
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

    insight = get_ai_insight(natal, current, aspect)

    sun_c = cosmic_cards.sign_color(natal["sun_sign"])
    moon_c = cosmic_cards.sign_color(natal["moon_sign"])
    cur_moon_c = cosmic_cards.sign_color(current["moon_sign"])

    st.markdown(f"""
    <div class="personal-card">
        <div style="color:#58a6ff; font-size:0.85rem; font-weight:700; text-align:center; margin-bottom:0.8rem; letter-spacing:2px; font-family:'Orbitron', sans-serif;">
            YOUR COSMIC CHART
        </div>
        <div style="display:flex; justify-content:space-around; text-align:center; gap:0.5rem;">
            <div><div style="color:#8b949e; font-size:0.5rem;">SUN SIGN</div><div style="font-size:1.1rem; font-weight:700; color:{sun_c};">{natal['sun_symbol']} {natal['sun_sign']}</div></div>
            <div><div style="color:#8b949e; font-size:0.5rem;">MOON SIGN</div><div style="font-size:1.1rem; font-weight:700; color:{moon_c};">{natal['moon_symbol']} {natal['moon_sign']}</div></div>
            <div><div style="color:#8b949e; font-size:0.5rem;">LUNAR PHASE</div><div style="font-size:1.1rem; font-weight:700; color:#fff;">{natal['phase_emoji']} {natal['phase_name']}</div></div>
            <div><div style="color:#8b949e; font-size:0.5rem;">FULL MOONS</div><div style="font-size:1.1rem; font-weight:700; color:#bc8cff;">{int(total_moons)} LIVED</div></div>
        </div>
        <div style="margin-top:0.8rem; background:rgba(0,0,0,0.3); padding:0.8rem; border-radius:10px; border:1px solid #1f6feb;">
            <div style="color:#58a6ff; font-weight:700; font-size:0.8rem; margin-bottom:0.2rem;">✨ {aspect.upper()} FORECAST</div>
            <div style="color:#e6edf3; line-height:1.4; font-size:0.9rem;">{guidance}</div>
        </div>
        {f'''
        <div style="margin-top:0.8rem; background:rgba(188, 140, 255, 0.1); padding:0.8rem; border-radius:10px; border:1px solid #bc8cff;">
            <div style="color:#bc8cff; font-weight:700; font-size:0.8rem; margin-bottom:0.2rem;">🔮 DEEPSEEK AI INSIGHT</div>
            <div style="color:#e6edf3; line-height:1.4; font-size:0.9rem; font-style: italic;">"{insight}"</div>
        </div>
        ''' if insight else ''}
    </div>
    """, unsafe_allow_html=True)

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
            <div class="stat-label" style="font-size:0.55rem;">Surface</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Age</div>
            <div class="stat-val">{current["age_days"]:.1f}d</div>
            <div class="stat-label" style="font-size:0.55rem;">Cycle</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    vcol, ecol = st.columns([1, 1])
    with vcol:
        st.markdown(f"""
        <div class="vibe-card">
            <div class="vibe-tag">ENERGY</div>
            <h3 style="color:{cur_moon_c}; margin-bottom:0.5rem; font-size:1.1rem;">{current['moon_symbol']} Moon in {current['moon_sign']}</h3>
            <p style="font-size:0.9rem; line-height:1.4; color:#c9d1d9;">{current['moon_vibe']}</p>
        </div>
        """, unsafe_allow_html=True)

    with ecol:
        st.subheader("🔭 2026 Cosmic Calendar")
        for d_str, title, desc in [
            ("March 3", "Total Lunar Eclipse", "Visible across the Americas, Europe, and Africa."),
            ("August 12, 2026", "Total Solar Eclipse", "Major eclipse visible in Europe & Greenland."),
            ("August 28, 2026", "Partial Lunar Eclipse", "Visible from the Pacific region."),
            ("September 26, 2026", "Corn Moon (Supermoon)", "The largest full moon appearance of the year."),
        ]:
            st.markdown(f'''
            <div class="event-item">
                <div class="event-info">
                    <div class="etitle">{title}</div>
                    <div class="edesc">{desc}</div>
                </div>
                <div class="event-date">{d_str}</div>
            </div>
            ''', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 🧠 Daily Reflection")
    reflection_ui.render_daily_reflection()


def render_calendar():
    st.markdown("""
    <div style="font-family: 'Orbitron', sans-serif; font-size: 0.8rem; letter-spacing: 3px; color: #bc8cff; text-transform: uppercase; margin-bottom: 0.3rem;">
        📅 Lunar Calendar
    </div>
    <div style="font-family: 'Crimson Pro', serif; font-size: 1rem; color: #8b949e; margin-bottom: 1.2rem; font-style: italic;">
        Track moon phases throughout the month.
    </div>
    """, unsafe_allow_html=True)

    now = datetime.now()
    if "calendar_month" not in st.session_state:
        st.session_state.calendar_month = now.month
    if "calendar_year" not in st.session_state:
        st.session_state.calendar_year = now.year

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
        st.markdown(
            f"<h3 style='text-align:center; color:#fff;'>{datetime(st.session_state.calendar_year, st.session_state.calendar_month, 1).strftime('%B %Y')}</h3>",
            unsafe_allow_html=True,
        )
    with nav_col3:
        if st.button("Next ▶", use_container_width=True):
            if st.session_state.calendar_month == 12:
                st.session_state.calendar_month = 1
                st.session_state.calendar_year += 1
            else:
                st.session_state.calendar_month += 1
            st.rerun()

    import calendar as cal

    month_cal = cal.monthcalendar(st.session_state.calendar_year, st.session_state.calendar_month)
    weekdays = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    header_cols = st.columns(7)
    for i, day in enumerate(weekdays):
        with header_cols[i]:
            st.markdown(
                f"<div style='text-align:center; color:#8b949e; font-size:0.7rem; font-weight:700;'>{day}</div>",
                unsafe_allow_html=True,
            )

    today = datetime.now()
    for week in month_cal:
        day_cols = st.columns(7)
        for i, day in enumerate(week):
            with day_cols[i]:
                if day == 0:
                    st.markdown("<div style='min-height:80px;'></div>", unsafe_allow_html=True)
                else:
                    date_obj = datetime(st.session_state.calendar_year, st.session_state.calendar_month, day)
                    day_data = get_celestial_data(date_obj.replace(tzinfo=timezone.utc))
                    is_today = (
                        day == today.day
                        and st.session_state.calendar_month == today.month
                        and st.session_state.calendar_year == today.year
                    )
                    st.markdown(f"""
                    <div style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.1); border-radius:8px; padding:0.5rem; text-align:center; min-height:80px; {'' if not is_today else 'border:2px solid #6e40c9; background:rgba(110,64,201,0.1);'}">
                        <div style="font-size:0.9rem; font-weight:700; color:#fff; margin-bottom:0.3rem;">{day}</div>
                        <div style="font-size:1.5rem; margin-bottom:0.2rem;">{day_data['phase_emoji']}</div>
                        <div style="font-size:0.6rem; color:#8b949e;">{day_data['illum']*100:.0f}%</div>
                    </div>
                    """, unsafe_allow_html=True)


def render_settings():
    st.markdown("""
    <div style="font-family: 'Orbitron', sans-serif; font-size: 0.8rem; letter-spacing: 3px; color: #bc8cff; text-transform: uppercase; margin-bottom: 0.3rem;">
        ⚙️ Settings
    </div>
    <div style="font-family: 'Crimson Pro', serif; font-size: 1rem; color: #8b949e; margin-bottom: 1.2rem; font-style: italic;">
        Manage your account, privacy, and subscription.
    </div>
    """, unsafe_allow_html=True)

    st.info(f"Logged in as **@{st.session_state.get('username', '?')}**")

    st.markdown("### 🧬 Birth chart")
    st.caption("Date, time, and place power your Cosmic Card (including Rising).")
    cosmic_cards.render_profile_form(
        st.session_state.get("user_hash", "anonymous"),
        key_prefix="settings",
    )

    st.markdown("---")
    st.markdown("### 🔒 Privacy & Consent")
    if st.button("Opt in to community sharing", key="set_opt_in"):
        st.success("You have opted in to community sharing.")
    if st.button("Opt out of community sharing", key="set_opt_out"):
        st.success("You have opted out of community sharing.")

    st.markdown("---")
    st.markdown("### 💎 Subscription")
    st.selectbox("Your Tier", ["Free", "Community ($5/mo)", "Resonance ($15/mo)"], key="set_tier")
    st.info("Upgrade to Community or Resonance for full access to AI insights and community features.")

    st.markdown("---")
    st.markdown("### 🗑️ Danger Zone")
    if st.button("Clear all journal entries", type="secondary", key="set_clear_j"):
        if "journal_entries" in st.session_state:
            st.session_state.journal_entries = []
            st.success("Journal entries cleared.")
    if st.button("Log out of this account", type="secondary", key="set_logout"):
        auth.logout()
        st.rerun()


def render_privacy():
    st.markdown("### 🔒 Privacy")
    st.caption("Control how your presence appears in the community.")
    st.info(f"Signed in as **@{st.session_state.get('username', '?')}**")
    if st.button("Opt in to community sharing", key="priv_in"):
        st.success("You have opted in to community sharing.")
    if st.button("Opt out of community sharing", key="priv_out"):
        st.success("You have opted out of community sharing.")
    st.markdown(
        "Your journal is private. Cosmic card trades are only visible to people you connect with."
    )


def render_my_profile():
    st.markdown("### 👤 My Profile")
    name = st.session_state.get("display_name", "Moon Wanderer")
    uname = st.session_state.get("username", "?")
    st.markdown(f"**{name}** · @{uname}")

    card = cosmic_cards.build_card(st.session_state.get("user_hash", "anonymous"))
    if card:
        n = card["natal"]
        parts = [f"{n['sun_symbol']} {n['sun_sign']}", f"{n['moon_symbol']} {n['moon_sign']}"]
        if n.get("has_rising"):
            parts.append(f"{n['rising_symbol']} Rising {n['rising_sign']}")
        st.markdown(" · ".join(parts))
        if card.get("birth_place"):
            st.caption(f"📍 {card['birth_place']}")
    else:
        st.caption("Add your birth data under Reflect → Birth Chart to unlock your card.")

    st.markdown("---")
    st.markdown("#### 🤝 Friends")
    friends = cosmic_cards.friends_of(st.session_state.get("user_hash", "anonymous"))
    if not friends:
        st.caption("No friends yet — trade cosmic cards to connect.")
    for fh in friends:
        fc = cosmic_cards.build_card(fh)
        if fc:
            nn = fc["natal"]
            st.markdown(
                f"• **{fc['display_name']}** — "
                f"{nn['sun_symbol']}{nn['sun_sign']} · {nn['moon_symbol']}{nn['moon_sign']}"
            )

    st.markdown("---")
    st.markdown("#### 🃏 Your Cosmic Card")
    if card:
        cosmic_cards.render_cosmic_cards_tab()
    else:
        st.info("Create your chart to collect and trade cards.")


def render_birth_chart():
    st.markdown("### 🧬 Birth Chart")
    st.caption("Date, time, and place power Rising and your Cosmic Card.")
    cosmic_cards.render_profile_form(
        st.session_state.get("user_hash", "anonymous"),
        key_prefix="birth",
    )


def render_human_design():
    st.markdown("### 🔮 Human Design")
    st.info("Human Design is coming soon — your chart space is reserved under Reflect.")


def render_entry_history():
    st.markdown("### 📜 Entry History")
    st.caption("Recent sealed journal reflections.")
    recent = journal_ui.get_recent_entries(limit=20)
    if not recent:
        st.info("No entries yet. Write one under Recollect → Journal.")
        return
    for phase, prompt_type, content, created_at in recent:
        label = journal_ui.PROMPTS.get(prompt_type, {}).get("label", prompt_type)
        st.markdown(f"**{phase}** · {label} · `{str(created_at)[:16]}`")
        st.markdown(f"> {content}")
        st.markdown("---")


def go_view(view: str):
    st.session_state.nav_view = view
    st.session_state.nav_popup = None
    st.rerun()


def toggle_popup(name: str):
    if st.session_state.get("nav_popup") == name:
        st.session_state.nav_popup = None
    else:
        st.session_state.nav_popup = name
    st.rerun()


# ---------------------------------------------------------------------------
# Sync phase + seed
# ---------------------------------------------------------------------------
if "current_phase" not in st.session_state:
    st.session_state.current_phase = get_celestial_data(datetime.now(timezone.utc))["phase_name"]

try:
    talk_db.seed_talk_posts()
except Exception:
    pass

# ---------------------------------------------------------------------------
# TOP BAR — profile avatar (top-right)
# ---------------------------------------------------------------------------
top_l, top_r = st.columns([4, 1])
with top_r:
    initial = (st.session_state.get("display_name") or st.session_state.get("username") or "M")[:1].upper()
    try:
        with st.popover(f"👤 {initial}", use_container_width=True):
            st.caption(f"@{st.session_state.get('username', '?')}")
            if st.button("My Profile", use_container_width=True, key="pop_profile"):
                go_view("my_profile")
            if st.button("Settings", use_container_width=True, key="pop_settings"):
                go_view("settings")
            if st.button("Log out", use_container_width=True, key="pop_logout"):
                auth.logout()
                st.rerun()
    except Exception:
        # Older Streamlit without popover
        if st.button(f"👤 {initial}", key="avatar_fallback"):
            st.session_state.show_profile_menu = not st.session_state.get("show_profile_menu", False)
            st.rerun()
        if st.session_state.get("show_profile_menu"):
            if st.button("My Profile", key="fb_profile"):
                go_view("my_profile")
            if st.button("Settings", key="fb_settings"):
                go_view("settings")
            if st.button("Log out", key="fb_logout"):
                auth.logout()
                st.rerun()

# ---------------------------------------------------------------------------
# MAIN CONTENT — by nav_view (Home unchanged)
# ---------------------------------------------------------------------------
view = st.session_state.get("nav_view", "home")

if view == "home":
    render_home()
elif view == "chat":
    chat_room.render_chat_tab()
elif view == "boards":
    boards.render_boards_tab()
elif view == "talk":
    talk_ui.render_talk_tab()
elif view == "cosmic_cards":
    cosmic_cards.render_cosmic_cards_tab()
elif view == "birth_chart":
    render_birth_chart()
elif view == "human_design":
    render_human_design()
elif view == "journal":
    journal_ui.render_journal_tab()
elif view == "daily_reflection":
    reflection_ui.render_daily_reflection()
elif view == "entry_history":
    render_entry_history()
elif view == "settings":
    render_settings()
elif view == "privacy":
    render_privacy()
elif view == "my_profile":
    render_my_profile()
elif view == "calendar":
    render_calendar()
else:
    render_home()

# ---------------------------------------------------------------------------
# SUB-MENU POPUP (above bottom nav)
# ---------------------------------------------------------------------------
popup = st.session_state.get("nav_popup")

if popup == "connect":
    st.markdown('<div class="nav-popup-panel"><div class="nav-popup-title">Connect</div></div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("💬 Chat", use_container_width=True, key="sub_chat"):
            go_view("chat")
    with c2:
        if st.button("📋 Boards", use_container_width=True, key="sub_boards"):
            go_view("boards")
    with c3:
        if st.button("🗣 Talk", use_container_width=True, key="sub_talk"):
            go_view("talk")

elif popup == "reflect":
    st.markdown('<div class="nav-popup-panel"><div class="nav-popup-title">Reflect</div></div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("🃏 Cards", use_container_width=True, key="sub_cards"):
            go_view("cosmic_cards")
    with c2:
        if st.button("🧬 Birth Chart", use_container_width=True, key="sub_birth"):
            go_view("birth_chart")
    with c3:
        if st.button("🔮 Human Design", use_container_width=True, key="sub_hd"):
            go_view("human_design")

elif popup == "recollect":
    st.markdown('<div class="nav-popup-panel"><div class="nav-popup-title">Recollect</div></div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("📓 Journal", use_container_width=True, key="sub_journal"):
            go_view("journal")
    with c2:
        if st.button("🌙 Daily Reflection", use_container_width=True, key="sub_daily"):
            go_view("daily_reflection")
    with c3:
        if st.button("📜 History", use_container_width=True, key="sub_history"):
            go_view("entry_history")

elif popup == "reset":
    st.markdown('<div class="nav-popup-panel"><div class="nav-popup-title">Reset</div></div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("⚙️ Settings", use_container_width=True, key="sub_settings"):
            go_view("settings")
    with c2:
        if st.button("🔒 Privacy", use_container_width=True, key="sub_privacy"):
            go_view("privacy")
    with c3:
        if st.button("🚪 Logout", use_container_width=True, key="sub_logout"):
            auth.logout()
            st.rerun()

# ---------------------------------------------------------------------------
# BOTTOM NAV — logo (Home) + 4 main sections (always visible)
# ---------------------------------------------------------------------------
st.markdown("---")

nav_home, nav1, nav2, nav3, nav4 = st.columns([1.1, 1, 1, 1, 1])

with nav_home:
    if st.button("🌙\nHome", use_container_width=True, key="nav_logo_home",
                 type="primary" if view == "home" else "secondary"):
        go_view("home")

with nav1:
    active = popup == "connect" or view in ("chat", "boards", "talk")
    if st.button("🔗\nConnect", use_container_width=True, key="nav_connect",
                 type="primary" if active else "secondary"):
        toggle_popup("connect")

with nav2:
    active = popup == "reflect" or view in ("cosmic_cards", "birth_chart", "human_design")
    if st.button("✨\nReflect", use_container_width=True, key="nav_reflect",
                 type="primary" if active else "secondary"):
        toggle_popup("reflect")

with nav3:
    active = popup == "recollect" or view in ("journal", "daily_reflection", "entry_history")
    if st.button("📔\nRecollect", use_container_width=True, key="nav_recollect",
                 type="primary" if active else "secondary"):
        toggle_popup("recollect")

with nav4:
    active = popup == "reset" or view in ("settings", "privacy")
    if st.button("↺\nReset", use_container_width=True, key="nav_reset",
                 type="primary" if active else "secondary"):
        toggle_popup("reset")

st.markdown(
    "<p class='bottom-nav-hint'>TAP A SECTION · LOGO RETURNS HOME</p>",
    unsafe_allow_html=True,
)
