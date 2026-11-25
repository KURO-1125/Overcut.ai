"""Hugging Face Gradio Space entry point.

Free personal accounts can host Gradio Spaces (Docker Spaces require PRO), so
this mounts the FastAPI gateway at the root and serves a minimal Gradio page at
/ui. The Space only needs this file, README.md and requirements.txt.
"""

import os
import secrets
import subprocess
import sys

os.environ.setdefault("OVERCUT_ENV", "production")
os.environ.setdefault("OVERCUT_DATA_DIR", "/tmp/overcut-data")
os.environ.setdefault("HF_HOME", "/tmp/hf-cache")
os.environ.setdefault(
    "OVERCUT_JWT_SECRET",
    os.getenv("SPACE_SIGNING_SECRET") or secrets.token_urlsafe(48),
)

SOURCE_DIR = os.getenv("OVERCUT_SRC", "/tmp/overcut-src")
REPO_URL = "https://github.com/KURO-1125/Overcut.ai.git"

if not os.path.isdir(os.path.join(SOURCE_DIR, "backend")):
    subprocess.run(
        ["git", "clone", "--depth", "1", REPO_URL, SOURCE_DIR],
        check=True,
    )
sys.path.insert(0, SOURCE_DIR)

import gradio as gr  # noqa: E402
from backend.api.main import app as api_app  # noqa: E402

with gr.Blocks(title="Overcut.ai API") as ui:
    gr.Markdown(
        "# Overcut.ai API\n\n"
        "This Space serves the Overcut.ai REST gateway. The dashboard is served "
        "separately; open `/api/health` to check `engine_ready`."
    )

api_app = gr.mount_gradio_app(api_app, ui, path="/ui")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(api_app, host="0.0.0.0", port=7860)
