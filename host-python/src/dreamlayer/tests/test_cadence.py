"""test_cadence.py — cadence scenes (INNOVATION_SESSION 5.1 #4): a first-class
breathing primitive. The interpreter drives an amplitude envelope (ramp in →
hold → ramp out), bounded like any scene — box-breathing, provable as ever."""
from __future__ import annotations

from dreamlayer.reality_compiler.v2.budgets import verify
from dreamlayer.reality_compiler.v2.figment import (
    CadenceSpec, Figment, Scene, Transition, END,
)
from dreamlayer.reality_compiler.v2.interpreter import Stage


def _breath_fig(cad=None):
    f = Figment(name="breathe", initial="a")
    f.scenes["a"] = Scene(
        id="a", duration_sec=60.0,
        cadence=cad if cad is not None else CadenceSpec(4.0, 4.0, 4.0),
        on_timeout=[Transition(target=END)])
    return f


def test_cadence_envelope_ramps_in_holds_and_ramps_out():
    st = Stage(_breath_fig())            # period 12: in 4, hold 4, out 4
    st.step(2.0)
    f = st.frame()
    assert f.cadence_phase == "in" and abs(f.cadence_level - 0.5) < 1e-6
    st.step(2.0)                         # elapsed 4 → hold
    f = st.frame()
    assert f.cadence_phase == "hold" and f.cadence_level == 1.0
    st.step(6.0)                         # elapsed 10 → out, 2/4 through
    f = st.frame()
    assert f.cadence_phase == "out" and abs(f.cadence_level - 0.5) < 1e-6


def test_no_cadence_scene_reports_nothing():
    f = Figment(name="plain", initial="a")
    f.scenes["a"] = Scene(id="a", duration_sec=5.0, on_timeout=[Transition(target=END)])
    st = Stage(f)
    st.step(1.0)
    fr = st.frame()
    assert fr.cadence_phase == "" and fr.cadence_level == 0.0


def test_cadence_round_trips_in_signed_json():
    f = _breath_fig()
    assert '"cadence"' in f.canonical_json()
    back = Figment.from_dict(f.to_dict())
    assert back.scenes["a"].cadence.period() == 12.0


def test_budget_accepts_a_valid_breath_and_rejects_a_too_fast_one():
    assert verify(_breath_fig()).ok
    fast = _breath_fig(CadenceSpec(0.1, 0.1, 0.1))     # period 0.3 < MIN_SCENE_SEC
    rep = verify(fast)
    assert not rep.ok and any(v.code == "cadence" for v in rep.violations)
