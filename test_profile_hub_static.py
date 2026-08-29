"""Regression checks for LunaTicK's profile-centered social flow."""

from pathlib import Path

app_source = Path("app.py").read_text(encoding="utf-8")
card_source = Path("cosmic_cards.py").read_text(encoding="utf-8")
chat_source = Path("chat_room.py").read_text(encoding="utf-8")
board_source = Path("boards.py").read_text(encoding="utf-8")

assert 'CARD_MODULE_VERSION = "birth_chart_horoscope_v1"' in card_source
assert 'getattr(cosmic_cards, "CARD_MODULE_VERSION", None) != "birth_chart_horoscope_v1"' in app_source
assert "def render_profile_launcher" in app_source
assert 'key="lunatick-profile-button"' in app_source
assert 'help="Open your profile, find members, and trade Cosmic Cards"' in app_source
assert "left: calc(2rem + env(safe-area-inset-left))" in app_source
assert "elif current_page == \"Profile\":" in app_source
assert "cosmic_cards.render_profile_hub()" in app_source
assert 'st.session_state.nav_page = "Profile"' in app_source
assert 'st.query_params.get("profile", "")' in app_source

assert "def render_profile_hub" in card_source
assert "def _render_profile_menu" in card_source
assert "def _render_profile_hub_member" in card_source
assert 'with st.popover("☰", help="Open Profile navigation", type="secondary")' in card_source
assert 'with st.expander("☰ Profile menu", expanded=True)' not in card_source
assert '"✎  My Profile · Edit"' in card_source
assert '"♧  My Friends"' in card_source
assert '"✉  My DMs"' in card_source
assert 'st.session_state["profile_hub_section"] = "friends"' in card_source
assert 'st.session_state["profile_hub_section"] = "dms"' in card_source
assert 'direct_messages.render_owner_dm_inbox()' in card_source
assert "def _render_profile_hub_search_form" in card_source
assert 'st.markdown("<div class=\'profile-hub-kicker\'>LunaTic member</div><h2>Member Profile</h2>"' in card_source
assert '"My Profile", key="profile_hub_my_profile"' not in card_source
assert 'st.session_state.pop("profile_hub_lookup", None)' in card_source
assert "if viewing_member:" in card_source
assert 'st.button("← Back", key="profile_hub_back")' not in card_source
assert 'st.button("Edit my profile", key="profile_hub_edit"' not in card_source
assert 'st.button("✎", key="profile_hub_edit", help="Edit your public profile"' in card_source
assert "def _render_profile_hub_connections" in card_source
assert "def _profile_hub_target_subject" in card_source
assert "get_card_profile_by_username_server_only" in card_source
assert "send_trade(user_hash, target_subject)" in card_source
assert "import direct_messages" in card_source
assert "direct_messages.render_member_direct_message(target_subject, profile)" in card_source
assert "def render_member_direct_message" in Path("direct_messages.py").read_text(encoding="utf-8")
assert "Direct messages require an accepted card-trade connection." in Path("supabase_store.py").read_text(encoding="utf-8")
assert "public birth inputs" not in card_source[card_source.index("def render_profile_hub"):]
assert "_render_trade_initiation(user_hash)" not in card_source[card_source.index("def render_cosmic_cards_tab"):]

assert 'from urllib.parse import quote' in chat_source
assert 'href=\'?profile={quote(profile_username, safe=\'\')}\'' in chat_source
assert '"profile_username": profiles.get(row["profile_auth_subject"], {}).get("username") or ""' in chat_source
assert 'from urllib.parse import quote' in board_source
assert 'href=\'?profile={quote(profile_username, safe=\'\')}\'' in board_source
assert '"profile_username": profiles.get(row["profile_auth_subject"], {}).get("username") or ""' in board_source

print("Profile hub launcher, discovery, Community profile-link, and connection-gated message checks passed.")
