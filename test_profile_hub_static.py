"""Regression checks for LunaTicK's profile-centered social flow."""

from pathlib import Path

app_source = Path("app.py").read_text(encoding="utf-8")
card_source = Path("cosmic_cards.py").read_text(encoding="utf-8")
chat_source = Path("chat_room.py").read_text(encoding="utf-8")
board_source = Path("boards.py").read_text(encoding="utf-8")

assert 'CARD_MODULE_VERSION = "profile_hub_social_v1"' in card_source
assert 'getattr(cosmic_cards, "CARD_MODULE_VERSION", None) != "profile_hub_social_v1"' in app_source
assert "def render_profile_launcher" in app_source
assert 'key="lunatick-profile-button"' in app_source
assert 'help="Open your profile, find members, and trade Cosmic Cards"' in app_source
assert "left: calc(2rem + env(safe-area-inset-left))" in app_source
assert "elif current_page == \"Profile\":" in app_source
assert "cosmic_cards.render_profile_hub()" in app_source
assert 'st.session_state.nav_page = "Profile"' in app_source
assert 'st.query_params.get("profile", "")' in app_source

assert "def render_profile_hub" in card_source
assert "def _render_profile_hub_member" in card_source
assert "def _render_profile_hub_connections" in card_source
assert "def _profile_hub_target_subject" in card_source
assert "get_card_profile_by_username_server_only" in card_source
assert "send_trade(user_hash, target_subject)" in card_source
assert "public birth inputs" not in card_source[card_source.index("def render_profile_hub"):]
assert "_render_trade_initiation(user_hash)" not in card_source[card_source.index("def render_cosmic_cards_tab"):]

assert 'from urllib.parse import quote' in chat_source
assert 'href=\'?profile={quote(profile_username, safe=\'\')}\'' in chat_source
assert '"profile_username": profiles.get(row["profile_auth_subject"], {}).get("username") or ""' in chat_source
assert 'from urllib.parse import quote' in board_source
assert 'href=\'?profile={quote(profile_username, safe=\'\')}\'' in board_source
assert '"profile_username": profiles.get(row["profile_auth_subject"], {}).get("username") or ""' in board_source

print("Profile hub launcher, discovery, and Community profile-link checks passed.")
