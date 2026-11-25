# Deploying Overcut.ai

Two-part deployment: **frontend on Vercel Hobby (free)** and the **API as a
Docker image**, currently targeted at a Hugging Face Docker Space but
host-agnostic. The API runs CPU-only, so diagnosis is served by the labelled
`DETERMINISTIC_HEURISTIC` engine; the 7B QLoRA tier stays local until the AWS
migration.

> **Cost note (verified 2026-11-25).** Vercel Hobby is free. On Hugging Face, a
> free account cannot create a Gradio Space on `cpu-basic`: the Hub refuses it
> with HTTP 402 ("hosting Gradio and Docker Spaces on free cpu-basic requires a
> PRO subscription"). Free accounts can still create Gradio Spaces on
> **ZeroGPU** (`zero-a10g`, up to 2 per account), which is the route in §2 and
> the one deployed live. Docker Spaces remain PRO-only (§2b).

## 1. Frontend — Vercel

1. vercel.com → **Add New → Project** → import `KURO-1125/Overcut.ai`.
2. Root Directory: `frontend`. Framework preset: **Vite** (build `npm run build`,
   output `dist/` are auto-detected).
3. Environment variable (Production):
   - `VITE_API_URL` = `https://<your-space-subdomain>.hf.space`
     (Vite bakes it at build time; redeploy after changing it.)
4. Deploy, then note the production domain, e.g. `https://overcut-ai.vercel.app`.

No rewrites are needed: the app routes in state, so every URL serves
`index.html`.

## 2. API — HF Space (Gradio SDK, ZeroGPU, free) — deployed

Files live in [`deploy/hf-gradio/`](deploy/hf-gradio). The entry point mounts the
FastAPI gateway at `/` and serves a small Gradio page (with a GPU attach probe,
which ZeroGPU requires) alongside it.

```
hf repos create <user>/overcut-api --type space --sdk gradio --public --flavor zero-a10g
hf upload <user>/overcut-api deploy/hf-gradio . --type space
hf spaces wait <user>/overcut-api --timeout 15m
```

Three ZeroGPU constraints are handled in `app.py` / `requirements.txt`:

| Constraint | Handling |
| :--- | :--- |
| ZeroGPU refuses torch builds other than 2.8–2.13 | torch/torchvision are not pinned; the runtime's preinstalled pair is used |
| ZeroGPU refuses to start without a `@spaces.GPU` function | `gpu_probe()` button on the root page (never called by the API) |
| The Space injects `GRADIO_SSR_MODE=True`; Gradio's Node SSR server binds 7860 before uvicorn | `os.environ["GRADIO_SSR_MODE"] = "False"` before importing gradio |

Also note: the image ships Gradio 6 (starlette ≥ 1.0), so fastapi/uvicorn/
pydantic/httpx are left unpinned here — `backend/requirements.txt` pins are older.

Set in Space **Settings → Variables** (optional; the API currently reflects any
origin):

- `OVERCUT_CORS_ORIGINS` = `https://<your-vercel-domain>`
- `OVERCUT_API_KEY` (then also `VITE_API_KEY` in Vercel; the bundle is public, so
  this only deters casual scraping)
- JWT signing defaults to `SPACE_SIGNING_SECRET`, so demo logins survive restarts

First start downloads the 605 MB OpenCLIP checkpoint (seconds on the Space's
link) and warms the FAISS store. Verified 2026-11-25 on
`kuro1125-overcut-api.hf.space`: `/api/health` → `{"status":"healthy",
"engine_ready":true}`; `POST /api/demo` → 200 in **6.3 s** with
`provider: DETERMINISTIC_HEURISTIC` and a served PNG crop.

Free ZeroGPU Spaces sleep when idle (48 h timer), re-clone the repo to `/tmp` on
wake, and have a daily ZeroGPU quota — the API itself never uses the GPU, so the
quota only covers the probe button.

**F1 data on datacenter hosts.** Checked 2026-11-25 in the Space's logs:
fastf1 falls back to `livetiming-mirror.fastf1.dev`, which answers "No data for
this session!" for requests from the Space, so `/api/telemetry/stream` serves
the synthetic generator instead of real session telemetry. The response now
carries `"simulated": true`, the timeline renders a `SIMULATED FEED` badge, and
the generator applies a deterministic per-driver offset/scale (seeded by car
number) so each driver's trace is distinct. EV telemetry is generated on the
server in both environments.

## 2b. API — HF Docker Space (paid alternative)

Requires HF PRO. Use [`deploy/hf-space/`](deploy/hf-space): SDK **Docker**, blank,
name `overcut-api`, upload `Dockerfile`, `README.md`, `start.sh`, set the same
variables, wait ~5 min for the build (torch CPU, open_clip, fastf1, matplotlib;
image 3.76 GB). The Dockerfile clones `main` from GitHub at build time, so a
**Factory rebuild** ships backend changes. Health and startup behave as in §2.

## 3. Hosting options and cost (re-verified 2026-11-25)

| Option | Cost | Notes |
| :--- | :--- | :--- |
| Vercel Hobby (frontend) | Free | Static hosting; the app works without the API, labelling data `SIMULATED` |
| HF Gradio Space on ZeroGPU | Free (up to 2 Spaces) | **Live route.** `cpu-basic` is refused on free accounts (HTTP 402); ZeroGPU requires torch 2.8–2.13, a `@spaces.GPU` function and SSR mode disabled — all handled in `deploy/hf-gradio/` |
| HF Docker Space, CPU Basic | HF PRO (paid) | Configs in `deploy/hf-space/` build and smoke-test cleanly; 2 vCPU / 16 GB; sleeps when idle; set `OVERCUT_JWT_SECRET` = `SPACE_SIGNING_SECRET` (stable across restarts) |
| Render free web service | Free | 512 MB RAM, spins down when idle — too small for torch + OpenCLIP, would need a heuristic-only image |
| Local backend + Cloudflare quick tunnel | Free, no account | Public HTTPS URL while the laptop runs; URL changes per start; fine for a live demo |
| AWS (App Runner / ECS Fargate; EC2 `g5` for the local 7B tier) | Pending credits | Same Docker image; only `VITE_API_URL` and `OVERCUT_CORS_ORIGINS` change |

### What works on any CPU host

| Feature | Behaviour |
| :--- | :--- |
| Landing pages, workspaces, chart interactions | Fully static on Vercel |
| Telemetry streams | Served by the API's synthetic generators |
| Execute Diagnosis | Heuristic engine, provider `DETERMINISTIC_HEURISTIC` |
| 7B QLoRA local tier | Not available (no GPU); UI label shows the active provider |
| FAISS precedent cards | Empty until `python scripts/generate_baseline.py` seeds the index (the dossier still renders without them) |
| Cold start | Space sleeps after inactivity; startup (CLIP load) measured at 200 s, then diagnosis is ~1 s |

## 4. Moving to AWS later

The same image runs unchanged on ECS/Fargate with GPU-less heuristics, or on a
`g5`/`g6` instance with the local adapter mounted at
`models/adapters/overcut-ev-7b-lora` for real local inference. Only two env
values change: `VITE_API_URL` (Vercel/CloudFront origin → ALB/API URL) and
`OVERCUT_CORS_ORIGINS`.
