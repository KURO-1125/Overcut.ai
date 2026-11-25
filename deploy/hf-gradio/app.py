"""Hugging Face Gradio Space entry point.

Free personal accounts cannot use cpu-basic for Gradio Spaces, so this runs on
ZeroGPU hardware, which in turn requires at least one @spaces.GPU function at
startup. The gateway itself is CPU-only; the GPU function is a small attach
probe exposed on the root page. The Space needs this file, README.md and
requirements.txt.
"""

import os
import secrets
import subprocess
import sys

os.environ.setdefault("OVERCUT_ENV", "production")
os.environ.setdefault("OVERCUT_DATA_DIR", "/tmp/overcut-data")
os.environ.setdefault("HF_HOME", "/tmp/hf-cache")
# The Space injects GRADIO_SSR_MODE=True; Gradio then starts a Node SSR server
# that binds 7860 before our uvicorn can, so it must be off.
os.environ["GRADIO_SSR_MODE"] = "False"
os.environ.setdefault(
    "OVERCUT_JWT_SECRET",
    os.getenv("SPACE_SIGNING_SECRET") or secrets.token_urlsafe(48),
)

SOURCE_DIR = os.getenv("OVERCUT_SRC", "/tmp/overcut-src")
REPO_URL = "https://github.com/KURO-1125/Overcut.ai.git"

try:
    if os.path.isdir(os.path.join(SOURCE_DIR, ".git")):
        # /tmp survives a Space restart, so a restart alone would keep running
        # the previously cloned revision. Fast-forward it to main instead.
        subprocess.run(
            ["git", "-C", SOURCE_DIR, "fetch", "--depth", "1", "origin", "main"],
            check=True,
        )
        subprocess.run(
            ["git", "-C", SOURCE_DIR, "reset", "--hard", "FETCH_HEAD"],
            check=True,
        )
    else:
        subprocess.run(
            ["git", "clone", "--depth", "1", REPO_URL, SOURCE_DIR],
            check=True,
        )
except subprocess.CalledProcessError as exc:
    print(f"[boot] source sync failed, using existing checkout: {exc}", flush=True)
sys.path.insert(0, SOURCE_DIR)

import gradio as gr  # noqa: E402
from backend.api.main import app as api_app  # noqa: E402

try:
    import spaces
except ImportError:
    class _SpacesStub:
        def GPU(self, *args, **kwargs):
            return lambda fn: fn

    spaces = _SpacesStub()


@spaces.GPU(duration=5)
def gpu_probe() -> str:
    import torch

    return f"torch {torch.__version__} · cuda {torch.cuda.is_available()}"


with gr.Blocks(title="Overcut.ai API") as ui:
    gr.Markdown(
        "# Overcut.ai API\n\n"
        "This Space serves the Overcut.ai REST gateway. The dashboard is served "
        "separately; open `/api/health` to check `engine_ready`."
    )
    with gr.Row():
        probe_btn = gr.Button("ZeroGPU attach probe")
        probe_out = gr.Textbox(label="Result", interactive=False)
    probe_btn.click(gpu_probe, outputs=probe_out)

api_app = gr.mount_gradio_app(api_app, ui, path="/")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(api_app, host="0.0.0.0", port=7860)
