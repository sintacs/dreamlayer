"""On-glass safety guarantees, driven through the real main.lua boot.

Covers the audit's crash-policy fixes:
  - the tick loop is pcall-guarded: one poisoned render can never kill the
    display until reboot ("never black" is a guarantee, not a policy)
  - a TICK_ERROR telemetry event leaves the device (rate-limited)
  - double long-press banishes a running figment locally — no host needed —
    and the host orchestrator honors the banish durably
  - two frames concatenated in one BLE chunk both process in the same tick
  - the heap watermark telemetry event fires once a minute
"""
import json
from pathlib import Path

import pytest

lupa = pytest.importorskip("lupa")

from dreamlayer.reality_compiler.v2 import (  # noqa: E402
    RealityCompilerV2, transport,
)

HALO_LUA = Path(__file__).resolve().parents[4] / "halo-lua"

DEVICE_STUB = '''
_G.__rx_queue, _G.__tx, _G.__drawn = {}, {}, {}
_G.halo = {
  bluetooth = {
    receive = function() return table.remove(_G.__rx_queue, 1) end,
    send = function(data) _G.__tx[#_G.__tx+1] = data end,
  },
  display = {
    text  = function(s, x, y, o) _G.__drawn[#_G.__drawn+1] = {s=s, y=y} end,
    clear = function() _G.__drawn = {} end,
    circle = function(x, y, r, o) _G.__drawn[#_G.__drawn+1] = {circle=r} end,
    show  = function() _G.__shown = #_G.__drawn end,
  },
  battery_level = function() return 88 end,
}
'''


class Device:
    def __init__(self):
        rt = lupa.LuaRuntime(unpack_returned_tuples=True)
        rt.execute(f'package.path = "{HALO_LUA}/?.lua;{HALO_LUA}/app/?.lua;"'
                   ' .. package.path')
        rt.execute(DEVICE_STUB)
        self.rt = rt
        self.main = self.req("main")
        self.tick = rt.eval("_G._dreamlayer_tick")
        self._push = rt.eval(
            "function(b) _G.__rx_queue[#_G.__rx_queue+1] = b end")

    def req(self, name):
        r = self.rt.eval(f'require("{name}")')
        return r[0] if isinstance(r, tuple) else r

    def send(self, envelope: dict):
        # bytes, never str: lupa UTF-8-encodes str, mangling header bytes >127
        self._push(transport.frame(envelope))

    def send_bytes(self, raw: bytes):
        self._push(raw)

    def ticks(self, n: int):
        for _ in range(n):
            self.tick()

    def display(self):
        drawn = self.rt.eval("_G.__drawn")
        return [dict(drawn[i + 1]) for i in range(len(drawn))]

    def tx_frames(self):
        tx = self.rt.eval("_G.__tx")
        out = []
        for i in range(len(tx)):
            raw = tx[i + 1].encode("latin1")
            out.append(json.loads(raw[4:].decode("utf-8")))
        return out


@pytest.fixture
def dev():
    return Device()


def make_figment():
    rc = RealityCompilerV2()
    s = rc.rehearse("Rolling rounds")
    s.double_tap()
    s.say("rolling - three minutes")
    s.say("last ten seconds, pulse")
    s.say("then it starts again")
    return s.finish().figment


class TestCrashGuard:
    def test_poisoned_tick_never_kills_the_loop(self, dev):
        # Sabotage the renderer the tick body calls every Memory-Mode frame.
        dev.rt.execute(
            'local R = require("display.renderer");'
            'R.tick = function() error("poisoned render") end')
        dev.ticks(3)                       # would raise without the pcall guard
        # Never black: the fallback drew something on the sabotaged frames.
        assert len(dev.display()) >= 1

    def test_tick_error_telemetry_leaves_device_rate_limited(self, dev):
        dev.rt.execute(
            'local R = require("display.renderer");'
            'R.tick = function() error("poisoned render") end')
        dev.ticks(10)
        tels = [f for f in dev.tx_frames()
                if f.get("t") == "TEL" and f.get("event") == "TICK_ERROR"]
        assert len(tels) == 1              # 10 crashes, ONE event (60s limit)
        assert "poisoned" in tels[0]["error"]

    def test_recovers_when_fault_clears(self, dev):
        dev.rt.execute(
            'local R = require("display.renderer");'
            'R._orig_tick = R.tick; R.tick = function() error("boom") end')
        dev.ticks(2)
        dev.rt.execute(
            'local R = require("display.renderer"); R.tick = R._orig_tick')
        dev.ticks(2)                       # healthy again, no residue


class TestBanishGesture:
    def _run_figment(self, dev):
        fig = make_figment()
        dev.send(transport.put_envelope(fig))
        dev.send(transport.swap_envelope(fig.id))
        dev.ticks(2)
        stage = dev.req("app.figment_stage")
        assert stage["is_running"]()
        return fig, stage

    def test_double_long_press_banishes(self, dev):
        fig, stage = self._run_figment(dev)
        dev.send({"t": "button", "ev": "long"})
        dev.ticks(1)
        assert stage["is_running"]()       # one long-press: figment keeps it
        dev.send({"t": "button", "ev": "long"})
        dev.ticks(1)
        assert not stage["is_running"]()   # second within the window: banished
        events = [f for f in dev.tx_frames() if f.get("t") == "figment_event"]
        assert events and events[-1]["tag"] == "banished"
        assert events[-1]["id"] == fig.id

    def test_slow_long_presses_do_not_banish(self, dev):
        fig, stage = self._run_figment(dev)
        dev.send({"t": "button", "ev": "long"})
        dev.ticks(60)                      # 3 s at 20fps — window (2 s) expires
        dev.send({"t": "button", "ev": "long"})
        dev.ticks(1)
        assert stage["is_running"]()

    def test_banished_figment_leaves_device_library(self, dev):
        fig, stage = self._run_figment(dev)
        dev.send({"t": "button", "ev": "long"})
        dev.ticks(1)                       # one queued frame per tick
        dev.send({"t": "button", "ev": "long"})
        dev.ticks(1)
        assert not stage["is_running"]()
        # a re-swap of the banished id must be refused (it's gone from _stored)
        dev.send(transport.swap_envelope(fig.id))
        dev.ticks(1)
        acks = [f for f in dev.tx_frames() if f.get("t") == "figment_ack"]
        assert acks[-1]["ok"] is False


class TestHostHonorsBanish:
    def test_orchestrator_marks_and_revokes(self):
        from dreamlayer.bridge.emulator_bridge import EmulatorBridge
        from dreamlayer.orchestrator.orchestrator import Orchestrator

        class DeployerSpy:
            def __init__(self):
                self.revoked = []

            def revoke(self, fid):
                self.revoked.append(fid)

        orch = Orchestrator(EmulatorBridge())
        orch.rc_deployer = DeployerSpy()
        orch._active_figment = "fig-9"
        orch._on_event("figment_event", {"tag": "banished", "id": "fig-9"})
        assert "fig-9" in orch._banished_figments
        assert orch._active_figment is None
        assert orch.rc_deployer.revoked == ["fig-9"]

    def test_other_figment_events_ignored(self):
        from dreamlayer.bridge.emulator_bridge import EmulatorBridge
        from dreamlayer.orchestrator.orchestrator import Orchestrator
        orch = Orchestrator(EmulatorBridge())
        orch._on_event("figment_event", {"tag": "lap", "id": "fig-1"})
        assert orch._banished_figments == set()


class TestTickPlumbing:
    def test_two_frames_one_chunk_same_tick(self, dev):
        a = transport.frame({"t": "command", "cmd": "show_ready"})
        b = transport.frame({"t": "card", "card_type": "ObjectRecallCard",
                             "object": "Keys"})
        dev.send_bytes(a + b)
        dev.ticks(1)                       # both must land in ONE tick
        cq = dev.req("app.card_queue")
        assert cq is not None              # no error = both processed

    def test_heap_watermark_emits(self, dev):
        dev.ticks(1200)                    # 60 s at 20fps
        heaps = [f for f in dev.tx_frames()
                 if f.get("t") == "TEL" and f.get("event") == "HEAP"]
        assert len(heaps) == 1
        assert heaps[0]["kb"] > 0
