"""Tests for display/transitions.lua (Meridian survivors of the v1
signature set), display/focus.lua (the Focus law that replaced the
killed signatures — docs/CINEMA_V2_DELTAS.md §1-§4), and the Line Field
2.0 host-side generator.

Lua side follows the lupa pattern from test_diagnostics.py, pinned to
Lua 5.3 to match the device runtime. A fake `frame` table records draw
calls so signature geometry is assertable without hardware.
"""
import json
import pathlib

import pytest

try:
    from lupa import lua53
    LUPA_AVAILABLE = True
except ImportError:
    LUPA_AVAILABLE = False

from dreamlayer.dream_mode.imu_reactor import ImuReactor, _WIRE_BUDGET
from dreamlayer.orchestrator.recall_context import RecallContext

LUA_ROOT = pathlib.Path(__file__).parents[4] / "halo-lua"


def _make_runtime(with_frame=True):
    rt = lua53.LuaRuntime(unpack_returned_tuples=True)
    rt.execute(f'package.path = "{LUA_ROOT.as_posix()}/?.lua;" .. package.path')
    if with_frame:
        rt.execute("""
        _calls = {}
        frame = { display = {
          line   = function(...) _calls[#_calls+1] = {"line", ...} end,
          rect   = function(...) _calls[#_calls+1] = {"rect", ...} end,
          circle = function(...) _calls[#_calls+1] = {"circle", ...} end,
          text   = function(...) _calls[#_calls+1] = {"text", ...} end,
          bitmap = function(...) end,
          clear  = function(...) end,
          show   = function(...) end,
          assign_color_ycbcr = function(...) _calls[#_calls+1] = {"pal", ...} end,
        }}
        """)
    else:
        rt.execute("frame = nil")
    return rt


@pytest.fixture()
def tr():
    if not LUPA_AVAILABLE:
        pytest.skip("lupa not installed")
    rt = _make_runtime()
    rt.execute('_tr = require("display.transitions")')
    rt.execute('_f  = require("display.focus")')
    rt.execute('_a  = require("display.animations")')
    return rt


# ---------------------------------------------------------------------------
# Enter durations / reduce_motion contract
# ---------------------------------------------------------------------------

def test_enter_durations_come_from_animations(tr):
    assert tr.eval('_tr.enter_duration("ghost_wake")') == \
        tr.eval("_a.SIG_GHOSTWAKE_MS")
    assert tr.eval('_tr.enter_duration("ripple")') == \
        tr.eval("_a.SIG_RIPPLE_MS")
    assert tr.eval('_f.enter_ms()') == \
        tr.eval("_a.SIG_FOCUS_TRAVEL_MS + _a.SIG_FOCUS_LAND_MS")
    assert tr.eval('_f.recede_ms()') == tr.eval("_a.SIG_RECEDE_MS")


def test_reduce_motion_collapses_enter_to_zero(tr):
    tr.execute("_tr.set_reduce_motion(true)")
    assert tr.eval('_f.enter_ms()') == 0
    assert tr.eval('_f.recede_ms()') == 0
    tr.execute("_tr.set_reduce_motion(false)")
    assert tr.eval('_f.enter_ms()') > 0


# ---------------------------------------------------------------------------
# Focus law: condensation travels from the horizon angle; the landed ring
# carries confidence as sweep (docs/cinema_v2/focus.md)
# ---------------------------------------------------------------------------

def test_focus_origin_defaults_to_now(tr):
    assert tr.eval("_f.origin_or_now({})") == -90
    assert tr.eval("_f.origin_or_now({ origin_deg = 30 })") == 30
    assert tr.eval("_f.origin_or_now(nil)") == -90


def test_focus_travel_draws_head(tr):
    tr.execute("_calls = {}")
    tr.execute("_f.travel(0.5, 0)")
    circles = tr.eval('(function() local n=0; for _,c in ipairs(_calls) do if c[1]=="circle" then n=n+1 end end; return n end)()')
    assert circles >= 1   # head (+ tail samples once t > 0.07)


def test_focus_travel_noop_under_reduce_motion(tr):
    tr.execute("_tr.set_reduce_motion(true)")
    tr.execute("_calls = {}")
    tr.execute("_f.travel(0.5, 0)")
    assert tr.eval("#_calls") == 0
    tr.execute("_tr.set_reduce_motion(false)")


def test_focus_hold_ring_sweep_scales_with_confidence(tr):
    tr.execute("_calls = {}; _f.hold_ring(1.0)")
    full = tr.eval("#_calls")
    tr.execute("_calls = {}; _f.hold_ring(0.25)")
    quarter = tr.eval("#_calls")
    assert full > quarter > 0    # arc segment count follows the sweep
    tr.execute("_calls = {}; _f.hold_ring(0.0)")
    assert tr.eval("#_calls") == 0   # no confidence, no ring


def test_focus_hold_ring_identical_under_reduce_motion(tr):
    tr.execute("_calls = {}; _f.hold_ring(0.6)")
    normal = tr.eval("#_calls")
    tr.execute("_tr.set_reduce_motion(true)")
    tr.execute("_calls = {}; _f.hold_ring(0.6)")
    reduced = tr.eval("#_calls")
    tr.execute("_tr.set_reduce_motion(false)")
    assert normal == reduced   # the v2 standard: reduce path is a no-op


def test_focus_landing_ring_restores_ghost_slot_when_done(tr):
    tr.execute("_calls = {}")
    tr.execute("_f.landing_ring(1.0)")
    pals = tr.eval('(function() local n=0; for _,c in ipairs(_calls) do if c[1]=="pal" then n=n+1 end end; return n end)()')
    assert pals >= 1   # ghost_text snapped back to base


# ---------------------------------------------------------------------------
# Shared exit
# ---------------------------------------------------------------------------

def test_exit_contract_scale_and_text_cut(tr):
    scale, text_ok = tr.eval("_tr.exit_contract(0.2)")
    assert abs(scale - 0.8) < 1e-6 and text_ok
    scale, text_ok = tr.eval("_tr.exit_contract(0.5)")
    assert abs(scale - 0.5) < 1e-6 and not text_ok   # text cuts at t=0.4


def test_exit_contract_reduce_motion_is_hard_cut(tr):
    tr.execute("_tr.set_reduce_motion(true)")
    scale, text_ok = tr.eval("_tr.exit_contract(0.5)")
    assert scale == 1 and text_ok
    scale, text_ok = tr.eval("_tr.exit_contract(1.0)")
    assert scale == 0 and not text_ok
    tr.execute("_tr.set_reduce_motion(false)")


# ---------------------------------------------------------------------------
# S2/S3/S5 + acoustics: draw without error, palette slots touched
# ---------------------------------------------------------------------------

def test_ghost_wake_draws_per_character(tr):
    tr.execute("_calls = {}")
    tr.execute('_tr.ghost_wake_text(128, 210, "ECHO", "sm", 0.5, 1234)')
    texts = tr.eval('(function() local n=0; for _,c in ipairs(_calls) do if c[1]=="text" then n=n+1 end end; return n end)()')
    assert texts == 4   # one draw per character


def test_truth_ripple_and_acoustics_run(tr):
    tr.execute("_tr.truth_ripple(0.4, 128, 96)")
    tr.execute("_tr.truth_ripple_cold(0.4, 128, 96)")
    tr.execute("_tr.chime(0.5)")
    tr.execute("_tr.chord(1.0, 128, 56, 0.8)")
    tr.execute("_tr.rumble(0.5)")


def test_all_signatures_noop_without_frame():
    if not LUPA_AVAILABLE:
        pytest.skip("lupa not installed")
    rt = _make_runtime(with_frame=False)
    rt.execute('_tr = require("display.transitions")')
    rt.execute('_f = require("display.focus")')
    rt.execute('_tr.ghost_wake_text(128, 210, "x", "sm", 0.5, 0)')
    rt.execute('_tr.truth_ripple(0.4)')
    rt.execute('_f.travel(0.5, 0)')
    rt.execute('_f.hold_ring(0.5)')
    rt.execute('_f.recede(0.5, 0)')


# ---------------------------------------------------------------------------
# Line Field 2.0 (host side, pairs with t="line_field" Lua handler)
# ---------------------------------------------------------------------------

def _imu_ctx(yaw=10.0, pitch=2.0):
    ctx = RecallContext()
    ctx.imu_pose = {"pitch": 0.0, "yaw": 0.0, "roll": 0.0}
    ctx.imu_delta = {"yaw": yaw, "pitch": pitch}
    return ctx


def test_line_field_fits_one_mtu_frame():
    r = ImuReactor()
    cmd = r.line_field(_imu_ctx())
    wire = json.dumps(cmd, separators=(",", ":"))
    assert len(wire) <= _WIRE_BUDGET


def test_line_field_has_12_vectors():
    r = ImuReactor()
    cmd = r.line_field(_imu_ctx())
    assert cmd["t"] == "line_field"
    assert len(cmd["v"]) == 48   # 12 vectors × 4 coords


def test_line_field_none_without_imu():
    r = ImuReactor()
    assert r.line_field(RecallContext()) is None


def test_line_field_gyroscopic_damping():
    """A single head-shake spike must not swing the field: the damped rate
    keeps ~90% suppressed within one tick."""
    r = ImuReactor()
    r.line_field(_imu_ctx(yaw=100.0))
    assert abs(r._yaw_damped) <= 100.0 * 0.11


def test_line_field_vectors_stay_on_display():
    r = ImuReactor()
    for _ in range(20):
        cmd = r.line_field(_imu_ctx(yaw=50.0, pitch=30.0))
    for coord in cmd["v"]:
        assert 6 <= coord <= 250
