"""Regression checks for the profile-centered Cosmic Cards connection flow."""

from pathlib import Path

card_source = Path("cosmic_cards.py").read_text(encoding="utf-8")
app_source = Path("app.py").read_text(encoding="utf-8")

assert 'CARD_MODULE_VERSION = "profile_hub_direct_messages_v3"' in card_source
assert 'getattr(cosmic_cards, "CARD_MODULE_VERSION", None) != "profile_hub_direct_messages_v3"' in app_source
assert "def render_profile_hub" in card_source
assert "def _render_profile_hub_member" in card_source
assert "def _profile_hub_target_subject" in card_source
assert "get_card_profile_by_username_server_only" in card_source
assert "send_trade(user_hash, target_subject)" in card_source
assert 'st.markdown("<div class=\'profile-hub-kicker\'>Discover and connect' in card_source
assert 'st.caption("Use the profile button in the upper-left corner to find members, connect, and trade Cosmic Cards.")' in card_source
assert "_render_trade_initiation(user_hash)" not in card_source[card_source.index("def render_cosmic_cards_tab"):]
assert "def render_profile_launcher" in app_source
assert 'key="lunatick-profile-button"' in app_source
assert 'st.session_state.nav_page = "Profile"' in app_source
assert 'elif current_page == "Profile":' in app_source

print("Cosmic Cards profile-centered connection checks passed.")
