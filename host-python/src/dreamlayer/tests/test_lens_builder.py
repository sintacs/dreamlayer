"""test_lens_builder.py — the no-code browser lens builder (INNOVATION Category 1).

Two guarantees that matter:
  1. the builder's JS budget constants stay in lockstep with the Python source of
     truth (reality_compiler/v2/figment.py) — no silent drift;
  2. a figment the browser builder produces is accepted by the *real* Python
     budget gate — so "valid in the browser" means valid on the glasses.
Also runs the JS self-test under Node when Node is present.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from dreamlayer.reality_compiler.v2 import figment as F
from dreamlayer.reality_compiler.v2.budgets import verify
from dreamlayer.reality_compiler.v2.figment import Figment

LENS = Path(__file__).resolve().parents[4] / "landing" / "assets" / "lens"
JS = LENS / "figment.js"


def _js_const(name: str) -> float:
    """Pull `NAME: <number>` out of the JS budget block."""
    import re
    m = re.search(rf"\b{name}\s*:\s*([0-9.]+)", JS.read_text())
    assert m, f"{name} not found in figment.js"
    return float(m.group(1))


def test_js_budgets_match_the_python_source():
    for name, py in [
        ("MAX_SCENES", F.MAX_SCENES), ("MAX_COUNTERS", F.MAX_COUNTERS),
        ("MAX_LINES", F.MAX_LINES), ("MAX_TEXT_LEN", F.MAX_TEXT_LEN),
        ("MAX_PULSE_HZ", F.MAX_PULSE_HZ), ("MIN_SCENE_SEC", F.MIN_SCENE_SEC),
        ("MAX_NAME_LEN", F.MAX_NAME_LEN), ("MAX_BRANCHES", F.MAX_BRANCHES),
    ]:
        assert _js_const(name) == float(py), f"{name} drifted: JS {_js_const(name)} vs py {py}"


def test_js_palette_tokens_match():
    text = JS.read_text()
    for tok in F.COLOR_TOKENS:
        assert f'"{tok}"' in text, f"palette token {tok} missing from figment.js"


@pytest.mark.skipif(not shutil.which("node"), reason="node not installed")
class TestUnderNode:
    def test_selftest_passes(self):
        r = subprocess.run(["node", "figment.selftest.js"], cwd=LENS,
                           capture_output=True, text=True)
        assert r.returncode == 0, r.stderr

    @pytest.mark.parametrize("recipe", ["interval", "countdown", "checklist", "breathing"])
    def test_a_browser_built_figment_passes_the_real_gate(self, recipe):
        # dump the template the browser would emit, load it with the real
        # Figment, and run the real budget verifier — the strongest parity check
        out = subprocess.run(
            ["node", "-e",
             f"console.log(JSON.stringify(require('./figment.js').templates.{recipe}()))"],
            cwd=LENS, capture_output=True, text=True)
        assert out.returncode == 0, out.stderr
        data = json.loads(out.stdout)
        fig = Figment.from_dict(data)
        report = verify(fig)
        assert report.ok, f"{recipe} rejected by the real gate: {report.violations}"


# -- the Brain import endpoint (Deploy to my Brain) ---------------------------

class TestBrainImport:
    def _brain(self, tmp_path):
        from dreamlayer.ai_brain.server import Brain
        return Brain(tmp_path)

    def _figment_dict(self):
        f = Figment(name="Imported", initial="a")
        f.add_scene(F.Scene(id="a", duration_sec=10.0,
                            lines=[F.TextLine("HI", row=0)],
                            on_timeout=[F.Transition(target=F.END)]))
        return f.to_dict()

    def test_import_verifies_signs_and_deploys(self, tmp_path):
        brain = self._brain(tmp_path)
        out = brain.rc_import(self._figment_dict())
        assert out["ok"] is True and out["safety"]["ok"] is True
        assert brain._rc_active == out["id"]              # on stage now

    def test_import_rejects_a_non_figment(self, tmp_path):
        brain = self._brain(tmp_path)
        assert brain.rc_import({"nonsense": True})["ok"] is False

    def test_import_rechecks_the_proof(self, tmp_path):
        brain = self._brain(tmp_path)
        bad = self._figment_dict()
        bad["scenes"]["a"]["pulse"] = {"window_sec": 5, "rate_hz": 99.0,
                                       "color": "accent_attention"}
        out = brain.rc_import(bad)
        assert out["ok"] is False                          # the Brain re-checks; 99Hz is out


# -- the builder page itself --------------------------------------------------

def test_builder_page_is_wired():
    page = (LENS.parents[1] / "lens-builder.html").read_text(encoding="utf-8")
    assert "assets/lens/figment.js" in page          # loads the logic module
    assert "This behavior <b>CANNOT</b>" in page or "This behavior" in page
    assert "/dreamlayer/rc/import" in page            # deploy hits the real endpoint
    assert "X-DreamLayer-Token" in page               # sends the Brain token
