"""test_imu_gesture_device.py — Nod to Remember, on-glass half. Boots the real
halo-lua/main.lua with the IMU boot flag ON and an accelerometer stub, injects a
synthetic nod trace, and asserts the classifier fires a NOD_SAVE that crosses to
the host as an `imu_gesture` envelope. Also asserts the flag is OFF by default,
so default boot is unchanged."""
import json
from pathlib import Path

import pytest

lupa = pytest.importorskip("lupa")

HALO_LUA = Path(__file__).resolve().parents[4] / "halo-lua"

# Same device stub as test_main_boot, plus an accelerometer + the boot flag.
_STUB = '''
_G.__rx_queue, _G.__tx, _G.__drawn, _G.__imu_queue = {}, {}, {}, {}
_G.halo = {
  bluetooth = {
    receive = function() return table.remove(_G.__rx_queue, 1) end,
    send = function(data) _G.__tx[#_G.__tx+1] = data end,
  },
  display = {
    text  = function(s, x, y, o) _G.__drawn[#_G.__drawn+1] = {s=s, y=y} end,
    clear = function() _G.__drawn = {} end,
    show  = function() _G.__shown = #_G.__drawn end,
  },
  battery_level = function() return 88 end,
  %s
  imu = { read = function()
    local s = table.remove(_G.__imu_queue, 1)
    if not s then return nil end
    return s[1], s[2], s[3]
  end },
}
'''


class _Dev:
    def __init__(self, config_line: str):
        rt = lupa.LuaRuntime(unpack_returned_tuples=True)
        rt.execute(f'package.path = "{HALO_LUA}/?.lua;{HALO_LUA}/app/?.lua;"'
                   ' .. package.path')
        rt.execute(_STUB % config_line)
        self.rt = rt
        r = rt.eval('require("main")')
        self.main = r[0] if isinstance(r, tuple) else r
        self.tick = rt.eval("_G._dreamlayer_tick")
        self._accel = rt.eval(
            "function(x,y,z) _G.__imu_queue[#_G.__imu_queue+1] = {x,y,z} end")

    def push_accel(self, x, y, z):
        self._accel(x, y, z)

    def ticks(self, n):
        for _ in range(n):
            self.tick()

    def tx_frames(self):
        tx = self.rt.eval("_G.__tx")
        out = []
        for i in range(len(tx)):
            raw = tx[i + 1].encode("latin1")
            out.append(json.loads(raw[4:].decode("utf-8")))
        return out


def test_nod_fires_an_imu_gesture_envelope_to_the_host():
    dev = _Dev("config = { imu_gestures = true },")
    # A nod on the Y axis: one +crossing then a −crossing within the 600ms window
    # (threshold 28, EMA a=0.35). X/Z stay 0 so shake/tilt never fire.
    dev.push_accel(0, 100, 0)     # EMA_y 100  → +crossing
    dev.push_accel(0, -100, 0)    # EMA_y 30
    dev.push_accel(0, -100, 0)    # EMA_y -15.5
    dev.push_accel(0, -100, 0)    # EMA_y -45  → −crossing  → NOD_SAVE
    dev.ticks(5)                  # one accel sample consumed per tick
    gestures = [f for f in dev.tx_frames() if f.get("t") == "imu_gesture"]
    assert any(g["gesture"] == "NOD_SAVE" for g in gestures)


def test_imu_gestures_are_off_by_default():
    dev = _Dev("")                # no config.imu_gestures → flag OFF
    dev.push_accel(0, 100, 0)
    dev.push_accel(0, -100, 0)
    dev.push_accel(0, -100, 0)
    dev.push_accel(0, -100, 0)
    dev.ticks(5)
    assert not [f for f in dev.tx_frames() if f.get("t") == "imu_gesture"]
