"""Shared test bootstrap.

The environment must be redirected *before* any ``backend`` module is imported,
because paths, secrets and engine settings are resolved once at import time.
"""

import os
import shutil
import tempfile

_TEST_DATA_DIR = tempfile.mkdtemp(prefix="overcut-test-data-")
os.environ["OVERCUT_DATA_DIR"] = _TEST_DATA_DIR
os.environ["OVERCUT_ENV"] = "test"
os.environ.setdefault("OVERCUT_JWT_SECRET", "test-only-secret-not-used-in-production")
os.environ.pop("OVERCUT_API_KEY", None)
os.environ.pop("GEMINI_API_KEY", None)

import pytest


@pytest.fixture(scope="session", autouse=True)
def _cleanup_test_data_dir():
    yield
    shutil.rmtree(_TEST_DATA_DIR, ignore_errors=True)
