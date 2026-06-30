"""
pytest tests for halo-lua/app/imu_gesture.lua.

Runs the Lua classifier under lupa (Lua 5.4/5.5 via Python bindings).
Falls back gracefully with a clear skip message if lupa is not installed.

Install: uv add lupa

All tests are pure synthetic IMU streams — no hardware, no BLE.

Design
------
Every interaction with the Lua classifier happens inside a single
self-contained Lua script string built by _run_lua().  Nothing crosses
the Python<->Lua boundary except:
  * scalar config values, formatted into the script as Lua literals
  * the results table, read back via lua.eval() after the script runs

This sidesteps three lupa gotchas that caused all prior versions to fail:
  1. lua.table(**kw) silently drops kwargs whose names contain underscores
  2. G.feed from Python is None — lupa does not follow __index metamethods
  3. lua.globals().underscore_name = x does not set the global correctly

EMA / stream design
-------------------
No EMA seeding or priming samples.  With alpha=0.35, feeding 5 samples
at ±35 crosses threshold ±28 organically (EMA reaches ~28.9 on sample 4).
"""
from __future__ import annotations

from pathlib import Path

import pytest

try:
    import lupa  # type: ignore
    from lupa import LuaRuntime
    HAS_LUPA = True
except ImportError:
    HAS_LUPA = False

REPO     = Path(__file__).resolve().parent.parent.parent
LUA_ROOT = REPO / "halo-lua"

requires_lupa = pytest.mark.skipif(
    not HAS_LUPA,
    reason="lupa not installed — run: uv add lupa",
)


# ---------------------------------------------------------------------------
# Runtime fixture  (one LuaRuntime per test-module run)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def lua():
    if not HAS_LUPA:
        pytest.skip("lupa not available")
    rt = LuaRuntime(unpack_returned_tuples=False)
    rt.execute(f"""
        package.path = package.path
            .. ";{LUA_ROOT}/?.lua"
            .. ";{LUA_ROOT}/?/init.lua"
    """)
    return rt


# ---------------------------------------------------------------------------
# Core runner
#
# Builds and executes a self-contained Lua script.  Returns a list of
# (gesture_name, confidence) tuples that fired during the stream.
# ---------------------------------------------------------------------------

def _lua_require(rt, module: str):
    result = rt.eval(f"require('{module}')")
    return result[0] if isinstance(result, tuple) else result


def _cfg_to_lua(cfg: dict) -> str:
    """Serialise a Python cfg dict to Lua table field lines."""
    parts = []
    for k, v in cfg.items():
        if isinstance(v, bool):
            parts.append(f"  {k} = {'true' if v else 'false'},")
        elif isinstance(v, (int, float)):
            parts.append(f"  {k} = {v},")
        elif isinstance(v, str):
            parts.append(f'  {k} = "{v.replace(chr(34), chr(92)+chr(34))}",')  
    return "\n".join(parts)


def _stream_to_lua(stream) -> str:
    """Serialise a Python stream list to a Lua array-of-arrays literal."""
    rows = ",\n    ".join(
        f"{{{ax}, {ay}, {az}, {t}}}"
        for ax, ay, az, t in stream
    )
    return f"{{\n    {rows}\n  }}"


def _run_lua(lua, stream, **cfg):
    """
    Execute one complete gesture-classifier run inside Lua.
    Returns [(name, confidence), ...] for every gesture that fired.
    """
    cfg_fields  = _cfg_to_lua(cfg)
    stream_lit  = _stream_to_lua(stream)

    script = f"""
      do
        -- fresh module each call
        package.loaded['app.imu_gesture'] = nil
        local M = require('app.imu_gesture')

        local fired = {{}}
        local opts = {{
{cfg_fields}
          on_gesture = function(name, conf)
            fired[#fired + 1] = {{name, conf}}
          end,
        }}

        local G = M.new(opts)
        local stream = {stream_lit}
        for _, v in ipairs(stream) do
          G:feed(v[1], v[2], v[3], v[4])
        end

        -- store results where Python can read them
        _last_fired = fired
      end
    """
    lua.execute(script)
    return _collect_fired(lua)


def _collect_fired(lua):
    """Read _last_fired Lua global into Python [(name, conf), ...]."""
    fired_ref = lua.eval("_last_fired")
    results = []
    i = 1
    while True:
        entry = fired_ref[i]
        if entry is None:
            break
        results.append((str(entry[1]), float(entry[2])))
        i += 1
    return results


def _names(fired):
    return [f[0] for f in fired]


# ---------------------------------------------------------------------------
# Stream builder helpers
# ---------------------------------------------------------------------------

FPS   = 50
DT_MS = 1000 // FPS   # 20 ms per sample


def _samples(ax=0.0, ay=0.0, az=0.0, count=1, start_ms=0):
    return [(ax, ay, az, start_ms + i * DT_MS) for i in range(count)]


# NOD  (Y-axis: +peak → -peak → rest)
# EMA alpha=0.35: 5 samples at 35 → EMA ~28.9 > threshold 28 on sample 4.
def _nod_stream(start_ms=0, strength=35.0):
    t = start_ms
    s  = _samples(0,  strength, 0, 5, t);  t += 5 * DT_MS
    s += _samples(0, -strength, 0, 5, t);  t += 5 * DT_MS
    s += _samples(0,  0,        0, 3, t)
    return s


# DOUBLE NOD: + - + - within gesture_window_ms=600 ms
# 4 legs × 5 × 20 ms = 400 ms < 600 ms
def _double_nod_stream(start_ms=0, strength=35.0):
    t = start_ms
    s  = _samples(0,  strength, 0, 5, t);  t += 5 * DT_MS
    s += _samples(0, -strength, 0, 5, t);  t += 5 * DT_MS
    s += _samples(0,  strength, 0, 5, t);  t += 5 * DT_MS
    s += _samples(0, -strength, 0, 5, t);  t += 5 * DT_MS
    s += _samples(0,  0,        0, 3, t)
    return s


# SHAKE  (X-axis: 3 alternating crossings)
def _shake_stream(start_ms=0, strength=32.0):
    t = start_ms
    s  = _samples(-strength, 0, 0, 5, t);  t += 5 * DT_MS
    s += _samples( strength, 0, 0, 5, t);  t += 5 * DT_MS
    s += _samples(-strength, 0, 0, 5, t);  t += 5 * DT_MS
    s += _samples( 0,        0, 0, 3, t)
    return s


# GLANCE  (Z-axis: brief +crossing then return within peek_max_ms=350 ms)
def _glance_stream(start_ms=0, strength=25.0, duration_ms=120):
    t    = start_ms
    rise = 4   # samples for EMA to cross threshold_tilt=20 at strength=25
    n    = max(1, duration_ms // DT_MS)
    s  = _samples(0, 0, strength, rise + n, t);  t += (rise + n) * DT_MS
    s += _samples(0, 0, 0,                3, t)
    return s


# TILT  (Z-axis: sustained negative for hold_tilt_ms=400 ms)
def _tilt_stream(start_ms=0, strength=-25.0, duration_ms=500):
    t  = start_ms
    n  = max(1, duration_ms // DT_MS)
    s  = _samples(0, 0, strength, n, t);  t += n * DT_MS
    s += _samples(0, 0, 0,        3, t)
    return s


# ---------------------------------------------------------------------------
# Tests: NOD_SAVE
# ---------------------------------------------------------------------------

@requires_lupa
class TestNodSave:
    def test_single_nod_fires(self, lua, gesture_module=None):
        assert "NOD_SAVE" in _names(_run_lua(lua, _nod_stream()))

    def test_nod_confidence_above_threshold(self, lua, gesture_module=None):
        for name, conf in _run_lua(lua, _nod_stream()):
            if name == "NOD_SAVE":
                assert conf >= 0.70

    def test_weak_nod_below_threshold_ignored(self, lua, gesture_module=None):
        assert "NOD_SAVE" not in _names(_run_lua(lua, _nod_stream(strength=5.0)))

    def test_nod_cooldown_prevents_double_fire(self, lua, gesture_module=None):
        s = _nod_stream(0) + _nod_stream(200)
        fired = _run_lua(lua, s)
        assert len([f for f in fired if f[0] == "NOD_SAVE"]) == 1

    def test_nod_fires_again_after_cooldown(self, lua, gesture_module=None):
        s = _nod_stream(0) + _nod_stream(2000)
        fired = _run_lua(lua, s)
        assert len([f for f in fired if f[0] == "NOD_SAVE"]) == 2


# ---------------------------------------------------------------------------
# Tests: DOUBLE_NOD
# ---------------------------------------------------------------------------

@requires_lupa
class TestDoubleNod:
    def test_double_nod_fires(self, lua, gesture_module=None):
        assert "DOUBLE_NOD" in _names(_run_lua(lua, _double_nod_stream()))

    def test_double_nod_not_shadowed_by_single_nod(self, lua, gesture_module=None):
        assert "DOUBLE_NOD" in _names(_run_lua(lua, _double_nod_stream()))

    def test_single_nod_does_not_fire_double_nod(self, lua, gesture_module=None):
        assert "DOUBLE_NOD" not in _names(_run_lua(lua, _nod_stream()))


# ---------------------------------------------------------------------------
# Tests: SHAKE_DISMISS
# ---------------------------------------------------------------------------

@requires_lupa
class TestShakeDismiss:
    def test_shake_fires(self, lua, gesture_module=None):
        assert "SHAKE_DISMISS" in _names(_run_lua(lua, _shake_stream()))

    def test_shake_confidence_above_threshold(self, lua, gesture_module=None):
        for name, conf in _run_lua(lua, _shake_stream()):
            if name == "SHAKE_DISMISS":
                assert conf >= 0.70

    def test_weak_shake_ignored(self, lua, gesture_module=None):
        assert "SHAKE_DISMISS" not in _names(_run_lua(lua, _shake_stream(strength=5.0)))

    def test_shake_cooldown(self, lua, gesture_module=None):
        s = _shake_stream(0) + _shake_stream(300)
        fired = _run_lua(lua, s)
        assert len([f for f in fired if f[0] == "SHAKE_DISMISS"]) == 1


# ---------------------------------------------------------------------------
# Tests: GLANCE_PEEK
# ---------------------------------------------------------------------------

@requires_lupa
class TestGlancePeek:
    def test_glance_fires(self, lua, gesture_module=None):
        assert "GLANCE_PEEK" in _names(_run_lua(lua, _glance_stream()))

    def test_long_tilt_not_glance(self, lua, gesture_module=None):
        assert "GLANCE_PEEK" not in _names(_run_lua(lua, _glance_stream(duration_ms=600)))


# ---------------------------------------------------------------------------
# Tests: TILT_REVEAL
# ---------------------------------------------------------------------------

@requires_lupa
class TestTiltReveal:
    def test_tilt_fires_when_held(self, lua, gesture_module=None):
        assert "TILT_REVEAL" in _names(_run_lua(lua, _tilt_stream(duration_ms=500)))

    def test_brief_tilt_does_not_fire(self, lua, gesture_module=None):
        assert "TILT_REVEAL" not in _names(_run_lua(lua, _tilt_stream(duration_ms=200)))


# ---------------------------------------------------------------------------
# Tests: noise immunity
# ---------------------------------------------------------------------------

@requires_lupa
class TestNoiseImmunity:
    def test_flat_zero_fires_nothing(self, lua, gesture_module=None):
        assert _run_lua(lua, _samples(0, 0, 0, 100, 0)) == []

    def test_low_noise_fires_nothing(self, lua, gesture_module=None):
        import random
        rng = random.Random(42)
        stream = [(rng.uniform(-8, 8), rng.uniform(-8, 8), rng.uniform(-8, 8), i * DT_MS)
                  for i in range(150)]
        assert _run_lua(lua, stream) == []

    def test_reset_clears_state(self, lua, gesture_module=None):
        # Feed +peak (no -peak yet), reset, then feed -peak only: NOD needs + then -
        script = f"""
          do
            package.loaded['app.imu_gesture'] = nil
            local M = require('app.imu_gesture')
            local fired = {{}}
            local G = M.new({{on_gesture = function(n,c) fired[#fired+1]={{n,c}} end}})
            -- partial nod: only +peak, no -peak
            for i = 0, 4 do G:feed(0, 35, 0, i*20) end
            G:reset()
            -- after reset, feed -peak only: should not produce a NOD_SAVE
            for i = 0, 4 do G:feed(0, -35, 0, 400 + i*20) end
            _last_fired = fired
          end
        """
        lua.execute(script)
        assert "NOD_SAVE" not in _names(_collect_fired(lua))


# ---------------------------------------------------------------------------
# Tests: multi-gesture independence
# ---------------------------------------------------------------------------

@requires_lupa
class TestMultiGesture:
    def test_nod_does_not_trigger_shake(self, lua, gesture_module=None):
        assert "SHAKE_DISMISS" not in _names(_run_lua(lua, _nod_stream()))

    def test_shake_does_not_trigger_nod(self, lua, gesture_module=None):
        assert "NOD_SAVE" not in _names(_run_lua(lua, _shake_stream()))

    def test_sequential_nod_then_shake(self, lua, gesture_module=None):
        nod   = _nod_stream(0)
        shake = _shake_stream(nod[-1][3] + 1000)
        fired = _run_lua(lua, nod + shake)
        names = _names(fired)
        assert "NOD_SAVE"      in names
        assert "SHAKE_DISMISS" in names


# ---------------------------------------------------------------------------
# Tests: custom config
# ---------------------------------------------------------------------------

@requires_lupa
class TestCustomConfig:
    def test_higher_threshold_ignores_normal_nod(self, lua, gesture_module=None):
        # threshold_nod=60 > EMA peak ~28.9 at strength=35 → no crossing
        fired = _run_lua(lua, _nod_stream(strength=35.0), threshold_nod=60)
        assert "NOD_SAVE" not in _names(fired)

    def test_wider_cooldown_prevents_second_gesture(self, lua, gesture_module=None):
        fired = _run_lua(lua, _nod_stream(0) + _nod_stream(2000), cooldown_ms=5000)
        assert len([f for f in fired if f[0] == "NOD_SAVE"]) == 1

    def test_shorter_cooldown_allows_rapid_fire(self, lua, gesture_module=None):
        fired = _run_lua(lua, _nod_stream(0) + _nod_stream(400), cooldown_ms=100)
        assert len([f for f in fired if f[0] == "NOD_SAVE"]) >= 2


# ---------------------------------------------------------------------------
# Fallback: inform when lupa is absent
# ---------------------------------------------------------------------------

@pytest.mark.skipif(HAS_LUPA, reason="lupa is installed")
def test_lupa_not_installed_inform():
    pytest.skip(
        "Gesture tests require lupa (Lua 5.4/5.5 Python bindings).\n"
        "Install with: uv add lupa\n"
        "Then re-run: uv run pytest scripts/tests/test_gestures.py -v"
    )
