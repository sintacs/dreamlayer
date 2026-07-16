"""Tests for display/palette_cycle.lua — motion by recolouring, not
redrawing. Covers ramp assignment, rotation, smooth YCbCr interpolation,
deterministic clock-driven cycling, reduce_motion, period wrap, and the
no-frame (headless) guard. lupa, pinned to Lua 5.3, same pattern as
test_materials.py."""
import pathlib

import pytest

try:
    from lupa import lua53
    LUPA_AVAILABLE = True
except ImportError:
    LUPA_AVAILABLE = False

LUA_ROOT = pathlib.Path(__file__).parents[4] / "halo-lua"

# four distinct primaries so rotation is unambiguous
RED, GREEN, BLUE, YELLOW = 0xFF0000, 0x00FF00, 0x0000FF, 0xFFFF00


def _make_runtime(with_frame=True):
    rt = lua53.LuaRuntime(unpack_returned_tuples=True)
    rt.execute(f'package.path = "{LUA_ROOT.as_posix()}/?.lua;" .. package.path')
    if with_frame:
        rt.execute("""
        _pal = {}
        frame = { display = {
          assign_color_ycbcr = function(slot, y, cb, cr)
            _pal[slot] = { y, cb, cr }
          end,
        }}
        """)
    else:
        rt.execute("frame = nil")
    return rt


def _setup(rt):
    # slash paths: palette_cycle requires "display/palette" (see its header),
    # so reservations must land on that same instance to be visible.
    rt.execute('_p  = require("display/palette")')
    rt.execute('_pc = require("display/palette_cycle")')
    # reserve four named slots to cycle over
    rt.execute('_p.reserve_dynamic("c1", 0x000000, 1)')
    rt.execute('_p.reserve_dynamic("c2", 0x000000, 2)')
    rt.execute('_p.reserve_dynamic("c3", 0x000000, 3)')
    rt.execute('_p.reserve_dynamic("c4", 0x000000, 4)')


def _new(rt, smooth=True, period=4000):
    _setup(rt)
    rt.execute(
        f"_cy = _pc.new({{'c1','c2','c3','c4'}}, "
        f"{{ {RED}, {GREEN}, {BLUE}, {YELLOW} }}, "
        f"{{ smooth = {'true' if smooth else 'false'}, period_ms = {period} }})")
    return rt


def _slot(rt, n):
    return tuple(int(v) for v in rt.eval(f"_pal[{n}]").values())


def _ycbcr(rt, hex_):
    y, cb, cr = rt.eval(f"{{ _p.hex_to_ycbcr({hex_}) }}").values()
    return int(y), int(cb), int(cr)


@pytest.fixture()
def rt():
    if not LUPA_AVAILABLE:
        pytest.skip("lupa not installed")
    return _make_runtime()


# ---------------------------------------------------------------------------
# Base arrangement + rotation
# ---------------------------------------------------------------------------

def test_base_arrangement_lays_ramp_across_slots(rt):
    _new(rt)
    rt.execute("_cy:restore()")           # offset 0
    assert _slot(rt, 1) == _ycbcr(rt, RED)
    assert _slot(rt, 2) == _ycbcr(rt, GREEN)
    assert _slot(rt, 3) == _ycbcr(rt, BLUE)
    assert _slot(rt, 4) == _ycbcr(rt, YELLOW)


def test_integer_advance_rotates_colours(rt):
    _new(rt, smooth=False)
    rt.execute("_cy:advance(1)")          # slide the ramp by one stop
    assert _slot(rt, 1) == _ycbcr(rt, GREEN)
    assert _slot(rt, 2) == _ycbcr(rt, BLUE)
    assert _slot(rt, 3) == _ycbcr(rt, YELLOW)
    assert _slot(rt, 4) == _ycbcr(rt, RED)    # wrapped around the ring


def test_full_rotation_returns_to_base(rt):
    _new(rt, smooth=False)
    rt.execute("_cy:advance(4)")          # #ramp == 4 -> identity
    assert _slot(rt, 1) == _ycbcr(rt, RED)
    assert _slot(rt, 4) == _ycbcr(rt, YELLOW)


# ---------------------------------------------------------------------------
# Smooth interpolation
# ---------------------------------------------------------------------------

def test_smooth_advance_interpolates_between_stops(rt):
    _new(rt, smooth=True)
    rt.execute("_cy:advance(0.5)")        # slot1 halfway RED -> GREEN
    y, cb, cr = _slot(rt, 1)
    ry, rcb, rcr = _ycbcr(rt, RED)
    gy, gcb, gcr = _ycbcr(rt, GREEN)
    for comp, lo, hi in ((y, ry, gy), (cb, rcb, gcb), (cr, rcr, gcr)):
        assert min(lo, hi) <= comp <= max(lo, hi)
    # genuinely between, not snapped to an endpoint
    assert (y, cb, cr) != (ry, rcb, rcr)
    assert (y, cb, cr) != (gy, gcb, gcr)


def test_stepped_mode_snaps_to_nearest_stop(rt):
    _new(rt, smooth=False)
    rt.execute("_cy:advance(0.5)")        # no interpolation -> the floor stop
    assert _slot(rt, 1) == _ycbcr(rt, RED)


# ---------------------------------------------------------------------------
# Clock-driven cycling: deterministic, moving, wrap, reduce_motion
# ---------------------------------------------------------------------------

def test_tick_is_deterministic(rt):
    _new(rt, period=4000)
    rt.execute("_cy:tick(1234)")
    a = [_slot(rt, n) for n in (1, 2, 3, 4)]
    rt.execute("_pal = {}; _cy:tick(1234)")
    b = [_slot(rt, n) for n in (1, 2, 3, 4)]
    assert a == b


def test_tick_moves_over_time(rt):
    _new(rt, period=4000)
    rt.execute("_cy:tick(0)")
    at0 = [_slot(rt, n) for n in (1, 2, 3, 4)]
    rt.execute("_pal = {}; _cy:tick(500)")
    at500 = [_slot(rt, n) for n in (1, 2, 3, 4)]
    assert at0 != at500                    # the colours flowed


def test_period_wraps(rt):
    _new(rt, period=4000)
    rt.execute("_cy:tick(0)")
    base = [_slot(rt, n) for n in (1, 2, 3, 4)]
    rt.execute("_pal = {}; _cy:tick(4000)")   # one full period later
    later = [_slot(rt, n) for n in (1, 2, 3, 4)]
    assert base == later


def test_reduce_motion_holds_base_arrangement(rt):
    _new(rt, period=4000)
    rt.execute("_cy:tick(1500, { reduce_motion = true })")
    a = [_slot(rt, n) for n in (1, 2, 3, 4)]
    rt.execute("_pal = {}; _cy:tick(9999, { reduce_motion = true })")
    b = [_slot(rt, n) for n in (1, 2, 3, 4)]
    assert a == b                          # frozen across time
    assert a[0] == _ycbcr(rt, RED)         # ...at the base arrangement


# ---------------------------------------------------------------------------
# Guards
# ---------------------------------------------------------------------------

def test_default_ramp_is_the_slots_own_colours(rt):
    _setup(rt)
    rt.execute('_p.reserve_dynamic("d1", 0xFF0000, 1)')  # re-point? no: idempotent
    # fresh names with distinct bases
    rt.execute('_p.reserve_dynamic("e1", 0x112233, 5)')
    rt.execute('_p.reserve_dynamic("e2", 0x445566, 6)')
    rt.execute("_cy2 = _pc.new({'e1','e2'})")            # no ramp -> bases
    rt.execute("_cy2:restore()")
    assert _slot(rt, 5) == _ycbcr(rt, 0x112233)
    assert _slot(rt, 6) == _ycbcr(rt, 0x445566)


def test_unreserved_slot_is_rejected(rt):
    _setup(rt)
    ok = rt.eval("(function() local ok = pcall(function() "
                 "_pc.new({'c1','never_reserved'}) end); return ok end)()")
    assert ok is False


def test_headless_tick_is_a_noop():
    if not LUPA_AVAILABLE:
        pytest.skip("lupa not installed")
    rt = _make_runtime(with_frame=False)
    _setup(rt)
    rt.execute(f"_cy = _pc.new({{'c1','c2','c3','c4'}}, {{ {RED},{GREEN},{BLUE},{YELLOW} }})")
    # no frame table: advancing must not raise
    rt.execute("_cy:tick(1000); _cy:advance(2); _cy:restore()")


# ---------------------------------------------------------------------------
# Integration: the dream renderer's idle sky flow. The sky slots cycle when
# the mic reactor is quiet, and yield the moment the reactor speaks.
# ---------------------------------------------------------------------------

def _dream_runtime():
    rt = lua53.LuaRuntime(unpack_returned_tuples=True)
    rt.execute(f'package.path = "{LUA_ROOT.as_posix()}/?.lua;" .. package.path')
    rt.execute("""
    _pal = {}
    frame = { display = {
      line   = function(...) end,
      rect   = function(...) end,
      circle = function(...) end,
      text   = function(...) end,
      bitmap = function(...) end,
      clear  = function(...) end,
      show   = function(...) end,
      assign_color_ycbcr = function(slot, y, cb, cr) _pal[slot] = { y, cb, cr } end,
    }}
    _dr = require("display.dream_renderer")
    """)
    return rt


def _sky(rt):
    return [tuple(int(v) for v in rt.eval(f"_pal[{n}]").values())
            for n in (1, 2, 3, 4)]


class TestDreamIdleFlow:
    def test_idle_sky_flows_when_reactor_is_quiet(self):
        if not LUPA_AVAILABLE:
            pytest.skip("lupa not installed")
        rt = _dream_runtime()
        rt.execute("_dr.draw_frame(2000)")
        a = _sky(rt)
        rt.execute("_pal = {}; _dr.draw_frame(5000)")
        b = _sky(rt)
        assert all(a) and all(b)          # the sky slots were assigned
        assert a != b                      # ...and the colours flowed

    def test_reduce_motion_freezes_the_idle_flow(self):
        if not LUPA_AVAILABLE:
            pytest.skip("lupa not installed")
        rt = _dream_runtime()
        rt.execute("_dr.draw_frame(2000, true)")
        a = _sky(rt)
        rt.execute("_pal = {}; _dr.draw_frame(8000, true)")
        b = _sky(rt)
        assert a == b                      # colour, no movement

    def test_reactor_push_takes_the_slots_and_flow_yields(self):
        if not LUPA_AVAILABLE:
            pytest.skip("lupa not installed")
        rt = _dream_runtime()
        rt.execute("_dr.draw_frame(10000)")          # establishes the clock
        # the reactor speaks: paint the four slots with distinct values
        rt.execute("""
          _dr.apply_palette_shift({
            {idx=1, y=100, cb=100, cr=100}, {idx=2, y=200, cb=200, cr=200},
            {idx=3, y=300, cb=300, cr=300}, {idx=4, y=400, cb=400, cr=400} })
        """)
        held = _sky(rt)
        assert held[0] == (100, 100, 100)
        # a frame inside the hold window: the flow must not overwrite them
        rt.execute("_dr.draw_frame(10500)")
        assert _sky(rt) == held
        # past the hold window: the flow resumes and recolours the slots
        rt.execute("_pal = {}; _dr.draw_frame(13000)")
        resumed = _sky(rt)
        assert all(resumed) and resumed[0] != (100, 100, 100)
