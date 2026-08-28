from pathlib import Path

app_source = Path("app.py").read_text(encoding="utf-8")
community_source = Path("community.py").read_text(encoding="utf-8")
chat_source = Path("chat_room.py").read_text(encoding="utf-8")
boards_source = Path("boards.py").read_text(encoding="utf-8")
cards_source = Path("cosmic_cards.py").read_text(encoding="utf-8")
moderation_source = Path("moderation.py").read_text(encoding="utf-8")

assert 'COMMUNITY_MODULE_VERSION = "talk_surface_toggle_v2"' in community_source
assert "LunaTicK Talk" in community_source
assert '("Live Chat", "Message Board")' in community_source
assert 'key="talk_active_surface"' in community_source
assert "horizontal=True" in community_source
assert "if active_surface == \"Live Chat\":" in community_source
assert "chat_room.render_chat_tab()" in community_source
assert "boards.render_boards_tab(compact=True)" in community_source
assert "talk-divider" not in community_source
assert "_render_public_profile_lookup" not in community_source
assert "render_moderation_console" not in community_source

assert "LIVE_CHAT_REFRESH_SECONDS = 5" in chat_source
assert "@fragment(run_every=LIVE_CHAT_REFRESH_SECONDS)" in chat_source
assert 'st.container(height=195, border=True)' in chat_source
assert "lunatick_talk_live_chat_form" in chat_source

assert "DEFAULT_BOARD_SLUG = \"general\"" in boards_source
assert "lunatick_talk_board_post" in boards_source
assert "st.selectbox(\"Board\"" not in boards_source
assert 'BOARD_MODULE_VERSION = "compact_feed_v1"' in boards_source
assert "def render_boards_tab(*, compact: bool = False)" in boards_source
assert "feed_height = 255 if compact else 275" in boards_source
assert 'key="talk-board-feed" if compact else None' in boards_source
assert '[data-testid="stMain"]:has(.st-key-talk-board-feed) [data-testid="stMainBlockContainer"]' in community_source
assert "padding-bottom: calc(4.425rem + env(safe-area-inset-bottom)) !important;" in community_source
assert "padding-bottom: calc(4rem + 0.9375rem) !important;" in community_source

assert 'BOARD_MODULE_VERSION", None) != "compact_feed_v1"' in app_source
assert "boards = importlib.reload(boards)" in app_source
assert 'COMMUNITY_MODULE_VERSION", None) != "talk_surface_toggle_v2"' in app_source
assert "import lunatick_talk_ui" not in app_source
assert "import lunatick_talk_db" not in app_source
assert "talk_db.seed_talk_posts" not in app_source
assert "moderation.render_moderation_console()" in app_source
assert "CARD_MODULE_VERSION\", None) != \"profile_menu_visible_v4\"" in app_source

# The five primary destinations follow the approved compact order and labels.
assert "NAV_ITEMS = [\n    (\"Calendar\", \"📅\", \"Inspect\"),\n    (\"Cosmic Cards\", \"🃏\", \"Collect\"),\n    (\"Community\", \"👥\", \"Connect\"),\n    (\"Journal\", \"📓\", \"Reflect\"),\n    (\"Tones\", \"🎵\", \"Correct\"),\n]" in app_source

# Five distinct Cosmic Card tile accents style inactive destinations. Any
# selected destination, Home, or Settings control uses the shared Rising gold.
for accent in ("#d8dee9", "#9c7bff", "#66a8ff", "#c5a6ff", "#73dfbf"):
    assert accent in app_source
assert "st-key-bottom_nav_calendar\"] { --nav-card-accent: #d8dee9" in app_source
assert "--nav-card-accent" in app_source
assert "button[kind=\"primary\"]" in app_source
assert "button[kind=\"secondary\"]" in app_source
assert "background: linear-gradient(135deg, #3d2f0a 0%, #6b5015 55%, #221804 100%) !important;" in app_source
assert "border-color: #f7d25c !important;" in app_source
assert "@keyframes lunatick-nav-active-arrival" in app_source
assert "animation: lunatick-nav-active-arrival 760ms" in app_source
assert "button:active" in app_source
assert "transform: scale(0.92) !important;" in app_source
assert 'if page_name in ("Community", "Journal", "Tones")' in app_source
assert "@media (min-width: 769px)" in app_source
assert "bottom: 2.625rem;" in app_source
assert ".stAppViewContainer:has([data-testid=\"stSidebar\"][aria-expanded=\"true\"]) .st-key-lunatick-bottom-nav" in app_source
assert "left: 18.75rem;" in app_source
assert "st-key-bottom_nav_tones button" in app_source
assert "word-break: keep-all !important;" in app_source
assert "@media (prefers-reduced-motion: reduce)" in app_source

# The fixed contextual Help component must remain out of normal page flow.
assert "Fixed contextual Help control" in app_source
assert "st-key-lunatick-page-help-button" in app_source
assert "st-key-lunatick-page-help-popover" in app_source
assert "PAGE_HELP_GUIDES =" in app_source
assert "def render_page_help(page_name: str)" in app_source
assert "render_page_help(current_page)" in app_source
assert "z-index: 1000001 !important;" in app_source
assert "right: calc(1.25rem + env(safe-area-inset-right)) !important;" in app_source
assert "[data-testid=\"stButton\"] button" in app_source
assert "max-height: calc(100dvh - 10.25rem - env(safe-area-inset-bottom))" in app_source

assert "import auth" in cards_source
assert "def render_profile_hub" in cards_source
assert "_render_trade_initiation(user_hash)" not in cards_source[cards_source.index("def render_cosmic_cards_tab"): ]
assert "CARD_MODULE_VERSION = \"profile_menu_visible_v4\"" in cards_source

assert '"Message board": "board_post"' in moderation_source
assert '"Live chat": "chat_message"' in moderation_source
assert "Talk posts" not in moderation_source
assert "Talk comments" not in moderation_source
