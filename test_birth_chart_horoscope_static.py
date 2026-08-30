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
assert "st.markdown(_birth_chart_svg(chart), unsafe_allow_html=True)" in source
collect_start = source.index("def render_cosmic_cards_tab")
chart_call = source.index("render_birth_chart_and_horoscope(profile)", collect_start)
card_render = source.index("render_collectible_card(my_card", collect_start)
card_gate = source.index("if not my_card:", chart_call)
assert card_render < chart_call < card_gate

assert "Your private birth chart will appear here after you save a birth date in Collect." in source
assert "the chart could not be calculated yet" in source
shareable_start = source.index("def shareable_card")
assert source.index("def _detailed_birth_chart") > shareable_start
assert "birth_date" not in source[source.index("def shareable_card"):source.index("def build_friend_card")]

# The SVG port preserves the Emergent component's geometry and visual vocabulary.
for required_geometry in (
    "outer_r = view_size * 0.465",
    "sign_r = view_size * 0.39",
    "track_r = view_size * 0.30",
    "inner_r = view_size * 0.14",
    "for degree in range(0, 360, 5)",
    "for i in range(12)",
    "r='10' fill='{item['color']}' opacity='0.15'",
    "r='5' fill='{item['color']}' opacity='0.9'",
    "birthChartCenterGlow",
    "birthChartOuterGlow",
    "stroke-dasharray='4,3'",
    "stroke-dasharray='6,3'",
    "center_label = sun[\"sign_symbol\"]",
):
    assert required_geometry in source, required_geometry

# The chart remains visually responsive and uses the existing dark cosmic palette.
for required_style in (
    ".lunatick-birth-chart",
    ".astro-position-row",
    ".astro-reading-card",
    "@media (max-width: 600px)",
):
    assert required_style in source, required_style

print("Birth chart, planetary positions, aspects, horoscope toggle, and privacy checks passed.")
