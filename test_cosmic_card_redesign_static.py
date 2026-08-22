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

assert "ascendant = (math.degrees(math.atan2(y, x)) + 180.0) % 360" in source
assert "def shareable_card" in source
assert "def build_friend_card" in source
assert "Your Collection" in source
assert "Add time + coords" in source
assert "use_loc = place.strip()" not in source
assert "actual_coordinates = _has_actual_coordinates(latitude, longitude)" in source
assert 'flex-flow:row nowrap !important;' in source
assert 'width:calc((100% - .84rem) / 3) !important;' in source
for tile_color in ("#f2cc60", "#bc8cff", "#6ee7b7"):
    assert tile_color in source, tile_color
assert 'if not hasattr(cosmic_cards, "shareable_card")' in app_source
assert "cosmic_cards = importlib.reload(cosmic_cards)" in app_source

print("Cosmic Card single-face, six-tile, share-safe, and warm-reload checks passed.")
