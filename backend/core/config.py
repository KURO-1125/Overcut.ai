"""Central runtime configuration for Overcut.ai.

All environment handling lives here so that paths, secrets and feature flags
are resolved once, in a predictable order. Import this module instead of
reading ``os.environ`` directly.
"""

import logging
import os
import secrets
from pathlib import Path

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent.parent


def _load_dotenv(path: Path) -> None:
    """Minimal .env loader (no extra dependency, never overrides real env vars)."""
    if not path.exists():
        return
    try:
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            if key.startswith("export "):
                key = key[len("export "):].strip()
            os.environ.setdefault(key, value.strip().strip('"').strip("'"))
    except OSError as exc:  # pragma: no cover - defensive
        logger.warning("Could not read %s: %s", path, exc)


_load_dotenv(BASE_DIR / ".env")


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        logger.warning("Invalid integer for %s; using %s", name, default)
        return default


ENV = os.getenv("OVERCUT_ENV", "development").strip().lower()
IS_PRODUCTION = ENV == "production"

# ─── Data locations ───────────────────────────────────────────────────────────
# OVERCUT_DATA_DIR lets tests (and deployments) redirect all mutable state
# (FAISS index, SQLite metadata, cached parquet, ROI crops) to a temp directory.
DATA_DIR = Path(os.getenv("OVERCUT_DATA_DIR", str(BASE_DIR / "data"))).resolve()
DB_DIR = DATA_DIR / "db"
ROI_DIR = DATA_DIR / "generated_roi"
CACHE_DIR = DATA_DIR / "raw_cache"
MODELS_DIR = Path(os.getenv("OVERCUT_MODELS_DIR", str(BASE_DIR / "models"))).resolve()

for _directory in (DATA_DIR, DB_DIR, ROI_DIR, CACHE_DIR):
    _directory.mkdir(parents=True, exist_ok=True)

# ─── Security ─────────────────────────────────────────────────────────────────
API_KEY = os.getenv("OVERCUT_API_KEY", "").strip()
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "OVERCUT_CORS_ORIGINS", "http://localhost:3000,http://localhost:5173"
    ).split(",")
    if origin.strip()
]


def _resolve_jwt_secret() -> str:
    secret = os.getenv("OVERCUT_JWT_SECRET", "").strip()
    if secret:
        return secret
    if IS_PRODUCTION:
        raise RuntimeError(
            "OVERCUT_JWT_SECRET must be set when OVERCUT_ENV=production."
        )
    logger.warning(
        "OVERCUT_JWT_SECRET is not set; using an ephemeral development secret. "
        "Sessions will be invalidated on restart."
    )
    return secrets.token_urlsafe(48)


JWT_SECRET = _resolve_jwt_secret()
JWT_ALGO = "HS256"
JWT_EXPIRE_MINUTES = _env_int("OVERCUT_JWT_EXPIRE", 10080)
MONGO_URI = os.getenv("OVERCUT_MONGO_URI", "").strip()

# ─── Model providers ──────────────────────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()

# ─── Compute limits ───────────────────────────────────────────────────────────
# Heavy analyses run in the threadpool; cap how many can run concurrently so a
# public deployment cannot exhaust RAM/GPU with parallel VLM or matplotlib work.
MAX_CONCURRENT_ANALYSES = max(1, _env_int("OVERCUT_MAX_CONCURRENT_ANALYSES", 2))
