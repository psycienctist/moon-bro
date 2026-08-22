"""Regression guard for the approved Home and Journal housekeeping pass."""

from pathlib import Path

app_source = Path("app.py").read_text(encoding="utf-8")
journal_source = Path("journal.py").read_text(encoding="utf-8")
home_source = app_source.split("def render_home():", 1)[1].split("def render_tones():", 1)[0]

assert "import daily_reflection as reflection_ui" not in app_source
assert 'getattr(journal_ui, "JOURNAL_MODULE_VERSION", None) != "daily_reflection_v1"' in app_source
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
assert "import daily_reflection as reflection_ui" in journal_source
assert 'JOURNAL_MODULE_VERSION = "daily_reflection_v1"' in journal_source
assert "reflection_ui.render_daily_reflection()" in journal_source
assert journal_source.index("reflection_ui.render_daily_reflection()") < journal_source.index("prompt_mode = st.radio")

print("Home simplification and Journal reflection relocation checks passed.")
