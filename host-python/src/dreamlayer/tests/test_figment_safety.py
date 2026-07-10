"""test_figment_safety.py — proof-carrying behaviors (INNOVATION_SESSION 3.2):
`dreamlayer figment safety` renders the budget proof as a human "this CANNOT…"
card the host shows before you consent."""
from __future__ import annotations

import json

from dreamlayer import cli
from dreamlayer.reality_compiler.v2 import RealityCompilerV2
from dreamlayer.reality_compiler.v2.figment import PulseSpec
from dreamlayer.reality_compiler.v2.safety import safety_card


def _valid_fig():
    rc = RealityCompilerV2()
    s = rc.rehearse("Rolling rounds")
    s.double_tap()
    s.say("rolling - three minutes")
    s.say("last ten seconds, pulse")
    s.say("then it starts again")
    return s.finish().figment


def _write(fig, tmp_path, name="fig.json"):
    p = tmp_path / name
    p.write_text(json.dumps(fig.to_dict()), encoding="utf-8")
    return p


def test_safety_card_lists_hard_guarantees():
    card = safety_card(_valid_fig())
    assert card["ok"] is True
    joined = " ".join(card["cannot"]).lower()
    assert "kill switch" in joined and "network" in joined and "pulse" in joined


def test_cli_prints_the_cannot_card(tmp_path, capsys):
    p = _write(_valid_fig(), tmp_path)
    rc = cli.main(["figment", "safety", str(p)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "This behavior CANNOT:" in out and "kill switch" in out
    assert "not a promise" in out


def test_cli_json(tmp_path, capsys):
    p = _write(_valid_fig(), tmp_path)
    assert cli.main(["figment", "safety", str(p), "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["ok"] and data["cannot"] and data["proof"]["scenes"] >= 1


def test_cli_flags_a_violator(tmp_path, capsys):
    fig = _valid_fig()
    fig.scenes[next(iter(fig.scenes))].pulse = PulseSpec(window_sec=2.0, rate_hz=9.0)
    p = _write(fig, tmp_path, "bad.json")
    rc = cli.main(["figment", "safety", str(p)])
    out = capsys.readouterr().out
    assert rc == 1 and "FAILS the sandbox" in out


def test_cli_rejects_non_figment(tmp_path, capsys):
    p = tmp_path / "nope.json"
    p.write_text('{"nope": true}', encoding="utf-8")
    assert cli.main(["figment", "safety", str(p)]) == 2
    assert "not a figment" in capsys.readouterr().err
