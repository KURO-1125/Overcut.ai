---
title: Overcut API
emoji: "\U0001F3CE"
colorFrom: gray
colorTo: green
sdk: gradio
python_version: "3.11"
app_file: app.py
pinned: false
---

# Overcut.ai API Space

Serves the Overcut.ai FastAPI gateway (CPU heuristic tier) on port 7860 with a
small Gradio page at `/ui`. The dashboard is deployed separately and points at
this Space with `VITE_API_URL=https://<user>-<space>.hf.space`.

Variables to set in Space settings:

- `OVERCUT_CORS_ORIGINS` — the dashboard origin, e.g. `https://overcut.vercel.app`
- optional `OVERCUT_API_KEY` (dashboard then needs `VITE_API_KEY`)
- JWT signing defaults to `SPACE_SIGNING_SECRET`, so demo sessions survive restarts

First start downloads OpenCLIP weights (~350 MB) and took 200 s on a cold CPU
container; allow a few minutes on the first request. Free Spaces sleep when idle
and re-run `app.py` on wake, which re-clones the repository to `/tmp`.
