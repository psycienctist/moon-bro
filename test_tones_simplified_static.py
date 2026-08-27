from pathlib import Path


app_source = Path("app.py").read_text(encoding="utf-8")

start = app_source.index("def render_tones():")
end = app_source.index("\ndef render_calendar():", start)
tones_source = app_source[start:end]

# The simplified surface removes waveform and Standard-mode choices, while
# retaining the requested adjustable binaural beat and sequence selection.
assert 'id="waveform"' not in tones_source
assert 'id="speed"' not in tones_source
assert 'id="mode-standard"' not in tones_source
assert 'id="mode-binaural"' not in tones_source
assert "Cycle speed" not in tones_source
assert "Waveform" not in tones_source
assert "Standard" not in tones_source
assert 'id="beat"' in tones_source
assert 'value="7.83"' in tones_source
assert 'id="cycle-mode"' in tones_source
assert '<option value="random">Random</option>' in tones_source
assert '<option value="sweep">Chakra Sweep</option>' in tones_source

# Playback always uses the same sine waveform and an 11-second cadence, while
# the user can choose the binaural beat difference and sequence behavior.
assert 'const LOCKED_WAVEFORM = "sine";' in tones_source
assert "let beatFrequency = 7.83;" in tones_source
assert "const AUTO_SHIFT_INTERVAL_MS = 11000;" in tones_source
assert "leftOsc.type = LOCKED_WAVEFORM;" in tones_source
assert "rightOsc.type = LOCKED_WAVEFORM;" in tones_source
assert "shiftInterval = setInterval(shiftToNextPreset, AUTO_SHIFT_INTERVAL_MS);" in tones_source
assert "cycleModeSelect.value === \"random\"" in tones_source
assert "Chakra Sweep" in tones_source
assert "Shifts every 11 seconds." in tones_source

# The short iframe and compact mobile rules leave room above the fixed rail.
assert "components.html(tone_generator_html, height=520, scrolling=False)" in tones_source
assert "@media (max-width: 480px)" in tones_source
assert ".actions {" in tones_source
assert "Listening volume" in tones_source
assert "Start tone" in tones_source
assert "Stop tone" in tones_source
