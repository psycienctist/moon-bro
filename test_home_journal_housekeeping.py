"""Regression guard for approved Home simplification and private free-writing Journal."""

from pathlib import Path

app_source = Path("app.py").read_text(encoding="utf-8")
journal_source = Path("journal.py").read_text(encoding="utf-8")
home_source = app_source.split("def render_home():", 1)[1].split("def render_tones():", 1)[0]

# Home remains limited to its approved factual cards and Moon-in-sign display.
assert "import daily_reflection" not in app_source
assert 'getattr(journal_ui, "JOURNAL_MODULE_VERSION", None) != "private_freewrite_v1"' in app_source
assert "2026 Cosmic Calendar" not in home_source
assert "render_daily_reflection" not in home_source
assert "vibe-card" not in home_source
assert "event-item" not in home_source
assert "DEEPSEEK AI INSIGHT" not in home_source
assert "FORECAST" not in home_source
assert "☾ MOON IN ENERGY" not in home_source
assert "YOUR COSMIC MOON COMPANION" not in home_source
assert "AI + I = All. Always." not in home_source
assert "Moon in {current['moon_sign']}" in home_source
assert "st.html(LUNATICK_CSS)" in app_source
assert "margin-bottom: 0.5rem;\n        box-shadow: 0 10px 30px rgba(31, 111, 235, 0.1);" in app_source
assert "margin: 0 0 0.5rem;" in app_source

# Journal is private free writing, not a reflection, prompt, chart, or badge product.
assert 'JOURNAL_MODULE_VERSION = "private_freewrite_v1"' in journal_source
assert "A private place for your own words." in journal_source
assert "Write freely" in journal_source
assert "Save entry" in journal_source
assert "Your saved entries" in journal_source
assert "Only you can see what you save here." in journal_source
for retired_surface in (
    "daily_reflection",
    "reflection_ui",
    "PROMPTS",
    "prompt_mode",
    "Phase Reflection",
    "Chart Resonance",
    "Mooned",
    "Moon Lit",
    "Moonwalker",
    "Over the Moon",
    "journal_practice",
    "current_phase",
):
    assert retired_surface not in journal_source

print("Home simplification and private free-writing Journal checks passed.")
