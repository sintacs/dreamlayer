"""test_packs.py — Earcon & Haptic Packs (INNOVATION_SESSION 1.5): the store's
sensory gate. A pack reskins the platform's feel; the gate enforces the rules
from haptics.ts so the phone can trust any pack it loads."""
from __future__ import annotations

import json

from dreamlayer import cli
from dreamlayer.plugins.packs import validate_pack


def _good_pack():
    return {
        "name": "Analog",
        "haptics": {
            "confirm": [{"at": 0}, {"at": 120}],   # 120ms span, ok
            "answer_ahead": [],                     # silent by design
        },
        "earcons": {
            "listen": ["listen1.mp3", "listen2.mp3"],   # ≥2 → rotation
        },
    }


def test_good_pack_passes():
    ok, reasons = validate_pack(_good_pack())
    assert ok and reasons == []


def test_pattern_over_400ms_is_rejected():
    pack = _good_pack()
    pack["haptics"]["confirm"] = [{"at": 0}, {"at": 450}]
    ok, reasons = validate_pack(pack)
    assert not ok and any("450ms" in r for r in reasons)


def test_answer_ahead_must_stay_silent():
    pack = _good_pack()
    pack["haptics"]["answer_ahead"] = [{"at": 0}]
    ok, reasons = validate_pack(pack)
    assert not ok and any("silent" in r for r in reasons)


def test_single_variant_earcon_family_breaks_rotation():
    pack = _good_pack()
    pack["earcons"]["listen"] = ["only.mp3"]
    ok, reasons = validate_pack(pack)
    assert not ok and any("rotation" in r for r in reasons)


def test_nameless_pack_rejected():
    pack = _good_pack()
    pack["name"] = ""
    ok, reasons = validate_pack(pack)
    assert not ok and any("name" in r for r in reasons)


def test_cli_validates_a_pack(tmp_path, capsys):
    p = tmp_path / "pack.json"
    p.write_text(json.dumps(_good_pack()), encoding="utf-8")
    assert cli.main(["packs", "validate", str(p)]) == 0
    assert "passes the sensory gate" in capsys.readouterr().out


def test_cli_flags_a_bad_pack(tmp_path, capsys):
    bad = _good_pack()
    bad["haptics"]["confirm"] = [{"at": 999}]
    p = tmp_path / "bad.json"
    p.write_text(json.dumps(bad), encoding="utf-8")
    assert cli.main(["packs", "validate", str(p)]) == 1
    assert "failed the sensory gate" in capsys.readouterr().out
