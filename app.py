import streamlit as st
import ephem
import math
import requests
from datetime import datetime, timezone, timedelta, date

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
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


init_session_state()

st.set_page_config(page_title="🌙 Lunatick", page_icon="🌙", layout="wide")

st.markdown(
    """<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Inter:wght@300;400;600&display=swap');
.stApp { background-color: #05070a; color: #e6edf3; font-family: 'Inter', sans-serif; }
h1, h2, h3, h4 { font-family: 'Orbitron', sans-serif; text-transform: uppercase; letter-spacing: 1px; }
</style>""",
    unsafe_allow_html=True,
)

journal_ui.init_db()
talk_db.init_db()
cosmic_cards.init_cards_db()
boards.init_boards_db()
chat_room.init_chat_db()
auth.init_auth_db()

if not auth.render_login_page():
    st.stop()

with st.sidebar:
    st.markdown("**@{}**".format(st.session_state.get("username", "?")))
    st.caption(st.session_state.get("display_name", ""))
    if st.button("Log out"):
        auth.logout()
        st.rerun()

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


def get_moon_phase_name(phase_frac):
    phases = [
        (0.00, "New Moon", "🌑"), (0.07, "Waxing Crescent", "🌒"), (0.25, "First Quarter", "🌓"),
        (0.43, "Waxing Gibbous", "🌔"), (0.50, "Full Moon", "🌕"), (0.57, "Waning Gibbous", "🌖"),
        (0.75, "Last Quarter", "🌗"), (0.93, "Waning Crescent", "🌘"), (1.00, "New Moon", "🌑"),
    ]
    for i in range(len(phases) - 1):
        if phases[i][0] <= phase_frac < phases[i + 1][0]:
            return phases[i][1], phases[i][2]
    return "New Moon", "🌑"


def get_celestial_data(date_utc):
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
    moon_lon = math.degrees(float(ephem.Ecliptic(moon).lon)) % 360
    moon_sign, moon_symbol, moon_vibe = get_zodiac_sign(moon_lon)
    sun_lon = math.degrees(float(ephem.Ecliptic(sun).lon)) % 360
    sun_sign, sun_symbol, _ = get_zodiac_sign(sun_lon)
    nfm = ephem.next_full_moon(obs.date)
    nfm_dt = ephem.Date(nfm).datetime().replace(tzinfo=timezone.utc)
    return {
        "moon_sign": moon_sign, "moon_symbol": moon_symbol, "moon_vibe": moon_vibe, "moon_lon": moon_lon,
        "sun_sign": sun_sign, "sun_symbol": sun_symbol,
        "phase_frac": phase_frac, "phase_name": phase_name, "phase_emoji": phase_emoji, "illum": illum,
        "next_full_dt": nfm_dt, "age_days": phase_frac * 29.53,
    }


def parse_birth_day(value):
    if value is None:
        return date(1990, 1, 1)
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except Exception:
        return date(1990, 1, 1)


def full_moons_lived(birth_day):
    birth_day = parse_birth_day(birth_day)
    birth_utc = datetime.combine(birth_day, datetime.min.time()).replace(tzinfo=timezone.utc)
    now_utc = datetime.now(timezone.utc)
    days = (now_utc - birth_utc).days
    if days < 0:
        return 0
    return int(days / 29.53)


@st.cache_data(ttl=3600)
def get_ai_insight(natal, current, aspect):
    api_key = st.secrets.get("DEEPSEEK_API_KEY")
    if not api_key:
        return None
    prompt = (
        "As a cosmic guide, provide a short, poetic, and encouraging astrology insight (max 3 sentences).\n"
        "User Natal: Sun in {}, Moon in {}.\n"
        "Current Sky: Moon in {} ({}).\n"
        "Natal-Current Aspect: {}.\n"
        "Tone: Mystical, empowering, and modern."
    ).format(
        natal["sun_sign"], natal["moon_sign"],
        current["moon_sign"], current["phase_name"], aspect,
    )
    try:
        response = requests.post(
            "https://api.deepseek.com/chat/completions",
            headers={"Authorization": "Bearer {}".format(api_key), "Content-Type": "application/json"},
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
        st.session_state.birth_date = date(1990, 1, 1)

    with st.sidebar:
        st.markdown("### 🧬 Birth chart")
        st.caption("Edit full date · time · place in **Cosmic Cards** or **Settings**.")
        bd_sidebar = st.date_input(
            "Birth date",
            value=parse_birth_day(st.session_state.birth_date),
            min_value=date(1920, 1, 1),
            max_value=date.today(),
            key="home_birth_date",
        )
        if bd_sidebar != parse_birth_day(st.session_state.birth_date):
            st.session_state.birth_date = bd_sidebar
            try:
                cosmic_cards.save_profile(
                    st.session_state.get("user_hash", "anonymous"),
                    st.session_state.get("display_name", "Moon Wanderer"),
                    bd_sidebar.isoformat(),
                )
            except Exception:
                pass
            st.rerun()

        card = cosmic_cards.build_card(st.session_state.get("user_hash", "anonymous"))
        if card and card.get("natal"):
            n = card["natal"]
            line = "{} **{}** · {} **{}**".format(
                n["sun_symbol"], n["sun_sign"], n["moon_symbol"], n["moon_sign"]
            )
            if n.get("has_rising"):
                line += " · ↑ {} **{}**".format(n["rising_symbol"], n["rising_sign"])
            st.markdown(line)
            if card.get("birth_place"):
                st.caption(card["birth_place"])
        st.success("🔒 Private: Insights are only visible to you.")

    # ---- Header / countdown (native Streamlit) ----
    delta = current["next_full_dt"] - now_utc
    d, rem = divmod(int(delta.total_seconds()), 86400)
    h, m_total = divmod(rem, 3600)
    m, _ = divmod(m_total, 60)

    st.title("🌙 LUNATICK")
    st.caption("MOON MONITOR · NEXT FULL MOON")
    c1, c2, c3 = st.columns(3)
    c1.metric("Days", d)
    c2.metric("Hours", h)
    c3.metric("Mins", m)

    # ---- Resolve natal data ----
    full_card = cosmic_cards.build_card(st.session_state.get("user_hash", "anonymous"))
    birth_day = parse_birth_day(st.session_state.birth_date)
    if full_card and full_card.get("birth_date"):
        birth_day = parse_birth_day(full_card["birth_date"])

    rising_sign = rising_symbol = None
    if full_card and full_card.get("natal"):
        natal_data = full_card["natal"]
        natal = {
            "sun_sign": natal_data["sun_sign"],
            "sun_symbol": natal_data["sun_symbol"],
            "moon_sign": natal_data["moon_sign"],
            "moon_symbol": natal_data["moon_symbol"],
            "phase_name": natal_data["phase_name"],
            "phase_emoji": natal_data["phase_emoji"],
            "moon_lon": natal_data["moon_lon"],
        }
        if natal_data.get("has_rising"):
            rising_sign = natal_data.get("rising_sign")
            rising_symbol = natal_data.get("rising_symbol")
    else:
        birth_utc_noon = datetime.combine(birth_day, datetime.min.time()).replace(tzinfo=timezone.utc)
        natal = get_celestial_data(birth_utc_noon)

    total_moons = full_moons_lived(birth_day)

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

    # ---- Cosmic chart (native widgets — never shows as code) ----
    st.subheader("YOUR COSMIC CHART")
    n_cols = 5 if rising_sign else 4
    cols = st.columns(n_cols)
    cols[0].metric("Sun Sign", "{} {}".format(natal["sun_symbol"], natal["sun_sign"]))
    cols[1].metric("Moon Sign", "{} {}".format(natal["moon_symbol"], natal["moon_sign"]))
    idx = 2
    if rising_sign:
        cols[idx].metric("Rising", "{} {}".format(rising_symbol, rising_sign))
        idx += 1
    cols[idx].metric("Lunar Phase", "{} {}".format(natal["phase_emoji"], natal["phase_name"]))
    cols[idx + 1].metric("Full Moons Lived", total_moons)

    st.info("✨ **{}** — {}".format(aspect.upper(), guidance))
    if insight:
        st.success("🔮 {}".format(insight))

    # ---- Current sky stats ----
    st.markdown("---")
    s1, s2, s3 = st.columns(3)
    s1.metric("Phase", "{} {}".format(current["phase_emoji"], current["phase_name"]))
    s2.metric("Glow", "{:.1f}%".format(current["illum"] * 100))
    s3.metric("Age", "{:.1f}d".format(current["age_days"]))

    vcol, ecol = st.columns([1, 1])
    with vcol:
        st.markdown("#### ENERGY")
        st.write("**{} Moon in {}**".format(current["moon_symbol"], current["moon_sign"]))
        st.write(current["moon_vibe"])

    with ecol:
        st.subheader("🔭 2026 Cosmic Calendar")
        for d_str, title, desc in [
            ("March 3", "Total Lunar Eclipse", "Visible across the Americas, Europe, and Africa."),
            ("August 12, 2026", "Total Solar Eclipse", "Major eclipse visible in Europe & Greenland."),
            ("August 28, 2026", "Partial Lunar Eclipse", "Visible from the Pacific region."),
            ("September 26, 2026", "Corn Moon (Supermoon)", "The largest full moon appearance of the year."),
        ]:
            st.markdown("**{}** — {}".format(title, d_str))
            st.caption(desc)

    st.markdown("---")
    st.markdown("### 🧠 Daily Reflection")
    reflection_ui.render_daily_reflection()


def render_calendar():
    st.subheader("📅 Lunar Calendar")
    st.caption("Track moon phases throughout the month.")

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
            "### {}".format(
                datetime(st.session_state.calendar_year, st.session_state.calendar_month, 1).strftime("%B %Y")
            )
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
        header_cols[i].markdown("**{}**".format(day))

    today = datetime.now()
    for week in month_cal:
        day_cols = st.columns(7)
        for i, day in enumerate(week):
            with day_cols[i]:
                if day == 0:
                    st.write("")
                else:
                    date_obj = datetime(st.session_state.calendar_year, st.session_state.calendar_month, day)
                    day_data = get_celestial_data(date_obj.replace(tzinfo=timezone.utc))
                    is_today = (
                        day == today.day
                        and st.session_state.calendar_month == today.month
                        and st.session_state.calendar_year == today.year
                    )
                    label = "**{}** {}".format(day, day_data["phase_emoji"])
                    if is_today:
                        label = "👉 " + label
                    st.markdown(label)
                    st.caption("{:.0f}%".format(day_data["illum"] * 100))


def render_settings():
    st.subheader("⚙️ Settings")
    st.caption("Account + birth chart.")
    st.info("Logged in as **@{}**".format(st.session_state.get("username", "?")))

    st.markdown("### 🧬 Birth chart data")

    form_fn = getattr(cosmic_cards, "render_profile_form", None)
    used_full = False
    if callable(form_fn):
        try:
            form_fn(st.session_state.get("user_hash", "anonymous"), key_prefix="settings")
            used_full = True
        except Exception as e:
            st.warning("Full profile form unavailable ({}); using simple form.".format(e))

    if not used_full:
        name = st.text_input(
            "Display name",
            value=st.session_state.get("display_name", "Moon Wanderer"),
            key="settings_simple_name",
        )
        bd = st.date_input(
            "Birth date",
            value=parse_birth_day(st.session_state.get("birth_date")),
            min_value=date(1920, 1, 1),
            max_value=date.today(),
            key="settings_simple_bd",
        )
        if st.button("💾 Save Profile", type="primary", key="settings_simple_save"):
            st.session_state.display_name = name.strip() or "Moon Wanderer"
            st.session_state.birth_date = bd
            try:
                cosmic_cards.save_profile(
                    st.session_state.get("user_hash", "anonymous"),
                    st.session_state.display_name,
                    bd.isoformat(),
                )
            except Exception:
                pass
            try:
                if st.session_state.get("username"):
                    auth.update_user_profile(
                        st.session_state.username,
                        st.session_state.display_name,
                        bd.isoformat(),
                    )
            except Exception:
                pass
            st.success("Profile saved.")
            st.rerun()

    card = cosmic_cards.build_card(st.session_state.get("user_hash", "anonymous"))
    if card and card.get("natal"):
        n = card["natal"]
        st.markdown(
            "**Card preview:** {} Sun {} · {} Moon {} · {} {}".format(
                n["sun_symbol"], n["sun_sign"],
                n["moon_symbol"], n["moon_sign"],
                n["phase_emoji"], n["phase_name"],
            )
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


if "current_phase" not in st.session_state:
    st.session_state.current_phase = get_celestial_data(datetime.now(timezone.utc))["phase_name"]

try:
    talk_db.seed_talk_posts()
except Exception:
    pass

tabs = st.tabs([
    "🌕 Home",
    "💬 Chat",
    "📋 Boards",
    "🃏 Cosmic Cards",
    "💬 LunaTick Talk",
    "📓 Journal",
    "📅 Calendar",
    "⚙️ Settings",
])

with tabs[0]:
    render_home()
with tabs[1]:
    chat_room.render_chat_tab()
with tabs[2]:
    boards.render_boards_tab()
with tabs[3]:
    cosmic_cards.render_cosmic_cards_tab()
with tabs[4]:
    talk_ui.render_talk_tab()
with tabs[5]:
    journal_ui.render_journal_tab()
with tabs[6]:
    render_calendar()
with tabs[7]:
    render_settings()

st.markdown("---")
st.caption("🌙 LUNATICK — YOUR COSMIC MOON COMPANION")
