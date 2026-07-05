"""test_plugin_install_real.py — installing a catalogue plugin actually runs.

The phone used to POST a bare {name} and optimistically show "installed", but
the Brain has no wired registry, so install(name) always failed — the plugin
never ran. The phone now sideloads the real package (manifest + source); this
proves the Brain validates and installs it, including the mesh-capability
plugin the store advertises but the Brain used to reject.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from dreamlayer.ai_brain.server import Brain

# repo_root/registry/packages/*.json
_PKG_DIR = Path(__file__).resolve().parents[4] / "registry" / "packages"


def _pkg(name: str) -> dict:
    return json.loads((_PKG_DIR / name).read_text())


def test_registry_packages_present():
    assert _PKG_DIR.is_dir(), f"missing {_PKG_DIR}"
    assert (_PKG_DIR / "hud-reactions-0.1.0.json").exists()


def test_brain_grants_mesh_and_shop(tmp_path):
    caps = Brain(tmp_path).plugin_capabilities()
    assert "mesh" in caps and "shop" in caps


def test_sideload_mesh_plugin_installs(tmp_path):
    """hud-reactions requires ['cards','mesh'] — the store advertises it, so the
    Brain must be able to install it."""
    b = Brain(tmp_path)
    pkg = _pkg("hud-reactions-0.1.0.json")
    r = b.install_plugin({"manifest": pkg["manifest"], "source": pkg["source"],
                          "grant": pkg["manifest"]["requires"]})
    assert r["ok"], r.get("errors")
    names = [p["name"] for p in r["state"]["installed"]]
    assert "hud-reactions" in names


def test_install_by_bare_name_is_honest(tmp_path):
    """A name alone can't install on the Brain (no wired registry) — it fails
    cleanly rather than silently doing nothing."""
    b = Brain(tmp_path)
    r = b.install_plugin({"name": "hud-reactions", "version": "0.1.0"})
    assert r["ok"] is False and r["errors"]


@pytest.mark.parametrize("fname", [p.name for p in sorted(_PKG_DIR.glob("*.json"))]
                         if _PKG_DIR.is_dir() else [])
def test_every_catalogue_package_installs(tmp_path, fname):
    """Every shipped package validates + installs on a Brain (no plugin the
    store lists is un-installable)."""
    b = Brain(tmp_path)
    pkg = _pkg(fname)
    r = b.install_plugin({"manifest": pkg["manifest"], "source": pkg["source"],
                          "grant": pkg["manifest"]["requires"]})
    assert r["ok"], (fname, r.get("errors"))


def test_install_over_http(tmp_path):
    import threading, urllib.request
    from dreamlayer.ai_brain.server.server import make_brain_server
    b = Brain(tmp_path)
    srv = make_brain_server(b, host="127.0.0.1", port=7805)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    tok = b.config.token
    pkg = _pkg("hud-reactions-0.1.0.json")

    def call(path, body):
        data = json.dumps(body).encode()
        req = urllib.request.Request("http://127.0.0.1:7805" + path, data=data, method="POST")
        req.add_header("Content-Type", "application/json")
        if tok:
            req.add_header("X-DreamLayer-Token", tok)
        return json.loads(urllib.request.urlopen(req).read())

    try:
        r = call("/dreamlayer/plugins/install",
                 {"manifest": pkg["manifest"], "source": pkg["source"]})
        assert r["ok"], r.get("errors")
    finally:
        srv.shutdown()
