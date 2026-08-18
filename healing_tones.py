"""A small, dependency-free Web Audio API tone generator for Lunatick."""

import streamlit.components.v1 as components


TONE_GENERATOR_HTML = r"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    :root {
      color-scheme: dark;
      --ink: #05070a;
      --panel: #0d111b;
      --panel-raised: #151b2a;
      --line: rgba(188, 140, 255, 0.32);
      --line-soft: rgba(255, 255, 255, 0.10);
      --text: #edf2ff;
      --muted: #99a4bb;
      --violet: #bc8cff;
      --violet-light: #ddc8ff;
      --blue: #58a6ff;
      --mint: #92e4bb;
      --rose: #ff8aa8;
    }

    * { box-sizing: border-box; }

    body {
      background: transparent;
      color: var(--text);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      margin: 0;
    }

    .tone-space {
      background:
        radial-gradient(circle at 92% 6%, rgba(88, 166, 255, 0.18), transparent 25rem),
        radial-gradient(circle at 8% 94%, rgba(188, 140, 255, 0.16), transparent 20rem),
        linear-gradient(145deg, #10182a 0%, #090d16 58%, #17102a 100%);
      border: 1px solid var(--line);
      border-radius: 1.2rem;
      box-shadow: 0 0 32px rgba(110, 64, 201, 0.18), inset 0 0 28px rgba(0, 0, 0, 0.20);
      overflow: hidden;
      padding: clamp(1rem, 4vw, 1.45rem);
    }

    .eyebrow {
      color: var(--violet);
      font-size: 0.67rem;
      font-weight: 800;
      letter-spacing: 0.18em;
      margin-bottom: 0.35rem;
      text-transform: uppercase;
    }

    h1 {
      font-family: Orbitron, Inter, sans-serif;
      font-size: clamp(1.22rem, 4vw, 1.55rem);
      letter-spacing: 0.07em;
      margin: 0;
      text-transform: uppercase;
    }

    .intro {
      color: var(--muted);
      font-size: 0.88rem;
      line-height: 1.5;
      margin: 0.55rem 0 1.15rem;
    }

    .section-label {
      color: var(--muted);
      display: block;
      font-size: 0.66rem;
      font-weight: 800;
      letter-spacing: 0.10em;
      margin-bottom: 0.48rem;
      text-transform: uppercase;
    }

    .presets {
      display: grid;
      gap: 0.5rem;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      margin-bottom: 1rem;
    }

    button, input, select { font: inherit; }

    .preset,
    .action {
      border: 1px solid var(--line-soft);
      border-radius: 0.75rem;
      color: var(--text);
      cursor: pointer;
      transition: background 140ms ease, border-color 140ms ease, transform 140ms ease;
    }

    .preset {
      background: rgba(255, 255, 255, 0.045);
      min-height: 3.45rem;
      padding: 0.55rem 0.65rem;
      text-align: left;
    }

    .preset:hover,
    .preset:focus-visible {
      border-color: var(--violet);
      outline: none;
      transform: translateY(-1px);
    }

    .preset[aria-pressed="true"] {
      background: rgba(188, 140, 255, 0.17);
      border-color: var(--violet);
    }

    .preset-name {
      display: block;
      font-size: 0.78rem;
      font-weight: 750;
    }

    .preset-frequency {
      color: var(--muted);
      display: block;
      font-size: 0.66rem;
      margin-top: 0.14rem;
    }

    .controls {
      display: grid;
      gap: 0.85rem;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      margin: 0.7rem 0 1rem;
    }

    .control { min-width: 0; }

    select,
    input[type="number"] {
      background: var(--panel-raised);
      border: 1px solid var(--line-soft);
      border-radius: 0.62rem;
      color: var(--text);
      min-height: 2.45rem;
      padding: 0.35rem 0.55rem;
      width: 100%;
    }

    input[type="range"] {
      accent-color: var(--violet);
      cursor: pointer;
      width: 100%;
    }

    .volume-line {
      align-items: center;
      display: flex;
      gap: 0.45rem;
    }

    output {
      color: var(--violet-light);
      font-size: 0.75rem;
      font-variant-numeric: tabular-nums;
      min-width: 2.6rem;
      text-align: right;
    }

    .mode-toggle {
      display: flex;
      background: var(--panel-raised);
      border: 1px solid var(--line-soft);
      border-radius: 0.75rem;
      overflow: hidden;
      margin-bottom: 1rem;
    }

    .mode-toggle button {
      flex: 1;
      border: none;
      background: transparent;
      color: var(--muted);
      padding: 0.35rem 0;
      font-weight: 700;
      font-size: 0.75rem;
      cursor: pointer;
      transition: all 0.2s ease;
    }

    .mode-toggle button.active {
      background: var(--violet);
      color: #fff;
      box-shadow: 0 0 12px rgba(188, 140, 255, 0.4);
    }

    .actions {
      display: grid;
      gap: 0.65rem;
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .action {
      font-size: 0.86rem;
      font-weight: 800;
      min-height: 2.7rem;
      padding: 0.55rem 0.7rem;
    }

    .start {
      background: linear-gradient(135deg, #7841c7, #aa70f0);
      border-color: var(--violet);
    }

    .start:hover,
    .start:focus-visible {
      background: linear-gradient(135deg, #8e5cde, #c18bff);
      outline: none;
    }

    .stop {
      background: rgba(255, 138, 168, 0.08);
      border-color: rgba(255, 138, 168, 0.38);
    }

    .stop:hover:not(:disabled),
    .stop:focus-visible:not(:disabled) {
      background: rgba(255, 138, 168, 0.16);
      outline: none;
    }

    button:disabled {
      cursor: not-allowed;
      opacity: 0.48;
    }

    .status {
      color: var(--muted);
      font-size: 0.78rem;
      line-height: 1.45;
      margin: 0.85rem 0 0;
      min-height: 1.15rem;
    }

    .status[data-state="playing"] { color: var(--mint); }
    .status[data-state="error"] { color: var(--rose); }

    .note {
      color: #72809b;
      font-size: 0.67rem;
      line-height: 1.42;
      margin: 0.45rem 0 0;
    }

    @media (max-width: 360px) {
      .controls { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <main class="tone-space" aria-labelledby="tones-title">
    <div class="eyebrow">Lunatick sound space</div>
    <h1 id="tones-title">Healing tones</h1>
    <p class="intro">Choose a tone, set a gentle listening level, and take a moment for yourself.</p>

    <span class="section-label">Tone presets</span>
    <div class="presets" aria-label="Tone presets">
      <button class="preset" type="button" data-frequency="174" aria-pressed="false">
        <span class="preset-name">Earth</span><span class="preset-frequency">174 Hz</span>
      </button>
      <button class="preset" type="button" data-frequency="285" aria-pressed="false">
        <span class="preset-name">Tide</span><span class="preset-frequency">285 Hz</span>
      </button>
      <button class="preset" type="button" data-frequency="432" aria-pressed="true">
        <span class="preset-name">Moon</span><span class="preset-frequency">432 Hz</span>
      </button>
      <button class="preset" type="button" data-frequency="528" aria-pressed="false">
        <span class="preset-name">Starlight</span><span class="preset-frequency">528 Hz</span>
      </button>
      <button class="preset" type="button" data-frequency="639" aria-pressed="false">
        <span class="preset-name">Heart</span><span class="preset-frequency">639 Hz</span>
      </button>
      <button class="preset" type="button" data-frequency="741" aria-pressed="false">
        <span class="preset-name">Clear</span><span class="preset-frequency">741 Hz</span>
      </button>
    </div>

    <!-- Mode Toggle -->
    <div class="mode-toggle" role="group" aria-label="Audio mode">
      <button id="mode-standard" class="active">Standard</button>
      <button id="mode-binaural">Binaural (Headphones)</button>
    </div>

    <div class="controls">
      <div class="control">
        <label class="section-label" for="frequency">Base frequency</label>
        <input id="frequency" type="number" min="100" max="1000" step="1" value="432" inputmode="numeric">
      </div>
      <div class="control" id="beat-control" style="display: none;">
        <label class="section-label" for="beat">Beat frequency (Hz)</label>
        <input id="beat" type="number" min="0" max="20" step="0.01" value="7.83" inputmode="decimal">
      </div>
      <div class="control">
        <label class="section-label" for="waveform">Waveform</label>
        <select id="waveform">
          <option value="sine">Sine — soft</option>
          <option value="triangle">Triangle — warm</option>
          <option value="sawtooth">Sawtooth — bright</option>
        </select>
      </div>
      <div class="control">
        <label class="section-label" for="volume">Listening volume</label>
        <div class="volume-line">
          <input id="volume" type="range" min="0" max="18" value="6" step="1" aria-describedby="volume-value">
          <output id="volume-value" for="volume">6%</output>
        </div>
      </div>
    </div>

    <div class="actions">
      <button id="start" class="action start" type="button">Start tone</button>
      <button id="stop" class="action stop" type="button" disabled>Stop tone</button>
    </div>

    <p id="status" class="status" role="status" aria-live="polite" data-state="idle">Ready — Moon is selected at 432 Hz.</p>
    <p class="note">For personal relaxation only. This feature is not medical treatment or a substitute for professional care.</p>
  </main>

  <script>
    (() => {
      const AudioContextClass = window.AudioContext || window.webkitAudioContext;
      const presetButtons = [...document.querySelectorAll(".preset")];
      const frequencyInput = document.getElementById("frequency");
      const beatInput = document.getElementById("beat");
      const waveform = document.getElementById("waveform");
      const volume = document.getElementById("volume");
      const volumeValue = document.getElementById("volume-value");
      const startButton = document.getElementById("start");
      const stopButton = document.getElementById("stop");
      const status = document.getElementById("status");
      const modeStandard = document.getElementById("mode-standard");
      const modeBinaural = document.getElementById("mode-binaural");
      const beatControl = document.getElementById("beat-control");

      let audioContext = null;
      let leftOsc = null;
      let rightOsc = null;
      let leftGain = null;
      let rightGain = null;
      let selectedFrequency = 432;
      let isBinaural = false;
      let beatFrequency = 7.83;

      function setStatus(message, state = "idle") {
        status.textContent = message;
        status.dataset.state = state;
      }

      function selectedPresetName() {
        const selected = presetButtons.find(button => button.getAttribute("aria-pressed") === "true");
        return selected ? selected.querySelector(".preset-name").textContent : "Custom";
      }

      function currentGain() {
        return Number(volume.value) / 100;
      }

      function setPlayingUI(isPlaying) {
        startButton.disabled = isPlaying;
        stopButton.disabled = !isPlaying;
      }

      function updateVolumeLabel() {
        volumeValue.textContent = `${volume.value}%`;
      }

      function stopTone() {
        const now = audioContext ? audioContext.currentTime : 0;

        if (leftOsc) {
          leftGain.gain.cancelScheduledValues(now);
          leftGain.gain.setValueAtTime(Math.max(leftGain.gain.value, 0), now);
          leftGain.gain.linearRampToValueAtTime(0, now + 0.10);
          leftOsc.stop(now + 0.11);
          leftOsc = null;
          leftGain = null;
        }
        if (rightOsc) {
          rightGain.gain.cancelScheduledValues(now);
          rightGain.gain.setValueAtTime(Math.max(rightGain.gain.value, 0), now);
          rightGain.gain.linearRampToValueAtTime(0, now + 0.10);
          rightOsc.stop(now + 0.11);
          rightOsc = null;
          rightGain = null;
        }

        setPlayingUI(false);
        setStatus("Tone stopped. Ready when you are.");
      }

      async function startTone() {
        if (!AudioContextClass) {
          setStatus("This browser does not support the Web Audio API.", "error");
          return;
        }

        try {
          if (!audioContext || audioContext.state === "closed") {
            audioContext = new AudioContextClass();
          }
          if (audioContext.state === "suspended") {
            await audioContext.resume();
          }

          // Stop existing tones if any
          if (leftOsc || rightOsc) {
            stopTone();
            // Wait a brief moment for cleanup
            await new Promise(r => setTimeout(r, 100));
          }

          // Create oscillators based on mode
          if (isBinaural) {
            // Left channel (Base frequency)
            leftOsc = audioContext.createOscillator();
            leftGain = audioContext.createGain();
            const leftPanner = audioContext.createStereoPanner();
            leftPanner.pan.value = -1; // Fully left

            leftOsc.type = waveform.value;
            leftOsc.frequency.setValueAtTime(selectedFrequency, audioContext.currentTime);

            leftGain.gain.setValueAtTime(0, audioContext.currentTime);
            leftGain.gain.linearRampToValueAtTime(currentGain(), audioContext.currentTime + 0.12);

            leftOsc.connect(leftGain);
            leftGain.connect(leftPanner);
            leftPanner.connect(audioContext.destination);
            leftOsc.start();

            // Right channel (Base + Beat frequency)
            const rightFreq = selectedFrequency + beatFrequency;
            rightOsc = audioContext.createOscillator();
            rightGain = audioContext.createGain();
            const rightPanner = audioContext.createStereoPanner();
            rightPanner.pan.value = 1; // Fully right

            rightOsc.type = waveform.value;
            rightOsc.frequency.setValueAtTime(rightFreq, audioContext.currentTime);

            rightGain.gain.setValueAtTime(0, audioContext.currentTime);
            rightGain.gain.linearRampToValueAtTime(currentGain(), audioContext.currentTime + 0.12);

            rightOsc.connect(rightGain);
            rightGain.connect(rightPanner);
            rightPanner.connect(audioContext.destination);
            rightOsc.start();

            // Cleanup handlers
            leftOsc.onended = () => { leftOsc = null; };
            rightOsc.onended = () => { rightOsc = null; };

            setPlayingUI(true);
            setStatus(`Binaural: ${selectedPresetName()} (${selectedFrequency}Hz + ${beatFrequency}Hz beat)`, "playing");
          } else {
            // Standard mono mode
            leftOsc = audioContext.createOscillator();
            leftGain = audioContext.createGain();

            leftOsc.type = waveform.value;
            leftOsc.frequency.setValueAtTime(selectedFrequency, audioContext.currentTime);

            leftGain.gain.setValueAtTime(0, audioContext.currentTime);
            leftGain.gain.linearRampToValueAtTime(currentGain(), audioContext.currentTime + 0.12);

            leftOsc.connect(leftGain);
            leftGain.connect(audioContext.destination);
            leftOsc.start();

            leftOsc.onended = () => { leftOsc = null; };

            setPlayingUI(true);
            setStatus(`Playing ${selectedPresetName()} at ${selectedFrequency} Hz.`, "playing");
          }
        } catch (error) {
          console.error("Unable to start tone", error);
          leftOsc = null;
          rightOsc = null;
          setPlayingUI(false);
          setStatus("The tone could not start. Check browser audio permissions and try again.", "error");
        }
      }

      function updateActiveFrequency() {
        const rawValue = Number(frequencyInput.value);
        selectedFrequency = Math.min(1000, Math.max(100, Number.isFinite(rawValue) ? rawValue : 432));
        frequencyInput.value = selectedFrequency;

        if (isBinaural && leftOsc && rightOsc && audioContext) {
          leftOsc.frequency.cancelScheduledValues(audioContext.currentTime);
          leftOsc.frequency.setTargetAtTime(selectedFrequency, audioContext.currentTime, 0.03);
          rightOsc.frequency.cancelScheduledValues(audioContext.currentTime);
          rightOsc.frequency.setTargetAtTime(selectedFrequency + beatFrequency, audioContext.currentTime, 0.03);
          setStatus(`Binaural: ${selectedPresetName()} (${selectedFrequency}Hz + ${beatFrequency}Hz beat)`, "playing");
        } else if (leftOsc && audioContext) {
          leftOsc.frequency.cancelScheduledValues(audioContext.currentTime);
          leftOsc.frequency.setTargetAtTime(selectedFrequency, audioContext.currentTime, 0.03);
          setStatus(`Playing ${selectedPresetName()} at ${selectedFrequency} Hz.`, "playing");
        } else {
          setStatus(`Ready — ${selectedPresetName()} is selected at ${selectedFrequency} Hz.`);
        }
      }

      function updateBeat() {
        const rawValue = Number(beatInput.value);
        beatFrequency = Math.min(20, Math.max(0, Number.isFinite(rawValue) ? rawValue : 7.83));
        beatInput.value = beatFrequency;

        if (isBinaural && leftOsc && rightOsc && audioContext) {
          rightOsc.frequency.cancelScheduledValues(audioContext.currentTime);
          rightOsc.frequency.setTargetAtTime(selectedFrequency + beatFrequency, audioContext.currentTime, 0.03);
          setStatus(`Binaural: ${selectedPresetName()} (${selectedFrequency}Hz + ${beatFrequency}Hz beat)`, "playing");
        } else {
          setStatus(`Binaural mode ready. Beat set to ${beatFrequency} Hz.`);
        }
      }

      function clearPresetSelection() {
        presetButtons.forEach(button => button.setAttribute("aria-pressed", "false"));
      }

      // Preset Buttons
      presetButtons.forEach(button => {
        button.addEventListener("click", () => {
          selectedFrequency = Number(button.dataset.frequency);
          frequencyInput.value = selectedFrequency;
          presetButtons.forEach(item => item.setAttribute("aria-pressed", String(item === button)));
          updateActiveFrequency();
        });
      });

      // Mode Toggle
      modeStandard.addEventListener("click", () => {
        isBinaural = false;
        modeStandard.classList.add("active");
        modeBinaural.classList.remove("active");
        beatControl.style.display = "none";
        if (leftOsc || rightOsc) {
          stopTone();
        }
        setStatus("Standard mode. Select a frequency.");
      });

      modeBinaural.addEventListener("click", () => {
        isBinaural = true;
        modeBinaural.classList.add("active");
        modeStandard.classList.remove("active");
        beatControl.style.display = "block";
        if (leftOsc || rightOsc) {
          stopTone();
        }
        setStatus(`Binaural mode. Beat set to ${beatFrequency} Hz.`);
      });

      frequencyInput.addEventListener("change", updateActiveFrequency);
      beatInput.addEventListener("change", updateBeat);
      
      waveform.addEventListener("change", () => {
        if (leftOsc) leftOsc.type = waveform.value;
        if (rightOsc) rightOsc.type = waveform.value;
      });

      volume.addEventListener("input", () => {
        updateVolumeLabel();
        const currentGainValue = currentGain();
        if (leftGain && audioContext) {
          leftGain.gain.cancelScheduledValues(audioContext.currentTime);
          leftGain.gain.setTargetAtTime(currentGainValue, audioContext.currentTime, 0.025);
        }
        if (rightGain && audioContext) {
          rightGain.gain.cancelScheduledValues(audioContext.currentTime);
          rightGain.gain.setTargetAtTime(currentGainValue, audioContext.currentTime, 0.025);
        }
      });

      startButton.addEventListener("click", startTone);
      stopButton.addEventListener("click", stopTone);

      window.addEventListener("pagehide", () => {
        if (leftOsc) { try { leftOsc.stop(); } catch (_) {} }
        if (rightOsc) { try { rightOsc.stop(); } catch (_) {} }
        if (audioContext && audioContext.state !== "closed") {
          audioContext.close();
        }
      });
    })();
  </script>
</body>
</html>
"""

def render_healing_tones() -> None:
    """Render the embedded, client-side tone generator."""
    components.html(TONE_GENERATOR_HTML, height=680, scrolling=False)