# Hyperframes Composition Brief: Overcut.ai

## Objective
Create a 20-second polished launch-style brag video for Overcut.ai, a dual-domain telemetry diagnostics platform (F1 + EV battery).

## Output
- Composition directory: `brag-output/composition/`
- Rendered video: `brag-output/brag.mp4`
- Format: landscape — 1920x1080
- Duration: 20 seconds

## Source Material
- Project root: `C:\Users\ydeep\Desktop\Overcut.ai`
- Primary files read: `frontend/src/index.css` (design tokens), `frontend/src/components/HomePage.jsx` (hero copy + stats), `frontend/src/components/EVLandingPage.jsx` (EV copy + stats), `frontend/src/components/DiagnosticDossierModal.jsx` (dossier structure), `README.md` (measured benchmark), `frontend/index.html` (title/description)
- Product name: Overcut.ai
- Tagline / strongest claim: "Precision Diagnostics. At Race Speed." / "Drag a window on a 100Hz waveform and get a structured engineering diagnosis grounded in retrieved precedent."
- Key UI or visual moment to recreate:
  - The real EV landing pack schematic (captured screenshot `assets/ui/ev-landing.png`): 4 modules, MOD-3 flagged, `Vsag -340mV`, `HIGH THERMAL LOAD - MOD-3`, green EV signal.
  - The real home hero (captured screenshot `assets/ui/home-hero.png`): "Precision Diagnostics. At Race Speed." with cyan constellation.
  - The Diagnostic Dossier modal structure: severity, confidence %, root cause determination, FAISS precedent matches with cosine similarity.
- Copy that must appear verbatim:
  - "Precision Diagnostics. At Race Speed."
  - "Hybrid/EV Battery Pack Cell Module Degraded"
  - "Vsag −340mV", "MOD-3", "HIGH THERMAL LOAD"
  - "7B QLoRA", "5.47 GB", "8 GB laptop GPU"
  - "P0A80", "65%"
  - "Drag a window. Get a diagnosis."
  - "One engine. Two machines."
  - "overcut.ai"

## Creative Direction
- Tone preset: polished
- Creative direction: race-control telemetry film — the anomaly becomes a signed dossier
- Interpretation: confident and precise. Fast cuts, restrained copy, generous holds. No hype language, no abstract filler; the product's own UI and vocabulary carry the film.
- Angle: follow one anomaly from wire to selection window to stamped dossier to on-device inference, then land on the dual-domain idea.
- Hook: cyan 100 Hz trace sags; a selection band drags over it; "Drag a window. Get a diagnosis."
- Outro / punchline: wordmark + "Precision Diagnostics. At Race Speed." + overcut.ai
- Avoid:
  - Generic SaaS language
  - Abstract filler visuals (particle systems, equalizers, fake dashboards not in the product)
  - Unrelated visual redesign — use the app's exact tokens, fonts and UI crops

## Visual Identity
- Background: `#030507`; surfaces `#080C10` / `#0D1218`; borders `#1A2535` / `#243040`
- Text: `#EEF6FC` / `#D4E4F0` / `#9AB0C4` / `#6B8299`
- Accent: `#00D4FF` cyan; F1 `#E8FF00`; EV `#00FF88`; severity high `#FF6B35`, critical `#FF3366`
- Display font: Space Grotesk 700; body Inter; labels JetBrains Mono uppercase with 0.12em tracking
- Visual references from the project: telemetry grid background, hero constellation rings, EV pack schematic with sag callout, dossier card with mono doc ref, severity chips

## Storyboard
Use `brag-output/brag-plan.md` as the creative contract.

Scene summary:
1. Anomaly in the wire — 3.2s — trace draws, sags, selection band drags; "Drag a window. Get a diagnosis."
2. Two machines — 3.2s — real home hero + real EV schematic crop in sequence; "One engine. Two machines."
3. The dossier — 5.0s — severity HIGH, DTC P0A80, 65%, root cause title, evidence rows, FAISS matches; stamp at 8.74s.
4. On device — 3.5s — "7B QLoRA", "5.47 GB" at 13.11s, "8 GB laptop GPU"; mono "measured resident VRAM".
5. Wordmark — 5.1s — OVERCUT.AI at 16.38s, tagline at 17.47s, overcut.ai, fade to black.

## Audio
- Audio role: steady professional bed with sparse precise accents
- Audio arc: bed enters with the trace, stays level, one stamp accent, one quiet proof beat, tagline bell, bed falls away at 19.2s
- Music: `assets/music/happy-beats-business-moves-vol-12-by-ende-dot-app.mp3` (109.96 BPM, CC BY 4.0, Sascha Ende)
- Music treatment: fade in 0–0.6s, data-volume ~0.32, fade out 19.2–20.0s, no ducking
- Music cue guidance: bundled preset `C:\Users\ydeep\.agents\skills\brag\assets\music\cues\happy-beats-business-moves-vol-12-by-ende-dot-app.music-cues.json`. Strong-cue locks: 8.74s dossier stamp, 13.11s VRAM stat, 17.47s tagline. Beat grid: dossier evidence rows 6.56 / 7.09 / 7.64 / 8.19s; wordmark 16.38s. Treat as hints; readability wins.
- Audio-reactive treatment: subtle; use RMS to breathe the background grid glow and the wordmark halo. No waveform/equalizer visuals.
- Audio-coupled moments:
  - Scene 1 selection band close — soft selection tick
  - Scene 3 evidence rows — card/row landing sounds; one soft impact on the DTC stamp at 8.74s
  - Scene 4 stats — light landing ticks
  - Scene 5 tagline — restrained bell at 17.47s; bed fades under it
- SFX selection guidance: `C:\Users\ydeep\.agents\skills\brag\assets\sfx\sfx-analysis.md`; prefer low high-frequency-risk files; polished restraint (3-4 cues total, volumes 0.55–0.7)
- Exact SFX choice: choose filenames, timestamps and density after the animation exists.
- Audio files: copy chosen music and SFX into `brag-output/composition/assets/`

## Hyperframes Instructions
Load the composition-building Hyperframes skills (`hyperframes`, `hyperframes-registry`, `media-use`, `hyperframes-cli`). Skip the `hyperframes` storyline step: no `references/types/*` or `references/story.md`, no `SPEC.md`. This brief and the brag plan replace them, including the LOOK line. Skip `usage`, `history`, `feedback`, REVIEW.md; `check` is the gate. Do not route into the generic launch-video workflow.

Requirements:
- Show the real UI: the two captured screenshots in `brag-output/assets/ui/` must appear (cropped/scaled is fine, not necessarily full-frame).
- Recreate the dossier faithfully from `DiagnosticDossierModal.jsx` structure (labels, severity chip, confidence, FAISS strip).
- Keep all text readable in the final render.
- Total runtime 20.0s, hard bound 15–25s.
- Include the planned music/SFX layer.
- Major reveals may lock to the listed strong cues within ±0.15s; mark beat locks.
- Run `npx hyperframes check` before render; render to `brag-output/brag.mp4`.
- Keep creation and rendering local.
