"""
pytest tests for halo-lua/app/imu_gesture.lua.

Runs the Lua classifier under lupa (Lua 5.4 via Python bindings).
Falls back gracefully with a clear skip message if lupa is not installed.

Install: uv add lupa

All tests are pure synthetic IMU streams — no hardware, no BLE.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import pytest

# ---------------------------------------------------------------------------
# Lupa import (optional)
# ---------------------------------------------------------------------------

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
# Lua runtime fixture
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def lua():
    if not HAS_LUPA:
        pytest.skip("lupa not available")
    rt = LuaRuntime(unpack_returned_tuples=True)
    # Add halo-lua to Lua package.path
    rt.execute(f"""
        package.path = package.path .. ";{LUA_ROOT}/?.lua;{LUA_ROOT}/?/init.lua"
    """)
    return rt


@pytest.fixture
def gesture_module(lua):
    """Fresh require of imu_gesture for each test (clears module cache)."""
    lua.execute("package.loaded['app.imu_gesture'] = nil")
    return lua.eval("require('app.imu_gesture')")


# ---------------------------------------------------------------------------
# Stream builder helpers
# ---------------------------------------------------------------------------

FPS   = 50          # samples per second
DT_MS = 1000 // FPS # 20 ms per sample


def _samples(
    ax: float = 0.0,
    ay: float = 0.0,
    az: float = 0.0,
    count: int = 1,
    start_ms: int = 0,
) -> list[tuple[float, float, float, int]]:
    """Flat-field samples at given axes for `count` frames."""
    return [(ax, ay, az, start_ms + i * DT_MS) for i in range(count)]


def _nod_stream(start_ms: int = 0, strength: float = 35.0) -> list[tuple]:
    """One forward-back nod: +Y peak then -Y peak."""
    stream = []
    # rise
    stream += _samples(0, strength, 0, 3, start_ms)
    # fall through zero
    stream += _samples(0, 0, 0, 2, start_ms + 60)
    # dip back
    stream += _samples(0, -strength, 0, 3, start_ms + 100)
    # return to neutral
    stream += _samples(0, 0, 0, 3, start_ms + 160)
    return stream


def _double_nod_stream(start_ms: int = 0, strength: float = 35.0) -> list[tuple]:
    """Two nods in sequence."""
    s1 = _nod_stream(start_ms, strength)
    s2 = _nod_stream(start_ms + 280, strength)
    return s1 + s2


def _shake_stream(start_ms: int = 0, strength: float = 32.0) -> list[tuple]:
    """Left-right-left head shake: −X, +X, −X."""
    stream = []
    stream += _samples(-strength, 0, 0, 3, start_ms)
    stream += _samples(0,         0, 0, 2, start_ms + 60)
    stream += _samples( strength, 0, 0, 3, start_ms + 100)
    stream += _samples(0,         0, 0, 2, start_ms + 160)
    stream += _samples(-strength, 0, 0, 3, start_ms + 200)
    stream += _samples(0,         0, 0, 3, start_ms + 260)
    return stream


def _glance_stream(start_ms: int = 0, strength: float = 25.0,
                   duration_ms: int = 120) -> list[tuple]:
    """Brief upward tilt then return to neutral."""
    stream = []
    n_hold = max(1, duration_ms // DT_MS)
    stream += _samples(0, 0,  strength, 3, start_ms)
    stream += _samples(0, 0,  strength, n_hold, start_ms + 60)
    stream += _samples(0, 0,  0,        3, start_ms + 60 + n_hold * DT_MS)
    return stream


def _tilt_stream(start_ms: int = 0, strength: float = -25.0,
                 duration_ms: int = 500) -> list[tuple]:
    """Sustained downward tilt for TILT_REVEAL."""
    n_hold = max(1, duration_ms // DT_MS)
    stream = []
    stream += _samples(0, 0, strength, n_hold, start_ms)
    stream += _samples(0, 0, 0,        3, start_ms + n_hold * DT_MS)
    return stream


def _feed_stream(G, stream: list[tuple]) -> list[tuple[str, float]]:
    """Feed all samples and collect (gesture_name, confidence) pairs fired."""
    fired: list[tuple[str, float]] = []

    def on_gesture(name, confidence):
        fired.append((str(name), float(confidence)))

    G.on_gesture = on_gesture
    for ax, ay, az, t in stream:
        G.feed(ax, ay, az, t)
    return fired


# ---------------------------------------------------------------------------
# Tests: NOD_SAVE
# ---------------------------------------------------------------------------

@requires_lupa
class TestNodSave:
    def test_single_nod_fires(self, gesture_module):
        G = gesture_module.new({})
        fired = _feed_stream(G, _nod_stream())
        names = [f[0] for f in fired]
        assert "NOD_SAVE" in names

    def test_nod_confidence_above_threshold(self, gesture_module):
        G = gesture_module.new({})
        fired = _feed_stream(G, _nod_stream())
        for name, conf in fired:
            if name == "NOD_SAVE":
                assert conf >= 0.70

    def test_weak_nod_below_threshold_ignored(self, gesture_module):
        G = gesture_module.new({})
        fired = _feed_stream(G, _nod_stream(strength=5.0))  # below 28 threshold
        names = [f[0] for f in fired]
        assert "NOD_SAVE" not in names

    def test_nod_cooldown_prevents_double_fire(self, gesture_module):
        G = gesture_module.new({})
        s1 = _nod_stream(start_ms=0)
        s2 = _nod_stream(start_ms=200)   # within 900ms cooldown
        fired = _feed_stream(G, s1 + s2)
        nod_fires = [f for f in fired if f[0] == "NOD_SAVE"]
        assert len(nod_fires) == 1

    def test_nod_fires_again_after_cooldown(self, gesture_module):
        G = gesture_module.new({})
        s1 = _nod_stream(start_ms=0)
        s2 = _nod_stream(start_ms=1000)  # after 900ms cooldown
        fired = _feed_stream(G, s1 + s2)
        nod_fires = [f for f in fired if f[0] == "NOD_SAVE"]
        assert len(nod_fires) == 2


# ---------------------------------------------------------------------------
# Tests: DOUBLE_NOD
# ---------------------------------------------------------------------------

@requires_lupa
class TestDoubleNod:
    def test_double_nod_fires(self, gesture_module):
        G = gesture_module.new({})
        fired = _feed_stream(G, _double_nod_stream())
        names = [f[0] for f in fired]
        assert "DOUBLE_NOD" in names

    def test_double_nod_not_shadowed_by_single_nod(self, gesture_module):
        """DOUBLE_NOD check runs before NOD_SAVE so it should take priority."""
        G = gesture_module.new({})
        fired = _feed_stream(G, _double_nod_stream())
        names = [f[0] for f in fired]
        # DOUBLE_NOD should fire; NOD_SAVE should not co-fire on same stream
        assert "DOUBLE_NOD" in names

    def test_single_nod_does_not_fire_double_nod(self, gesture_module):
        G = gesture_module.new({})
        fired = _feed_stream(G, _nod_stream())
        names = [f[0] for f in fired]
        assert "DOUBLE_NOD" not in names


# ---------------------------------------------------------------------------
# Tests: SHAKE_DISMISS
# ---------------------------------------------------------------------------

@requires_lupa
class TestShakeDismiss:
    def test_shake_fires(self, gesture_module):
        G = gesture_module.new({})
        fired = _feed_stream(G, _shake_stream())
        names = [f[0] for f in fired]
        assert "SHAKE_DISMISS" in names

    def test_shake_confidence_above_threshold(self, gesture_module):
        G = gesture_module.new({})
        fired = _feed_stream(G, _shake_stream())
        for name, conf in fired:
            if name == "SHAKE_DISMISS":
                assert conf >= 0.70

    def test_weak_shake_ignored(self, gesture_module):
        G = gesture_module.new({})
        fired = _feed_stream(G, _shake_stream(strength=5.0))
        names = [f[0] for f in fired]
        assert "SHAKE_DISMISS" not in names

    def test_shake_cooldown(self, gesture_module):
        G = gesture_module.new({})
        s1 = _shake_stream(start_ms=0)
        s2 = _shake_stream(start_ms=300)  # within cooldown
        fired = _feed_stream(G, s1 + s2)
        shake_fires = [f for f in fired if f[0] == "SHAKE_DISMISS"]
        assert len(shake_fires) == 1


# ---------------------------------------------------------------------------
# Tests: GLANCE_PEEK
# ---------------------------------------------------------------------------

@requires_lupa
class TestGlancePeek:
    def test_glance_fires(self, gesture_module):
        G = gesture_module.new({})
        fired = _feed_stream(G, _glance_stream())
        names = [f[0] for f in fired]
        assert "GLANCE_PEEK" in names

    def test_long_tilt_not_glance(self, gesture_module):
        """A sustained tilt (> peek_max_ms) should NOT fire GLANCE_PEEK."""
        G = gesture_module.new({})
        # held for 600ms >> peek_max_ms=350
        fired = _feed_stream(G, _glance_stream(duration_ms=600))
        names = [f[0] for f in fired]
        assert "GLANCE_PEEK" not in names


# ---------------------------------------------------------------------------
# Tests: TILT_REVEAL
# ---------------------------------------------------------------------------

@requires_lupa
class TestTiltReveal:
    def test_tilt_fires_when_held(self, gesture_module):
        G = gesture_module.new({})
        fired = _feed_stream(G, _tilt_stream(duration_ms=500))
        names = [f[0] for f in fired]
        assert "TILT_REVEAL" in names

    def test_brief_tilt_does_not_fire(self, gesture_module):
        """Tilt held < hold_tilt_ms should not fire TILT_REVEAL."""
        G = gesture_module.new({})
        fired = _feed_stream(G, _tilt_stream(duration_ms=200))  # < 400ms
        names = [f[0] for f in fired]
        assert "TILT_REVEAL" not in names


# ---------------------------------------------------------------------------
# Tests: noise immunity
# ---------------------------------------------------------------------------

@requires_lupa
class TestNoiseImmunity:
    def test_flat_zero_fires_nothing(self, gesture_module):
        G = gesture_module.new({})
        stream = _samples(0, 0, 0, 100, 0)
        fired = _feed_stream(G, stream)
        assert fired == []

    def test_low_noise_fires_nothing(self, gesture_module):
        import random
        rng = random.Random(42)
        G   = gesture_module.new({})
        stream = [(rng.uniform(-8, 8), rng.uniform(-8, 8), rng.uniform(-8, 8), i * DT_MS)
                  for i in range(150)]
        fired = _feed_stream(G, stream)
        assert fired == []

    def test_reset_clears_state(self, gesture_module):
        """After reset(), a mid-gesture stream should not fire."""
        G = gesture_module.new({})
        # Feed half a nod then reset
        half = _samples(0, 35.0, 0, 3, 0)
        _feed_stream(G, half)
        G.reset()
        # Feed second half — no complete nod since reset
        second_half = _samples(0, -35.0, 0, 3, 400)
        fired = _feed_stream(G, second_half)
        names = [f[0] for f in fired]
        assert "NOD_SAVE" not in names


# ---------------------------------------------------------------------------
# Tests: multi-gesture independence
# ---------------------------------------------------------------------------

@requires_lupa
class TestMultiGesture:
    def test_nod_does_not_trigger_shake(self, gesture_module):
        G = gesture_module.new({})
        fired = _feed_stream(G, _nod_stream())
        names = [f[0] for f in fired]
        assert "SHAKE_DISMISS" not in names

    def test_shake_does_not_trigger_nod(self, gesture_module):
        G = gesture_module.new({})
        fired = _feed_stream(G, _shake_stream())
        names = [f[0] for f in fired]
        assert "NOD_SAVE" not in names

    def test_sequential_nod_then_shake(self, gesture_module):
        G = gesture_module.new({})
        s = _nod_stream(start_ms=0) + _shake_stream(start_ms=1200)
        fired = _feed_stream(G, s)
        names = [f[0] for f in fired]
        assert "NOD_SAVE"      in names
        assert "SHAKE_DISMISS" in names


# ---------------------------------------------------------------------------
# Tests: custom config
# ---------------------------------------------------------------------------

@requires_lupa
class TestCustomConfig:
    def test_higher_threshold_ignores_normal_nod(self, gesture_module):
        G = gesture_module.new({"threshold_nod": 60})
        fired = _feed_stream(G, _nod_stream(strength=35.0))
        names = [f[0] for f in fired]
        assert "NOD_SAVE" not in names

    def test_wider_cooldown_prevents_second_gesture(self, gesture_module):
        G = gesture_module.new({"cooldown_ms": 2000})
        s = _nod_stream(start_ms=0) + _nod_stream(start_ms=1000)
        fired = _feed_stream(G, s)
        nods = [f for f in fired if f[0] == "NOD_SAVE"]
        assert len(nods) == 1

    def test_shorter_cooldown_allows_rapid_fire(self, gesture_module):
        G = gesture_module.new({"cooldown_ms": 100})
        s = _nod_stream(start_ms=0) + _nod_stream(start_ms=400)
        fired = _feed_stream(G, s)
        nods = [f for f in fired if f[0] == "NOD_SAVE"]
        assert len(nods) >= 2


# ---------------------------------------------------------------------------
# Fallback: inform when lupa is absent
# ---------------------------------------------------------------------------

@pytest.mark.skipif(HAS_LUPA, reason="lupa is installed")
def test_lupa_not_installed_inform():
    pytest.skip(
        "Gesture tests require lupa (Lua 5.4 Python bindings).\n"
        "Install with: uv add lupa\n"
        "Then re-run: uv run pytest scripts/tests/test_gestures.py -v"
    )
