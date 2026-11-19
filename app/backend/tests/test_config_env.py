"""Config .env anchoring (audit SH-1).

The app must read .env from the CODE location (leg root / backend dir),
never from the process CWD: running the server from the wrong directory
used to silently lose the NVIDIA key. These tests assert the anchor
without ever printing a secret value — only booleans and schemes.
"""
import os
import subprocess
import sys

import pytest

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_env_files_are_absolute_and_point_at_leg_root():
    from app.core.config import _ENV_FILES, _LEG_ROOT, _BACKEND_DIR

    # The anchor entries are absolute paths derived from __file__; the
    # bare ".env" (CWD, lowest precedence) is intentionally still there.
    assert str(_LEG_ROOT / ".env") in _ENV_FILES
    assert str(_BACKEND_DIR / ".env") in _ENV_FILES
    assert os.path.isabs(str(_LEG_ROOT / ".env"))
    assert os.path.isabs(str(_BACKEND_DIR / ".env"))


def test_key_loads_from_unrelated_cwd():
    """Import the config from /tmp: the leg-root .env must still be found.

    Depends on the trial key being present in opencode/.env (it is, while
    the key is installed); if the key is revoked the test fails loudly
    instead of silently passing with an empty key.
    """
    code = (
        "from app.core.config import settings;"
        "print('KEY_LOADED', bool(settings.NVIDIA_API_KEY));"
        "print('DB_IS_SQLITE', settings.DATABASE_URL.startswith('sqlite'))"
    )
    env = dict(os.environ, PYTHONPATH=BACKEND_DIR)
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd="/tmp", env=env, capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, result.stderr
    assert "KEY_LOADED True" in result.stdout, result.stdout
    # The leg .env ships postgresql+asyncpg, but asyncpg is not installed:
    # config must fall back to sqlite (loudly) instead of crashing.
    assert "DB_IS_SQLITE True" in result.stdout, result.stdout
