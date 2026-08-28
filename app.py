import streamlit as st
import ephem
import importlib
import math
import requests
from datetime import datetime, timezone, timedelta

# ---------------------------------------------------------------------------
# Import modules
# ---------------------------------------------------------------------------
import journal as journal_ui
import cosmic_cards
import track_calendar
import boards
import chat_room
import community
import reading_requests
import moderation
import auth
import database_backup
import supabase_backup
import supabase_store

# Streamlit can retain imported helper modules across a live-code update. If
# the Settings UI has been refreshed before auth.py, reload this one module so
# the paired profile-save and public-profile interfaces are both available.
if not all(
    hasattr(auth, method)
    for method in ("update_presence_profile", "get_public_profile", "request_password_reset")
):
    auth = importlib.reload(auth)

# Reload Journal when a warm Streamlit worker retained the former
# reflection/prompt renderer instead of the approved private free-writing view.
if getattr(journal_ui, "JOURNAL_MODULE_VERSION", None) != "private_freewrite_v1":
    journal_ui = importlib.reload(journal_ui)

# The backup Settings view can be updated before its server-only adapter in a
# warm Streamlit process. Reload only when the required snapshot reader is absent.
if not hasattr(supabase_store.SupabaseStore, "list_backup_rows"):
    supabase_store = importlib.reload(supabase_store)

# The Message Board renderer must be refreshed before Community: a warm worker
# otherwise retains the former render_boards_tab() signature without compact=.
if getattr(boards, "BOARD_MODULE_VERSION", None) != "compact_feed_v1":
    boards = importlib.reload(boards)

# The Connect page is an imported module. Require the focused Talk surface so
# a warm worker cannot retain the former profile and moderation-heavy Community UI.
if getattr(community, "COMMUNITY_MODULE_VERSION", None) != "talk_surface_toggle_v2":
    community = importlib.reload(community)

# Reading Requests owns private reader matching and conversations. Reload it on
# deployment so the Home entry point never targets a stale request workflow.
if getattr(reading_requests, "READING_REQUESTS_MODULE_VERSION", None) != "reader_requests_private_messages_v1":
    reading_requests = importlib.reload(reading_requests)

# A warm Streamlit worker can retain an older Cosmic Card renderer and routing
# function after app.py updates. Require the complete approved visual-trade
# module version rather than checking only a helper that older releases share.
if getattr(cosmic_cards, "CARD_MODULE_VERSION", None) != "profile_hub_direct_messages_v3":
    cosmic_cards = importlib.reload(cosmic_cards)

# The phone-first Track renderer is also an imported module. Reload it only
# when a warm worker retained the prior calendar implementation.
if getattr(track_calendar, "TRACK_MODULE_VERSION", None) != "upcoming_events_v1":
    track_calendar = importlib.reload(track_calendar)


def init_session_state():
    defaults = {
        "user_hash": "anonymous",
        "is_authenticated": False,
        "current_phase": "Waxing Gibbous",
        "current_tab": "Journal",
        "journal_freewrite_input": "",
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

    /* Keep LunaTicK dark regardless of the device's OS/browser preference.
       This also makes native form controls advertise a dark color scheme. */
    :root, html, body, .stApp {
        color-scheme: dark !important;
        background-color: #05070a !important;
        color: #e6edf3 !important;
        overflow-x: hidden;
    }

    .stApp {
        font-family: 'Inter', sans-serif;
    }

    /* The Home Reading Requests entry replaces the taller Moon-status copy,
       preserving the existing no-scroll phone composition. */
    .home-reading-request-button {
        align-items: center;
        background: rgba(188, 140, 255, 0.14);
        border: 1px solid rgba(188, 140, 255, 0.68);
        border-radius: 8px;
        color: #f0f6fc !important;
        display: flex;
        font-size: 0.8rem;
        font-weight: 700;
        justify-content: center;
        letter-spacing: 0.04em;
        margin-top: 0.48rem;
        min-height: 2.1rem;
        padding: 0.28rem 0.7rem;
        text-decoration: none !important;
    }
    .home-reading-request-button:hover {
        background: rgba(188, 140, 255, 0.28);
        border-color: #bc8cff;
        color: #ffffff !important;
    }

    [data-testid="stAppViewContainer"],
    [data-testid="stMain"] {
        background-color: #05070a !important;
        color: #e6edf3 !important;
    }

    /* Streamlit widgets can otherwise inherit a light OS color scheme on
       mobile browsers. Set foreground, surface, placeholder, caret, and
       border colors explicitly so Journal entries are always readable. */
    [data-testid="stTextInput"] input,
    [data-testid="stTextArea"] textarea,
    [data-testid="stNumberInput"] input,
    [data-testid="stDateInput"] input,
    [data-testid="stTimeInput"] input,
    [data-testid="stSelectbox"] input,
    [data-testid="stMultiSelect"] input {
        background-color: #0d1117 !important;
        color: #f0f6fc !important;
        -webkit-text-fill-color: #f0f6fc !important;
        caret-color: #bc8cff !important;
        border-color: #4c3a78 !important;
    }

    [data-testid="stTextInput"] [data-baseweb="input"],
    [data-testid="stTextArea"] [data-baseweb="textarea"],
    [data-testid="stNumberInput"] [data-baseweb="input"],
    [data-testid="stDateInput"] [data-baseweb="input"],
    [data-testid="stTimeInput"] [data-baseweb="input"],
    [data-testid="stSelectbox"] [data-baseweb="select"],
    [data-testid="stMultiSelect"] [data-baseweb="select"] {
        background-color: #0d1117 !important;
        border-color: #4c3a78 !important;
    }

    [data-testid="stTextInput"] input::placeholder,
    [data-testid="stTextArea"] textarea::placeholder,
    [data-testid="stNumberInput"] input::placeholder,
    [data-testid="stDateInput"] input::placeholder,
    [data-testid="stTimeInput"] input::placeholder {
        color: #9aa7bd !important;
        -webkit-text-fill-color: #9aa7bd !important;
        opacity: 1 !important;
    }

    [data-testid="stTextInput"] input:focus,
    [data-testid="stTextArea"] textarea:focus,
    [data-testid="stNumberInput"] input:focus,
    [data-testid="stDateInput"] input:focus,
    [data-testid="stTimeInput"] input:focus {
        border-color: #bc8cff !important;
        box-shadow: 0 0 0 1px #bc8cff !important;
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
        margin: 0 0 0.5rem;
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
        margin-bottom: 0.5rem;
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

    /* Preserve the original header overlay so no dark bar consumes space
       above the Moon Monitor on phone screens. */
    [data-testid="stHeader"] {
        background: transparent !important;
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
        background: linear-gradient(135deg, #071a31 0%, #0b3159 55%, #07111f 100%) !important;
        border: 1px solid #38bdf8 !important;
        border-radius: 0;
        box-shadow: 0 0 12px rgba(56, 189, 248, 0.28);
        color: #dbeeff !important;
        display: flex;
        font-family: 'Orbitron', sans-serif;
        font-size: 0.72rem;
        font-weight: 700;
        height: 100%;
        justify-content: flex-start;
        letter-spacing: 0.08em;
        opacity: 1 !important;
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
        border-color: #7dd3fc;
        box-shadow: 0 0 18px rgba(56, 189, 248, 0.42);
        color: #f0fbff;
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
        background: linear-gradient(135deg, #071a31 0%, #0b3159 55%, #07111f 100%) !important;
        border: 1px solid #38bdf8 !important;
        border-radius: 0;
        box-shadow: 0 0 12px rgba(56, 189, 248, 0.28);
        color: #dbeeff !important;
        display: flex;
        font-size: 1rem;
        height: 100%;
        justify-content: center;
        min-height: 0;
        opacity: 1 !important;
        padding: 0;
        transition: border-color 180ms ease, box-shadow 180ms ease, color 180ms ease;
        width: 100%;
    }

    [class*="st-key-lunatick-settings-gear"] [data-testid="stButton"] > button:hover,
    [class*="st-key-lunatick-settings-gear"] [data-testid="stButton"] > button:focus-visible {
        border-color: #7dd3fc;
        box-shadow: 0 0 18px rgba(56, 189, 248, 0.42);
        color: #f0fbff;
        outline: none;
    }

    /* Selected utility destinations use the shared Rising-card gold state. */
    [class*="st-key-lunatick-home-logo"] [data-testid="stButton"] > button[kind="primary"],
    [class*="st-key-lunatick-home-logo"] [data-testid="stButton"] > button[data-testid="stBaseButton-primary"],
    [class*="st-key-lunatick-settings-gear"] [data-testid="stButton"] > button[kind="primary"],
    [class*="st-key-lunatick-settings-gear"] [data-testid="stButton"] > button[data-testid="stBaseButton-primary"] {
        background: linear-gradient(135deg, #3d2f0a 0%, #6b5015 55%, #221804 100%) !important;
        border-color: #f7d25c !important;
        box-shadow: 0 0 18px rgba(247, 210, 92, 0.42) !important;
        color: #fff3c4 !important;
        opacity: 1 !important;
    }

    /* The lower-right area belongs to Streamlit's optional hosted control.
       Leave it as the native app background when that control is not mounted,
       rather than drawing a full-width lunar-glass panel that can look broken. */
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

    /* Begin app content flush with the viewport top while retaining enough
       lower clearance for the fixed navigation and persistent controls. */
    [data-testid="stMainBlockContainer"] {
        padding-bottom: 9rem;
        padding-top: 0 !important;
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

    /* Every destination starts as a blue, softly graduated lunar panel. */
    .st-key-lunatick-bottom-nav [data-testid="stButton"] > button {
        background: linear-gradient(135deg, #071a31 0%, #0b3159 55%, #07111f 100%) !important;
        border: 1px solid #38bdf8 !important;
        box-shadow: 0 0 12px rgba(56, 189, 248, 0.28);
        color: #dbeeff !important;
        transition: background 180ms ease, border-color 180ms ease, box-shadow 180ms ease, color 180ms ease;
    }

    .st-key-lunatick-bottom-nav [data-testid="stButton"] > button:hover,
    .st-key-lunatick-bottom-nav [data-testid="stButton"] > button:focus-visible {
        border-color: #7dd3fc !important;
        box-shadow: 0 0 18px rgba(56, 189, 248, 0.42) !important;
        color: #f0fbff !important;
        outline: none;
    }

    /* The selected destination uses the dark-purple, purple-bordered state. */
    .st-key-lunatick-bottom-nav [data-testid="stButton"] > button[kind="primary"],
    .st-key-lunatick-bottom-nav [data-testid="stButton"] > button[data-testid="stBaseButton-primary"] {
        background: linear-gradient(135deg, #21113f 0%, #3b1b72 55%, #180c30 100%) !important;
        border-color: #bc8cff !important;
        box-shadow: 0 0 18px rgba(188, 140, 255, 0.42) !important;
        color: #f0e6ff !important;
    }

    /* Streamlit portals fixed controls through their own keyed element
       wrappers. Keep Home and Settings in the established blue/purple system
       while the five destinations inherit distinct Cosmic Card tile accents. */
    [class*="st-key-bottom_nav_calendar"] { --nav-card-accent: #d8dee9; --nav-card-glow: rgba(216, 222, 233, 0.20); }
    [class*="st-key-bottom_nav_cosmic_cards"] { --nav-card-accent: #9c7bff; --nav-card-glow: rgba(156, 123, 255, 0.22); }
    [class*="st-key-bottom_nav_community"] { --nav-card-accent: #66a8ff; --nav-card-glow: rgba(102, 168, 255, 0.22); }
    [class*="st-key-bottom_nav_journal"] { --nav-card-accent: #c5a6ff; --nav-card-glow: rgba(197, 166, 255, 0.20); }
    [class*="st-key-bottom_nav_tones"] { --nav-card-accent: #73dfbf; --nav-card-glow: rgba(115, 223, 191, 0.20); }

    [class*="st-key-bottom_nav_"] button,
    [class*="st-key-lunatick_home_logo_button"] button,
    [class*="st-key-lunatick_settings_gear_button"] button {
        background: linear-gradient(135deg, #071a31 0%, #0b3159 55%, #07111f 100%) !important;
        border: 1px solid #38bdf8 !important;
        box-shadow: 0 0 12px rgba(56, 189, 248, 0.28) !important;
        color: #dbeeff !important;
    }

    /* Home and Settings form a paired LunaTicK utility zone. Inactive controls
       echo the upper logo's purple panel while active controls keep their shared
       Rising-gold state farther below. This rule deliberately changes paint only. */
    [class*="st-key-lunatick_home_logo_button"] button[kind="secondary"],
    [class*="st-key-lunatick_home_logo_button"] button[data-testid="stBaseButton-secondary"],
    [class*="st-key-lunatick_settings_gear_button"] button[kind="secondary"],
    [class*="st-key-lunatick_settings_gear_button"] button[data-testid="stBaseButton-secondary"] {
        background: linear-gradient(135deg, #21113f 0%, #3b1b72 55%, #180c30 100%) !important;
        border-color: #bc8cff !important;
        box-shadow: 0 0 18px rgba(188, 140, 255, 0.42) !important;
        color: #f0e6ff !important;
    }

    [class*="st-key-lunatick_home_logo_button"] button[kind="secondary"]:hover,
    [class*="st-key-lunatick_home_logo_button"] button:focus-visible,
    [class*="st-key-lunatick_settings_gear_button"] button[kind="secondary"]:hover,
    [class*="st-key-lunatick_settings_gear_button"] button:focus-visible {
        background: linear-gradient(135deg, #2d1755 0%, #512696 55%, #21113f 100%) !important;
        border-color: #ddc8ff !important;
        box-shadow: 0 0 21px rgba(188, 140, 255, 0.54) !important;
        color: #ffffff !important;
    }

    /* The five destination buttons use the established Cosmic Card border,
       inset glow, and deep panel surface associated with their tile accent. */
    [class*="st-key-bottom_nav_"] button[kind="secondary"],
    [class*="st-key-bottom_nav_"] button[data-testid="stBaseButton-secondary"] {
        background: linear-gradient(145deg, rgba(31, 46, 78, 0.92), rgba(8, 14, 29, 0.96)) !important;
        border-color: var(--nav-card-accent) !important;
        box-shadow: inset 0 0 18px var(--nav-card-glow), 0 0 11px var(--nav-card-glow) !important;
        color: var(--nav-card-accent) !important;
    }

    [class*="st-key-bottom_nav_"] button[kind="secondary"]:hover,
    [class*="st-key-bottom_nav_"] button[kind="secondary"]:focus-visible,
    [class*="st-key-bottom_nav_"] button[data-testid="stBaseButton-secondary"]:hover,
    [class*="st-key-bottom_nav_"] button[data-testid="stBaseButton-secondary"]:focus-visible {
        background: linear-gradient(145deg, rgba(42, 59, 99, 0.92), rgba(13, 24, 48, 0.94)) !important;
        border-color: var(--nav-card-accent) !important;
        box-shadow: inset 0 0 18px var(--nav-card-glow), 0 0 18px var(--nav-card-glow) !important;
        color: var(--nav-card-accent) !important;
    }

    /* A selected destination visibly arrives with a short gold bloom. The
       slower settle remains compact enough for the fixed mobile rail. */
    @keyframes lunatick-nav-active-arrival {
        0% { opacity: 0.30; transform: translateY(5px) scale(0.84); filter: brightness(0.58) saturate(0.72); }
        42% { opacity: 1; transform: translateY(-3px) scale(1.075); filter: brightness(1.38) saturate(1.18); }
        72% { opacity: 1; transform: translateY(1px) scale(0.985); filter: brightness(1.08); }
        100% { opacity: 1; transform: translateY(0) scale(1); filter: brightness(1); }
    }

    [class*="st-key-bottom_nav_"] button,
    [class*="st-key-lunatick_home_logo_button"] button,
    [class*="st-key-lunatick_settings_gear_button"] button {
        transition: background 220ms ease, border-color 220ms ease, box-shadow 220ms ease, color 220ms ease, transform 220ms ease, filter 220ms ease, opacity 220ms ease !important;
        will-change: transform, filter, opacity;
    }

    /* Instant touch confirmation is visible before Streamlit changes the
       destination, then the selected control plays its arrival sequence. */
    [class*="st-key-bottom_nav_"] button:active,
    [class*="st-key-lunatick_home_logo_button"] button:active,
    [class*="st-key-lunatick_settings_gear_button"] button:active {
        transform: scale(0.92) !important;
        filter: brightness(1.28) saturate(1.18) !important;
        box-shadow: 0 0 26px rgba(247, 210, 92, 0.58) !important;
    }

    /* Whichever of the seven controls is selected uses the shared Rising-card
       gold state. Other primary destinations retain their own Card accent. */
    [class*="st-key-bottom_nav_"] button[kind="primary"],
    [class*="st-key-bottom_nav_"] button[data-testid="stBaseButton-primary"],
    [class*="st-key-lunatick_home_logo_button"] button[kind="primary"],
    [class*="st-key-lunatick_home_logo_button"] button[data-testid="stBaseButton-primary"],
    [class*="st-key-lunatick_settings_gear_button"] button[kind="primary"],
    [class*="st-key-lunatick_settings_gear_button"] button[data-testid="stBaseButton-primary"] {
        background: linear-gradient(135deg, #3d2f0a 0%, #6b5015 55%, #221804 100%) !important;
        border-color: #f7d25c !important;
        box-shadow: 0 0 18px rgba(247, 210, 92, 0.42) !important;
        color: #fff3c4 !important;
        animation: lunatick-nav-active-arrival 760ms cubic-bezier(0.16, 0.88, 0.26, 1) both;
    }

    @media (prefers-reduced-motion: reduce) {
        [class*="st-key-bottom_nav_"] button,
        [class*="st-key-lunatick_home_logo_button"] button,
        [class*="st-key-lunatick_settings_gear_button"] button {
            animation: none !important;
            transition: none !important;
        }
    }

    /* Keep the longer Connect label compact without changing the shared
       desktop tab height. Its icon-over-label layout is enabled only on
       narrow phones below. */
    .st-key-lunatick-bottom-nav .st-key-bottom_nav_community button {
        letter-spacing: -0.01em;
        overflow-wrap: normal;
        padding-left: 0.06rem !important;
        padding-right: 0.06rem !important;
        word-break: keep-all;
    }

    @media (max-width: 480px) {
        /* Midpoint lift above the hosted platform's bottom-right management
           overlay. The rail buttons and their horizontal layout are unchanged. */
        [data-testid="stMainBlockContainer"] {
            padding-bottom: calc(8.425rem + env(safe-area-inset-bottom));
            padding-top: 0 !important;
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
            white-space: pre-line !important;
            word-break: keep-all !important;
        }

        /* Keep the musical-tone destination as one intact compact label,
           even on the 375 px-wide phone shown in the report. */
        .st-key-lunatick-bottom-nav .st-key-bottom_nav_tones button {
            font-size: 0.56rem !important;
            letter-spacing: -0.035em;
            overflow-wrap: normal !important;
            padding-left: 0 !important;
            padding-right: 0 !important;
            white-space: pre-line !important;
            word-break: keep-all !important;
        }

        /* Journal is the widest remaining compact label on narrow iPhones.
           Tighten only its own typography and padding so the final "l" cannot
           create a third line or stretch the otherwise fixed-height rail. */
        .st-key-lunatick-bottom-nav .st-key-bottom_nav_journal button {
            font-size: 0.56rem !important;
            letter-spacing: -0.02em;
            overflow-wrap: normal !important;
            padding-left: 0.04rem !important;
            padding-right: 0.04rem !important;
            white-space: pre-line !important;
            word-break: keep-all !important;
        }
    }

    /* On tablet and desktop, the persistent sidebar occupies 18.75rem.
       Keep both navigation rows wholly inside the remaining content region.
       The mobile rail below 769px deliberately retains its existing geometry. */
    @media (min-width: 769px) {
        .st-key-lunatick-bottom-nav {
            bottom: 2.625rem;
        }

        [class*="st-key-lunatick-home-logo"] [data-testid="stButton"] {
            left: 0 !important;
            width: calc(100vw - 2.625rem) !important;
        }

        [class*="st-key-lunatick-settings-gear"] [data-testid="stButton"] {
            left: calc(100vw - 2.625rem) !important;
        }

        .stAppViewContainer:has([data-testid="stSidebar"][aria-expanded="true"]) .st-key-lunatick-bottom-nav {
            left: 18.75rem;
            right: 0;
            width: auto;
        }

        .stAppViewContainer:has([data-testid="stSidebar"][aria-expanded="true"]) [class*="st-key-lunatick-home-logo"] [data-testid="stButton"] {
            left: 18.75rem !important;
            width: calc(100vw - 21.375rem) !important;
        }

        .stAppViewContainer:has([data-testid="stSidebar"][aria-expanded="true"]) [class*="st-key-lunatick-settings-gear"] [data-testid="stButton"] {
            left: calc(100vw - 2.625rem) !important;
        }
    }

    /* ---------------------------------------------------------------------
       Fixed contextual Help control
       ---------------------------------------------------------------------
       The keyed trigger and guide are fixed-position overlays. They do not
       participate in normal page flow, keeping compact Home/Connect screens
       and the established fixed navigation unchanged. */
    [class*="st-key-lunatick-page-help-button"],
    [class*="st-key-lunatick-profile-button"],
    .stElementContainer:has(.st-key-lunatick-page-help-button),
    .stElementContainer:has(.st-key-lunatick-page-help-popover),
    .stElementContainer:has(.st-key-lunatick-profile-button) {
        height: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
        pointer-events: none;
    }

    /* Streamlit gives each container a layout wrapper in the parent flex stack.
       Flatten these two wrappers as well so their normal 1rem row gap cannot
       contribute invisible scroll height beneath the fixed overlay. */
    [data-testid="stLayoutWrapper"]:has(.st-key-lunatick-page-help-button),
    [data-testid="stLayoutWrapper"]:has(.st-key-lunatick-page-help-popover),
    [data-testid="stLayoutWrapper"]:has(.st-key-lunatick-profile-button) {
        display: contents !important;
    }

    [class*="st-key-lunatick-profile-button"] [data-testid="stButton"] {
        position: fixed !important;
        top: calc(0.9rem + env(safe-area-inset-top)) !important;
        left: calc(2rem + env(safe-area-inset-left)) !important;
        z-index: 1000001 !important;
        width: 2.15rem !important;
        height: 2.15rem !important;
        margin: 0 !important;
        padding: 0 !important;
        pointer-events: auto !important;
    }

    [class*="st-key-lunatick-profile-button"] [data-testid="stButton"] button {
        align-items: center;
        background: linear-gradient(145deg, rgba(47, 30, 91, 0.98), rgba(17, 13, 39, 0.98)) !important;
        border: 1px solid rgba(188, 140, 255, 0.90) !important;
        border-radius: 999px !important;
        box-shadow: 0 0 16px rgba(188, 140, 255, 0.28), inset 0 1px 0 rgba(255, 255, 255, 0.18) !important;
        color: #f0e6ff !important;
        display: flex;
        font-size: 1rem !important;
        height: 2.15rem !important;
        justify-content: center;
        line-height: 1;
        min-height: 0 !important;
        padding: 0 !important;
        pointer-events: auto !important;
        transition: border-color 180ms ease, background 180ms ease, box-shadow 180ms ease, transform 180ms ease;
        width: 2.15rem !important;
    }

    [class*="st-key-lunatick-profile-button"] [data-testid="stButton"] button:hover,
    [class*="st-key-lunatick-profile-button"] [data-testid="stButton"] button:focus-visible {
        background: linear-gradient(145deg, #593bb0, #25184f) !important;
        border-color: #e0ccff !important;
        box-shadow: 0 0 20px rgba(188, 140, 255, 0.50), inset 0 1px 0 rgba(255, 255, 255, 0.30) !important;
        outline: none;
        transform: scale(1.06);
    }

    [class*="st-key-lunatick-profile-button"] [data-testid="stButton"] button:active {
        transform: scale(0.93);
    }

    [class*="st-key-lunatick-page-help-button"] [data-testid="stButton"] {
        position: fixed !important;
        top: calc(0.9rem + env(safe-area-inset-top)) !important;
        right: calc(2rem + env(safe-area-inset-right)) !important;
        /* Streamlit's transparent header sits at z-index 999990. The Help
           trigger must be above it for physical taps, not only DOM clicks. */
        z-index: 1000001 !important;
        width: 2.15rem !important;
        height: 2.15rem !important;
        margin: 0 !important;
        padding: 0 !important;
        pointer-events: auto !important;
    }

    [class*="st-key-lunatick-page-help-button"] [data-testid="stButton"] button {
        align-items: center;
        background: linear-gradient(145deg, rgba(194, 218, 255, 0.96), rgba(130, 164, 232, 0.95)) !important;
        border: 1px solid rgba(239, 245, 255, 0.98) !important;
        border-radius: 999px !important;
        box-shadow: 0 0 16px rgba(138, 178, 255, 0.38), inset 0 1px 0 rgba(255, 255, 255, 0.48) !important;
        color: #172340 !important;
        display: flex;
        font-family: 'Orbitron', sans-serif;
        font-size: 0.92rem !important;
        font-weight: 900;
        height: 2.15rem !important;
        justify-content: center;
        line-height: 1;
        min-height: 0 !important;
        padding: 0 !important;
        pointer-events: auto !important;
        transition: border-color 180ms ease, background 180ms ease, box-shadow 180ms ease, transform 180ms ease;
        width: 2.15rem !important;
    }

    [class*="st-key-lunatick-page-help-button"] [data-testid="stButton"] button:hover,
    [class*="st-key-lunatick-page-help-button"] [data-testid="stButton"] button:focus-visible {
        background: linear-gradient(145deg, #f4f8ff, #b8d2ff) !important;
        border-color: #ffffff !important;
        box-shadow: 0 0 20px rgba(188, 140, 255, 0.54), inset 0 1px 0 rgba(255, 255, 255, 0.74) !important;
        outline: none;
        transform: scale(1.06);
    }

    [class*="st-key-lunatick-page-help-button"] [data-testid="stButton"] button:active {
        transform: scale(0.93);
    }

    [class*="st-key-lunatick-page-help-popover"] {
        position: fixed !important;
        top: calc(3.85rem + env(safe-area-inset-top)) !important;
        right: calc(2rem + env(safe-area-inset-right)) !important;
        z-index: 1000000 !important;
        pointer-events: auto;
        width: min(21rem, calc(100vw - 1.5rem)) !important;
        max-height: min(28rem, calc(100dvh - 10.75rem - env(safe-area-inset-bottom))) !important;
        margin: 0 !important;
        overflow-y: auto !important;
        overscroll-behavior: contain;
        padding: 0.85rem !important;
        background:
            radial-gradient(circle at 88% 8%, rgba(125, 211, 252, 0.12), transparent 12rem),
            linear-gradient(145deg, rgba(18, 27, 53, 0.985), rgba(7, 12, 25, 0.99)) !important;
        border: 1px solid rgba(188, 140, 255, 0.62) !important;
        border-radius: 0.9rem !important;
        box-shadow: 0 18px 42px rgba(0, 0, 0, 0.56), 0 0 24px rgba(110, 64, 201, 0.20) !important;
    }

    [class*="st-key-lunatick-page-help-popover"] .lunatick-help-title {
        color: #f0e6ff;
        font-family: 'Orbitron', sans-serif;
        font-size: 0.78rem;
        font-weight: 800;
        letter-spacing: 0.09em;
        line-height: 1.35;
        margin: 0 0 0.35rem;
        text-transform: uppercase;
    }

    [class*="st-key-lunatick-page-help-popover"] .lunatick-help-intro {
        color: #b9c7dc;
        font-family: 'Crimson Pro', serif;
        font-size: 0.98rem;
        line-height: 1.35;
        margin: 0 0 0.55rem;
    }

    [class*="st-key-lunatick-page-help-popover"] .lunatick-help-list {
        color: #dbeeff;
        font-size: 0.78rem;
        line-height: 1.45;
        margin: 0;
        padding-left: 1.1rem;
    }

    [class*="st-key-lunatick-page-help-popover"] .lunatick-help-list li {
        margin: 0.26rem 0;
    }

    [class*="st-key-lunatick-page-help-popover"] [data-testid="stButton"] {
        margin-top: 0.7rem !important;
    }

    [class*="st-key-lunatick-page-help-popover"] [data-testid="stButton"] button {
        background: rgba(40, 26, 76, 0.96) !important;
        border: 1px solid #bc8cff !important;
        border-radius: 0.55rem !important;
        color: #f0e6ff !important;
        font-size: 0.76rem !important;
        min-height: 2rem !important;
    }

    @media (max-width: 480px) {
        [class*="st-key-lunatick-profile-button"] [data-testid="stButton"] {
            top: calc(0.9rem + env(safe-area-inset-top)) !important;
            left: calc(1.25rem + env(safe-area-inset-left)) !important;
        }

        [class*="st-key-lunatick-page-help-button"] [data-testid="stButton"] {
            top: calc(0.9rem + env(safe-area-inset-top)) !important;
            right: calc(1.25rem + env(safe-area-inset-right)) !important;
        }

        [class*="st-key-lunatick-page-help-popover"] {
            top: calc(3.85rem + env(safe-area-inset-top)) !important;
            right: calc(1.25rem + env(safe-area-inset-right)) !important;
            width: calc(100vw - 2.5rem) !important;
            max-height: calc(100dvh - 10.25rem - env(safe-area-inset-bottom)) !important;
            padding: 0.75rem !important;
        }
    }

    @media (prefers-reduced-motion: reduce) {
        [class*="st-key-lunatick-page-help-button"] [data-testid="stButton"] button,
        [class*="st-key-lunatick-profile-button"] [data-testid="stButton"] button {
            transition: none !important;
        }
    }

    ::-webkit-scrollbar { width: 6px; }
</style>
"""
st.html(LUNATICK_CSS)

# ---------------------------------------------------------------------------
# Init DBs early (needed for auth profiles)
# ---------------------------------------------------------------------------
journal_ui.init_db()
cosmic_cards.init_cards_db()
boards.init_boards_db()
chat_room.init_chat_db()
reading_requests.init_reading_requests_db()
auth.init_auth_db()

# ---------------------------------------------------------------------------
# AUTH GATE — must log in before using the app
# ---------------------------------------------------------------------------
if not auth.render_login_page():
    st.stop()

# Logged-in sidebar identity + logout
with st.sidebar:
    st.markdown(f"{st.session_state.get('avatar', '🌙')} **@{st.session_state.get('username', '?')}**")
    st.caption(st.session_state.get("display_name", ""))
    st.button("Log out", on_click=auth.logout)

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
            <div style="color:{cur_moon_c}; font-size:1.05rem; font-weight:700; margin-bottom:0.28rem;">{current['moon_symbol']} Moon in {current['moon_sign']}</div>
            <a class="home-reading-request-button" href="?reading_requests=1" aria-label="Open Reading Requests">✦ Reading Requests</a>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="stats-row">
        <div class="stat-card">
            <div class="stat-label">Glow</div>
            <div class="stat-val">{current["illum"]*100:.1f}%</div>
            <div class="stat-label" style="font-size:0.55rem;">Surface</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Phase</div>
            <div class="stat-val" style="font-size:1.5rem;">{current["phase_emoji"]}</div>
            <div class="stat-label" style="font-size:0.55rem;">{current["phase_name"]}</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Age</div>
            <div class="stat-val">{current["age_days"]:.1f}d</div>
            <div class="stat-label" style="font-size:0.55rem;">Cycle</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


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
          font-size: 0.82rem;
          line-height: 1.38;
          margin: 0.42rem 0 0.72rem;
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
          gap: 0.4rem;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          margin-bottom: 0.62rem;
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
          min-height: 2.65rem;
          padding: 0.4rem 0.55rem;
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
          gap: 0.52rem;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          margin: 0.46rem 0 0.62rem;
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
          gap: 0.52rem;
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
          font-size: 0.72rem;
          line-height: 1.32;
          margin: 0.5rem 0 0;
          min-height: 1rem;
        }

        .status[data-state="playing"] { color: var(--mint); }
        .status[data-state="error"] { color: var(--rose); }

        .note {
          color: #72809b;
          font-size: 0.61rem;
          line-height: 1.32;
          margin: 0.28rem 0 0;
        }

        @media (max-width: 480px) {
          .tone-space { padding: 0.75rem; }
          .eyebrow { font-size: 0.56rem; margin-bottom: 0.24rem; }
          h1 { font-size: 1.2rem; }
          .intro { font-size: 0.76rem; margin: 0.3rem 0 0.48rem; }
          .section-label { font-size: 0.58rem; margin-bottom: 0.3rem; }
          .presets { gap: 0.32rem; margin-bottom: 0.45rem; }
          .preset { min-height: 2.35rem; padding: 0.3rem 0.45rem; }
          .preset-name { font-size: 0.72rem; }
          .preset-frequency { font-size: 0.59rem; margin-top: 0.08rem; }
          .controls { gap: 0.38rem; margin: 0.35rem 0 0.5rem; }
          select, input[type="number"] { min-height: 2.22rem; }
          .action { min-height: 2.42rem; font-size: 0.78rem; padding: 0.42rem 0.5rem; }
          .status { font-size: 0.66rem; margin-top: 0.38rem; }
          .note { font-size: 0.55rem; margin-top: 0.22rem; }
        }

        @media (max-width: 360px) {
          .actions { gap: 0.42rem; }
        }
      </style>
    </head>
    <body>
      <main class="tone-space" aria-labelledby="tones-title">
        <div class="eyebrow">Lunatick sound space</div>
        <h1 id="tones-title">Healing tones</h1>
        <p class="intro">Binaural sine tones shift every 11 seconds. Set your beat difference, sequence, and listening level.</p>

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

        <div class="controls">
          <div class="control">
            <label class="section-label" for="frequency">Base frequency</label>
            <input id="frequency" type="number" min="100" max="1000" step="1" value="432" inputmode="numeric">
          </div>
          <div class="control">
            <label class="section-label" for="beat">Beat difference (Hz)</label>
            <input id="beat" type="number" min="0" max="20" step="0.01" value="7.83" inputmode="decimal">
          </div>
          <div class="control">
            <label class="section-label" for="cycle-mode">Tone sequence</label>
            <select id="cycle-mode">
              <option value="random">Random</option>
              <option value="sweep">Chakra Sweep</option>
            </select>
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

        <p id="status" class="status" role="status" aria-live="polite" data-state="idle">Ready — Moon is selected for binaural sine playback.</p>
        <p class="note">For personal relaxation only. This feature is not medical treatment or a substitute for professional care.</p>
      </main>

      <script>
        (() => {
          const AudioContextClass = window.AudioContext || window.webkitAudioContext;
          const presetButtons = [...document.querySelectorAll(".preset")];
          const frequencyInput = document.getElementById("frequency");
          const beatInput = document.getElementById("beat");
          const cycleModeSelect = document.getElementById("cycle-mode");
          const volume = document.getElementById("volume");
          const volumeValue = document.getElementById("volume-value");
          const startButton = document.getElementById("start");
          const stopButton = document.getElementById("stop");
          const status = document.getElementById("status");

          const LOCKED_WAVEFORM = "sine";
          const AUTO_SHIFT_INTERVAL_MS = 11000;
          const GLIDE_DURATION_SECONDS = 2.5;
          const presetFrequencies = [174, 285, 432, 528, 639, 741];

          let audioContext = null;
          let leftOsc = null;
          let rightOsc = null;
          let leftGain = null;
          let rightGain = null;
          let selectedFrequency = 432;
          let beatFrequency = 7.83;
          let shiftInterval = null;
          let sequenceIndex = presetFrequencies.indexOf(selectedFrequency);
          let sequenceDirection = 1;

          function setStatus(message, state = "idle") {
            status.textContent = message;
            status.dataset.state = state;
          }

          function selectedPresetName(freq) {
            const button = presetButtons.find((item) => Number(item.dataset.frequency) === freq);
            return button ? button.querySelector(".preset-name").textContent : "Custom";
          }

          function currentGain() {
            return Number(volume.value) / 100;
          }

          function setPlayingUI(isPlaying) {
            startButton.disabled = isPlaying;
            stopButton.disabled = !isPlaying;
          }

          function updateVolumeLabel() {
            volumeValue.textContent = `${volume.value}%`;
          }

          function highlightPreset(freq) {
            presetButtons.forEach((button) => {
              button.setAttribute("aria-pressed", String(Number(button.dataset.frequency) === freq));
            });
          }

          function sequenceLabel() {
            return cycleModeSelect.value === "sweep" ? "Chakra Sweep" : "Random";
          }

          function applyFrequency(freq, announce = true) {
            selectedFrequency = Math.min(1000, Math.max(100, Number(freq) || 432));
            frequencyInput.value = selectedFrequency;
            sequenceIndex = presetFrequencies.indexOf(selectedFrequency);
            highlightPreset(selectedFrequency);

            if (audioContext && leftOsc && rightOsc) {
              const now = audioContext.currentTime;
              leftOsc.frequency.cancelScheduledValues(now);
              leftOsc.frequency.exponentialRampToValueAtTime(selectedFrequency, now + GLIDE_DURATION_SECONDS);
              rightOsc.frequency.cancelScheduledValues(now);
              rightOsc.frequency.exponentialRampToValueAtTime(
                selectedFrequency + beatFrequency,
                now + GLIDE_DURATION_SECONDS,
              );
            }

            if (announce) {
              const state = leftOsc && rightOsc ? "playing" : "idle";
              setStatus(
                `${state === "playing" ? "Playing" : "Ready"} binaural sine — ${selectedPresetName(selectedFrequency)} ` +
                `(${selectedFrequency} Hz + ${beatFrequency} Hz beat, ${sequenceLabel()}). Shifts every 11 seconds.`,
                state,
              );
            }
          }

          function shiftToNextPreset() {
            let nextIndex;
            if (cycleModeSelect.value === "random") {
              nextIndex = Math.floor(Math.random() * presetFrequencies.length);
            } else {
              sequenceIndex += sequenceDirection;
              if (sequenceIndex >= presetFrequencies.length - 1) {
                sequenceIndex = presetFrequencies.length - 1;
                sequenceDirection = -1;
              } else if (sequenceIndex <= 0) {
                sequenceIndex = 0;
                sequenceDirection = 1;
              }
              nextIndex = sequenceIndex;
            }
            applyFrequency(presetFrequencies[nextIndex]);
          }

          function stopTone() {
            const now = audioContext ? audioContext.currentTime : 0;
            if (shiftInterval) {
              clearInterval(shiftInterval);
              shiftInterval = null;
            }
            if (leftOsc && leftGain) {
              leftGain.gain.cancelScheduledValues(now);
              leftGain.gain.setValueAtTime(Math.max(leftGain.gain.value, 0), now);
              leftGain.gain.linearRampToValueAtTime(0, now + 0.10);
              leftOsc.stop(now + 0.11);
            }
            if (rightOsc && rightGain) {
              rightGain.gain.cancelScheduledValues(now);
              rightGain.gain.setValueAtTime(Math.max(rightGain.gain.value, 0), now);
              rightGain.gain.linearRampToValueAtTime(0, now + 0.10);
              rightOsc.stop(now + 0.11);
            }
            leftOsc = null;
            rightOsc = null;
            leftGain = null;
            rightGain = null;
            setPlayingUI(false);
            setStatus("Tone stopped. Ready for binaural sine playback.");
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
                await new Promise((resolve) => setTimeout(resolve, 100));
              }

              const now = audioContext.currentTime;
              leftOsc = audioContext.createOscillator();
              leftGain = audioContext.createGain();
              const leftPanner = audioContext.createStereoPanner();
              leftPanner.pan.value = -1;
              leftOsc.type = LOCKED_WAVEFORM;
              leftOsc.frequency.setValueAtTime(selectedFrequency, now);
              leftGain.gain.setValueAtTime(0, now);
              leftGain.gain.linearRampToValueAtTime(currentGain(), now + 0.12);
              leftOsc.connect(leftGain);
              leftGain.connect(leftPanner);
              leftPanner.connect(audioContext.destination);
              leftOsc.start();

              rightOsc = audioContext.createOscillator();
              rightGain = audioContext.createGain();
              const rightPanner = audioContext.createStereoPanner();
              rightPanner.pan.value = 1;
              rightOsc.type = LOCKED_WAVEFORM;
              rightOsc.frequency.setValueAtTime(selectedFrequency + beatFrequency, now);
              rightGain.gain.setValueAtTime(0, now);
              rightGain.gain.linearRampToValueAtTime(currentGain(), now + 0.12);
              rightOsc.connect(rightGain);
              rightGain.connect(rightPanner);
              rightPanner.connect(audioContext.destination);
              rightOsc.start();

              shiftInterval = setInterval(shiftToNextPreset, AUTO_SHIFT_INTERVAL_MS);
              setPlayingUI(true);
              applyFrequency(selectedFrequency);
            } catch (error) {
              console.error("Unable to start tone", error);
              leftOsc = null;
              rightOsc = null;
              leftGain = null;
              rightGain = null;
              setPlayingUI(false);
              setStatus("The tone could not start. Check browser audio permissions and try again.", "error");
            }
          }

          presetButtons.forEach((button) => {
            button.addEventListener("click", () => applyFrequency(Number(button.dataset.frequency)));
          });

          frequencyInput.addEventListener("change", () => applyFrequency(frequencyInput.value));
          beatInput.addEventListener("change", () => {
            const rawValue = Number(beatInput.value);
            beatFrequency = Math.min(20, Math.max(0, Number.isFinite(rawValue) ? rawValue : 7.83));
            beatInput.value = beatFrequency;
            if (audioContext && rightOsc) {
              rightOsc.frequency.cancelScheduledValues(audioContext.currentTime);
              rightOsc.frequency.setTargetAtTime(selectedFrequency + beatFrequency, audioContext.currentTime, 0.03);
            }
            applyFrequency(selectedFrequency);
          });
          cycleModeSelect.addEventListener("change", () => {
            sequenceIndex = presetFrequencies.indexOf(selectedFrequency);
            sequenceDirection = 1;
            applyFrequency(selectedFrequency);
          });
          volume.addEventListener("input", () => {
            updateVolumeLabel();
            const gain = currentGain();
            if (leftGain && audioContext) {
              leftGain.gain.cancelScheduledValues(audioContext.currentTime);
              leftGain.gain.setTargetAtTime(gain, audioContext.currentTime, 0.025);
            }
            if (rightGain && audioContext) {
              rightGain.gain.cancelScheduledValues(audioContext.currentTime);
              rightGain.gain.setTargetAtTime(gain, audioContext.currentTime, 0.025);
            }
          });
          startButton.addEventListener("click", startTone);
          stopButton.addEventListener("click", stopTone);

          window.addEventListener("pagehide", () => {
            if (shiftInterval) clearInterval(shiftInterval);
            if (leftOsc) { try { leftOsc.stop(); } catch (_) {} }
            if (rightOsc) { try { rightOsc.stop(); } catch (_) {} }
            if (audioContext && audioContext.state !== "closed") audioContext.close();
          });
        })();
      </script>
    </body>
    </html>
    """

    components.html(tone_generator_html, height=520, scrolling=False)


def render_calendar():
    """Render the phone-first Track calendar implementation."""
    track_calendar.render_track_tab()


def _is_backup_owner() -> bool:
    """Allow full-database export only for the email configured in Cloud secrets."""
    try:
        backup_config = st.secrets.get("backup", {})
        owner_email = str(backup_config.get("owner_email", "")).strip().lower()
    except Exception:
        return False

    current_email = str(st.session_state.get("email", "")).strip().lower()
    return bool(owner_email and current_email and owner_email == current_email)


def render_settings():
    st.markdown("""
    <div style="font-family: 'Orbitron', sans-serif; font-size: 0.8rem; letter-spacing: 3px; color: #bc8cff; text-transform: uppercase; margin-bottom: 0.3rem;">
        ⚙️ Settings
    </div>
    <div style="font-family: 'Crimson Pro', serif; font-size: 1rem; color: #8b949e; margin-bottom: 1.2rem; font-style: italic;">
        Manage your account, privacy, and subscription.
    </div>
    """, unsafe_allow_html=True)

    avatar_options = ["🌙", "🔮", "🪐", "✨", "🌿", "🔥", "🌊", "🦋", "☄️", "🧿"]
    current_avatar = st.session_state.get("avatar", "🌙")
    if current_avatar not in avatar_options:
        avatar_options.insert(0, current_avatar)

    st.markdown("### ✦ Profile & Presence")
    st.caption("Choose how you appear across LunaTicK Community. Your sign-in email stays private.")
    st.markdown(
        f"""
        <div style="display:flex; align-items:center; gap:0.7rem; padding:0.75rem 0.9rem; margin:0.45rem 0 0.9rem; border:1px solid rgba(188,140,255,0.24); border-radius:12px; background:rgba(110,64,201,0.10);">
          <div style="font-size:2rem; line-height:1;">{current_avatar}</div>
          <div>
            <div style="color:#f0f6fc; font-weight:700;">{st.session_state.get('display_name', 'Moon Wanderer')}</div>
            <div style="color:#bc8cff; font-size:0.82rem;">@{st.session_state.get('username', 'moon_wanderer')}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form("presence_profile_form", clear_on_submit=False):
        profile_columns = st.columns([1, 2])
        with profile_columns[0]:
            avatar = st.selectbox(
                "Avatar",
                avatar_options,
                index=avatar_options.index(current_avatar),
                help="Select an icon for your LunaTicK presence.",
            )
        with profile_columns[1]:
            username = st.text_input(
                "Username",
                value=st.session_state.get("username", ""),
                max_chars=24,
                help="3–24 lowercase letters, numbers, or underscores. This is your public handle.",
            )
        display_name = st.text_input(
            "Display name",
            value=st.session_state.get("display_name", "Moon Wanderer"),
            max_chars=48,
            help="This is the name shown beside your avatar.",
        )
        bio = st.text_area(
            "Bio",
            value=st.session_state.get("bio", ""),
            max_chars=240,
            height=96,
            placeholder="A few words about your cosmic orbit…",
            help="Optional. Up to 240 characters.",
        )
        save_presence = st.form_submit_button("Save profile", type="primary", use_container_width=True)

    if save_presence:
        saved, message = auth.update_presence_profile(username, display_name, avatar, bio)
        if saved:
            st.success(message)
            st.rerun()
        else:
            st.error(message)

    st.markdown("---")
    st.markdown("### 🧬 Birth chart")
    st.caption("Date, time, and place power your Cosmic Card (including Rising).")
    cosmic_cards.render_profile_form(
        st.session_state.get("user_hash", "anonymous"),
        key_prefix="settings",
    )

    st.markdown("---")
    st.markdown("### 🔒 Cosmic Card privacy")
    st.caption(
        "Your public profile always keeps its Cosmic Card. Control whether the card shows "
        "your derived cosmic values or a private-details card state."
    )
    current_card_values_visible = cosmic_cards.public_card_values_visible(
        st.session_state.get("user_hash", "anonymous")
    )
    show_public_card_values = st.toggle(
        "Show my cosmic values on my public profile",
        value=current_card_values_visible,
        key="public_card_values_visible_toggle",
        help="When off, your visible profile card keeps its design but hides Sun, Moon, Rising, phase, full-moon count, and Dominant Planet.",
    )
    if show_public_card_values != current_card_values_visible:
        cosmic_cards.set_public_card_values_visible(
            st.session_state.get("user_hash", "anonymous"), show_public_card_values
        )
        st.session_state.pop("public_card_values_visible_toggle", None)
        if show_public_card_values:
            st.toast("Your public Cosmic Card now shows its derived values.")
        else:
            st.toast("Your public Cosmic Card remains visible; its derived values are now private.")
        st.rerun()

    if moderation.is_moderator():
        st.markdown("---")
        st.markdown("### 🛡️ Community moderation")
        st.caption("Review and manage public LunaTicK Talk content. Private Journals remain unavailable.")
        moderation.render_moderation_console()

    st.markdown("---")
    st.markdown("### 🔐 Password & Sign-in")
    account_email = str(st.session_state.get("email", "")).strip().lower()
    st.caption(
        "LunaTicK never stores your password. Auth0 manages sign-in and sends secure reset links to your account email."
    )
    if account_email:
        if st.button(
            "Email me a password-reset link",
            key="settings_password_reset",
            type="secondary",
            use_container_width=True,
        ):
            sent, message = auth.request_password_reset(account_email)
            if sent:
                st.success(message)
            else:
                st.warning(message)
    else:
        st.info("Your account email is unavailable in this session. Log out and sign in again to request a reset link.")

    st.markdown("---")
    st.markdown("### 💎 Subscription")
    st.selectbox("Your Tier", ["Free", "Community ($5/mo)", "Resonance ($15/mo)"])
    st.info("Upgrade to Community or Resonance for full access to AI insights and community features.")

    st.markdown("---")
    if _is_backup_owner():
        st.markdown("### 🗄️ Backup & Recovery")
        if auth.using_supabase_backend():
            st.caption(
                "Owner-only logical Supabase export. It packages the live LunaTicK data tables with "
                "per-table counts and SHA-256 verification; it never includes service credentials."
            )
            st.warning(
                "Keep the downloaded ZIP and manifest in secure offline storage. This export is a "
                "point-in-time logical snapshot, not an in-app restore button."
            )
            if st.button("Prepare verified Supabase backup", key="prepare_supabase_backup", type="secondary"):
                try:
                    store = supabase_store.SupabaseStore(
                        supabase_store.SupabaseSettings.from_streamlit_secrets()
                    )
                    backup_bytes, backup_manifest, backup_name = (
                        supabase_backup.create_verified_supabase_backup(store)
                    )
                    st.session_state["supabase_backup_bytes"] = backup_bytes
                    st.session_state["supabase_backup_manifest"] = backup_manifest
                    st.session_state["supabase_backup_name"] = backup_name
                    st.success(
                        f"Verified backup ready: {backup_manifest['archive_bytes']:,} bytes · "
                        f"{sum(backup_manifest['table_counts'].values()):,} rows across "
                        f"{len(backup_manifest['table_counts'])} tables."
                    )
                except Exception as error:
                    st.error(f"Supabase backup could not be prepared: {error}")

            if st.session_state.get("supabase_backup_bytes"):
                backup_manifest = st.session_state["supabase_backup_manifest"]
                backup_name = st.session_state["supabase_backup_name"]
                st.download_button(
                    "Download verified Supabase backup",
                    data=st.session_state["supabase_backup_bytes"],
                    file_name=backup_name,
                    mime="application/zip",
                    use_container_width=True,
                    key="download_supabase_backup",
                )
                st.download_button(
                    "Download backup manifest",
                    data=supabase_backup.manifest_bytes(backup_manifest),
                    file_name=supabase_backup.manifest_filename(backup_name),
                    mime="application/json",
                    use_container_width=True,
                    key="download_supabase_backup_manifest",
                )
                st.caption(
                    f"Archive SHA-256: `{backup_manifest['archive_sha256']}` · "
                    f"Snapshot SHA-256: `{backup_manifest['snapshot_sha256']}`"
                )
        else:
            st.caption("Owner-only legacy SQLite export for the explicit rollback backend.")
            if st.button("Prepare verified SQLite backup", key="prepare_sqlite_backup", type="secondary"):
                try:
                    backup_bytes, backup_manifest, backup_name = database_backup.create_verified_backup()
                    st.session_state["sqlite_backup_bytes"] = backup_bytes
                    st.session_state["sqlite_backup_manifest"] = backup_manifest
                    st.session_state["sqlite_backup_name"] = backup_name
                    st.success(
                        f"Verified backup ready: {backup_manifest['database_bytes']:,} bytes · "
                        f"{sum(backup_manifest['table_counts'].values())} rows across "
                        f"{len(backup_manifest['table_counts'])} tables."
                    )
                except Exception as error:
                    st.error(f"Backup could not be prepared: {error}")

            if st.session_state.get("sqlite_backup_bytes"):
                backup_manifest = st.session_state["sqlite_backup_manifest"]
                backup_name = st.session_state["sqlite_backup_name"]
                st.download_button(
                    "Download verified SQLite backup",
                    data=st.session_state["sqlite_backup_bytes"],
                    file_name=backup_name,
                    mime="application/vnd.sqlite3",
                    use_container_width=True,
                    key="download_sqlite_backup",
                )
                st.download_button(
                    "Download backup manifest",
                    data=database_backup.manifest_bytes(backup_manifest),
                    file_name=database_backup.manifest_filename(backup_name),
                    mime="application/json",
                    use_container_width=True,
                    key="download_sqlite_backup_manifest",
                )
                st.caption(
                    f"SHA-256: `{backup_manifest['sha256']}` · SQLite integrity check: "
                    f"{backup_manifest['integrity_check']}"
                )

    st.markdown("---")
    st.markdown("### 🗑️ Danger Zone")
    if st.button("Clear all journal entries", type="secondary"):
        if "journal_entries" in st.session_state:
            st.session_state.journal_entries = []
            st.success("Journal entries cleared.")
    st.button("Log out of this account", type="secondary", on_click=auth.logout)


# Sync phase
if "current_phase" not in st.session_state:
    st.session_state.current_phase = get_celestial_data(datetime.now(timezone.utc))["phase_name"]

# ---------------------------------------------------------------------------
# Main App — Fixed Bottom Navigation
# ---------------------------------------------------------------------------
if "nav_page" not in st.session_state:
    st.session_state.nav_page = "Home"

if st.query_params.get("reading_requests") == "1":
    st.session_state.nav_page = "Reading Requests"
    st.query_params.pop("reading_requests", None)

# A calendar day uses a lightweight query route so the compact HTML grid stays
# horizontal on phones. Preserve Track on that route even if Streamlit creates
# a fresh script session for the browser navigation.
if str(st.query_params.get("track_day", "")).strip():
    st.session_state.nav_page = "Calendar"

# Community usernames use this lightweight route to open the same safe public
# profile surface without placing immutable account identifiers in the UI.
requested_profile = str(st.query_params.get("profile", "")).strip().lstrip("@")
if requested_profile:
    st.session_state.profile_hub_lookup = requested_profile
    st.session_state.profile_return_page = "Community"
    st.session_state.nav_page = "Profile"
    st.query_params.pop("profile", None)

# Existing sessions may still point to a former standalone social tab. Move
# those users directly into the unified Community destination on the next run.
if st.session_state.nav_page in {"Chat", "Boards", "LunaTick Talk", "LunaTicK Talk"}:
    st.session_state.nav_page = "Community"


def set_nav_page(page_name: str) -> None:
    """Switch destinations and clear a date-selection route when leaving Track."""
    st.session_state.nav_page = page_name
    if page_name != "Calendar":
        st.query_params.pop("track_day", None)


PAGE_HELP_GUIDES = {
    "Home": {
        "title": "Home guide",
        "intro": "A private snapshot of your current lunar rhythm and personal cosmic chart.",
        "items": (
            "Moon Monitor shows the countdown to the next full moon.",
            "Your Cosmic Chart uses your saved private birth data; it is not posted to community spaces.",
            "Reading Requests opens the free community matching area for astrology readings.",
            "Glow, Phase, and Age summarize the current lunar cycle.",
        ),
    },
    "Calendar": {
        "title": "Inspect guide",
        "intro": "Browse the lunar calendar, upcoming celestial moments, and your own private notes.",
        "items": (
            "Use the arrow controls to move between months.",
            "Moon icons indicate the lunar phase for each day.",
            "Marked events highlight notable lunar or celestial dates.",
            "Private notes stay visible only to you.",
        ),
    },
    "Cosmic Cards": {
        "title": "Collect guide",
        "intro": "Create and manage a Cosmic Card while keeping your exact birth details private.",
        "items": (
            "Add your birth date, local time, and a city or postal code to begin.",
            "Confirm the resolved place, coordinates, and timezone before saving.",
            "Rising is calculated from a tropical Placidus chart using Swiss Ephemeris.",
            "Settings controls whether derived card values are visible on your public profile.",
        ),
    },
    "Community": {
        "title": "Connect guide",
        "intro": "Choose a live conversation or a lasting community discussion.",
        "items": (
            "Live Chat refreshes lightly so the room stays current.",
            "Message Board supports upvotes, downvotes, and Newest, Top, or Controversial sorting.",
            "Reading Requests are free, community-only, and open private messages only after a match.",
            "Keep personal birth details and private information out of public posts.",
        ),
    },
    "Journal": {
        "title": "Reflect guide",
        "intro": "A personal writing space intended only for your own saved reflections.",
        "items": (
            "Write freely, then save an entry when you are ready.",
            "Saved journal entries are private by design.",
            "Use Clear to discard unsaved text from the current writing area.",
        ),
    },
    "Tones": {
        "title": "Correct guide",
        "intro": "Set a gentle listening tone for personal relaxation and reflection.",
        "items": (
            "Choose a preset or set your own frequency and waveform.",
            "Binaural mode is designed for headphone listening.",
            "Adjust cycle speed and listening volume before starting a tone.",
            "This feature is for personal relaxation only and is not medical treatment.",
        ),
    },
    "Profile": {
        "title": "Profile guide",
        "intro": "Your public LunaTicK presence and your private card-collection connections.",
        "items": (
            "Search an exact public @username to view a member profile.",
            "Send a card trade to request a mutual connection; the other member must accept it.",
            "Accepted connections can display Cosmic Cards when the owner has activated one.",
            "Profiles never reveal private birth inputs, account email, or location details.",
        ),
    },
    "Settings": {
        "title": "Settings guide",
        "intro": "Manage your profile, private birth-chart inputs, visibility preferences, and account options.",
        "items": (
            "Your sign-in email remains private; your public profile uses your chosen handle and display name.",
            "Birth date, time, coordinates, and resolved place are private inputs.",
            "Use Cosmic Card privacy to choose whether derived values appear on your public card.",
            "Moderation tools appear here only for authorized moderators.",
        ),
    },
    "Reading Requests": {
        "title": "Reading Requests guide",
        "intro": "Request or volunteer for a free community astrology reading.",
        "items": (
            "Readers can describe their availability and areas of practice.",
            "Requesters can share only the details they choose to provide.",
            "Private lightweight messages become available only to matched participants.",
            "Do not publish exact birth details in public discussion areas.",
        ),
    },
}


def open_profile_hub(return_page: str) -> None:
    """Open the standalone social profile page and preserve the calling destination."""
    st.session_state.profile_return_page = return_page if return_page != "Profile" else "Home"
    st.session_state.profile_hub_section = "profile"
    st.session_state.nav_page = "Profile"


def render_profile_launcher(page_name: str) -> None:
    """Render the fixed profile entry point outside normal layout flow."""
    if page_name == "Profile":
        return
    with st.container(key="lunatick-profile-button"):
        st.button(
            "👤",
            key=f"lunatick_profile_open_{page_name.lower().replace(' ', '_')}",
            help="Open your profile, find members, and trade Cosmic Cards",
            type="secondary",
            on_click=open_profile_hub,
            args=(page_name,),
        )


def render_page_help(page_name: str) -> None:
    """Render a fixed page guide without adding normal-flow layout height."""
    guide = PAGE_HELP_GUIDES.get(page_name, PAGE_HELP_GUIDES["Home"])
    slug = page_name.lower().replace(" ", "_")
    state_key = f"lunatick_page_help_open_{slug}"

    with st.container(key="lunatick-page-help-button"):
        toggled = st.button(
            "?",
            key=f"lunatick_page_help_toggle_{slug}",
            help=f"Open the {guide['title'].lower()}",
            type="secondary",
        )

    if toggled:
        st.session_state[state_key] = not st.session_state.get(state_key, False)

    if not st.session_state.get(state_key, False):
        return

    guide_items = "".join(f"<li>{item}</li>" for item in guide["items"])
    with st.container(key="lunatick-page-help-popover"):
        st.markdown(
            f"""
            <section class="lunatick-help-content" role="dialog" aria-label="{guide['title']}">
              <div class="lunatick-help-title">? {guide['title']}</div>
              <p class="lunatick-help-intro">{guide['intro']}</p>
              <ul class="lunatick-help-list">{guide_items}</ul>
            </section>
            """,
            unsafe_allow_html=True,
        )
        if st.button(
            "Close guide",
            key=f"lunatick_page_help_close_{slug}",
            use_container_width=True,
            type="secondary",
        ):
            st.session_state[state_key] = False
            st.rerun()


# Render one destination in the normal page body.
current_page = st.session_state.nav_page

if current_page == "Home":
    render_home()
elif current_page == "Community":
    community.render_community()
elif current_page == "Reading Requests":
    reading_requests.render_reading_requests()
elif current_page == "Cosmic Cards":
    cosmic_cards.render_cosmic_cards_tab()
elif current_page == "Profile":
    cosmic_cards.render_profile_hub()
elif current_page == "Journal":
    journal_ui.render_journal_tab()
elif current_page == "Calendar":
    render_calendar()
elif current_page == "Tones":
    render_tones()
elif current_page == "Settings":
    render_settings()
else:
    st.session_state.nav_page = "Home"
    st.rerun()

# Both fixed controls sit outside normal page flow, so neither shifts destinations
# or extends compact Home/Connect screens.
render_profile_launcher(current_page)
render_page_help(current_page)

NAV_ITEMS = [
    ("Calendar", "📅", "Inspect"),
    ("Cosmic Cards", "🃏", "Collect"),
    ("Community", "👥", "Connect"),
    ("Journal", "📓", "Reflect"),
    ("Tones", "🎵", "Correct"),
]

with st.container(key="lunatick-bottom-nav"):
    nav_columns = st.columns(len(NAV_ITEMS), gap="small")

    for column, (page_name, icon, compact_label) in zip(nav_columns, NAV_ITEMS):
        nav_label = (
            f"{icon}\n{compact_label}"
            if page_name in ("Community", "Journal", "Tones")
            else f"{icon} {compact_label}"
        )
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

with st.container(key="lunatick-home-logo"):
    st.button(
        "🌙 LUNATICK",
        key="lunatick_home_logo_button",
        type="primary" if current_page == "Home" else "secondary",
        help="Return to Home",
        on_click=set_nav_page,
        args=("Home",),
    )

with st.container(key="lunatick-settings-gear"):
    st.button(
        "⚙️",
        key="lunatick_settings_gear_button",
        type="primary" if current_page == "Settings" else "secondary",
        help="Open Settings",
        on_click=set_nav_page,
        args=("Settings",),
    )
