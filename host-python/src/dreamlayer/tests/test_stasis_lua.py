"""Stasis on the device — the shutter and ribbon draw real pixels through
the integrated Lua, stay inside the frame budget, fade on their own, and
the handler is registered in the live host_comm dispatch."""
import pathlib

import pytest

try:
    import lupa  # noqa: F401
    LUPA_AVAILABLE = True
except ImportError:
    LUPA_AVAILABLE = False

pytestmark = pytest.mark.skipif(not LUPA_AVAILABLE, reason="lupa required")

REPO = pathlib.Path(__file__).parents[4]


def _session():
    from dreamlayer.bridge.lua_raster import LuaRasterHarness
    h = LuaRasterHarness()
    h.execute("__now = 0")
    h.execute('_r  = require("display.renderer")')
    h.execute('_sx = require("display.stasis")')
    h.execute("_r.bind(nil, function() return __now end)")
    h.sync_dynamic_slots()
    return h


def _tick_calls(h, at_ms):
    h.execute(f"__now = {at_ms}")
    h.display.draw_calls = 0
    h.execute("_r.tick()")
    return h.display.draw_calls


def _budget(h):
    return int(h.eval('require("display.animations").DRAW_CALLS_MAX'))


def test_freeze_shutter_and_ribbon_draw_within_budget():
    h = _session()
    base = _tick_calls(h, 1000)
    h.execute('_sx.on_stasis({ t = "stasis", mode = "freeze" })')
    during = _tick_calls(h, 1050)               # mid-shutter
    assert during > base, "the shutter must draw real pixels"
    worst = max(_tick_calls(h, 1050 + i * 50) for i in range(1, 12))
    assert worst <= _budget(h)


def test_freeze_fades_to_invisible_on_its_own():
    # calm technology: dormant Stasis is invisible — no badge, no count
    h = _session()
    h.execute('_sx.on_stasis({ t = "stasis", mode = "freeze" })')
    _tick_calls(h, 1000)                        # latch t0
    _tick_calls(h, 4500)                        # past shutter + settle
    assert not h.eval("_sx.is_active()")


def test_offer_breathes_then_gives_up_quietly():
    h = _session()
    h.execute('_sx.on_stasis({ t = "stasis", mode = "offer" })')
    a = _tick_calls(h, 1000)
    assert a > 0 and h.eval('_sx.state()') == "offer"
    _tick_calls(h, 12500)                       # past OFFER_GLOW_MS
    assert not h.eval("_sx.is_active()"), "unaccepted offers expire silently"


def test_clear_stops_everything_immediately():
    h = _session()
    h.execute('_sx.on_stasis({ t = "stasis", mode = "offer" })')
    _tick_calls(h, 1000)
    h.execute('_sx.on_stasis({ t = "stasis", mode = "clear" })')
    assert not h.eval("_sx.is_active()")


def test_ribbon_rides_over_a_held_card_within_budget():
    h = _session()
    _tick_calls(h, 1000)
    h.execute('__now = 1050; _r.show_card({ type = "SavedMemoryCard",'
              ' primary = "House keys" })')
    h.execute('_sx.on_stasis({ t = "stasis", mode = "offer" })')
    worst = max(_tick_calls(h, 1050 + i * 50) for i in range(1, 20))
    assert 0 < worst <= _budget(h)


def test_handler_is_registered_in_the_live_dispatch():
    h = _session()
    h.execute('_hc = require("ble.host_comm")')
    h.execute('_hc.on_message({ t = "stasis", mode = "offer" })')
    assert h.eval('_sx.state()') == "offer"
