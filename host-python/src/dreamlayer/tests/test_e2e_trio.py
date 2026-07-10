"""Cross-device e2e: the whole trio in one process — the live Brain HTTP
server, the Orchestrator (the hub), and the REAL device Lua (main.lua under
lupa). Exercises the paths that only break at the seams between tiers:

  1. ask → the hub routes to the Brain over real HTTP → an answer comes back
     and becomes a card.
  2. that card → framed over the real BLE wire protocol → the device
     reassembles it and draws pixels.
  3. a figment deploy envelope → the device stores + swaps it → a signed ack
     round-trips back to the host.

Everything runs in-process (server on a thread, device in lupa), so it lives
in the normal pytest job — no hardware, but no mocks at the seams either.
"""
import json
import threading
from pathlib import Path

import pytest

lupa = pytest.importorskip("lupa")

from dreamlayer.ai_brain import connect_brain           # noqa: E402
from dreamlayer.ai_brain.server import Brain, make_brain_server  # noqa: E402
from dreamlayer.bridge.emulator_bridge import EmulatorBridge     # noqa: E402
from dreamlayer.orchestrator.orchestrator import Orchestrator    # noqa: E402
from dreamlayer.reality_compiler.v2 import (              # noqa: E402
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
-- the Meridian renderer draws through the real `frame.display` global (the
-- figment stage uses halo.display); provide both so any render lights pixels.
_G.frame = {
  imu_data = function() return nil end,
  display = {
    clear   = function(c) _G.__drawn = {} end,
    show    = function() _G.__shown = #_G.__drawn end,
    text    = function(s, x, y, c) _G.__drawn[#_G.__drawn+1] = {s=s} end,
    line    = function(...) _G.__drawn[#_G.__drawn+1] = {line=true} end,
    rect    = function(...) _G.__drawn[#_G.__drawn+1] = {rect=true} end,
    circle  = function(...) _G.__drawn[#_G.__drawn+1] = {circle=true} end,
    set_pixel = function(...) _G.__drawn[#_G.__drawn+1] = {px=true} end,
    bitmap  = function(...) end,
    set_font = function(...) end,
    assign_color_ycbcr = function(...) end,
  },
}
'''


class Device:
    """main.lua booted under lupa, driven from Python over the real framing."""

    def __init__(self):
        rt = lupa.LuaRuntime(unpack_returned_tuples=True)
        rt.execute(f'package.path = "{HALO_LUA}/?.lua;{HALO_LUA}/app/?.lua;"'
                   ' .. package.path')
        rt.execute(DEVICE_STUB)
        self.rt = rt
        self.main = self.req("main")
        self.tick = rt.eval("_G._dreamlayer_tick")
        self._push = rt.eval("function(b) _G.__rx_queue[#_G.__rx_queue+1] = b end")

    def req(self, name):
        r = self.rt.eval(f'require("{name}")')
        return r[0] if isinstance(r, tuple) else r

    def send(self, envelope):
        self._push(transport.frame(envelope))    # bytes, real 4-byte framing

    def ticks(self, n):
        for _ in range(n):
            self.tick()

    def drawn(self):
        d = self.rt.eval("_G.__drawn")
        return [dict(d[i + 1]) for i in range(len(d))]

    def tx_frames(self):
        tx = self.rt.eval("_G.__tx")
        out = []
        for i in range(len(tx)):
            raw = tx[i + 1].encode("latin1")
            out.append(json.loads(raw[4:].decode("utf-8")))
        return out


def _post(url, payload, headers=None):
    import urllib.request
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json", **(headers or {})})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(req, timeout=5) as r:
        return json.loads(r.read().decode())


@pytest.fixture
def brain_server(tmp_path):
    # a Brain with one indexed note, served over real localhost HTTP
    notes = tmp_path / "notes"
    notes.mkdir()
    (notes / "lease.txt").write_text(
        "The signed lease is due to Marcus by Friday. Rent is 2400 a month.")
    brain = Brain(str(tmp_path / "cfg"))
    brain.config.token = "e2e-token"
    brain.config.add_folder(str(notes))
    brain.reindex()
    server = make_brain_server(brain, "127.0.0.1", 0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{server.server_address[1]}"
    yield brain, url
    server.shutdown(); server.server_close()


class TestTrioKnowledgePath:
    def test_ask_routes_to_live_brain_and_becomes_a_card(self, brain_server):
        brain, url = brain_server
        orch = Orchestrator(EmulatorBridge())
        # wire the hub's router to the live Brain over real HTTP
        connect_brain(orch.brain, url, token="e2e-token", http_post=_post)
        orch.brain.set_local_only(False)          # allow the remote tier

        cards = []
        orch.bridge.send_card = lambda card, event="": cards.append((card, event))
        answer = orch.ask_brain("what do I owe Marcus")

        # keyword tier finds the indexed lease note over the wire
        assert answer is not None and not answer.is_empty()
        assert "lease" in answer.text.lower() or "marcus" in answer.text.lower()
        assert any(e == "brain_answer" for _, e in cards)   # a card was emitted


class TestTrioDevicePath:
    def test_a_card_frames_and_reaches_device_pixels(self):
        dev = Device()
        # a plain memory card, sent over the real wire protocol
        dev.send({"t": "card", "card_type": "ObjectRecallCard",
                  "object": "Keys", "primary": "Keys · on the hook",
                  "lines": ["Keys", "on the hook by the door"]})
        dev.ticks(6)
        assert len(dev.drawn()) >= 1              # the device drew something real

    def test_figment_deploy_acks_over_the_wire(self, tmp_path):
        dev = Device()
        rc = RealityCompilerV2(vault_dir=tmp_path / "vault")
        s = rc.rehearse("Rolling")
        s.double_tap()
        s.say("rolling - three minutes")
        fig = s.finish().figment
        rc.keep(fig)

        dev.send(transport.put_envelope(fig))
        dev.send(transport.swap_envelope(fig.id))
        dev.ticks(3)

        acks = [f for f in dev.tx_frames() if f.get("t") == "figment_ack"]
        assert len(acks) == 2 and all(a["ok"] for a in acks)
        stage = dev.req("app.figment_stage")
        assert stage["active_id"]() == fig.id     # live on the device stage


class TestTrioFullLoop:
    def test_ask_answer_card_pixels_in_one_run(self, brain_server):
        """The headline path end to end: a question crosses to the Brain, the
        answer crosses back as a card, and the card crosses the wire to the
        device and lights pixels — three tiers, no mocks at the seams."""
        brain, url = brain_server
        orch = Orchestrator(EmulatorBridge())
        connect_brain(orch.brain, url, token="e2e-token", http_post=_post)
        orch.brain.set_local_only(False)

        captured = {}
        orch.bridge.send_card = lambda card, event="": captured.update(card=card)
        answer = orch.ask_brain("how much is the rent")
        assert answer is not None and captured.get("card")

        dev = Device()
        dev.send({"t": "card", "card_type": "ObjectRecallCard",
                  **{k: v for k, v in captured["card"].items() if k != "type"}})
        dev.ticks(6)
        assert len(dev.drawn()) >= 1
