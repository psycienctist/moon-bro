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
import community
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
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


init_session_state()

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

    .glow-container {
        background: radial-gradient(circle at top right, #1b1040 0%, #05070a 100%);
        border: 1px solid #6e40c9;
        border-radius: 16px;
        padding: 0.8rem 1rem;
        margin-bottom: 0.5rem;
        box-shadow: 0 0 30px rgba(110, 64, 201, 0.15);
        position: relative;
        text-align: center;
        animation: lunatick-glow-pulse 8s ease-in-out infinite;
    }

    /* A deliberately slow, low-contrast ambient glow for the Home monitor. */
    @keyframes lunatick-glow-pulse {
        0%, 100% {
            border-color: rgba(110, 64, 201, 0.72);
            box-shadow: 0 0 26px rgba(110, 64, 201, 0.14), 0 0 44px rgba(31, 111, 235, 0.04);
        }
        50% {
            border-color: rgba(188, 140, 255, 0.94);
            box-shadow: 0 0 38px rgba(188, 140, 255, 0.24), 0 0 64px rgba(31, 111, 235, 0.10);
        }
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

    /* Fluid visual feedback for Streamlit expanders, including Cosmic Card
       term explanations. The opening panel fades/slides in without changing
       the existing expander content or behavior. */
    [data-testid="stExpander"],
    [data-testid="stExpander"] details {
        border-color: rgba(188, 140, 255, 0.22);
        transition: border-color 220ms ease, box-shadow 220ms ease, background-color 220ms ease;
    }

    [data-testid="stExpander"]:has(details[open]),
    [data-testid="stExpander"][open] {
        border-color: rgba(188, 140, 255, 0.52);
        box-shadow: 0 0 18px rgba(188, 140, 255, 0.10);
    }

    [data-testid="stExpander"] summary svg,
    [data-testid="stExpander"] details summary svg {
        transition: transform 220ms ease;
    }

    [data-testid="stExpander"] details[open] > div,
    [data-testid="stExpander"][open] > div {
        animation: lunatick-expander-reveal 260ms ease-out both;
    }

    @keyframes lunatick-expander-reveal {
        from { opacity: 0; transform: translateY(-5px); }
        to { opacity: 1; transform: translateY(0); }
    }

    /* Remove Streamlit chrome so the application reads as a focused native
       experience. App content and the custom Lunatick navigation are intact. */
    #MainMenu,
    [data-testid="stDeployButton"],
    .stDeployButton,
    [data-testid="stToolbar"],
    [data-testid="stAppFooter"],
    [data-testid="stManageApp"],
    [data-testid="stManageAppButton"],
    footer {
        display: none !important;
    }

    [data-testid="stHeader"] {
        background: transparent;
    }

    @media (prefers-reduced-motion: reduce) {
        .glow-container,
        [data-testid="stExpander"],
        [data-testid="stExpander"] * {
            animation: none !important;
            transition: none !important;
        }
    }

    /* ---------------------------------------------------------------------
       Persistent lower-left Lunatick home logo
       ---------------------------------------------------------------------
       Sits at the true bottom-left of the viewport, in the same strip as
       Streamlit's native "Manage app" control. Does not modify, offset,
       or depend on the bottom navigation bar in any way. */
    [class*="st-key-lunatick-home-logo"] {
        height: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
        pointer-events: none;
    }

    [class*="st-key-lunatick-home-logo"] [data-testid="stButton"] {
        position: fixed !important;
        z-index: 1001 !important;
        left: 0 !important;
        bottom: 0 !important;
        /* The Home logo remains at its original full half-screen width. */
        width: 50vw !important;
        height: 2.625rem !important;
        margin: 0 !important;
        padding: 0 !important;
        display: block !important;
        visibility: visible !important;
        opacity: 1 !important;
        pointer-events: auto;
    }

    [class*="st-key-lunatick-home-logo"] [data-testid="stButton"] > button {
        align-items: center;
        background: linear-gradient(135deg, rgba(13, 31, 60, 0.98), rgba(45, 27, 105, 0.98));
        border: 1px solid rgba(188, 140, 255, 0.62);
        border-radius: 0;
        box-shadow: 0 0 12px rgba(110, 64, 201, 0.22);
        color: #d2a8ff;
        display: flex;
        font-family: 'Orbitron', sans-serif;
        font-size: 0.72rem;
        font-weight: 700;
        height: 100%;
        justify-content: flex-start;
        letter-spacing: 0.08em;
        overflow: hidden;
        padding: 0 0.75rem;
        pointer-events: auto;
        text-overflow: ellipsis;
        transition: border-color 180ms ease, box-shadow 180ms ease;
        white-space: nowrap;
        width: 100%;
    }

    [class*="st-key-lunatick-home-logo"] [data-testid="stButton"] > button:hover,
    [class*="st-key-lunatick-home-logo"] [data-testid="stButton"] > button:focus-visible {
        border-color: #bc8cff;
        box-shadow: 0 0 18px rgba(188, 140, 255, 0.38);
        color: #f0e6ff;
        outline: none;
    }

    /* Persistent compact Settings control, placed directly beside the
       lower-left Home logo. It is independent of the fixed navigation rail. */
    [class*="st-key-lunatick-settings-gear"] {
        height: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
        pointer-events: none;
    }

    [class*="st-key-lunatick-settings-gear"] [data-testid="stButton"] {
        position: fixed !important;
        z-index: 1002 !important;
        left: 50vw !important;
        bottom: 0 !important;
        width: 2.625rem !important;
        height: 2.625rem !important;
        margin: 0 !important;
        padding: 0 !important;
        display: block !important;
        visibility: visible !important;
        opacity: 1 !important;
        pointer-events: auto;
    }

    [class*="st-key-lunatick-settings-gear"] [data-testid="stButton"] > button {
        align-items: center;
        background: linear-gradient(135deg, rgba(24, 29, 48, 0.98), rgba(45, 27, 105, 0.98));
        border: 1px solid rgba(188, 140, 255, 0.62);
        border-radius: 0;
        box-shadow: 0 0 12px rgba(110, 64, 201, 0.22);
        color: #d2a8ff;
        display: flex;
        font-size: 1rem;
        height: 100%;
        justify-content: center;
        min-height: 0;
        padding: 0;
        transition: border-color 180ms ease, box-shadow 180ms ease, color 180ms ease;
        width: 100%;
    }

    [class*="st-key-lunatick-settings-gear"] [data-testid="stButton"] > button:hover,
    [class*="st-key-lunatick-settings-gear"] [data-testid="stButton"] > button:focus-visible {
        border-color: #bc8cff;
        box-shadow: 0 0 18px rgba(188, 140, 255, 0.38);
        color: #f0e6ff;
        outline: none;
    }

    /* The persistent Home and Settings controls mirror the active red state
       used by the selected bottom-navigation destination. */
    [class*="st-key-lunatick-home-logo-active"] [data-testid="stButton"] > button,
    [class*="st-key-lunatick-settings-gear-active"] [data-testid="stButton"] > button {
        background: linear-gradient(135deg, #f25555, #e33f3f) !important;
        border-color: rgba(255, 196, 196, 0.90) !important;
        box-shadow: 0 0 18px rgba(242, 85, 85, 0.42) !important;
        color: #ffffff !important;
    }

    @media (max-width: 480px) {
        [class*="st-key-lunatick-home-logo"] [data-testid="stButton"] {
            width: 50vw !important;
            height: 2.625rem !important;
            bottom: 0 !important;
            left: 0 !important;
        }

        [class*="st-key-lunatick-home-logo"] [data-testid="stButton"] > button {
            font-size: 0.66rem;
            padding: 0 0.6rem;
        }

        [class*="st-key-lunatick-settings-gear"] [data-testid="stButton"] {
            left: 50vw !important;
            bottom: 0 !important;
            width: 2.625rem !important;
            height: 2.625rem !important;
        }
    }

    /* ---------------------------------------------------------------------
       Fixed bottom navigation
       ---------------------------------------------------------------------
       The keyed container at the end of this file receives the documented
       `.st-key-lunatick-bottom-nav` class in Streamlit 1.40+.
    */

    /* Keep the page's final card, form control, and footer above the fixed
       navigation bar. */
    [data-testid="stMainBlockContainer"] {
        padding-bottom: 9rem;
    }

    /* Pin only the dedicated navigation container to the viewport. */
    .st-key-lunatick-bottom-nav {
        position: fixed;
        z-index: 1000;
        bottom: 0;
        left: 0;
        right: 0;
        width: 100%;
        margin: 0;
        padding: 0.55rem clamp(0.6rem, 2vw, 1.5rem) calc(0.55rem + env(safe-area-inset-bottom));
        background: rgba(10, 14, 23, 0.96);
        border-top: 1px solid rgba(188, 140, 255, 0.36);
        box-shadow: 0 -10px 30px rgba(0, 0, 0, 0.38);
        backdrop-filter: blur(14px);
        -webkit-backdrop-filter: blur(14px);
    }

    /* Centre the contents on wide displays while the bar spans the viewport. */
    .st-key-lunatick-bottom-nav > div {
        max-width: 1400px;
        margin-left: auto;
        margin-right: auto;
    }

    /* The five primary destinations now fit in one fixed row. Streamlit's
       responsive stacking is overridden only inside this dedicated rail. */
    .st-key-lunatick-bottom-nav [data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        gap: 0.25rem !important;
        overflow: hidden !important;
        overscroll-behavior-x: none;
        padding: 0.05rem 0.1rem 0.15rem;
        touch-action: pan-y;
        width: 100% !important;
    }

    /* Five equal columns eliminate horizontal rail scrolling on every screen. */
    .st-key-lunatick-bottom-nav [data-testid="stColumn"] {
        flex: 1 1 0 !important;
        min-width: 0 !important;
        width: auto !important;
    }

    /* These rules are deliberately scoped to the navigation, leaving every
       other Lunatick button unchanged. */
    .st-key-lunatick-bottom-nav [data-testid="stButton"] > button {
        min-height: 2.7rem;
        padding: 0.35rem 0.35rem;
        border-radius: 0.7rem;
        font-size: 0.7rem;
        line-height: 1.15;
        white-space: nowrap;
    }

    /* Keep the longer Connect label compact on one line without changing
       any other bottom-navigation button. */
    .st-key-lunatick-bottom-nav .st-key-bottom_nav_community button {
        /* Preserve the shared tab typography and height. Only the horizontal
           padding is tightened so “Connect” fits as a complete second line. */
        letter-spacing: -0.01em;
        overflow-wrap: normal;
        padding-left: 0.06rem !important;
        padding-right: 0.06rem !important;
        white-space: pre-line !important;
        word-break: keep-all;
    }

    @media (max-width: 480px) {
        /* Midpoint lift above the hosted platform's bottom-right management
           overlay. The rail buttons and their horizontal layout are unchanged. */
        [data-testid="stMainBlockContainer"] {
            padding-bottom: calc(8.425rem + env(safe-area-inset-bottom));
        }

        .st-key-lunatick-bottom-nav {
            bottom: calc(2.625rem + env(safe-area-inset-bottom));
            padding: 0.4rem 0.35rem calc(0.4rem + env(safe-area-inset-bottom));
        }

        .st-key-lunatick-bottom-nav [data-testid="stColumn"] {
            flex: 1 1 0 !important;
            min-width: 0 !important;
            width: auto !important;
        }

        .st-key-lunatick-bottom-nav [data-testid="stButton"] > button {
            min-height: 2.55rem;
            padding: 0.3rem 0.2rem;
            font-size: 0.63rem;
        }

        .st-key-lunatick-bottom-nav .st-key-bottom_nav_community button {
            padding-left: 0.04rem !important;
            padding-right: 0.04rem !important;
        }
    }

    ::-webkit-scrollbar { width: 6px; }
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

# Logged-in sidebar identity + logout
with st.sidebar:
    st.markdown(f"**@{st.session_state.get('username', '?')}**")
    st.caption(st.session_state.get("display_name", ""))
    if st.button("Log out"):
        auth.logout()
        st.rerun()

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


def render_tones():
    """Render Lunatick's client-side, user-controlled Web Audio tone space."""
    # This local import deliberately leaves the existing top-level imports
    # untouched. The component runs in an isolated browser iframe, so no audio
    # or listening data is sent to the server.
    import streamlit.components.v1 as components

    tone_generator_html = r"""
    <!doctype html>
    <html lang="en">
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <style>
        :root {
          color-scheme: dark;
          --ink: #05070a;
          --panel: #0d111b;
          --panel-raised: #151b2a;
          --line: rgba(188, 140, 255, 0.32);
          --line-soft: rgba(255, 255, 255, 0.10);
          --text: #edf2ff;
          --muted: #99a4bb;
          --violet: #bc8cff;
          --violet-light: #ddc8ff;
          --blue: #58a6ff;
          --mint: #92e4bb;
          --rose: #ff8aa8;
        }

        * { box-sizing: border-box; }

        body {
          background: transparent;
          color: var(--text);
          font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
          margin: 0;
        }

        .tone-space {
          background:
            radial-gradient(circle at 92% 6%, rgba(88, 166, 255, 0.18), transparent 25rem),
            radial-gradient(circle at 8% 94%, rgba(188, 140, 255, 0.16), transparent 20rem),
            linear-gradient(145deg, #10182a 0%, #090d16 58%, #17102a 100%);
          border: 1px solid var(--line);
          border-radius: 1.2rem;
          box-shadow: 0 0 32px rgba(110, 64, 201, 0.18), inset 0 0 28px rgba(0, 0, 0, 0.20);
          overflow: hidden;
          padding: clamp(1rem, 4vw, 1.45rem);
        }

        .eyebrow {
          color: var(--violet);
          font-size: 0.67rem;
          font-weight: 800;
          letter-spacing: 0.18em;
          margin-bottom: 0.35rem;
          text-transform: uppercase;
        }

        h1 {
          font-family: Orbitron, Inter, sans-serif;
          font-size: clamp(1.22rem, 4vw, 1.55rem);
          letter-spacing: 0.07em;
          margin: 0;
          text-transform: uppercase;
        }

        .intro {
          color: var(--muted);
          font-size: 0.88rem;
          line-height: 1.5;
          margin: 0.55rem 0 1.15rem;
        }

        .section-label {
          color: var(--muted);
          display: block;
          font-size: 0.66rem;
          font-weight: 800;
          letter-spacing: 0.10em;
          margin-bottom: 0.48rem;
          text-transform: uppercase;
        }

        .presets {
          display: grid;
          gap: 0.5rem;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          margin-bottom: 1rem;
        }

        button, input, select { font: inherit; }

        .preset,
        .action {
          border: 1px solid var(--line-soft);
          border-radius: 0.75rem;
          color: var(--text);
          cursor: pointer;
          transition: background 140ms ease, border-color 140ms ease, transform 140ms ease;
        }

        .preset {
          background: rgba(255, 255, 255, 0.045);
          min-height: 3.45rem;
          padding: 0.55rem 0.65rem;
          text-align: left;
        }

        .preset:hover,
        .preset:focus-visible {
          border-color: var(--violet);
          outline: none;
          transform: translateY(-1px);
        }

        .preset[aria-pressed="true"] {
          background: rgba(188, 140, 255, 0.17);
          border-color: var(--violet);
        }

        .preset-name {
          display: block;
          font-size: 0.78rem;
          font-weight: 750;
        }

        .preset-frequency {
          color: var(--muted);
          display: block;
          font-size: 0.66rem;
          margin-top: 0.14rem;
        }

        .controls {
          display: grid;
          gap: 0.85rem;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          margin: 0.7rem 0 1rem;
        }

        .control { min-width: 0; }

        select,
        input[type="number"] {
          background: var(--panel-raised);
          border: 1px solid var(--line-soft);
          border-radius: 0.62rem;
          color: var(--text);
          min-height: 2.45rem;
          padding: 0.35rem 0.55rem;
          width: 100%;
        }

        input[type="range"] {
          accent-color: var(--violet);
          cursor: pointer;
          width: 100%;
        }

        .volume-line {
          align-items: center;
          display: flex;
          gap: 0.45rem;
        }

        output {
          color: var(--violet-light);
          font-size: 0.75rem;
          font-variant-numeric: tabular-nums;
          min-width: 2.6rem;
          text-align: right;
        }

        .actions {
          display: grid;
          gap: 0.65rem;
          grid-template-columns: repeat(2, minmax(0, 1fr));
        }

        .action {
          font-size: 0.86rem;
          font-weight: 800;
          min-height: 2.7rem;
          padding: 0.55rem 0.7rem;
        }

        .start {
          background: linear-gradient(135deg, #7841c7, #aa70f0);
          border-color: var(--violet);
        }

        .start:hover,
        .start:focus-visible {
          background: linear-gradient(135deg, #8e5cde, #c18bff);
          outline: none;
        }

        .stop {
          background: rgba(255, 138, 168, 0.08);
          border-color: rgba(255, 138, 168, 0.38);
        }

        .stop:hover:not(:disabled),
        .stop:focus-visible:not(:disabled) {
          background: rgba(255, 138, 168, 0.16);
          outline: none;
        }

        button:disabled {
          cursor: not-allowed;
          opacity: 0.48;
        }

        .status {
          color: var(--muted);
          font-size: 0.78rem;
          line-height: 1.45;
          margin: 0.85rem 0 0;
          min-height: 1.15rem;
        }

        .status[data-state="playing"] { color: var(--mint); }
        .status[data-state="error"] { color: var(--rose); }

        .note {
          color: #72809b;
          font-size: 0.67rem;
          line-height: 1.42;
          margin: 0.45rem 0 0;
        }

        @media (max-width: 360px) {
          .controls { grid-template-columns: 1fr; }
        }
      </style>
    </head>
    <body>
      <main class="tone-space" aria-labelledby="tones-title">
        <div class="eyebrow">Lunatick sound space</div>
        <h1 id="tones-title">Healing tones</h1>
        <p class="intro">Choose a tone, set a gentle listening level, and take a moment for yourself.</p>

        <span class="section-label">Tone presets</span>
        <div class="presets" aria-label="Tone presets">
          <button class="preset" type="button" data-frequency="174" aria-pressed="false">
            <span class="preset-name">Earth</span><span class="preset-frequency">174 Hz</span>
          </button>
          <button class="preset" type="button" data-frequency="285" aria-pressed="false">
            <span class="preset-name">Tide</span><span class="preset-frequency">285 Hz</span>
          </button>
          <button class="preset" type="button" data-frequency="432" aria-pressed="true">
            <span class="preset-name">Moon</span><span class="preset-frequency">432 Hz</span>
          </button>
          <button class="preset" type="button" data-frequency="528" aria-pressed="false">
            <span class="preset-name">Starlight</span><span class="preset-frequency">528 Hz</span>
          </button>
          <button class="preset" type="button" data-frequency="639" aria-pressed="false">
            <span class="preset-name">Heart</span><span class="preset-frequency">639 Hz</span>
          </button>
          <button class="preset" type="button" data-frequency="741" aria-pressed="false">
            <span class="preset-name">Clear</span><span class="preset-frequency">741 Hz</span>
          </button>
        </div>

        <!-- Mode Toggle (Standard / Binaural only) -->
        <div class="mode-toggle" role="group" aria-label="Audio mode">
          <button id="mode-standard" class="active">Standard</button>
          <button id="mode-binaural">Binaural (Headphones)</button>
        </div>

        <div class="controls">
          <div class="control">
            <label class="section-label" for="frequency">Base frequency</label>
            <input id="frequency" type="number" min="100" max="1000" step="1" value="432" inputmode="numeric">
          </div>
          <div class="control" id="beat-control" style="display: none;">
            <label class="section-label" for="beat">Beat frequency (Hz)</label>
            <input id="beat" type="number" min="0" max="20" step="0.01" value="7.83" inputmode="decimal">
          </div>
          <div class="control">
            <label class="section-label" for="waveform">Waveform</label>
            <select id="waveform">
              <option value="sine">Sine — soft</option>
              <option value="triangle">Triangle — warm</option>
              <option value="sawtooth">Sawtooth — bright</option>
            </select>
          </div>
          <div class="control">
            <label class="section-label" for="cycle-mode">Cycle mode</label>
            <select id="cycle-mode">
              <option value="random">Random</option>
              <option value="sweep">Chakra Sweep</option>
            </select>
          </div>
          <div class="control">
            <label class="section-label" for="speed">Cycle speed (seconds)</label>
            <div class="volume-line">
              <input id="speed" type="range" min="2" max="12" step="1" value="5" aria-describedby="speed-value">
              <output id="speed-value" for="speed">5s</output>
            </div>
          </div>
          <div class="control">
            <label class="section-label" for="volume">Listening volume</label>
            <div class="volume-line">
              <input id="volume" type="range" min="0" max="18" value="6" step="1" aria-describedby="volume-value">
              <output id="volume-value" for="volume">6%</output>
            </div>
          </div>
        </div>

        <div class="actions">
          <button id="start" class="action start" type="button">Start tone</button>
          <button id="stop" class="action stop" type="button" disabled>Stop tone</button>
        </div>

        <p id="status" class="status" role="status" aria-live="polite" data-state="idle">Ready — Moon is selected at 432 Hz.</p>
        <p class="note">For personal relaxation only. This feature is not medical treatment or a substitute for professional care.</p>
      </main>

      <script>
        (() => {
          const AudioContextClass = window.AudioContext || window.webkitAudioContext;
          const presetButtons = [...document.querySelectorAll(".preset")];
          const frequencyInput = document.getElementById("frequency");
          const beatInput = document.getElementById("beat");
          const waveform = document.getElementById("waveform");
          const volume = document.getElementById("volume");
          const volumeValue = document.getElementById("volume-value");
          const speedInput = document.getElementById("speed");
          const speedValue = document.getElementById("speed-value");
          const cycleModeSelect = document.getElementById("cycle-mode");
          const startButton = document.getElementById("start");
          const stopButton = document.getElementById("stop");
          const status = document.getElementById("status");
          const modeStandard = document.getElementById("mode-standard");
          const modeBinaural = document.getElementById("mode-binaural");
          const beatControl = document.getElementById("beat-control");

          let audioContext = null;
          let leftOsc = null;
          let rightOsc = null;
          let leftGain = null;
          let rightGain = null;
          let isBinaural = false;
          let isRandom = false; // true if any cyclic mode (random or sweep)
          let beatFrequency = 7.83;
          let selectedFrequency = 432;
          let randomInterval = null;
          let cycleDelay = 5000; // Default 5 seconds
          const glideDuration = 2.5; // Fixed 2.5 second glide
          let sequenceIndex = 0;
          let sequenceDirection = 1; // 1 for ascending, -1 for descending
          const presetFrequencies = [174, 285, 432, 528, 639, 741];

          function setStatus(message, state = "idle") {
            status.textContent = message;
            status.dataset.state = state;
          }

          function selectedPresetName(freq) {
            const button = presetButtons.find(b => Number(b.dataset.frequency) === freq);
            return button ? button.querySelector(".preset-name").textContent : "Custom";
          }

          function currentGain() {
            return Number(volume.value) / 100;
          }

          function setPlayingUI(isPlaying) {
            startButton.disabled = isPlaying;
            stopButton.disabled = !isPlaying;
            presetButtons.forEach(btn => btn.disabled = isPlaying && isRandom);
          }

          function updateVolumeLabel() {
            volumeValue.textContent = `${volume.value}%`;
          }

          function updateSpeedLabel() {
            cycleDelay = Number(speedInput.value) * 1000;
            speedValue.textContent = `${speedInput.value}s`;
            // If cyclic mode is running, reset interval with new delay
            if (isRandom && randomInterval) {
              clearInterval(randomInterval);
              randomInterval = setInterval(() => {
                cycleNext();
              }, cycleDelay);
            }
          }

          function highlightPreset(freq) {
            presetButtons.forEach(btn => {
              const isActive = Number(btn.dataset.frequency) === freq;
              btn.setAttribute("aria-pressed", isActive ? "true" : "false");
            });
          }

          function setFrequency(freq) {
            selectedFrequency = freq;
            highlightPreset(freq);
            const now = audioContext.currentTime;
            if (isBinaural && leftOsc && rightOsc && audioContext) {
              leftOsc.frequency.cancelScheduledValues(now);
              leftOsc.frequency.exponentialRampToValueAtTime(freq, now + glideDuration);
              rightOsc.frequency.cancelScheduledValues(now);
              rightOsc.frequency.exponentialRampToValueAtTime(freq + beatFrequency, now + glideDuration);
            } else if (leftOsc && audioContext) {
              leftOsc.frequency.cancelScheduledValues(now);
              leftOsc.frequency.exponentialRampToValueAtTime(freq, now + glideDuration);
            }
            // Update status
            const modeName = cycleModeSelect.value === 'random' ? 'Random' : 'Chakra Sweep';
            if (isRandom) {
              setStatus(`${modeName}: ${selectedPresetName(freq)} (${freq} Hz)${isBinaural ? ` + ${beatFrequency} Hz beat` : ''}`, "playing");
            } else {
              setStatus(`Playing ${selectedPresetName(freq)} at ${freq} Hz.`, "playing");
            }
          }

          function cycleNext() {
            let nextFreq;
            if (cycleModeSelect.value === 'random') {
              // Random pick
              const randomIndex = Math.floor(Math.random() * presetFrequencies.length);
              nextFreq = presetFrequencies[randomIndex];
            } else {
              // Chakra Sweep: sequential up and down
              nextFreq = presetFrequencies[sequenceIndex];
              sequenceIndex += sequenceDirection;
              if (sequenceIndex >= presetFrequencies.length - 1) {
                sequenceDirection = -1;
              } else if (sequenceIndex <= 0) {
                sequenceDirection = 1;
              }
            }
            setFrequency(nextFreq);
          }

          function stopTone() {
            const now = audioContext ? audioContext.currentTime : 0;
            if (randomInterval) {
              clearInterval(randomInterval);
              randomInterval = null;
            }
            if (leftOsc) {
              leftGain.gain.cancelScheduledValues(now);
              leftGain.gain.setValueAtTime(Math.max(leftGain.gain.value, 0), now);
              leftGain.gain.linearRampToValueAtTime(0, now + 0.10);
              leftOsc.stop(now + 0.11);
              leftOsc = null; leftGain = null;
            }
            if (rightOsc) {
              rightGain.gain.cancelScheduledValues(now);
              rightGain.gain.setValueAtTime(Math.max(rightGain.gain.value, 0), now);
              rightGain.gain.linearRampToValueAtTime(0, now + 0.10);
              rightOsc.stop(now + 0.11);
              rightOsc = null; rightGain = null;
            }
            setPlayingUI(false);
            setStatus("Tone stopped. Ready when you are.");
          }

          async function startTone() {
            if (!AudioContextClass) {
              setStatus("This browser does not support the Web Audio API.", "error");
              return;
            }

            try {
              if (!audioContext || audioContext.state === "closed") {
                audioContext = new AudioContextClass();
              }
              if (audioContext.state === "suspended") {
                await audioContext.resume();
              }

              if (leftOsc || rightOsc) {
                stopTone();
                await new Promise(r => setTimeout(r, 100));
              }

              // Determine starting frequency
              let startFreq = selectedFrequency;
              if (isRandom) {
                // Reset sequence for sweep
                sequenceIndex = 0;
                sequenceDirection = 1;
                if (cycleModeSelect.value === 'random') {
                  const randomIndex = Math.floor(Math.random() * presetFrequencies.length);
                  startFreq = presetFrequencies[randomIndex];
                } else {
                  startFreq = presetFrequencies[0];
                }
                highlightPreset(startFreq);
                // Start the interval
                randomInterval = setInterval(() => {
                  cycleNext();
                }, cycleDelay);
              }

              if (isBinaural) {
                // Left channel
                leftOsc = audioContext.createOscillator();
                leftGain = audioContext.createGain();
                const leftPanner = audioContext.createStereoPanner();
                leftPanner.pan.value = -1;
                leftOsc.type = waveform.value;
                leftOsc.frequency.setValueAtTime(startFreq, audioContext.currentTime);
                leftGain.gain.setValueAtTime(0, audioContext.currentTime);
                leftGain.gain.linearRampToValueAtTime(currentGain(), audioContext.currentTime + 0.12);
                leftOsc.connect(leftGain);
                leftGain.connect(leftPanner);
                leftPanner.connect(audioContext.destination);
                leftOsc.start();

                // Right channel
                const rightFreq = startFreq + beatFrequency;
                rightOsc = audioContext.createOscillator();
                rightGain = audioContext.createGain();
                const rightPanner = audioContext.createStereoPanner();
                rightPanner.pan.value = 1;
                rightOsc.type = waveform.value;
                rightOsc.frequency.setValueAtTime(rightFreq, audioContext.currentTime);
                rightGain.gain.setValueAtTime(0, audioContext.currentTime);
                rightGain.gain.linearRampToValueAtTime(currentGain(), audioContext.currentTime + 0.12);
                rightOsc.connect(rightGain);
                rightGain.connect(rightPanner);
                rightPanner.connect(audioContext.destination);
                rightOsc.start();

                leftOsc.onended = () => { leftOsc = null; };
                rightOsc.onended = () => { rightOsc = null; };

                setPlayingUI(true);
                const modeName = cycleModeSelect.value === 'random' ? 'Random' : 'Chakra Sweep';
                setStatus(`${modeName}: ${selectedPresetName(startFreq)} (${startFreq} Hz + ${beatFrequency} Hz beat)`, "playing");
              } else {
                // Standard mono
                leftOsc = audioContext.createOscillator();
                leftGain = audioContext.createGain();
                leftOsc.type = waveform.value;
                leftOsc.frequency.setValueAtTime(startFreq, audioContext.currentTime);
                leftGain.gain.setValueAtTime(0, audioContext.currentTime);
                leftGain.gain.linearRampToValueAtTime(currentGain(), audioContext.currentTime + 0.12);
                leftOsc.connect(leftGain);
                leftGain.connect(audioContext.destination);
                leftOsc.start();

                leftOsc.onended = () => { leftOsc = null; };

                setPlayingUI(true);
                const modeName = cycleModeSelect.value === 'random' ? 'Random' : 'Chakra Sweep';
                setStatus(`${modeName}: ${selectedPresetName(startFreq)} (${startFreq} Hz)`, "playing");
              }
            } catch (error) {
              console.error("Unable to start tone", error);
              leftOsc = null; rightOsc = null;
              setPlayingUI(false);
              setStatus("The tone could not start. Check browser audio permissions and try again.", "error");
            }
          }

          function updateActiveFrequency() {
            const rawValue = Number(frequencyInput.value);
            selectedFrequency = Math.min(1000, Math.max(100, Number.isFinite(rawValue) ? rawValue : 432));
            frequencyInput.value = selectedFrequency;
            highlightPreset(selectedFrequency);
            if (!isRandom && leftOsc) {
              setFrequency(selectedFrequency);
            } else if (!isRandom) {
              setStatus(`Ready — ${selectedPresetName(selectedFrequency)} is selected at ${selectedFrequency} Hz.`);
            }
          }

          function updateBeat() {
            const rawValue = Number(beatInput.value);
            beatFrequency = Math.min(20, Math.max(0, Number.isFinite(rawValue) ? rawValue : 7.83));
            beatInput.value = beatFrequency;
            if (isBinaural && leftOsc && rightOsc && audioContext) {
              rightOsc.frequency.cancelScheduledValues(audioContext.currentTime);
              rightOsc.frequency.setTargetAtTime(selectedFrequency + beatFrequency, audioContext.currentTime, 0.03);
              setStatus(`Binaural: ${selectedPresetName(selectedFrequency)} (${selectedFrequency}Hz + ${beatFrequency}Hz beat)`, "playing");
            } else {
              setStatus(`Binaural mode ready. Beat set to ${beatFrequency} Hz.`);
            }
          }

          function clearPresetSelection() {
            presetButtons.forEach(button => button.setAttribute("aria-pressed", "false"));
          }

          // Preset Buttons
          presetButtons.forEach(button => {
            button.addEventListener("click", () => {
              if (isRandom) return;
              selectedFrequency = Number(button.dataset.frequency);
              frequencyInput.value = selectedFrequency;
              presetButtons.forEach(item => item.setAttribute("aria-pressed", String(item === button)));
              updateActiveFrequency();
            });
          });

          // Cycle mode selector (activates cyclic mode)
          cycleModeSelect.addEventListener("change", () => {
            isRandom = true;
            if (leftOsc) {
              clearInterval(randomInterval);
              sequenceIndex = 0;
              sequenceDirection = 1;
              if (cycleModeSelect.value === 'random') {
                const randomIndex = Math.floor(Math.random() * presetFrequencies.length);
                setFrequency(presetFrequencies[randomIndex]);
              } else {
                setFrequency(presetFrequencies[0]);
              }
              randomInterval = setInterval(() => {
                cycleNext();
              }, cycleDelay);
            } else {
              setStatus(`Cycle mode: ${cycleModeSelect.value === 'random' ? 'Random' : 'Chakra Sweep'}`);
            }
          });

          // Mode Toggle (Standard/Binaural)
          modeStandard.addEventListener("click", () => {
            isBinaural = false;
            isRandom = false;
            modeStandard.classList.add("active");
            modeBinaural.classList.remove("active");
            beatControl.style.display = "none";
            if (leftOsc || rightOsc) stopTone();
            setPlayingUI(false);
            setStatus("Standard mode. Select a frequency.");
          });

          modeBinaural.addEventListener("click", () => {
            isBinaural = true;
            isRandom = false;
            modeBinaural.classList.add("active");
            modeStandard.classList.remove("active");
            beatControl.style.display = "block";
            if (leftOsc || rightOsc) stopTone();
            setPlayingUI(false);
            setStatus(`Binaural mode. Beat set to ${beatFrequency} Hz.`);
          });

          frequencyInput.addEventListener("change", updateActiveFrequency);
          beatInput.addEventListener("change", updateBeat);

          waveform.addEventListener("change", () => {
            if (leftOsc) leftOsc.type = waveform.value;
            if (rightOsc) rightOsc.type = waveform.value;
          });

          volume.addEventListener("input", () => {
            updateVolumeLabel();
            const currentGainValue = currentGain();
            if (leftGain && audioContext) {
              leftGain.gain.cancelScheduledValues(audioContext.currentTime);
              leftGain.gain.setTargetAtTime(currentGainValue, audioContext.currentTime, 0.025);
            }
            if (rightGain && audioContext) {
              rightGain.gain.cancelScheduledValues(audioContext.currentTime);
              rightGain.gain.setTargetAtTime(currentGainValue, audioContext.currentTime, 0.025);
            }
          });

          speedInput.addEventListener("input", updateSpeedLabel);

          startButton.addEventListener("click", startTone);
          stopButton.addEventListener("click", stopTone);

          window.addEventListener("pagehide", () => {
            if (leftOsc) { try { leftOsc.stop(); } catch (_) {} }
            if (rightOsc) { try { rightOsc.stop(); } catch (_) {} }
            if (audioContext && audioContext.state !== "closed") {
              audioContext.close();
            }
          });
        })();
      </script>
    </body>
    </html>
    """

    components.html(tone_generator_html, height=800, scrolling=False)


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
    if st.button("Opt in to community sharing"):
        st.success("You have opted in to community sharing.")
    if st.button("Opt out of community sharing"):
        st.success("You have opted out of community sharing.")

    st.markdown("---")
    st.markdown("### 💎 Subscription")
    st.selectbox("Your Tier", ["Free", "Community ($5/mo)", "Resonance ($15/mo)"])
    st.info("Upgrade to Community or Resonance for full access to AI insights and community features.")

    st.markdown("---")
    st.markdown("### 🗑️ Danger Zone")
    if st.button("Clear all journal entries", type="secondary"):
        if "journal_entries" in st.session_state:
            st.session_state.journal_entries = []
            st.success("Journal entries cleared.")
    if st.button("Log out of this account", type="secondary"):
        auth.logout()
        st.rerun()


# Sync phase
if "current_phase" not in st.session_state:
    st.session_state.current_phase = get_celestial_data(datetime.now(timezone.utc))["phase_name"]

# Soft seed for talk (safe if already done)
try:
    talk_db.seed_talk_posts()
except Exception:
    pass

# ---------------------------------------------------------------------------
# Main App — Fixed Bottom Navigation
# ---------------------------------------------------------------------------
# Persist the selected destination across Streamlit reruns. Home remains the
# first-run default.
if "nav_page" not in st.session_state:
    st.session_state.nav_page = "Home"

# Existing sessions may still point to a former standalone social tab. Move
# those users directly into the unified Community destination on the next run.
if st.session_state.nav_page in {"Chat", "Boards", "LunaTick Talk"}:
    st.session_state.nav_page = "Community"


def set_nav_page(page_name: str) -> None:
    """Switch destinations before the next normal Streamlit script run."""
    st.session_state.nav_page = page_name


# Render one destination in the normal page body. The navigation itself is
# emitted after this content, but the CSS above fixes it to the viewport.
current_page = st.session_state.nav_page

if current_page == "Home":
    render_home()
elif current_page == "Community":
    community.render_community()
elif current_page == "Cosmic Cards":
    cosmic_cards.render_cosmic_cards_tab()
elif current_page == "Journal":
    journal_ui.render_journal_tab()
elif current_page == "Calendar":
    render_calendar()
elif current_page == "Tones":
    render_tones()
elif current_page == "Settings":
    render_settings()
else:
    # Defensive fallback for an old or unexpected session value.
    st.session_state.nav_page = "Home"
    st.rerun()

# The bottom rail now contains only the five primary destinations. Home and
# Settings remain available through their approved persistent controls, while
# Community contains the former Chat, Boards, and LunaTicK Talk experiences.
NAV_ITEMS = [
    ("Community", "👥", "Connect"),
    ("Journal", "📓", "Journal"),
    ("Calendar", "📅", "Track"),
    ("Cosmic Cards", "🃏", "Deal"),
    ("Tones", "🎵", "Heal"),
]

# `key` gives this container the `.st-key-lunatick-bottom-nav` class. The
# scoped CSS above keeps this one `st.columns` row horizontal on mobile and
# makes it fixed at the bottom of the viewport from launch.
with st.container(key="lunatick-bottom-nav"):
    nav_columns = st.columns(len(NAV_ITEMS), gap="small")

    for column, (page_name, icon, compact_label) in zip(nav_columns, NAV_ITEMS):
        # Community is the only longer label. An explicit line break preserves
        # the shared icon-over-label treatment without breaking “Connect”.
        nav_label = f"{icon}\n{compact_label}" if page_name == "Community" else f"{icon} {compact_label}"
        with column:
            st.button(
                nav_label,
                key=f"bottom_nav_{page_name.lower().replace(' ', '_')}",
                type="primary" if st.session_state.nav_page == page_name else "secondary",
                use_container_width=True,
                help=f"Open {page_name}",
                on_click=set_nav_page,
                args=(page_name,),
            )

# The footer remains in normal document flow. The main-container bottom padding
# added in CSS keeps it fully scrollable above the persistent navigation.
# This separate control is a permanent, lower-left Home shortcut. It uses the
# existing navigation callback but does not add or alter any NAV_ITEMS entry.
home_logo_key = "lunatick-home-logo-active" if current_page == "Home" else "lunatick-home-logo"
with st.container(key=home_logo_key):
    st.button(
        "🌙 LUNATICK",
        key="lunatick_home_logo_button",
        help="Return to Home",
        on_click=set_nav_page,
        args=("Home",),
    )

# Small adjacent Settings shortcut. This is intentionally separate from the
# navigation rail and preserves the existing Settings route unchanged.
settings_gear_key = "lunatick-settings-gear-active" if current_page == "Settings" else "lunatick-settings-gear"
with st.container(key=settings_gear_key):
    st.button(
        "⚙️",
        key="lunatick_settings_gear_button",
        help="Open Settings",
        on_click=set_nav_page,
        args=("Settings",),
    )

st.markdown(
    "<p style='text-align:center; color:#484f58; font-size:0.65rem; "
    "font-family:Orbitron, sans-serif;'>"
    "🌙 LUNATICK — YOUR COSMIC MOON COMPANION"
    "<br><span style='font-size:0.5rem;'>AI + I = All. Always.</span>"
    "</p>",
    unsafe_allow_html=True,
)