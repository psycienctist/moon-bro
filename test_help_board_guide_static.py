from pathlib import Path

app_source = Path("app.py").read_text(encoding="utf-8")
boards_source = Path("boards.py").read_text(encoding="utf-8")

assert "linear-gradient(145deg, rgba(18, 27, 53, 0.78), rgba(7, 12, 25, 0.72))" in app_source
assert "backdrop-filter: blur(14px) saturate(125%)" in app_source
assert "background: rgba(40, 26, 76, 0.72)" in app_source
assert "backdrop-filter: blur(8px)" in app_source

assert "PINNED_FEATURE_GUIDE" in boards_source
for phrase in (
    "## Connect · Message Board and Live Chat",
    "## Correct · Binaural Beats",
    "## Inspect · Calendar",
    "## Reflect · Journal",
    "## Collect · Cosmic Cards",
    "## Prospect · Reading Requests",
    "To start a board thread",
    "Newest",
    "Top",
    "Controversial",
    "Voting",
    "11-second tone shift",
    "Private event",
    "free-writing",
    "share-safe chart results",
    "Reading Requests",
    "A simple LunaTicK habit",
):
    assert phrase in boards_source
assert '📌 Pinned LunaTicK Feature Guide' in boards_source
assert 'Correct · Calendar · Journal · Cosmic Cards · Reading Requests' in boards_source
assert 'key="talk-board-feed" if compact else None' in boards_source
assert 'with st.expander("📌 Pinned LunaTicK Feature Guide", expanded=False):' in boards_source
assert boards_source.index('Pinned LunaTicK Feature Guide') > boards_source.index('key="talk-board-feed"')

print("Help translucency and pinned board guide checks passed.")
