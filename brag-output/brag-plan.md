# Brag Plan: Overcut.ai

## What is this app?
A multimethod telemetry diagnostics platform: you drag a window over 100 Hz Formula 1 waveforms or EV battery-pack telemetry and it returns a structured, precedent-grounded engineering diagnosis — DTC code, severity, cited evidence — from a 7B QLoRA model running on the laptop in front of you.

## The angle
The brag is a race-control telemetry film: a waveform anomaly becomes a signed engineering dossier. No generic AI optimism — the product's own promise is specific ("Drag a window on a 100Hz waveform and get a structured engineering diagnosis grounded in retrieved precedent"), and its own UI already looks like mission control. The film follows one anomaly from wire → window → dossier → on-device inference, and lands on the dual-domain idea that one engine serves both a race car and a battery pack.

## Hook (first 2-3 seconds)
A cyan 100 Hz trace draws across pure black. The line dips hard. A selection band drags over the dip and the caption lands: **"Drag a window. Get a diagnosis."** The hook is the motion itself — telemetry being interrogated, not a logo.

## Key moments (the middle)
- **Two machines, one engine.** The real home hero and the real EV pack schematic appear as live UI crops: "Precision Diagnostics. At Race Speed." on the left, a MOD-3 cell sag flagged `−340mV` on the right.
- **The dossier assembles.** Severity HIGH, DTC `P0A80`, confidence 65%, root cause, three evidence rows, and FAISS precedent matches stack in one by one like a signed report — then the DTC stamp lands on a strong cue.
- **On device.** `7B QLoRA` / `5.47 GB` measured resident / `8 GB laptop GPU` — the measured local footprint, not a cloud promise.

## Outro / punchline
Wordmark slam `OVERCUT.AI` with the diagonal overcut slash, tagline holds: **"Precision Diagnostics. At Race Speed."** Then `overcut.ai` in mono, fade to black.

## User flow worth showing
1. An anomaly appears in a 100 Hz waveform (entry).
2. The analyst drags a selection window over the sag (key action) — the real interaction the hero copy describes.
3. A structured dossier returns: severity, DTC, confidence, cited evidence, precedent matches (result).

## Tone
- Preset: `polished`
- Creative direction: race-control telemetry film — the anomaly becomes a signed dossier
- Interpretation: confident, restrained, precise. Fast motion and hard cuts, but every line holds long enough to read. No jokes, no hype words; the product's own vocabulary does the bragging.

## Format: landscape — 1920x1080
## Duration: 20 seconds

## Visual identity (from the project)
- Background: `#030507` (`--bg-floor`), surfaces `#080C10` / `#0D1218`
- Accent: `#00D4FF` cyan (`--accent`); F1 signal `#E8FF00`; EV signal `#00FF88`; severity `#FF6B35` / `#FF3366`
- Text: `#EEF6FC` bright, `#D4E4F0` primary, `#9AB0C4` secondary, `#6B8299` muted
- Display font: Space Grotesk (700); body: Inter; labels: JetBrains Mono (uppercase, tracked)
- Strongest visual element: the cyan telemetry grid + hero constellation on black, and the EV pack schematic with the MOD-3 fault flag and `Vsag -340mV` callout

## Share copy (draft)
One diagnostic engine for F1 telemetry and EV battery packs — 7B QLoRA, 5.47 GB of VRAM, diagnosis grounded in retrieved precedent. Drag a window. Get a diagnosis.

## Audio direction
- Role: steady professional bed with a few precise accents
- Music: `happy-beats-business-moves-vol-12-by-ende-dot-app.mp3` (clean, steady, 109.96 BPM)
- Music treatment: start at 0.0, fade in over 0.6 s, bed at 0.32, fade out 19.2–20.0 s; no ducking
- Music cue guidance: bundled preset `cues/happy-beats-business-moves-vol-12-by-ende-dot-app.music-cues.json`; strong-cue locks at 8.74 s (dossier stamp), 13.11 s (measured VRAM stat), 17.47 s (tagline); beat grid for dossier rows 6.56 / 7.09 / 7.64 / 8.19 s and wordmark at 16.38 s
- Audio-reactive treatment: subtle; music RMS may breathe background grid glow and wordmark halo only. No equalizer/waveform visuals.
- SFX posture: sparse; motion-matched; professional restraint (3-4 cues total)
- Audio-coupled moments: selection drag tick, evidence row landings, dossier stamp, wordmark landing, tagline bell
- Restraint rule: no impacts under the hook line; never compete with the bed; nothing louder than the tagline cue

## Storyboard

### Scene 1 — Anomaly in the wire — 3.2s
Black `#030507` with a faint telemetry grid. A cyan 100 Hz trace draws left→right (0.1→1.0 s). At 1.35 s the trace sags sharply; the dip region tints toward severity orange. A translucent cyan selection band drags across the sag (1.5→2.0 s) with a thin dashed border and `100 Hz` mono label. Caption lands at 0.8 s and holds to the cut: **"Drag a window. Get a diagnosis."** (bright white, Space Grotesk 700; "Get a diagnosis." in cyan).
Sequential/interaction: yes — simulated drag of the selection band over the sag
Audio intent: quiet tension, the bed arrives with the trace
Audio-coupled idea: subtle selection tick as the band closes
Music: vol-12 bed, low
Transition mood: hard cut → Scene 2

### Scene 2 — Two machines — 3.2s
Two real UI crops slide in: at 3.25 s the actual home hero ("Precision" / cyan "Diagnostics." / "At Race Speed.") as the left panel with a faint cyan wash; at 4.15 s the actual EV landing pack schematic as the right panel with a green wash and the `−340mV` MOD-3 callout visible. A thin center seam separates them; mono tags `FORMULA 1 · 100 Hz` and `EV FLEET · NASA PCoE`. Headline lands at 4.9 s: **"One engine. Two machines."**
Sequential/interaction: yes — two panels arrive in sequence
Audio intent: the product's breadth lands; panels feel placed, not thrown
Audio-coupled idea: soft panel landing accents, one per panel
Music: bed continues
Transition mood: soft wipe → Scene 3

### Scene 3 — The dossier — 5.0s
A dossier panel modeled on the product's Diagnostic Dossier modal (surface `#080C10`, border `#243040`, mono doc-ref line `OVERCUT-DOSSIER-EV-MOD3`). Header: `DIAGNOSTIC DOSSIER`. Left column: severity chip **HIGH** (orange), DTC **P0A80** in mono, confidence **65%** ring (`0.65 Confidence Gate`). Right/below: `Root Cause Determination` with the project's own label **"Hybrid/EV Battery Pack Cell Module Degraded"**; three evidence rows land one by one at 6.56 / 7.09 / 7.64 s — `Vsag −340 mV`, `MOD-3`, `HIGH THERMAL LOAD`. At 8.74 s (strong cue) the DTC stamp and `GROUNDED IN RETRIEVED PRECEDENT` line land. A narrow strip shows three FAISS precedent rows with cosine-similarity values (0.94, 0.91, 0.87) appearing at 8.2–8.7 s.
Sequential/interaction: yes — evidence rows and precedent strip appear one by one
Audio intent: assembly clicks build to one authoritative stamp
Audio-coupled idea: row landings, then one soft impact on the stamp
Music: bed continues
Transition mood: clean rise → Scene 4

### Scene 4 — On device — 3.5s
Full black. Mono label `LOCAL INFERENCE`. Huge **7B QLoRA** (cyan) at 11.6 s. At 13.11 s (strong cue) **5.47 GB** lands with the sub-label `measured resident VRAM`; at 13.64 s **8 GB laptop GPU** in mono. A thin horizontal line draws under the numbers; no charts, no bars.
Sequential/interaction: yes — three readings arrive in sequence
Audio intent: quiet confidence; this is the proof beat
Audio-coupled idea: counter/landing ticks on each reading
Music: bed continues
Transition mood: hard cut → Scene 5

### Scene 5 — Wordmark — 5.1s
Black. The `OVERCUT.AI` wordmark (the app's real header glyph: diamond-O mono mark + Space Grotesk wordmark) lands at 16.38 s. Tagline lands at 17.47 s (strong cue): **"Precision Diagnostics. At Race Speed."** with "Diagnostics." in cyan. Below, mono `overcut.ai`. Hold to 19.6 s, fade to black.
Sequential/interaction: none
Audio intent: land the film, then let the bed fall away
Audio-coupled idea: soft bell on the tagline, music fades under it
Music: fade out 19.2–20.0
Transition mood: fade to black (end)

**Music mood for this video:** steady, clean, professional (polished)
**Audio summary:** a quiet bed carries a single telemetry anomaly through hard cuts to a stamped dossier, then a brief on-device proof beat and a restrained logo landing.
