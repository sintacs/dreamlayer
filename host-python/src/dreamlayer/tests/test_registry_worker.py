"""test_registry_worker.py — the registry Worker's node self-tests run in CI.

The Worker is JS (Cloudflare), so its logic is exercised by node self-tests
next to it; this drives them through pytest so the hardening (plugin-name
validation, comment XSS-neutralisation, figment-submit shape checks) can't rot.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

API = Path(__file__).resolve().parents[4] / "registry-api"


@pytest.mark.skipif(not shutil.which("node"), reason="node not installed")
@pytest.mark.parametrize("selftest", ["worker.plugins.test.mjs", "worker.figments.test.mjs"])
def test_worker_selftest(selftest):
    r = subprocess.run(["node", selftest], cwd=API, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr or r.stdout


@pytest.mark.skipif(not shutil.which("node"), reason="node not installed")
def test_worker_syntax():
    r = subprocess.run(["node", "--check", "worker.js"], cwd=API, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
