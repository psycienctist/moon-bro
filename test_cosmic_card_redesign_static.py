"""Static regression checks for the approved single-face Cosmic Card redesign."""

from pathlib import Path


source = Path("cosmic_cards.py").read_text(encoding="utf-8")
app_source = Path("app.py").read_text(encoding="utf-8")

# The active experience is a one-face six-field card. Old back/flip pathways
# and unsupported Human Design/rarity mechanics must not return.
for removed_symbol in (
    "render_card_back",
    "show_card_back",
    "🔄 Flip",
    "HD Type",
    "HD Profile",
    "HD Authority",
    "HD Flavor",
    "RARITY_STYLE",
    "def _rarity",
):
    assert removed_symbol not in source, removed_symbol

for required_tile in (
    '"sun"',
    '"moon"',
    '"rising"',
    '"birth_phase"',
    '"full_moons"',
    '"dominant"',
):
    assert required_tile in source, required_tile

assert "swe.houses_ex" in source
assert "_geocode_place" in source
assert "TimezoneFinder" in source
assert "def shareable_card" in source
assert "def build_friend_card" in source
assert "Your Collection" in source
assert "Add coords" in source
assert "Birth city or postal/ZIP code" in source
assert "Confirm the matching birthplace" in source
assert "use_loc = place.strip()" not in source
assert "actual_coordinates = _has_actual_coordinates(latitude, longitude)" not in source
assert "grid-template-columns:repeat(3,minmax(0,1fr))" in source
assert "cosmic-card-tile-label" in source
assert "cosmic-card-tile-symbol" in source
assert "cosmic-card-tile-value" in source
for tile_color in ("#d8dee9", "#66a8ff", "#f7d25c", "#c5a6ff", "#9c7bff", "#73dfbf"):
    assert tile_color in source, tile_color
assert "@media (max-width: 600px)" in source
assert "min-height:82px" in source
assert "def render_profile_hub" in source
assert "_render_trade_initiation(user_hash)" not in source[source.index("def render_cosmic_cards_tab"): ]
assert source.index("render_collectible_card(my_card") < source.index('st.markdown("#### Your Collection")')
assert "cosmic_detail" in source
assert 'CARD_MODULE_VERSION = "birth_chart_horoscope_v1"' in source
for tile_class in ("cosmic-card-tile--sun", "cosmic-card-tile--moon", "cosmic-card-tile--rising", "cosmic-card-tile--birth_phase", "cosmic-card-tile--full_moons", "cosmic-card-tile--dominant"):
    assert tile_class in source, tile_class
assert 'getattr(cosmic_cards, "CARD_MODULE_VERSION", None) != "birth_chart_horoscope_v1"' in app_source
assert "cosmic_cards = importlib.reload(cosmic_cards)" in app_source

print("Cosmic Card single-face, six-tile, share-safe, and warm-reload checks passed.")
