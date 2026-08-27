from pathlib import Path


app_source = Path("app.py").read_text(encoding="utf-8")

start = app_source.index("def render_tones():")
end = app_source.index("\ndef render_calendar():", start)
tones_source = app_source[start:end]

# The simplified surface exposes only presets, private base-frequency input,
# listening volume, and playback controls.
assert 'id="waveform"' not in tones_source
assert 'id="cycle-mode"' not in tones_source
assert 'id="speed"' not in tones_source
assert 'id="mode-standard"' not in tones_source
assert 'id="mode-binaural"' not in tones_source
assert 'id="beat"' not in tones_source
assert "Cycle speed" not in tones_source
assert "Waveform" not in tones_source
assert "Standard" not in tones_source
assert "Chakra Sweep" not in tones_source

# Playback always uses the same sine waveform, binaural offset, and cadence.
assert 'const LOCKED_WAVEFORM = "sine";' in tones_source
assert "const BINAURAL_BEAT_HZ = 7.83;" in tones_source
assert "const AUTO_SHIFT_INTERVAL_MS = 11000;" in tones_source
assert "leftOsc.type = LOCKED_WAVEFORM;" in tones_source
assert "rightOsc.type = LOCKED_WAVEFORM;" in tones_source
assert "shiftInterval = setInterval(shiftToNextPreset, AUTO_SHIFT_INTERVAL_MS);" in tones_source
assert "Shifts every 11 seconds." in tones_source

# The short iframe and compact mobile rules leave room above the fixed rail.
assert "components.html(tone_generator_html, height=520, scrolling=False)" in tones_source
assert "@media (max-width: 480px)" in tones_source
assert ".actions {" in tones_source
assert "Listening volume" in tones_source
assert "Start tone" in tones_source
assert "Stop tone" in tones_source
