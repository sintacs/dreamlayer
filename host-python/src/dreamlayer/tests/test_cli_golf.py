"""test_cli_golf.py — `dreamlayer golf verify`: the compiler referees a figment
(budgets must pass to be eligible) and scores its expressiveness per byte
(INNOVATION_SESSION 1.3)."""
from __future__ import annotations

import json

from dreamlayer import cli
from dreamlayer.reality_compiler.v2 import RealityCompilerV2
from dreamlayer.reality_compiler.v2.figment import PulseSpec


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


def test_golf_verify_scores_a_valid_figment(tmp_path, capsys):
    p = _write(_valid_fig(), tmp_path)
    rc = cli.main(["golf", "verify", str(p)])
    out = capsys.readouterr().out
    assert rc == 0 and "BUDGETS OK" in out and "golf score" in out


def test_golf_verify_json_reports_the_breakdown(tmp_path, capsys):
    p = _write(_valid_fig(), tmp_path)
    assert cli.main(["golf", "verify", str(p), "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["ok"] is True
    sc = data["score"]
    assert sc["golf_score"] > 0 and sc["scenes"] >= 1 and sc["bytes"] > 0
    assert isinstance(sc["event_types"], list)


def test_golf_disqualifies_a_budget_violator(tmp_path, capsys):
    fig = _valid_fig()
    sid = next(iter(fig.scenes))
    # jam a strobe past MAX_PULSE_HZ into a scene → disqualified, however clever
    fig.scenes[sid].pulse = PulseSpec(window_sec=2.0, rate_hz=9.0)
    p = _write(fig, tmp_path, "bad.json")
    rc = cli.main(["golf", "verify", str(p)])
    assert rc == 1 and "BUDGETS VIOLATED" in capsys.readouterr().out


def test_golf_accepts_a_wrapped_listing(tmp_path, capsys):
    fig = _valid_fig()
    p = tmp_path / "listing.json"
    p.write_text(json.dumps({"figment": fig.to_dict(), "author_sig": "x"}),
                 encoding="utf-8")
    assert cli.main(["golf", "verify", str(p), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["ok"] is True


def test_golf_rejects_non_figment(tmp_path, capsys):
    p = tmp_path / "nope.json"
    p.write_text('{"hello": "world"}', encoding="utf-8")
    assert cli.main(["golf", "verify", str(p)]) == 2
    assert "not a figment" in capsys.readouterr().err
