"""
pytest tests for halo-lua/app/imu_gesture.lua.

Runs the Lua classifier under lupa (Lua 5.4/5.5 via Python bindings).
Falls back gracefully with a clear skip message if lupa is not installed.

Install: uv add lupa

All tests are pure synthetic IMU streams — no hardware, no BLE.

Lupa / Lua method-call note
---------------------------
Lua colon-methods (``function M:feed(...)``) must be called from Python as
``obj.feed(obj, ...)`` because lupa uses dot-attribute access and does NOT
auto-insert ``self``.  All helpers below use this pattern.
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
# Runtime + module helpers
# ---------------------------------------------------------------------------

def _lua_require(rt, module: str):
    """require() and always return just the table (lua55 returns a tuple)."""
    result = rt.eval(f"require('{module}')")
    return result[0] if isinstance(result, tuple) else result


@pytest.fixture(scope="module")
def lua():
    if not HAS_LUPA:
        pytest.skip("lupa not available")
    rt = LuaRuntime(unpack_returned_tuples=False)
    rt.execute(f"""
        package.path = package.path .. ";{LUA_ROOT}/?.lua;{LUA_ROOT}/?/init.lua"
    """)
    return rt


@pytest.fixture
def gesture_module(lua):
    lua.execute("package.loaded['app.imu_gesture'] = nil")
    return _lua_require(lua, "app.imu_gesture")


def _new(M, lua, **cfg):
    """Call M.new(cfg_table) — new() is a plain function, not a method."""
    return M.new(lua.table(**cfg))


# ---------------------------------------------------------------------------
# Stream builder helpers
# ---------------------------------------------------------------------------

FPS   = 50
DT_MS = 1000 // FPS


def _samples(ax=0.0, ay=0.0, az=0.0, count=1, start_ms=0):
    return [(ax, ay, az, start_ms + i * DT_MS) for i in range(count)]


def _nod_stream(start_ms=0, strength=35.0):
    s  = _samples(0,  strength, 0, 3, start_ms)
    s += _samples(0,  0,        0, 2, start_ms + 60)
    s += _samples(0, -strength, 0, 3, start_ms + 100)
    s += _samples(0,  0,        0, 3, start_ms + 160)
    return s


def _double_nod_stream(start_ms=0, strength=35.0):
    return _nod_stream(start_ms, strength) + _nod_stream(start_ms + 280, strength)


def _shake_stream(start_ms=0, strength=32.0):
    s  = _samples(-strength, 0, 0, 3, start_ms)
    s += _samples( 0,        0, 0, 2, start_ms + 60)
    s += _samples( strength, 0, 0, 3, start_ms + 100)
    s += _samples( 0,        0, 0, 2, start_ms + 160)
    s += _samples(-strength, 0, 0, 3, start_ms + 200)
    s += _samples( 0,        0, 0, 3, start_ms + 260)
    return s


def _glance_stream(start_ms=0, strength=25.0, duration_ms=120):
    n  = max(1, duration_ms // DT_MS)
    s  = _samples(0, 0, strength, 3, start_ms)
    s += _samples(0, 0, strength, n, start_ms + 60)
    s += _samples(0, 0, 0,        3, start_ms + 60 + n * DT_MS)
    return s


def _tilt_stream(start_ms=0, strength=-25.0, duration_ms=500):
    n  = max(1, duration_ms // DT_MS)
    s  = _samples(0, 0, strength, n, start_ms)
    s += _samples(0, 0, 0,        3, start_ms + n * DT_MS)
    return s


def _feed_stream(G, stream):
    """Feed samples and collect (name, confidence) pairs.

    G:feed is a Lua colon-method; lupa requires explicit self:
        G.feed(G, ax, ay, az, t)
    """
    fired = []

    def on_gesture(name, confidence):
        fired.append((str(name), float(confidence)))

    G.on_gesture = on_gesture
    for ax, ay, az, t in stream:
        G.feed(G, ax, ay, az, t)   # <-- explicit self
    return fired


# ---------------------------------------------------------------------------
# Tests: NOD_SAVE
# ---------------------------------------------------------------------------

@requires_lupa
class TestNodSave:
    def test_single_nod_fires(self, lua, gesture_module):
        G = _new(gesture_module, lua)
        assert "NOD_SAVE" in [f[0] for f in _feed_stream(G, _nod_stream())]

    def test_nod_confidence_above_threshold(self, lua, gesture_module):
        G = _new(gesture_module, lua)
        for name, conf in _feed_stream(G, _nod_stream()):
            if name == "NOD_SAVE":
                assert conf >= 0.70

    def test_weak_nod_below_threshold_ignored(self, lua, gesture_module):
        G = _new(gesture_module, lua)
        assert "NOD_SAVE" not in [f[0] for f in _feed_stream(G, _nod_stream(strength=5.0))]

    def test_nod_cooldown_prevents_double_fire(self, lua, gesture_module):
        G = _new(gesture_module, lua)
        fired = _feed_stream(G, _nod_stream(0) + _nod_stream(200))
        assert len([f for f in fired if f[0] == "NOD_SAVE"]) == 1

    def test_nod_fires_again_after_cooldown(self, lua, gesture_module):
        G = _new(gesture_module, lua)
        fired = _feed_stream(G, _nod_stream(0) + _nod_stream(1000))
        assert len([f for f in fired if f[0] == "NOD_SAVE"]) == 2


# ---------------------------------------------------------------------------
# Tests: DOUBLE_NOD
# ---------------------------------------------------------------------------

@requires_lupa
class TestDoubleNod:
    def test_double_nod_fires(self, lua, gesture_module):
        G = _new(gesture_module, lua)
        assert "DOUBLE_NOD" in [f[0] for f in _feed_stream(G, _double_nod_stream())]

    def test_double_nod_not_shadowed_by_single_nod(self, lua, gesture_module):
        G = _new(gesture_module, lua)
        assert "DOUBLE_NOD" in [f[0] for f in _feed_stream(G, _double_nod_stream())]

    def test_single_nod_does_not_fire_double_nod(self, lua, gesture_module):
        G = _new(gesture_module, lua)
        assert "DOUBLE_NOD" not in [f[0] for f in _feed_stream(G, _nod_stream())]


# ---------------------------------------------------------------------------
# Tests: SHAKE_DISMISS
# ---------------------------------------------------------------------------

@requires_lupa
class TestShakeDismiss:
    def test_shake_fires(self, lua, gesture_module):
        G = _new(gesture_module, lua)
        assert "SHAKE_DISMISS" in [f[0] for f in _feed_stream(G, _shake_stream())]

    def test_shake_confidence_above_threshold(self, lua, gesture_module):
        G = _new(gesture_module, lua)
        for name, conf in _feed_stream(G, _shake_stream()):
            if name == "SHAKE_DISMISS":
                assert conf >= 0.70

    def test_weak_shake_ignored(self, lua, gesture_module):
        G = _new(gesture_module, lua)
        assert "SHAKE_DISMISS" not in [f[0] for f in _feed_stream(G, _shake_stream(strength=5.0))]

    def test_shake_cooldown(self, lua, gesture_module):
        G = _new(gesture_module, lua)
        fired = _feed_stream(G, _shake_stream(0) + _shake_stream(300))
        assert len([f for f in fired if f[0] == "SHAKE_DISMISS"]) == 1


# ---------------------------------------------------------------------------
# Tests: GLANCE_PEEK
# ---------------------------------------------------------------------------

@requires_lupa
class TestGlancePeek:
    def test_glance_fires(self, lua, gesture_module):
        G = _new(gesture_module, lua)
        assert "GLANCE_PEEK" in [f[0] for f in _feed_stream(G, _glance_stream())]

    def test_long_tilt_not_glance(self, lua, gesture_module):
        G = _new(gesture_module, lua)
        assert "GLANCE_PEEK" not in [f[0] for f in _feed_stream(G, _glance_stream(duration_ms=600))]


# ---------------------------------------------------------------------------
# Tests: TILT_REVEAL
# ---------------------------------------------------------------------------

@requires_lupa
class TestTiltReveal:
    def test_tilt_fires_when_held(self, lua, gesture_module):
        G = _new(gesture_module, lua)
        assert "TILT_REVEAL" in [f[0] for f in _feed_stream(G, _tilt_stream(duration_ms=500))]

    def test_brief_tilt_does_not_fire(self, lua, gesture_module):
        G = _new(gesture_module, lua)
        assert "TILT_REVEAL" not in [f[0] for f in _feed_stream(G, _tilt_stream(duration_ms=200))]


# ---------------------------------------------------------------------------
# Tests: noise immunity
# ---------------------------------------------------------------------------

@requires_lupa
class TestNoiseImmunity:
    def test_flat_zero_fires_nothing(self, lua, gesture_module):
        G = _new(gesture_module, lua)
        assert _feed_stream(G, _samples(0, 0, 0, 100, 0)) == []

    def test_low_noise_fires_nothing(self, lua, gesture_module):
        import random
        rng = random.Random(42)
        G = _new(gesture_module, lua)
        stream = [(rng.uniform(-8, 8), rng.uniform(-8, 8), rng.uniform(-8, 8), i * DT_MS)
                  for i in range(150)]
        assert _feed_stream(G, stream) == []

    def test_reset_clears_state(self, lua, gesture_module):
        G = _new(gesture_module, lua)
        _feed_stream(G, _samples(0, 35.0, 0, 3, 0))
        G.reset(G)   # colon-method: explicit self
        fired = _feed_stream(G, _samples(0, -35.0, 0, 3, 400))
        assert "NOD_SAVE" not in [f[0] for f in fired]


# ---------------------------------------------------------------------------
# Tests: multi-gesture independence
# ---------------------------------------------------------------------------

@requires_lupa
class TestMultiGesture:
    def test_nod_does_not_trigger_shake(self, lua, gesture_module):
        G = _new(gesture_module, lua)
        assert "SHAKE_DISMISS" not in [f[0] for f in _feed_stream(G, _nod_stream())]

    def test_shake_does_not_trigger_nod(self, lua, gesture_module):
        G = _new(gesture_module, lua)
        assert "NOD_SAVE" not in [f[0] for f in _feed_stream(G, _shake_stream())]

    def test_sequential_nod_then_shake(self, lua, gesture_module):
        G = _new(gesture_module, lua)
        fired = _feed_stream(G, _nod_stream(0) + _shake_stream(1200))
        names = [f[0] for f in fired]
        assert "NOD_SAVE"      in names
        assert "SHAKE_DISMISS" in names


# ---------------------------------------------------------------------------
# Tests: custom config
# ---------------------------------------------------------------------------

@requires_lupa
class TestCustomConfig:
    def test_higher_threshold_ignores_normal_nod(self, lua, gesture_module):
        G = _new(gesture_module, lua, threshold_nod=60)
        assert "NOD_SAVE" not in [f[0] for f in _feed_stream(G, _nod_stream(strength=35.0))]

    def test_wider_cooldown_prevents_second_gesture(self, lua, gesture_module):
        G = _new(gesture_module, lua, cooldown_ms=2000)
        fired = _feed_stream(G, _nod_stream(0) + _nod_stream(1000))
        assert len([f for f in fired if f[0] == "NOD_SAVE"]) == 1

    def test_shorter_cooldown_allows_rapid_fire(self, lua, gesture_module):
        G = _new(gesture_module, lua, cooldown_ms=100)
        fired = _feed_stream(G, _nod_stream(0) + _nod_stream(400))
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
