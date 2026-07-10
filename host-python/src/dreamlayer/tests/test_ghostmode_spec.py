"""test_ghostmode_spec.py — pins the normative test vector in
docs/GHOSTMODE_PROTOCOL.md §7.4 to the reference implementation, and checks the
core receive rules (forge / replay / wrong-circle / self drop). If the wire
format ever changes, the published spec vector fails loudly."""
from __future__ import annotations

from pathlib import Path

from dreamlayer.confluence.mesh import (
    InMemoryBus, MeshManager, MeshPacket, _derive_group_key, _mac,
)

SPEC = Path(__file__).resolve().parents[4] / "docs" / "GHOSTMODE_PROTOCOL.md"

VEC = {
    "group_id": "7f3a9c1b2d4e",
    "code": "amber-tide-fox",
    "group_key": "7e98870b287be188f0707eee57bbc1cb5032a1898cf6502d99a055546315fd9e",
    "sender": "a1b2c3d4e5f6",
    "seq": 1,
    "kind": "weather",
    "body": {"state": 0.62, "colors": [3, 7, 11, 14]},
    "payload": '{"body":{"colors":[3,7,11,14],"state":0.62},"group_id":"7f3a9c1b2d4e",'
               '"kind":"weather","sender":"a1b2c3d4e5f6","seq":1}',
    "mac": "9343bef912ce997c91d611e3",
}


def test_spec_test_vector_matches_the_code():
    key = _derive_group_key(VEC["group_id"], VEC["code"])
    assert key.hex() == VEC["group_key"]
    pkt = MeshPacket(group_id=VEC["group_id"], sender=VEC["sender"], seq=VEC["seq"],
                     kind=VEC["kind"], body=VEC["body"])
    assert pkt.payload() == VEC["payload"]
    assert _mac(key, pkt.payload()) == VEC["mac"]


def test_spec_document_publishes_the_same_vector():
    text = SPEC.read_text(encoding="utf-8")
    assert VEC["group_key"] in text
    assert VEC["mac"] in text
    assert VEC["payload"] in text


def _pair():
    bus = InMemoryBus()
    a = MeshManager(me="aaaaaaaaaaaa")
    gid, code = a.form()
    b = MeshManager(me="bbbbbbbbbbbb")
    b.join(gid, code)
    for m in (a.me, b.me):
        bus.attach(m)
    return bus, a, b, gid, code


def test_receive_accepts_a_valid_packet_and_rejects_a_forgery():
    _bus, a, b, _gid, _code = _pair()
    pkt = a.emit("weather", {"state": 0.5, "colors": [1, 2, 3, 4]})
    assert b.receive(pkt.to_wire()) is not None          # authentic
    forged = pkt.to_wire()
    forged["mac"] = "0" * 24
    assert b.receive(forged) is None                     # bad MAC → dropped


def test_receive_drops_replays_and_self_and_wrong_circle():
    _bus, a, b, _gid, _code = _pair()
    p1 = a.emit("weather", {"state": 0.5, "colors": [1, 2, 3, 4]})
    assert b.receive(p1.to_wire()) is not None
    assert b.receive(p1.to_wire()) is None               # replay (seq not advanced)
    assert a.receive(p1.to_wire()) is None               # self-echo
    stranger = MeshManager(me="cccccccccccc")
    stranger.form()                                      # a different circle
    sp = stranger.emit("weather", {"state": 0.1, "colors": [0, 0, 0, 0]})
    assert b.receive(sp.to_wire()) is None               # wrong group_id
