"""Static privacy and presentation checks for the shared Profile hub."""

from pathlib import Path

community_source = Path("community.py").read_text(encoding="utf-8")
card_source = Path("cosmic_cards.py").read_text(encoding="utf-8")
store_source = Path("supabase_store.py").read_text(encoding="utf-8")
app_source = Path("app.py").read_text(encoding="utf-8")

# The dedicated profile hub renders a safe public profile, then only a compact
# public-card return value. It must resolve an immutable target server-side.
profile_hub_source = card_source[card_source.index("def _render_profile_hub_member"):card_source.index("def render_cosmic_cards_tab")]
assert "auth.get_public_profile(requested_handle)" in profile_hub_source
assert "_profile_hub_target_subject(username)" in profile_hub_source
assert "public_card = build_public_card_by_username(username)" in profile_hub_source
assert "render_collectible_card(public_card, is_owner=False" in profile_hub_source
assert "compact=True" in profile_hub_source
assert "def _render_profile_summary" in card_source
assert "display_name" in profile_hub_source
assert "username" in profile_hub_source
assert "birth_date" not in profile_hub_source
assert "birth_time" not in profile_hub_source
assert "birth_place" not in profile_hub_source
assert "email" not in profile_hub_source

# The server-side resolver may access inputs only to return a share-safe card.
assert "def build_public_card_by_username" in card_source
assert "get_card_profile_by_username_server_only" in card_source
assert "public_card_values_visible" in card_source
assert 'return _public_card_shell(source, "private")' in card_source
assert 'return _public_card_shell(source, "awaiting")' in card_source
assert "def _render_public_card_state" in card_source
assert "def set_public_card_values_visible" in card_source
assert "def get_card_profile_by_username_server_only" in store_source
assert "public_card_values_visible" in store_source
assert '"Show my cosmic values on my public profile"' in app_source
assert 'key="public_card_values_visible_toggle"' in app_source
assert "if show_public_card_values != current_card_values_visible:" in app_source
assert "set_public_card_values_visible" in app_source
assert "Save Cosmic Card privacy" not in app_source

# Connect remains a compact switcher; linked authors open the shared Profile hub.
assert 'COMMUNITY_MODULE_VERSION = "talk_surface_toggle_v2"' in community_source
assert 'getattr(community, "COMMUNITY_MODULE_VERSION", None) != "talk_surface_toggle_v2"' in app_source
assert 'st.query_params.get("profile", "")' in app_source

print("Public-profile Cosmic Card privacy and shared-profile checks passed.")
