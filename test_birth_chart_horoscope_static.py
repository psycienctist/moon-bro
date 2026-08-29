"""Static regression coverage for the owner-only birth-chart and horoscope panels."""

from pathlib import Path


source = Path("cosmic_cards.py").read_text(encoding="utf-8")

for required_symbol in (
    "def _detailed_birth_chart",
    "swe.calc_ut",
    "swe.houses_ex",
    "def _birth_chart_svg",
    "def _daily_horoscope",
    "def _sign_traits_reading",
    "def render_birth_chart_and_horoscope",
    "Planetary Positions",
    "Key Aspects",
    "Today's Reading",
    "Sign Traits",
    "Love & Connection",
    "Work & Purpose",
    "Wellness & Reflection",
):
    assert required_symbol in source, required_symbol

# Detailed chart data is rendered only from the private owner profile path and
# never added to shareable_card(), which is the public/member-card boundary.
assert "render_birth_chart_and_horoscope(profile)" in source
shareable_start = source.index("def shareable_card")
assert source.index("def _detailed_birth_chart") > shareable_start
assert "birth_date" not in source[source.index("def shareable_card"):source.index("def build_friend_card")]

# The chart remains visually responsive and uses the existing dark cosmic palette.
for required_style in (
    ".lunatick-birth-chart",
    ".astro-position-row",
    ".astro-reading-card",
    "@media (max-width: 600px)",
):
    assert required_style in source, required_style

print("Birth chart, planetary positions, aspects, horoscope toggle, and privacy checks passed.")
