# Deploying Overcut.ai (free tier)

Current target: **frontend on Vercel + API on a Hugging Face Docker Space**, both
free. The API runs CPU-only, so diagnosis is served by the labelled
`DETERMINISTIC_HEURISTIC` engine; the 7B QLoRA tier stays local until the AWS
migration. Everything here is a placeholder for that move — nothing in the code
is Vercel- or HF-specific.

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

## 2. API — Hugging Face Space (Docker, CPU)

1. huggingface.co → **New Space** → SDK **Docker** → *Blank* → name it
   `overcut-api`. Public is fine (the API has no secrets).
2. Upload the three files from [`deploy/hf-space/`](deploy/hf-space) to the
   Space repo root: `Dockerfile`, `README.md` and `start.sh` (web UI:
   *Files → Add file*, or `git clone` the Space and copy them in).
3. Space **Settings → Variables**:
   - `OVERCUT_CORS_ORIGINS` = `https://<your-vercel-domain>`
   - optional: `OVERCUT_API_KEY` (then also set `VITE_API_KEY` in Vercel — note
     that value is public in the bundle, so it only deters casual scraping)
   - optional: `OVERCUT_JWT_SECRET`. Without it, `start.sh` generates an
     ephemeral secret per container, so demo logins reset on restart.
4. Wait for the build (~5 min verified locally: torch CPU, open_clip, fastf1,
   matplotlib; image 3.76 GB).
5. Health check: `https://<space>.hf.space/api/health` returns
   `{"status":"healthy","engine_ready":true,...}`. Startup loads the OpenCLIP
   weights synchronously — measured **200 s** on a cold container, so expect a
   long first "starting" phase before the port opens; subsequent requests are
   fast.

The Dockerfile clones `main` from GitHub at build time. After pushing backend
changes, open the Space → **Factory rebuild**.

## 3. What works / what does not on the free tier

| Feature | Free tier behaviour |
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
