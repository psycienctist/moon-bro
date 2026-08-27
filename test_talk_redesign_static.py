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
assert "feed_height = 175 if compact else 275" in boards_source
assert "st.container(height=feed_height, border=True)" in boards_source

assert 'BOARD_MODULE_VERSION", None) != "compact_feed_v1"' in app_source
assert "boards = importlib.reload(boards)" in app_source
assert 'COMMUNITY_MODULE_VERSION", None) != "talk_surface_toggle_v2"' in app_source
assert "import lunatick_talk_ui" not in app_source
assert "import lunatick_talk_db" not in app_source
assert "talk_db.seed_talk_posts" not in app_source
assert "moderation.render_moderation_console()" in app_source
assert "CARD_MODULE_VERSION\", None) != \"accurate_ascendant_zip_location_v2\"" in app_source

assert "import auth" in cards_source
assert "def _render_trade_profile_lookup" in cards_source
assert "with st.popover(\"🤝 Trade Cards\")" in cards_source
assert "CARD_MODULE_VERSION = \"accurate_ascendant_zip_location_v2\"" in cards_source

assert '"Message board": "board_post"' in moderation_source
assert '"Live chat": "chat_message"' in moderation_source
assert "Talk posts" not in moderation_source
assert "Talk comments" not in moderation_source
