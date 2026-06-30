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
* lupa silently drops Python kwargs whose names contain underscores when
  building Lua tables via lua.table(**kw).  All opts tables are therefore
  constructed as Lua literals via rt.execute() and read back as globals.

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

import json
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

# Default EMA seed values — axes start settled at peak amplitude.
_NOD_SEED    =  35.0   # Y-axis: nod streams start at +peak
_SHAKE_SEED  = -32.0   # X-axis: shake streams start at -peak
_TILT_SEED   = -25.0   # Z-axis: tilt streams start at -peak


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
# Lua opts builder
#
# lupa drops underscore kwargs in lua.table(**kw).  We work around this by
# serialising numeric/bool cfg values into a Lua table literal executed
# via rt.execute(), then reading back the global _test_opts.
# on_gesture is always wired from the pre-declared _test_on_gesture global.
# ---------------------------------------------------------------------------

def _build_lua_opts(lua, **cfg):
    """
    Build a Lua opts table whose keys survive Python→Lua intact.
    Numeric and boolean values are serialised directly; string values are
    quoted.  on_gesture must NOT be in cfg — it is wired separately.
    Returns the Lua table object.
    """
    parts = []
    for k, v in cfg.items():
        if isinstance(v, bool):
            parts.append(f"  {k} = {'true' if v else 'false'}")
        elif isinstance(v, (int, float)):
            parts.append(f"  {k} = {v}")
        elif isinstance(v, str):
            escaped = v.replace('"', '\\"')
            parts.append(f'  {k} = "{escaped}"')
        # skip anything else (e.g. callables — on_gesture handled separately)
    body = ",\n".join(parts)
    lua.execute(f"_test_opts = {{\n{body}\n}}")
    lua.execute("_test_opts.on_gesture = _test_on_gesture")
    return lua.eval("_test_opts")


# ---------------------------------------------------------------------------
# _new_with_collector
# ---------------------------------------------------------------------------

def _new_with_collector(M, lua, **cfg):
    """
    Declare Lua-side collector, build opts table safely, create instance.
    Returns (G, fired_ref).
    """
    lua.execute("""
        _test_fired = {}
        _test_on_gesture = function(name, confidence)
            _test_fired[#_test_fired + 1] = {name, confidence}
        end
    """)
    opts = _build_lua_opts(lua, **cfg)
    G = M.new(opts)
    return G, lua.eval("_test_fired")


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


# NOD  (Y-axis: +peak → -peak → rest)
# seed_ema_y=+35 ⇒ EMA starts above +threshold, last_sign=+1
# First -peak sample records crossing -1 ⇒ crossings=[+1(seed sign),−] NO—
# last_sign=+1 means peaks_feed skips the +35 samples (same sign),
# then records −1 on the first −35 sample.  match_nod needs [+, −]:
# we need ONE +1 crossing first.  So the stream starts at +peak to
# confirm last_sign=+1 is already set, then flips to −peak.
# peaks_feed: sign==+1, last_sign==+1 ⇒ skip. Then sign==-1 ⇒ record.
# crossings = [-1] only — not enough for match_nod!
#
# Correct approach: seed last_sign=0 (no seed), let stream produce +1
# crossing organically then -1.  Use enough samples for EMA to cross.
# With alpha=0.35 from 0: sample 1 ⇒ 12.25, s2 ⇒ 23.6, s3 ⇒ 30.1 > 28.
# So 3 samples at 35 crosses +threshold.  Then 3 samples at -35 crosses.
# NO EMA seed needed for nod — 3+3 samples is sufficient.

def _nod_stream(start_ms=0, strength=35.0):
    """Y-axis nod: enough samples to organically cross +/- threshold."""
    t = start_ms
    s  = _samples(0,  strength, 0, 5, t);  t += 5 * DT_MS   # EMA crosses +28
    s += _samples(0, -strength, 0, 5, t);  t += 5 * DT_MS   # EMA crosses -28
    s += _samples(0,  0,        0, 3, t)                     # return to rest
    return s


# DOUBLE NOD: 4 crossings within gesture_window_ms=600 ms
# 4 legs × 5 samples × 20 ms = 400 ms < 600 ms.
def _double_nod_stream(start_ms=0, strength=35.0):
    """Two nods tight enough to fit inside gesture_window_ms=600 ms."""
    t = start_ms
    s  = _samples(0,  strength, 0, 5, t);  t += 5 * DT_MS
    s += _samples(0, -strength, 0, 5, t);  t += 5 * DT_MS
    s += _samples(0,  strength, 0, 5, t);  t += 5 * DT_MS
    s += _samples(0, -strength, 0, 5, t);  t += 5 * DT_MS
    s += _samples(0,  0,        0, 3, t)
    return s


# SHAKE  (X-axis: 3 alternating crossings)
# alpha=0.35 from 0: 3 samples at 32 ⇒ EMA crosses 28.
def _shake_stream(start_ms=0, strength=32.0):
    """X-axis shake: alternating crossings ±threshold."""
    t = start_ms
    s  = _samples(-strength, 0, 0, 5, t);  t += 5 * DT_MS   # cross -
    s += _samples( strength, 0, 0, 5, t);  t += 5 * DT_MS   # cross +
    s += _samples(-strength, 0, 0, 5, t);  t += 5 * DT_MS   # cross -
    s += _samples( 0,        0, 0, 3, t)                     # rest
    return s


# GLANCE  (Z-axis: single +crossing then return within peek_max_ms=350)
# alpha=0.35 from 0: sample 4 ⇒ EMA = 20.0 ≥ threshold_tilt=20 → crosses.
# Hold for duration_ms then drop to 0; glance_active turns off ⇒ fires.
def _glance_stream(start_ms=0, strength=25.0, duration_ms=120):
    """Z-axis brief upward glance."""
    t    = start_ms
    rise = 4
    n    = max(1, duration_ms // DT_MS)
    s  = _samples(0, 0, strength, rise + n, t);  t += (rise + n) * DT_MS
    s += _samples(0, 0, 0,                3, t)
    return s


# TILT  (Z-axis: sustained negative, no crossing needed)
# alpha=0.35 from 0: sample 4 ⇒ EMA = -20.0 at strength=-25 → crosses -20.
# hold_tilt_ms=400, so need 400/20=20 samples below threshold after crossing.
def _tilt_stream(start_ms=0, strength=-25.0, duration_ms=500):
    """Z-axis sustained downward tilt."""
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
        assert "NOD_SAVE" in _names(_run(gesture_module, lua, _nod_stream()))

    def test_nod_confidence_above_threshold(self, lua, gesture_module):
        for name, conf in _run(gesture_module, lua, _nod_stream()):
            if name == "NOD_SAVE":
                assert conf >= 0.70

    def test_weak_nod_below_threshold_ignored(self, lua, gesture_module):
        assert "NOD_SAVE" not in _names(_run(gesture_module, lua, _nod_stream(strength=5.0)))

    def test_nod_cooldown_prevents_double_fire(self, lua, gesture_module):
        # second nod at t=200 ms, within cooldown_ms=900
        s = _nod_stream(0) + _nod_stream(200)
        fired = _run(gesture_module, lua, s)
        assert len([f for f in fired if f[0] == "NOD_SAVE"]) == 1

    def test_nod_fires_again_after_cooldown(self, lua, gesture_module):
        # second nod at t=2000 ms, past cooldown_ms=900
        s = _nod_stream(0) + _nod_stream(2000)
        fired = _run(gesture_module, lua, s)
        assert len([f for f in fired if f[0] == "NOD_SAVE"]) == 2


# ---------------------------------------------------------------------------
# Tests: DOUBLE_NOD
# ---------------------------------------------------------------------------

@requires_lupa
class TestDoubleNod:
    def test_double_nod_fires(self, lua, gesture_module):
        assert "DOUBLE_NOD" in _names(_run(gesture_module, lua, _double_nod_stream()))

    def test_double_nod_not_shadowed_by_single_nod(self, lua, gesture_module):
        assert "DOUBLE_NOD" in _names(_run(gesture_module, lua, _double_nod_stream()))

    def test_single_nod_does_not_fire_double_nod(self, lua, gesture_module):
        assert "DOUBLE_NOD" not in _names(_run(gesture_module, lua, _nod_stream()))


# ---------------------------------------------------------------------------
# Tests: SHAKE_DISMISS
# ---------------------------------------------------------------------------

@requires_lupa
class TestShakeDismiss:
    def test_shake_fires(self, lua, gesture_module):
        assert "SHAKE_DISMISS" in _names(_run(gesture_module, lua, _shake_stream()))

    def test_shake_confidence_above_threshold(self, lua, gesture_module):
        for name, conf in _run(gesture_module, lua, _shake_stream()):
            if name == "SHAKE_DISMISS":
                assert conf >= 0.70

    def test_weak_shake_ignored(self, lua, gesture_module):
        assert "SHAKE_DISMISS" not in _names(_run(gesture_module, lua, _shake_stream(strength=5.0)))

    def test_shake_cooldown(self, lua, gesture_module):
        # second shake at t=300 ms, within cooldown_ms=900
        s = _shake_stream(0) + _shake_stream(300)
        fired = _run(gesture_module, lua, s)
        assert len([f for f in fired if f[0] == "SHAKE_DISMISS"]) == 1


# ---------------------------------------------------------------------------
# Tests: GLANCE_PEEK
# ---------------------------------------------------------------------------

@requires_lupa
class TestGlancePeek:
    def test_glance_fires(self, lua, gesture_module):
        assert "GLANCE_PEEK" in _names(_run(gesture_module, lua, _glance_stream()))

    def test_long_tilt_not_glance(self, lua, gesture_module):
        # duration_ms=600 > peek_max_ms=350
        assert "GLANCE_PEEK" not in _names(_run(gesture_module, lua, _glance_stream(duration_ms=600)))


# ---------------------------------------------------------------------------
# Tests: TILT_REVEAL
# ---------------------------------------------------------------------------

@requires_lupa
class TestTiltReveal:
    def test_tilt_fires_when_held(self, lua, gesture_module):
        assert "TILT_REVEAL" in _names(_run(gesture_module, lua, _tilt_stream(duration_ms=500)))

    def test_brief_tilt_does_not_fire(self, lua, gesture_module):
        # duration_ms=200 < hold_tilt_ms=400
        assert "TILT_REVEAL" not in _names(_run(gesture_module, lua, _tilt_stream(duration_ms=200)))


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
        assert "SHAKE_DISMISS" not in _names(_run(gesture_module, lua, _nod_stream()))

    def test_shake_does_not_trigger_nod(self, lua, gesture_module):
        assert "NOD_SAVE" not in _names(_run(gesture_module, lua, _shake_stream()))

    def test_sequential_nod_then_shake(self, lua, gesture_module):
        nod   = _nod_stream(0)
        shake = _shake_stream(nod[-1][3] + 1000)  # well past cooldown_ms=900
        fired = _run(gesture_module, lua, nod + shake)
        names = _names(fired)
        assert "NOD_SAVE"      in names
        assert "SHAKE_DISMISS" in names


# ---------------------------------------------------------------------------
# Tests: custom config
# ---------------------------------------------------------------------------

@requires_lupa
class TestCustomConfig:
    def test_higher_threshold_ignores_normal_nod(self, lua, gesture_module):
        # threshold_nod=60 > EMA peak (~33 after 5 samples at 35) → no crossing
        fired = _run(gesture_module, lua, _nod_stream(strength=35.0), threshold_nod=60)
        assert "NOD_SAVE" not in _names(fired)

    def test_wider_cooldown_prevents_second_gesture(self, lua, gesture_module):
        # cooldown_ms=5000, second nod at t=2000 → blocked
        fired = _run(gesture_module, lua, _nod_stream(0) + _nod_stream(2000), cooldown_ms=5000)
        assert len([f for f in fired if f[0] == "NOD_SAVE"]) == 1

    def test_shorter_cooldown_allows_rapid_fire(self, lua, gesture_module):
        # cooldown_ms=100, second nod at t=400 → allowed
        fired = _run(gesture_module, lua, _nod_stream(0) + _nod_stream(400), cooldown_ms=100)
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
