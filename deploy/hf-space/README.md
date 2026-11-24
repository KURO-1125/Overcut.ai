---
title: Overcut API
emoji: ⚡
colorFrom: green
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
---

# Overcut.ai API (free CPU demo tier)

FastAPI backend for the Overcut.ai telemetry diagnostics workspace.

- No GPU on this tier: `/api/analyze_anomaly` serves the labelled
  `DETERMINISTIC_HEURISTIC` engine, never a VLM claim.
- The first analysis downloads the OpenCLIP ViT-B/32 weights to `/tmp/hf-cache`
  (cold start ~1-2 min), then they persist for the container's lifetime.
- The image is built from https://github.com/KURO-1125/Overcut.ai (public).
  Push changes there, then use **Factory rebuild** in the Space settings.
- Required Space variable: `OVERCUT_CORS_ORIGINS` set to the deployed frontend
  origin (e.g. `https://overcut-ai.vercel.app`).
