"""
pytest tests for halo-lua/app/imu_gesture.lua.

Runs the Lua classifier under lupa (Lua 5.4/5.5 via Python bindings).
Falls back gracefully with a clear skip message if lupa is not installed.

Install: uv add lupa

All tests are pure synthetic IMU streams — no hardware, no BLE.

Lupa notes
----------
* lua55 always returns require() as (table, path) — _lua_require unwraps it.
* Lua colon-methods need explicit self from Python: G.feed(G, ...).
* Python functions cannot be reliably written into Lua table fields after
  construction via attribute assignment.  Instead we inject a Lua-side
  collector table at new() time and read it back from Python after feeding.

EMA seeding
-----------
The gesture classifier uses an EMA smoother (alpha=0.35).  Rather than
prepending priming samples (which generate spurious crossings, fire early,
and consume cooldowns), every _run() call passes seed_ema_x/y/z so each
axis starts pre-settled at the first expected peak of the incoming stream.
The peak detector's last_sign is initialised to match, so the first
genuine direction change is captured immediately.
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

# Default seed values: EMA starts settled at peak so the first sample
# heading toward the opposite pole immediately generates a crossing.
_NOD_SEED   =  35.0   # Y-axis starts at +peak for nod streams
_SHAKE_SEED = -32.0   # X-axis starts at -peak for shake streams
_TILT_SEED  = -25.0   # Z-axis starts at -peak for tilt streams
_GLANCE_SEED =  25.0  # Z-axis starts at +peak for glance streams


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


# ---------------------------------------------------------------------------
# _new_with_collector
# ---------------------------------------------------------------------------

def _new_with_collector(M, lua, **cfg):
    """
    Injects a Lua-side on_gesture collector into the instance so Python
    can read results without needing to assign a Python callable after the
    fact (which lupa/lua55 does not support reliably).
    """
    lua.execute("""
        _test_fired = {}
        _test_on_gesture = function(name, confidence)
            _test_fired[#_test_fired + 1] = {name, confidence}
        end
    """)
    cfg["on_gesture"] = lua.eval("_test_on_gesture")
    G = M.new(lua.table(**cfg))
    fired_ref = lua.eval("_test_fired")
    return G, fired_ref


def _collect(lua, fired_ref):
    """Convert the Lua-side fired list to Python [(name, confidence), ...]."""
    results = []
    i = 1
    while True:
        entry = fired_ref[i]
        if entry is None:
            break
        results.append((str(entry[1]), float(entry[2])))
        i += 1
    return results


def _feed(G, stream):
    """Feed all (ax, ay, az, t) samples; G:feed needs explicit self."""
    for ax, ay, az, t in stream:
        G.feed(G, ax, ay, az, t)


def _run(M, lua, stream, **cfg):
    """One-shot: create instance, feed stream, return [(name, conf), ...]."""
    G, fired_ref = _new_with_collector(M, lua, **cfg)
    _feed(G, stream)
    return _collect(lua, fired_ref)


# ---------------------------------------------------------------------------
# Stream builder helpers
# ---------------------------------------------------------------------------

FPS   = 50
DT_MS = 1000 // FPS   # 20 ms per sample


def _samples(ax=0.0, ay=0.0, az=0.0, count=1, start_ms=0):
    return [(ax, ay, az, start_ms + i * DT_MS) for i in range(count)]


# ---------------------------------------------------------------------------
# NOD stream  (Y-axis: + → - → rest)
#
# With seed_ema_y=+peak the EMA is already above +threshold, last_sign=+1.
# The stream moves Y to -peak immediately → first sample crossing to -1
# is recorded.  Pattern [+1, -1] satisfies match_nod.
# ---------------------------------------------------------------------------

def _nod_stream(start_ms=0, strength=35.0):
    t = start_ms
    s  = _samples(0,  strength, 0, 4, t);  t += 4 * DT_MS   # confirm +peak
    s += _samples(0, -strength, 0, 6, t);  t += 6 * DT_MS   # cross to -peak
    s += _samples(0,  0,        0, 3, t)                     # return to rest
    return s


# ---------------------------------------------------------------------------
# DOUBLE NOD stream  (Y-axis: + → - → + → - within gesture_window_ms=600)
#
# Inter-nod gap must be small so all 4 crossings land within 600 ms.
# Total: 4+4+4+4 = 16 samples × 20 ms = 320 ms < 600 ms.
# ---------------------------------------------------------------------------

def _double_nod_stream(start_ms=0, strength=35.0):
    t = start_ms
    s  = _samples(0,  strength, 0, 4, t);  t += 4 * DT_MS
    s += _samples(0, -strength, 0, 4, t);  t += 4 * DT_MS
    s += _samples(0,  strength, 0, 4, t);  t += 4 * DT_MS
    s += _samples(0, -strength, 0, 4, t);  t += 4 * DT_MS
    s += _samples(0,  0,        0, 3, t)
    return s


# ---------------------------------------------------------------------------
# SHAKE stream  (X-axis: - → + → - → rest, 3 alternating crossings)
#
# With seed_ema_x=-peak, last_sign=-1.  Stream moves to +peak (crossing
# +1), back to -peak (crossing -1), then to +peak (-→ third crossing +1)
# giving [-1(seed), +1, -1, +1] — match_shake sees 3 alternating entries.
# Wait: last_sign is pre-seeded to -1 but no crossing is stored yet.
# The first sample at +peak records crossing +1, then -peak records -1,
# then +peak records +1 → crossings = [+1,-1,+1] → match_shake passes.
# ---------------------------------------------------------------------------

def _shake_stream(start_ms=0, strength=32.0):
    t = start_ms
    s  = _samples( strength, 0, 0, 5, t);  t += 5 * DT_MS   # cross +
    s += _samples(-strength, 0, 0, 5, t);  t += 5 * DT_MS   # cross -
    s += _samples( strength, 0, 0, 5, t);  t += 5 * DT_MS   # cross +
    s += _samples( 0,        0, 0, 3, t)                     # rest
    return s


# ---------------------------------------------------------------------------
# GLANCE stream  (Z-axis: +peak briefly then rest)
#
# With seed_ema_z=+peak, last_sign=+1, crossings=[].  The stream holds
# +peak for duration_ms then returns to 0.  While at +peak, match_glance
# returns nil (crossings is empty — no NEW crossing has been recorded).
# When Z drops to 0, the EMA falls below +threshold: next peaks_feed call
# does NOT record a crossing (sign becomes 0, not -1).  _glance_active was
# set... wait — match_glance only fires when crossings==[+1].  We need the
# initial rise to register.
#
# Strategy: start seed at 0 (not pre-seeded), deliver +peak samples so the
# EMA crosses +threshold organically, then drop back to 0.  The EMA with
# alpha=0.35 needs ~6 samples to cross 20 from 0:
#   after 1: 8.75  after 2: 14.2  after 3: 17.7  after 4: 20.0 ← crosses!
# So 4 samples at 25.0 is sufficient to cross threshold_tilt=20.
# ---------------------------------------------------------------------------

def _glance_stream(start_ms=0, strength=25.0, duration_ms=120):
    t  = start_ms
    # Organic rise — no seed — so crossing is recorded naturally
    rise = 4   # samples needed for EMA to cross threshold_tilt=20 at strength=25
    n    = max(1, duration_ms // DT_MS)
    s  = _samples(0, 0, strength, rise + n, t);  t += (rise + n) * DT_MS
    s += _samples(0, 0, 0,                3, t)
    return s


# ---------------------------------------------------------------------------
# TILT stream  (Z-axis: sustained -peak for duration_ms)
#
# TILT_REVEAL uses sustained-value logic (no crossing needed), just
# sz < -threshold for hold_tilt_ms=400 ms.  With seed_ema_z=-peak the
# EMA is already below -threshold on sample 1.
# ---------------------------------------------------------------------------

def _tilt_stream(start_ms=0, strength=-25.0, duration_ms=500):
    t  = start_ms
    n  = max(1, duration_ms // DT_MS)
    s  = _samples(0, 0, strength, n, t);  t += n * DT_MS
    s += _samples(0, 0, 0,        3, t)
    return s


def _names(fired):
    return [f[0] for f in fired]


# ---------------------------------------------------------------------------
# Tests: NOD_SAVE
# ---------------------------------------------------------------------------

@requires_lupa
class TestNodSave:
    def test_single_nod_fires(self, lua, gesture_module):
        assert "NOD_SAVE" in _names(
            _run(gesture_module, lua, _nod_stream(), seed_ema_y=_NOD_SEED))

    def test_nod_confidence_above_threshold(self, lua, gesture_module):
        for name, conf in _run(gesture_module, lua, _nod_stream(), seed_ema_y=_NOD_SEED):
            if name == "NOD_SAVE":
                assert conf >= 0.70

    def test_weak_nod_below_threshold_ignored(self, lua, gesture_module):
        # strength=5 < threshold=28; seed at 5 so last_sign stays 0
        assert "NOD_SAVE" not in _names(
            _run(gesture_module, lua, _nod_stream(strength=5.0), seed_ema_y=5.0))

    def test_nod_cooldown_prevents_double_fire(self, lua, gesture_module):
        # Second nod starts 200 ms after first — within cooldown_ms=900
        s = _nod_stream(0) + _nod_stream(200)
        fired = _run(gesture_module, lua, s, seed_ema_y=_NOD_SEED)
        assert len([f for f in fired if f[0] == "NOD_SAVE"]) == 1

    def test_nod_fires_again_after_cooldown(self, lua, gesture_module):
        # Second nod at t=2000 ms — well past cooldown_ms=900
        s = _nod_stream(0) + _nod_stream(2000)
        fired = _run(gesture_module, lua, s, seed_ema_y=_NOD_SEED)
        assert len([f for f in fired if f[0] == "NOD_SAVE"]) == 2


# ---------------------------------------------------------------------------
# Tests: DOUBLE_NOD
# ---------------------------------------------------------------------------

@requires_lupa
class TestDoubleNod:
    def test_double_nod_fires(self, lua, gesture_module):
        assert "DOUBLE_NOD" in _names(
            _run(gesture_module, lua, _double_nod_stream(), seed_ema_y=_NOD_SEED))

    def test_double_nod_not_shadowed_by_single_nod(self, lua, gesture_module):
        assert "DOUBLE_NOD" in _names(
            _run(gesture_module, lua, _double_nod_stream(), seed_ema_y=_NOD_SEED))

    def test_single_nod_does_not_fire_double_nod(self, lua, gesture_module):
        assert "DOUBLE_NOD" not in _names(
            _run(gesture_module, lua, _nod_stream(), seed_ema_y=_NOD_SEED))


# ---------------------------------------------------------------------------
# Tests: SHAKE_DISMISS
# ---------------------------------------------------------------------------

@requires_lupa
class TestShakeDismiss:
    def test_shake_fires(self, lua, gesture_module):
        assert "SHAKE_DISMISS" in _names(
            _run(gesture_module, lua, _shake_stream(), seed_ema_x=_SHAKE_SEED))

    def test_shake_confidence_above_threshold(self, lua, gesture_module):
        for name, conf in _run(gesture_module, lua, _shake_stream(), seed_ema_x=_SHAKE_SEED):
            if name == "SHAKE_DISMISS":
                assert conf >= 0.70

    def test_weak_shake_ignored(self, lua, gesture_module):
        assert "SHAKE_DISMISS" not in _names(
            _run(gesture_module, lua, _shake_stream(strength=5.0), seed_ema_x=-5.0))

    def test_shake_cooldown(self, lua, gesture_module):
        # Second shake at t=300 ms — within cooldown_ms=900
        s = _shake_stream(0) + _shake_stream(300)
        fired = _run(gesture_module, lua, s, seed_ema_x=_SHAKE_SEED)
        assert len([f for f in fired if f[0] == "SHAKE_DISMISS"]) == 1


# ---------------------------------------------------------------------------
# Tests: GLANCE_PEEK
# ---------------------------------------------------------------------------

@requires_lupa
class TestGlancePeek:
    def test_glance_fires(self, lua, gesture_module):
        # No seed — organic EMA rise so crossing is recorded
        assert "GLANCE_PEEK" in _names(
            _run(gesture_module, lua, _glance_stream()))

    def test_long_tilt_not_glance(self, lua, gesture_module):
        # duration_ms=600 > peek_max_ms=350 → should NOT fire GLANCE_PEEK
        assert "GLANCE_PEEK" not in _names(
            _run(gesture_module, lua, _glance_stream(duration_ms=600)))


# ---------------------------------------------------------------------------
# Tests: TILT_REVEAL
# ---------------------------------------------------------------------------

@requires_lupa
class TestTiltReveal:
    def test_tilt_fires_when_held(self, lua, gesture_module):
        assert "TILT_REVEAL" in _names(
            _run(gesture_module, lua, _tilt_stream(duration_ms=500), seed_ema_z=_TILT_SEED))

    def test_brief_tilt_does_not_fire(self, lua, gesture_module):
        # duration_ms=200 < hold_tilt_ms=400 → should NOT fire
        assert "TILT_REVEAL" not in _names(
            _run(gesture_module, lua, _tilt_stream(duration_ms=200), seed_ema_z=_TILT_SEED))


# ---------------------------------------------------------------------------
# Tests: noise immunity
# ---------------------------------------------------------------------------

@requires_lupa
class TestNoiseImmunity:
    def test_flat_zero_fires_nothing(self, lua, gesture_module):
        assert _run(gesture_module, lua, _samples(0, 0, 0, 100, 0)) == []

    def test_low_noise_fires_nothing(self, lua, gesture_module):
        import random
        rng = random.Random(42)
        stream = [(rng.uniform(-8, 8), rng.uniform(-8, 8), rng.uniform(-8, 8), i * DT_MS)
                  for i in range(150)]
        assert _run(gesture_module, lua, stream) == []

    def test_reset_clears_state(self, lua, gesture_module):
        G, fired_ref = _new_with_collector(gesture_module, lua)
        _feed(G, _samples(0, 35.0, 0, 3, 0))
        G.reset(G)
        _feed(G, _samples(0, -35.0, 0, 3, 400))
        assert "NOD_SAVE" not in _names(_collect(lua, fired_ref))


# ---------------------------------------------------------------------------
# Tests: multi-gesture independence
# ---------------------------------------------------------------------------

@requires_lupa
class TestMultiGesture:
    def test_nod_does_not_trigger_shake(self, lua, gesture_module):
        assert "SHAKE_DISMISS" not in _names(
            _run(gesture_module, lua, _nod_stream(), seed_ema_y=_NOD_SEED))

    def test_shake_does_not_trigger_nod(self, lua, gesture_module):
        assert "NOD_SAVE" not in _names(
            _run(gesture_module, lua, _shake_stream(), seed_ema_x=_SHAKE_SEED))

    def test_sequential_nod_then_shake(self, lua, gesture_module):
        nod   = _nod_stream(0)
        # Shake starts well after nod cooldown (900 ms) expires
        shake = _shake_stream(nod[-1][3] + 1000)
        fired = _run(gesture_module, lua, nod + shake,
                     seed_ema_y=_NOD_SEED, seed_ema_x=_SHAKE_SEED)
        names = _names(fired)
        assert "NOD_SAVE"      in names
        assert "SHAKE_DISMISS" in names


# ---------------------------------------------------------------------------
# Tests: custom config
# ---------------------------------------------------------------------------

@requires_lupa
class TestCustomConfig:
    def test_higher_threshold_ignores_normal_nod(self, lua, gesture_module):
        # threshold_nod=60 > strength=35 → EMA never crosses, no NOD_SAVE
        fired = _run(gesture_module, lua, _nod_stream(strength=35.0),
                     seed_ema_y=35.0, threshold_nod=60)
        assert "NOD_SAVE" not in _names(fired)

    def test_wider_cooldown_prevents_second_gesture(self, lua, gesture_module):
        # cooldown_ms=5000, second nod at t=2000 → blocked
        fired = _run(gesture_module, lua, _nod_stream(0) + _nod_stream(2000),
                     seed_ema_y=_NOD_SEED, cooldown_ms=5000)
        assert len([f for f in fired if f[0] == "NOD_SAVE"]) == 1

    def test_shorter_cooldown_allows_rapid_fire(self, lua, gesture_module):
        # cooldown_ms=100, second nod at t=400 → allowed
        fired = _run(gesture_module, lua, _nod_stream(0) + _nod_stream(400),
                     seed_ema_y=_NOD_SEED, cooldown_ms=100)
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
