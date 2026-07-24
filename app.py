import streamlit as st
import datetime
import random
import hashlib
import math
from dataclasses import dataclass
from typing import List, Optional
import json

try:
    import ephem
    HAS_EPHEM = True
except ImportError:
    HAS_EPHEM = False

st.set_page_config(
    page_title="LunaTick",
    page_icon="🌙",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=Inter:wght@300;400;500;600&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    background-color: #0a0a0f;
    color: #e8e6f0;
}
.stApp {
    background: linear-gradient(180deg, #0a0a0f 0%, #0f0f1a 50%, #0a0a0f 100%);
}
h1, h2, h3 {
    font-family: 'Space Grotesk', sans-serif !important;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
.stButton>button {
    background: linear-gradient(135deg, #7c3aed, #5b21b6);
    color: #ffffff;
    border: none;
    border-radius: 16px;
    padding: 12px 28px;
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 600;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    transition: all 0.3s ease;
    width: 100%;
}
.stButton>button:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 30px rgba(124, 58, 237, 0.4);
}
.stButton>button[kind="secondary"] {
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.1);
}
.stTextInput>div>div>input, .stTextArea>div>div>textarea,
.stDateInput>div>div>input, .stTimeInput>div>div>input {
    background: rgba(255,255,255,0.03) !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    border-radius: 12px !important;
    color: #e8e6f0 !important;
    font-family: 'Inter', sans-serif !important;
}
.stTextInput>div>div>input:focus, .stTextArea>div>div>textarea:focus {
    border-color: #7c3aed !important;
    box-shadow: 0 0 0 2px rgba(124, 58, 237, 0.2) !important;
}
.cosmic-card {
    background: rgba(255,255,255,0.02);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 20px;
    padding: 24px;
    margin-bottom: 16px;
    backdrop-filter: blur(10px);
}
.cosmic-card:hover {
    border-color: rgba(124, 58, 237, 0.3);
}
.pulse-card {
    background: linear-gradient(135deg, rgba(124,58,237,0.15), rgba(91,33,182,0.1));
    border: 1px solid rgba(124,58,237,0.25);
    border-radius: 20px;
    padding: 24px;
    margin-bottom: 16px;
}
.phase-pill {
    display: inline-block;
    background: rgba(124,58,237,0.15);
    color: #a78bfa;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 500;
    letter-spacing: 0.05em;
    margin-right: 6px;
}
.sign-pill {
    display: inline-block;
    background: rgba(255,255,255,0.06);
    color: #c4b5fd;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 500;
    margin-right: 6px;
}
.countdown-box {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 16px;
    padding: 20px;
    text-align: center;
}
.countdown-number {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 2.5rem;
    font-weight: 700;
    color: #a78bfa;
    line-height: 1;
}
.countdown-label {
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.15em;
    color: #6b7280;
    margin-top: 8px;
}
.section-label {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.2em;
    color: #6b7280;
    margin-bottom: 4px;
}
.section-title {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.8rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #f3f4f6;
    margin-bottom: 8px;
}
.section-subtitle {
    font-style: italic;
    color: #9ca3af;
    font-size: 0.95rem;
    margin-bottom: 24px;
}
.fixed-bottom-nav {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    background: rgba(10, 10, 15, 0.95);
    backdrop-filter: blur(10px);
    border-top: 1px solid rgba(255, 255, 255, 0.06);
    padding: 10px 12px 14px 12px;
    z-index: 9999;
    display: flex;
    justify-content: space-around;
    align-items: center;
}
.fixed-bottom-nav button {
    background: transparent !important;
    border: none !important;
    color: #6b7280 !important;
    font-family: 'Inter', sans-serif;
    font-size: 0.7rem;
    text-align: center;
    padding: 4px 8px;
    border-radius: 8px;
    transition: all 0.2s ease;
    flex: 1;
}
.fixed-bottom-nav button:hover {
    color: #a78bfa !important;
    background: rgba(124, 58, 237, 0.1) !important;
}
.fixed-bottom-nav button.active {
    color: #a78bfa !important;
    background: rgba(124, 58, 237, 0.15) !important;
}
.main-content {
    padding-bottom: 80px;
}
.c3-badge {
    text-align: center;
    padding: 16px;
    color: #4b5563;
    font-size: 0.7rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
}
.post-card {
    background: rgba(255,255,255,0.02);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 16px;
    padding: 20px;
    margin-bottom: 12px;
}
.post-header {
    display: flex;
    align-items: center;
    margin-bottom: 12px;
}
.post-avatar {
    width: 36px;
    height: 36px;
    border-radius: 50%;
    background: linear-gradient(135deg, #7c3aed, #4c1d95);
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    font-size: 0.8rem;
    color: white;
    margin-right: 12px;
}
.post-meta {
    color: #9ca3af;
    font-size: 0.8rem;
}
.post-content {
    color: #e8e6f0;
    line-height: 1.6;
    margin-bottom: 12px;
}
.board-card {
    background: rgba(255,255,255,0.02);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 20px;
    padding: 24px;
    margin-bottom: 16px;
    cursor: pointer;
    transition: all 0.3s ease;
}
.board-card:hover {
    border-color: rgba(124,58,237,0.3);
    transform: translateY(-2px);
}
.board-icon {
    font-size: 2rem;
    margin-bottom: 12px;
}
.board-title {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.3rem;
    font-weight: 600;
    color: #f3f4f6;
    margin-bottom: 8px;
}
.board-desc {
    color: #9ca3af;
    font-size: 0.9rem;
    margin-bottom: 12px;
}
.board-count {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.15em;
    color: #6b7280;
}
.chart-card {
    background: linear-gradient(135deg, rgba(124,58,237,0.1), rgba(91,33,182,0.05));
    border: 1px solid rgba(124,58,237,0.2);
    border-radius: 20px;
    padding: 20px;
    text-align: center;
    transition: all 0.3s ease;
}
.chart-card:hover {
    border-color: rgba(124,58,237,0.4);
    box-shadow: 0 8px 30px rgba(124,58,237,0.15);
}
.chart-avatar {
    width: 60px;
    height: 60px;
    border-radius: 50%;
    background: linear-gradient(135deg, #7c3aed, #4c1d95);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.5rem;
    font-weight: 700;
    color: white;
    margin: 0 auto 12px;
}
.prompt-card {
    background: rgba(255,255,255,0.02);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 16px;
    padding: 20px;
    margin-bottom: 12px;
    cursor: pointer;
    transition: all 0.3s ease;
}
.prompt-card:hover {
    border-color: rgba(124,58,237,0.3);
}
.prompt-card.selected {
    border-color: #7c3aed;
    background: rgba(124,58,237,0.08);
}
.main .block-container {
    padding-bottom: 100px !important;
}
.stTabs [data-baseweb="tab-list"] {
    gap: 0;
    background: rgba(255,255,255,0.02);
    border-radius: 16px;
    padding: 4px;
}
.stTabs [data-baseweb="tab"] {
    color: #6b7280;
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.8rem;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    border-radius: 12px;
    padding: 10px 20px;
}
.stTabs [aria-selected="true"] {
    background: rgba(124,58,237,0.2) !important;
    color: #a78bfa !important;
}
.streamlit-expanderHeader {
    background: rgba(255,255,255,0.02) !important;
    border: 1px solid rgba(255,255,255,0.06) !important;
    border-radius: 12px !important;
    color: #e8e6f0 !important;
}
.stSelectbox>div>div, .stMultiSelect>div>div {
    background: rgba(255,255,255,0.03) !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    border-radius: 12px !important;
    color: #e8e6f0 !important;
}
hr {
    border-color: rgba(255,255,255,0.06) !important;
    margin: 24px 0 !important;
}
</style>
""", unsafe_allow_html=True)

SIGNS = ["Aries","Taurus","Gemini","Cancer","Leo","Virgo",
         "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"]
SIGN_EMOJIS = {
    "Aries":"♈","Taurus":"♉","Gemini":"♊","Cancer":"♋",
    "Leo":"♌","Virgo":"♍","Libra":"♎","Scorpio":"♏",
    "Sagittarius":"♐","Capricorn":"♑","Aquarius":"♒","Pisces":"♓"
}
BOARDS = [
    {"id":"general","icon":"🌙","name":"General","desc":"Open discussion for all moon bros & sis.","posts":1},
    {"id":"rituals","icon":"🕯️","name":"Full Moon Rituals","desc":"Share & discover lunar rituals and practices.","posts":2},
    {"id":"astrology","icon":"♒","name":"Astrology","desc":"Birth charts, transits, retrogrades — all welcome.","posts":0},
    {"id":"sightings","icon":"🔭","name":"Sky Sightings","desc":"Photos of the moon, eclipses, planets & beyond.","posts":0},
    {"id":"memes","icon":"😹","name":"Cosmic Memes","desc":"Lunar humor & cosmic chaos.","posts":0},
    {"id":"intentions","icon":"✨","name":"Intentions","desc":"Set, share, and reflect on your lunar intentions.","posts":0},
]
PHASE_NAMES = ["New Moon","Waxing Crescent","First Quarter","Waxing Gibbous",
               "Full Moon","Waning Gibbous","Last Quarter","Waning Crescent"]

def get_moon_data(d: datetime.date = None):
    if d is None:
        d = datetime.date.today()
    dt = datetime.datetime.combine(d, datetime.time(12,0))
    if HAS_EPHEM:
        o = ephem.Observer()
        o.date = dt
        m = ephem.Moon(o)
        phase = m.phase
        age = (m.phase / 100.0) * 29.53
        nm = ephem.next_full_moon(o.date)
        next_full = nm.datetime().replace(tzinfo=None)
        lon = math.degrees(m.hlon)
        sign_idx = int((lon % 360) / 30)
        moon_sign = SIGNS[sign_idx]
    else:
        ref = datetime.date(2000,1,6)
        days_since = (d - ref).days
        synodic = 29.53059
        age = days_since % synodic
        phase = (age / synodic) * 100
        current_age = age
        days_to_full = (14.765 - current_age) % synodic
        if days_to_full < 0.5:
            days_to_full += synodic
        next_full = dt + datetime.timedelta(days=days_to_full)
        moon_sign = SIGNS[int((days_since * 0.9856) % 12)]
    phase_idx = min(7, int((age / 29.53) * 8))
    phase_name = PHASE_NAMES[phase_idx]
    return {
        "phase_name": phase_name,
        "illumination": round(phase, 1),
        "age_days": round(age, 1),
        "next_full_moon": next_full,
        "moon_sign": moon_sign,
        "full_moons_lived": _full_moons_lived(d)
    }

def _full_moons_lived(birth_date: datetime.date) -> int:
    ref = datetime.date(2000,1,6)
    if birth_date < ref:
        days = (ref - birth_date).days
        return int(days / 29.53)
    else:
        days = (datetime.date.today() - birth_date).days
        return int(days / 29.53)

def get_countdown(target: datetime.datetime) -> dict:
    now = datetime.datetime.now()
    diff = target - now
    if diff.total_seconds() < 0:
        return {"days":0,"hours":0,"mins":0}
    days = diff.days
    hours, rem = divmod(diff.seconds, 3600)
    mins, _ = divmod(rem, 60)
    return {"days":days,"hours":hours,"mins":mins}

def get_sun_sign(dob: datetime.date) -> str:
    d, m = dob.day, dob.month
    if (m==3 and d>=21) or (m==4 and d<=19): return "Aries"
    if (m==4 and d>=20) or (m==5 and d<=20): return "Taurus"
    if (m==5 and d>=21) or (m==6 and d<=20): return "Gemini"
    if (m==6 and d>=21) or (m==7 and d<=22): return "Cancer"
    if (m==7 and d>=23) or (m==8 and d<=22): return "Leo"
    if (m==8 and d>=23) or (m==9 and d<=22): return "Virgo"
    if (m==9 and d>=23) or (m==10 and d<=22): return "Libra"
    if (m==10 and d>=23) or (m==11 and d<=21): return "Scorpio"
    if (m==11 and d>=22) or (m==12 and d<=21): return "Sagittarius"
    if (m==12 and d>=22) or (m==1 and d<=19): return "Capricorn"
    if (m==1 and d>=20) or (m==2 and d<=18): return "Aquarius"
    return "Pisces"

def get_moon_sign_from_dob(dob: datetime.date) -> str:
    seed = int(hashlib.md5(f"moon_{dob.isoformat()}".encode()).hexdigest(), 16)
    return SIGNS[seed % 12]

def get_cycle_forecast(phase_name: str) -> str:
    forecasts = {
        "New Moon": "A fresh beginning. Plant seeds, set intentions, embrace the blank slate.",
        "Waxing Crescent": "Nurture what you've planted. Take the first steps toward your goals.",
        "First Quarter": "Decision time. Push through resistance — the half-light reveals your path.",
        "Waxing Gibbous": "Refine and adjust. You're close to the peak — polish your work.",
        "Full Moon": "Illumination and release. What was hidden comes to light. Celebrate, then let go.",
        "Waning Gibbous": "Gratitude and sharing. Spread the wisdom you've gathered under the full light.",
        "Last Quarter": "Forgiveness and surrender. Cut what no longer serves. Prepare for rest.",
        "Waning Crescent": "Rest and reflect. Dream deep. The cycle renews soon.",
    }
    return forecasts.get(phase_name, "Trust the current phase.")

def get_daily_prompt(phase_name: str) -> str:
    prompts = {
        "New Moon": "What seed are you planting under this dark moon?",
        "Waxing Crescent": "What small step can you take today toward your intention?",
        "First Quarter": "Where are you meeting resistance, and what does it teach you?",
        "Waxing Gibbous": "What needs refinement before you reach the peak?",
        "Full Moon": "What truth is being illuminated for you right now?",
        "Waning Gibbous": "What wisdom from this cycle are you ready to share?",
        "Last Quarter": "What are you releasing with gratitude?",
        "Waning Crescent": "What is your inner voice whispering as the cycle closes?",
    }
    return prompts.get(phase_name, "What does the moon reflect in you tonight?")

@dataclass
class UserProfile:
    display_name: str
    birth_date: datetime.date
    birth_time: Optional[datetime.time]
    birth_location: str
    sun_sign: str
    moon_sign: str
    handle: str
    privacy_opt_in: bool = False
    subscription_tier: str = "Free"

@dataclass
class Post:
    id: str
    author: str
    author_handle: str
    title: str
    content: str
    board_id: str
    phase_tag: str
    timestamp: str
    likes: int = 0
    broken_hearts: int = 0

@dataclass
class JournalEntry:
    id: str
    prompt_type: str
    prompt_text: str
    content: str
    phase: str
    timestamp: str

@dataclass
class CosmicCard:
    handle: str
    display_name: str
    sun_sign: str
    moon_sign: str
    birth_phase: str
    full_moons: int
    collected: bool = False

def init_state():
    defaults = {
        "onboarded": False,
        "current_view": "home",
        "current_tab": "timeline",
        "profile": None,
        "posts": _seed_posts(),
        "journal_entries": [],
        "collected_cards": [],
        "friends": [],
        "liked_posts": set(),
        "broken_posts": set(),
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

def _seed_posts() -> List[Post]:
    return [
        Post("p1","luna_admin","@luna_admin","luna_admin's Cosmic Card",
             "♑ Capricorn · ♍ Virgo · Born under Waning Gibbous","general",
             "Waning Gibbous","2026-07-23 20:37",0,0),
        Post("p2","Unifinality","@Unifinality","Full Moon Reflections",
             "Anyone else feeling extra emotional tonight? I've been crying at everything. The moon is so bright.","general",
             "Waxing Gibbous","2026-07-23 18:15",0,0),
        Post("p3","TEST_7dc90ead","@TEST_7dc90ead","Ritual Setup",
             "My Wolf Moon ritual setup is ready. Candles, crystals, and a lot of intention.","rituals",
             "Full Moon","2026-07-22 21:00",0,0),
    ]

init_state()

def render_onboarding():
    st.markdown("""
    <div style="text-align:center; padding: 40px 0 20px;">
        <div style="font-size: 4rem; margin-bottom: 8px;">🌙</div>
        <h1 style="font-size: 2.5rem; margin-bottom: 8px;">LUNATICK</h1>
        <p style="color: #9ca3af; font-style: italic;">Gather under the same moon.</p>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("<div class='section-label'>Step 1 of 1</div>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>Enter Your Birth Data</div>", unsafe_allow_html=True)
    st.markdown("<div class='section-subtitle'>We use this to generate your Cosmic Chart. Nothing leaves your orbit without consent.</div>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        dob = st.date_input("Birth Date", value=datetime.date(1990,1,15),
                           min_value=datetime.date(1900,1,1),
                           max_value=datetime.date.today(), key="onb_dob")
    with col2:
        tob = st.time_input("Birth Time (optional)", value=None, key="onb_tob")
    location = st.text_input("Birth Location (city or coordinates)", 
                            placeholder="e.g., Brooklyn, NY",
                            key="onb_loc")
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("✨ Generate My Cosmic Chart", use_container_width=True):
        sun = get_sun_sign(dob)
        moon = get_moon_sign_from_dob(dob)
        handle = f"TEST_{hashlib.md5(str(random.random()).encode()).hexdigest()[:8]}"
        st.session_state.profile = UserProfile(
            display_name=handle,
            birth_date=dob,
            birth_time=tob,
            birth_location=location or "Unknown",
            sun_sign=sun,
            moon_sign=moon,
            handle=handle,
            privacy_opt_in=False,
            subscription_tier="Free"
        )
        st.session_state.onboarded = True
        st.rerun()

def render_home():
    moon = get_moon_data()
    countdown = get_countdown(moon["next_full_moon"])
    st.markdown("""
    <div style="text-align:center; padding: 20px 0 10px;">
        <div style="font-size: 3rem;">🌙</div>
        <h1 style="font-size: 2.2rem; margin: 4px 0; background: linear-gradient(135deg, #a78bfa, #7c3aed); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">LUNATICK</h1>
        <p style="color: #6b7280; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.3em;">Moon Monitor</p>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("<div class='section-label' style='text-align:center;'>Next Full Moon</div>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"""
        <div class="countdown-box">
            <div class="countdown-number">{countdown['days']}</div>
            <div class="countdown-label">Days</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="countdown-box">
            <div class="countdown-number">{countdown['hours']}</div>
            <div class="countdown-label">Hours</div>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class="countdown-box">
            <div class="countdown-number">{countdown['mins']}</div>
            <div class="countdown-label">Mins</div>
        </div>
        """, unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    profile = st.session_state.profile
    full_moons = moon["full_moons_lived"] if profile else 0
    if profile:
        full_moons = _full_moons_lived(profile.birth_date)
    st.markdown("""
    <div class="cosmic-card">
        <div style="text-align:center; margin-bottom: 16px;">
            <span style="color: #7c3aed; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.2em;">Your Cosmic Chart</span>
        </div>
        <div style="display: flex; justify-content: space-around; text-align: center; flex-wrap: wrap; gap: 16px;">
            <div>
                <div style="font-size: 0.65rem; text-transform: uppercase; letter-spacing: 0.15em; color: #6b7280; margin-bottom: 8px;">Sun Sign</div>
                <div style="font-size: 2rem; margin-bottom: 4px;">{}</div>
                <div style="font-family: 'Space Grotesk'; font-weight: 600; font-size: 1.1rem;">{}</div>
            </div>
            <div>
                <div style="font-size: 0.65rem; text-transform: uppercase; letter-spacing: 0.15em; color: #6b7280; margin-bottom: 8px;">Moon Sign</div>
                <div style="font-size: 2rem; margin-bottom: 4px;">{}</div>
                <div style="font-family: 'Space Grotesk'; font-weight: 600; font-size: 1.1rem;">{}</div>
            </div>
            <div>
                <div style="font-size: 0.65rem; text-transform: uppercase; letter-spacing: 0.15em; color: #6b7280; margin-bottom: 8px;">Lunar Phase</div>
                <div style="font-size: 2rem; margin-bottom: 4px;">🌙</div>
                <div style="font-family: 'Space Grotesk'; font-weight: 600; font-size: 1.1rem;">{}</div>
            </div>
            <div>
                <div style="font-size: 0.65rem; text-transform: uppercase; letter-spacing: 0.15em; color: #6b7280; margin-bottom: 8px;">Full Moons</div>
                <div style="font-family: 'Space Grotesk'; font-weight: 700; font-size: 2rem; color: #a78bfa;">{}</div>
                <div style="font-size: 0.75rem; color: #6b7280;">LIVED</div>
            </div>
        </div>
    </div>
    """.format(
        SIGN_EMOJIS.get(profile.sun_sign, "☉") if profile else "☉",
        profile.sun_sign if profile else "—",
        SIGN_EMOJIS.get(profile.moon_sign, "☽") if profile else "☽",
        profile.moon_sign if profile else "—",
        moon["phase_name"],
        full_moons
    ), unsafe_allow_html=True)
    st.markdown("""
    <div style="display: flex; justify-content: space-around; margin: 16px 0;">
        <div style="text-align: center;">
            <div style="font-size: 0.65rem; text-transform: uppercase; letter-spacing: 0.15em; color: #6b7280;">Phase</div>
            <div style="font-family: 'Space Grotesk'; font-weight: 600; color: #a78bfa;">{}</div>
        </div>
        <div style="text-align: center;">
            <div style="font-size: 0.65rem; text-transform: uppercase; letter-spacing: 0.15em; color: #6b7280;">Glow</div>
            <div style="font-family: 'Space Grotesk'; font-weight: 600; color: #a78bfa;">{}%</div>
        </div>
        <div style="text-align: center;">
            <div style="font-size: 0.65rem; text-transform: uppercase; letter-spacing: 0.15em; color: #6b7280;">Age</div>
            <div style="font-family: 'Space Grotesk'; font-weight: 600; color: #a78bfa;">{}d</div>
        </div>
    </div>
    """.format(moon["phase_name"], moon["illumination"], moon["age_days"]), unsafe_allow_html=True)
    forecast = get_cycle_forecast(moon["phase_name"])
    st.markdown(f"""
    <div class="pulse-card">
        <div style="display: flex; align-items: center; margin-bottom: 12px;">
            <span style="font-size: 1.2rem; margin-right: 8px;">✨</span>
            <span style="font-family: 'Space Grotesk'; font-weight: 600; color: #a78bfa; text-transform: uppercase; letter-spacing: 0.1em;">Cycle Forecast</span>
        </div>
        <p style="color: #e8e6f0; line-height: 1.6; margin: 0;">{forecast}</p>
    </div>
    """, unsafe_allow_html=True)
    prompt = get_daily_prompt(moon["phase_name"])
    st.markdown(f"""
    <div class="cosmic-card">
        <div style="font-size: 0.65rem; text-transform: uppercase; letter-spacing: 0.2em; color: #6b7280; margin-bottom: 8px;">Daily Reflection</div>
        <p style="color: #e8e6f0; font-style: italic; line-height: 1.6; margin: 0;">{prompt}</p>
    </div>
    """, unsafe_allow_html=True)

def render_community():
    moon = get_moon_data()
    st.markdown("<div class='section-label'>LunaTick Talk</div>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>The Cosmic Timeline</div>", unsafe_allow_html=True)
    st.markdown("<div class='section-subtitle'>Share your reflections. Read what others are feeling. You are not alone under the moon.</div>", unsafe_allow_html=True)
    st.markdown(f"""
    <div class="pulse-card">
        <div style="display: flex; align-items: center; margin-bottom: 12px;">
            <span style="font-size: 1.2rem; margin-right: 8px;">🌕</span>
            <span style="font-family: 'Space Grotesk'; font-weight: 600; color: #a78bfa; text-transform: uppercase; letter-spacing: 0.1em;">LunaTick Pulse</span>
        </div>
        <p style="color: #e8e6f0; line-height: 1.6; margin: 0;">
            Tonight's {moon['phase_name']} calls for {get_cycle_forecast(moon['phase_name']).split('.')[0].lower()}. 
            The community is reflecting under the same light. You are not alone.
        </p>
    </div>
    """, unsafe_allow_html=True)
    sub = st.tabs(["💬 Timeline", "🌐 Boards", "🃏 Cards", "👥 Kindred"])
    with sub[0]:
        render_timeline()
    with sub[1]:
        render_boards()
    with sub[2]:
        render_cards()
    with sub[3]:
        render_kindred()

def render_timeline():
    with st.expander("🌙 Share something with the community"):
        name = st.text_input("Your display name", value=st.session_state.profile.display_name if st.session_state.profile else "", key="post_name")
        title = st.text_input("Title (e.g., 'My Wolf Moon ritual setup')", key="post_title")
        body = st.text_area("What's on your mind under tonight's moon?", key="post_body")
        phase = st.selectbox("Phase tag", PHASE_NAMES, key="post_phase")
        board = st.selectbox("Board", [b["name"] for b in BOARDS], key="post_board")
        if st.button("🌙 Cast Into the Void", use_container_width=True):
            if body.strip():
                bid = [b["id"] for b in BOARDS if b["name"]==board][0]
                new_post = Post(
                    id=f"p{len(st.session_state.posts)+1}",
                    author=name or "Anonymous",
                    author_handle=f"@{name or 'anon'}",
                    title=title or "Untitled Transmission",
                    content=body,
                    board_id=bid,
                    phase_tag=phase,
                    timestamp=datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                    likes=0, broken_hearts=0
                )
                st.session_state.posts.insert(0, new_post)
                st.success("✨ Cast into the void.")
                st.rerun()
    filter_phase = st.selectbox("Filter by Phase", ["All Phases"] + PHASE_NAMES, key="filter_phase")
    posts = st.session_state.posts
    if filter_phase != "All Phases":
        posts = [p for p in posts if p.phase_tag == filter_phase]
    for post in posts:
        st.markdown(f"""
        <div class="post-card">
            <div class="post-header">
                <div class="post-avatar">{post.author[:2].upper()}</div>
                <div>
                    <div style="font-weight: 600; color: #f3f4f6;">{post.author}</div>
                    <div class="post-meta">{post.timestamp} · #{post.board_id.upper()}</div>
                </div>
            </div>
            <div style="font-family: 'Space Grotesk'; font-weight: 600; font-size: 1.1rem; margin-bottom: 8px;">{post.title}</div>
            <div class="post-content">{post.content}</div>
            <div>
                <span class="phase-pill">{post.phase_tag}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        c1, c2, c3 = st.columns([1,1,6])
        with c1:
            if st.button(f"❤️ {post.likes}", key=f"like_{post.id}"):
                if post.id not in st.session_state.liked_posts:
                    post.likes += 1
                    st.session_state.liked_posts.add(post.id)
                    st.rerun()
        with c2:
            if st.button(f"💔 {post.broken_hearts}", key=f"break_{post.id}"):
                if post.id not in st.session_state.broken_posts:
                    post.broken_hearts += 1
                    st.session_state.broken_posts.add(post.id)
                    st.rerun()

def render_boards():
    st.markdown("<div class='section-label'>Message Boards</div>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>Categorized Constellations</div>", unsafe_allow_html=True)
    st.markdown("<div class='section-subtitle'>Pick a constellation. Drop your transmission.</div>", unsafe_allow_html=True)
    for board in BOARDS:
        st.markdown(f"""
        <div class="board-card">
            <div class="board-icon">{board['icon']}</div>
            <div class="board-title">{board['name']}</div>
            <div class="board-desc">{board['desc']}</div>
            <div class="board-count">{board['posts']} Posts</div>
        </div>
        """, unsafe_allow_html=True)

def render_cards():
    st.markdown("<div class='section-label'>Cosmic Collection</div>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>Birth Chart Cards</div>", unsafe_allow_html=True)
    st.markdown("<div class='section-subtitle'>Request, exchange, and collect. Each card is a soul's cosmic signature.</div>", unsafe_allow_html=True)
    demo_cards = [
        CosmicCard("@TEST_7dc90ead","TEST_7dc90ead","Capricorn","Virgo","Waning Gibbous",365,False),
        CosmicCard("@luna_admin","luna_admin","Capricorn","Virgo","Waning Gibbous",450,True),
        CosmicCard("@Stardust_9e2b","Stardust_9e2b","Aquarius","Pisces","New Moon",289,False),
    ]
    cols = st.columns(3)
    for i, card in enumerate(demo_cards):
        with cols[i]:
            st.markdown(f"""
            <div class="chart-card">
                <div class="chart-avatar">{card.display_name[:2].upper()}</div>
                <div style="font-family: 'Space Grotesk'; font-weight: 600; color: #f3f4f6; margin-bottom: 4px;">{card.display_name}</div>
                <div style="font-size: 0.8rem; color: #9ca3af; margin-bottom: 12px;">{card.handle}</div>
                <div style="display: flex; justify-content: center; gap: 12px; margin-bottom: 12px;">
                    <div>
                        <div style="font-size: 1.5rem;">{SIGN_EMOJIS[card.sun_sign]}</div>
                        <div style="font-size: 0.7rem; color: #6b7280;">{card.sun_sign}</div>
                    </div>
                    <div>
                        <div style="font-size: 1.5rem;">{SIGN_EMOJIS[card.moon_sign]}</div>
                        <div style="font-size: 0.7rem; color: #6b7280;">{card.moon_sign}</div>
                    </div>
                </div>
                <div style="font-size: 0.75rem; color: #6b7280; margin-bottom: 4px;">☉ TWIN SUN</div>
                <div style="font-size: 0.7rem; color: #4b5563;">{card.full_moons} Full Moons</div>
            </div>
            """, unsafe_allow_html=True)
            if card.collected:
                st.button("✨ In Collection", disabled=True, key=f"col_{i}")
            else:
                if st.button("🤝 Request Exchange", key=f"req_{i}"):
                    st.session_state.friends.append(card.handle)
                    st.success(f"✨ Friend request sent to {card.display_name}!")
                    st.rerun()

def render_kindred():
    st.markdown("<div class='section-label'>Cosmic Kindred</div>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>Your Connections</div>", unsafe_allow_html=True)
    st.markdown("<div class='section-subtitle'>Souls who have exchanged cards with you.</div>", unsafe_allow_html=True)
    if not st.session_state.friends:
        st.markdown("""
        <div style="text-align: center; padding: 60px 20px; color: #4b5563;">
            <div style="font-size: 3rem; margin-bottom: 16px;">🌑</div>
            <p>No kindred connections yet.</p>
            <p style="font-size: 0.85rem;">Exchange cosmic cards to build your constellation.</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        for friend in st.session_state.friends:
            st.markdown(f"""
            <div class="post-card">
                <div class="post-header">
                    <div class="post-avatar">{friend[1:3].upper()}</div>
                    <div>
                        <div style="font-weight: 600; color: #f3f4f6;">{friend}</div>
                        <div class="post-meta">Cosmic Card Exchanged</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

def render_journal():
    moon = get_moon_data()
    st.markdown("<div class='section-label'>Luna Journal</div>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>Three Prompts. One Moon. Your Voice.</div>", unsafe_allow_html=True)
    st.markdown("<div class='section-subtitle'>Choose your prompt mode:</div>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🌙 Phase Reflection", use_container_width=True):
            st.session_state.journal_prompt = "phase"
    with col2:
        if st.button("✨ Chart Resonance", use_container_width=True):
            st.session_state.journal_prompt = "chart"
    with col3:
        if st.button("📖 Free Write", use_container_width=True):
            st.session_state.journal_prompt = "free"
    prompt_type = st.session_state.get("journal_prompt", "phase")
    if prompt_type == "phase":
        prompt_text = f"Consider the current phase — {moon['phase_name']}. Are you planting, building, refining, releasing, or resting?"
        st.markdown(f"""
        <div class="prompt-card selected">
            <div style="font-family: 'Space Grotesk'; font-weight: 600; color: #f3f4f6; margin-bottom: 8px;">🌙 Phase Reflection</div>
            <p style="color: #9ca3af; font-style: italic; margin: 0;">{prompt_text}</p>
        </div>
        """, unsafe_allow_html=True)
    elif prompt_type == "chart":
        profile = st.session_state.profile
        sun = profile.sun_sign if profile else "your Sun"
        moon_sign = profile.moon_sign if profile else "your Moon"
        prompt_text = f"Your {sun} Sun and {moon_sign} Moon — how are they dancing today?"
        st.markdown(f"""
        <div class="prompt-card selected">
            <div style="font-family: 'Space Grotesk'; font-weight: 600; color: #f3f4f6; margin-bottom: 8px;">✨ Chart Resonance</div>
            <p style="color: #9ca3af; font-style: italic; margin: 0;">{prompt_text}</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="prompt-card selected">
            <div style="font-family: 'Space Grotesk'; font-weight: 600; color: #f3f4f6; margin-bottom: 8px;">📖 Free Write</div>
            <p style="color: #9ca3af; font-style: italic; margin: 0;">No prompt. Just you, the page, and the moon.</p>
        </div>
        """, unsafe_allow_html=True)
    st.markdown("<div style='margin-top: 16px; color: #6b7280; font-size: 0.85rem;'>Your reflection:</div>", unsafe_allow_html=True)
    entry = st.text_area("", placeholder="How is this moon phase showing up in your life right now?", key="journal_entry", label_visibility="collapsed")
    if st.button("🌙 Seal Entry to the Moon", use_container_width=True):
        if entry.strip():
            new_entry = JournalEntry(
                id=f"j{len(st.session_state.journal_entries)+1}",
                prompt_type=prompt_type,
                prompt_text=prompt_text if prompt_type != "free" else "Free Write",
                content=entry,
                phase=moon["phase_name"],
                timestamp=datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            )
            st.session_state.journal_entries.insert(0, new_entry)
            st.success("✨ Entry sealed.")
            st.rerun()
    if st.session_state.journal_entries:
        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown("<div class='section-label'>Entry History</div>", unsafe_allow_html=True)
        for ent in st.session_state.journal_entries[:5]:
            st.markdown(f"""
            <div class="cosmic-card">
                <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                    <span class="phase-pill">{ent.phase}</span>
                    <span style="font-size: 0.75rem; color: #4b5563;">{ent.timestamp}</span>
                </div>
                <div style="font-size: 0.8rem; color: #a78bfa; margin-bottom: 8px;">{ent.prompt_text}</div>
                <p style="color: #e8e6f0; line-height: 1.6; margin: 0;">{ent.content}</p>
            </div>
            """, unsafe_allow_html=True)

def render_settings():
    st.markdown("<div class='section-label'>Settings</div>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>Manage Your Orbit</div>", unsafe_allow_html=True)
    st.markdown("<div class='section-subtitle'>Your account, privacy, and subscription.</div>", unsafe_allow_html=True)
    profile = st.session_state.profile
    st.markdown("<div style='font-family: Space Grotesk; font-weight: 600; color: #f3f4f6; margin-bottom: 12px;'>Profile</div>", unsafe_allow_html=True)
    new_name = st.text_input("Display Name", value=profile.display_name if profile else "", key="set_name")
    new_dob = st.date_input("Birth Date", value=profile.birth_date if profile else datetime.date(1990,1,15), key="set_dob")
    new_tob = st.time_input("Birth Time", value=profile.birth_time if profile else None, key="set_tob")
    new_loc = st.text_input("Birth Location", value=profile.birth_location if profile else "", key="set_loc")
    if st.button("💾 Save Profile"):
        if profile:
            profile.display_name = new_name
            profile.birth_date = new_dob
            profile.birth_time = new_tob
            profile.birth_location = new_loc
            profile.sun_sign = get_sun_sign(new_dob)
            profile.moon_sign = get_moon_sign_from_dob(new_dob)
        st.success("✨ Profile updated.")
        st.rerun()
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("<div style='font-family: Space Grotesk; font-weight: 600; color: #f3f4f6; margin-bottom: 12px;'>🔒 Privacy & Consent</div>", unsafe_allow_html=True)
    opt_in = st.toggle("Opt in to anonymous community sharing", value=profile.privacy_opt_in if profile else False, key="set_privacy")
    if profile:
        profile.privacy_opt_in = opt_in
    st.markdown("""
    <p style="color: #6b7280; font-size: 0.8rem;">
        When opted in, your birth chart data is anonymized and aggregated 
        to help the LunaTick community discover cosmic patterns. 
        Your identity is never shared.
    </p>
    """, unsafe_allow_html=True)
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("<div style='font-family: Space Grotesk; font-weight: 600; color: #f3f4f6; margin-bottom: 12px;'>💎 Subscription</div>", unsafe_allow_html=True)
    tier = st.selectbox("Your Tier", ["Free", "Community", "Resonance"], 
                       index=["Free","Community","Resonance"].index(profile.subscription_tier) if profile else 0,
                       key="set_tier")
    if profile:
        profile.subscription_tier = tier
    st.markdown("""
    <div style="background: rgba(255,255,255,0.02); border-radius: 12px; padding: 16px; margin-top: 12px;">
        <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
            <span style="color: #9ca3af;">Free</span>
            <span style="color: #6b7280;">Basic access</span>
        </div>
        <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
            <span style="color: #a78bfa;">Community</span>
            <span style="color: #6b7280;">Full timeline + boards</span>
        </div>
        <div style="display: flex; justify-content: space-between;">
            <span style="color: #a78bfa;">Resonance</span>
            <span style="color: #6b7280;">AI insights + card trading</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("<hr>", unsafe_allow_html=True)
    if st.button("🔄 Reset App (Clear All Data)", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

def render_bottom_nav():
    st.markdown("""
    <style>
    .fixed-bottom-nav {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        background: rgba(10, 10, 15, 0.95);
        backdrop-filter: blur(10px);
        border-top: 1px solid rgba(255, 255, 255, 0.06);
        padding: 10px 12px 14px 12px;
        z-index: 9999;
        display: flex;
        justify-content: space-around;
        align-items: center;
    }
    .fixed-bottom-nav button {
        background: transparent !important;
        border: none !important;
        color: #6b7280 !important;
        font-family: 'Inter', sans-serif;
        font-size: 0.7rem;
        text-align: center;
        padding: 4px 8px;
        border-radius: 8px;
        transition: all 0.2s ease;
        flex: 1;
    }
    .fixed-bottom-nav button:hover {
        color: #a78bfa !important;
        background: rgba(124, 58, 237, 0.1) !important;
    }
    .fixed-bottom-nav button.active {
        color: #a78bfa !important;
        background: rgba(124, 58, 237, 0.15) !important;
    }
    .main-content {
        padding-bottom: 80px;
    }
    </style>
    """, unsafe_allow_html=True)

    views = [
        ("🌙", "LunaTick", "home"),
        ("🌐", "Community", "community"),
        ("📓", "Journal", "journal"),
        ("⚙️", "Settings", "settings"),
    ]

    nav_html = '<div class="fixed-bottom-nav">'
    for icon, label, view in views:
        active_class = 'active' if st.session_state.current_view == view else ''
        nav_html += f'''
        <button class="{active_class}" onclick="
            var key = 'nav_{view}';
            var btn = document.querySelector('[data-testid="button"][data-key="' + key + '"]');
            if (btn) btn.click();
        ">
            <div style="font-size:1.4rem; line-height:1.2;">{icon}</div>
            <div style="font-size:0.6rem; margin-top:2px;">{label}</div>
        </button>
        '''
    nav_html += '</div>'
    st.markdown(nav_html, unsafe_allow_html=True)

    for icon, label, view in views:
        if st.button(f"{icon} {label}", key=f"nav_{view}", use_container_width=True):
            st.session_state.current_view = view
            st.rerun()

def render_footer():
    st.markdown("""
    <div class="c3-badge">
        🌙 A Common Cents Culture (C3) Project
    </div>
    """, unsafe_allow_html=True)

def main():
    if not st.session_state.onboarded:
        render_onboarding()
        render_footer()
        return

    st.markdown("""
    <div style="text-align:center; padding: 8px 0;">
        <span style="font-size: 1.2rem; font-family: 'Space Grotesk'; font-weight: 700; letter-spacing: 0.15em; color: #a78bfa;">🌙 LUNATICK</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="main-content">', unsafe_allow_html=True)

    view = st.session_state.current_view
    if view == "home":
        render_home()
    elif view == "community":
        render_community()
    elif view == "journal":
        render_journal()
    elif view == "settings":
        render_settings()

    st.markdown('</div>', unsafe_allow_html=True)

    render_footer()
    render_bottom_nav()

if __name__ == "__main__":
    main()