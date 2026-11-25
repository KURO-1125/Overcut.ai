---
title: Overcut API
emoji: "\U0001F3CE"
colorFrom: gray
colorTo: green
sdk: gradio
app_file: app.py
pinned: false
---

# Overcut.ai API Space

Serves the Overcut.ai FastAPI gateway (CPU heuristic tier) on port 7860, with a
small Gradio page (including a ZeroGPU attach probe) at the root. The dashboard
is deployed separately and points at this Space with
`VITE_API_URL=https://<user>-<space>.hf.space`.

Notes for this flavor:

- `zero-a10g` hardware is used because free accounts cannot create Gradio Spaces
  on `cpu-basic`; the API itself runs on CPU. ZeroGPU requires at least one
  `@spaces.GPU` function at startup, hence the probe button.
- `GRADIO_SSR_MODE` is forced off in `app.py`; the Space injects it as `True`,
  and the resulting Node SSR server binds port 7860 before uvicorn can.

Variables to set in Space settings:

- `OVERCUT_CORS_ORIGINS` — the dashboard origin, e.g. `https://overcut.vercel.app`
- optional `OVERCUT_API_KEY` (dashboard then needs `VITE_API_KEY`)
- JWT signing defaults to `SPACE_SIGNING_SECRET`, so demo sessions survive restarts

First start downloads the 605 MB OpenCLIP checkpoint (finished in ~1-2 s on the
Space's fast link; the local cold start measured 200 s end to end). Free Spaces
sleep when idle and re-run `app.py` on wake, which re-clones the repository to
`/tmp`.
