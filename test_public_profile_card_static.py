"""Static privacy and presentation checks for featured Community profile cards."""

from pathlib import Path

community_source = Path("community.py").read_text(encoding="utf-8")
card_source = Path("cosmic_cards.py").read_text(encoding="utf-8")
store_source = Path("supabase_store.py").read_text(encoding="utf-8")
app_source = Path("app.py").read_text(encoding="utf-8")

# Community keeps the existing public identity profile and then renders only
# the compact feature-card return value. It must not name any private input.
assert 'featured_card = cosmic_cards.build_public_card_by_username(profile["username"])' in community_source
assert "compact=True" in community_source
assert "render_collectible_card(" in community_source
for forbidden in ("birth_date", "birth_time", "birth_place", "latitude", "longitude", "auth_subject", "email"):
    assert forbidden not in community_source, forbidden

# The server-side resolver may access inputs only in order to convert them
# through shareable_card before returning to the renderer.
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
assert "Save Cosmic Card privacy" in app_source
assert 'COMMUNITY_MODULE_VERSION = "public_profile_card_v1"' in community_source
assert 'getattr(community, "COMMUNITY_MODULE_VERSION", None) != "public_profile_card_v1"' in app_source

print("Public-profile Cosmic Card privacy and compact-render checks passed.")
