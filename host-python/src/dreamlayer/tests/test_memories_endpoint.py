"""test_memories_endpoint.py — the phone Memories tab's real backend.

The tab used to render seed-only sample data (refresh() was a no-op). The Brain
now assembles kept memory from what it holds — places you saved (Waypath),
people you've met and favors owed (Social Lens), and dated reminders — served at
GET /dreamlayer/memories.
"""
from __future__ import annotations

import json
import time

from dreamlayer.ai_brain.server import Brain


def _seed(tmp_path) -> Brain:
    b = Brain(tmp_path)
    # a place you saved
    b.waypath_stash("bike", "the north rack")
    # a person you met, with a favor owed
    b.voice_social("meet_person", {"who": "Priya", "relation": "neighbor",
                                    "note": "teaches ceramics"})
    b.voice_social("debt", {"who": "Priya", "dir": "they_owe", "what": "$20"})
    # a dated reminder
    (tmp_path / "reminders.json").write_text(json.dumps(
        [{"title": "Renew passport", "ts": time.time() + 3600, "list": ""}]))
    return b


def test_memories_assembles_all_kinds(tmp_path):
    mems = _seed(tmp_path).memories()["memories"]
    kinds = {m["kind"] for m in mems}
    assert {"Place", "Person", "Promise"} <= kinds
    joined = " | ".join(m["summary"] for m in mems)
    assert "north rack" in joined
    assert "Priya" in joined
    assert "Priya owes you $20" in joined
    assert "Renew passport" in joined
    # every memory carries an epoch-ms ts and an id the phone can key on
    assert all(isinstance(m["ts"], int) and m["id"] for m in mems)


def test_memories_empty_is_clean(tmp_path):
    assert Brain(tmp_path).memories()["memories"] == []


def test_debt_you_owe_phrasing(tmp_path):
    b = Brain(tmp_path)
    b.voice_social("meet_person", {"who": "Dana"})
    b.voice_social("debt", {"who": "Dana", "dir": "i_owe", "what": "lunch"})
    proms = [m["summary"] for m in b.memories()["memories"] if m["kind"] == "Promise"]
    assert any(s == "You owe Dana lunch" for s in proms), proms


def test_memories_over_http(tmp_path):
    import threading, urllib.request
    from dreamlayer.ai_brain.server.server import make_brain_server
    b = _seed(tmp_path)
    srv = make_brain_server(b, host="127.0.0.1", port=7806)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    tok = b.config.token
    try:
        req = urllib.request.Request("http://127.0.0.1:7806/dreamlayer/memories")
        if tok:
            req.add_header("X-DreamLayer-Token", tok)
        got = json.loads(urllib.request.urlopen(req).read())
        assert got["memories"] and any(m["kind"] == "Place" for m in got["memories"])
    finally:
        srv.shutdown()
