"""Stasis on the Orchestrator — the zero-word freeze, the choreographed
resume, the ambient offer, the compost night, and all five veil rules."""

import json

from dreamlayer.orchestrator.stasis import DAY
from dreamlayer.pipelines.ingest import MemoryEvent

NOW = 1_700_000_000.0
UTTER = "so if the hinge is binding, the torque spike should show up when"


class FakeBridge:
    """Captures everything (EmulatorBridge keeps only last_card)."""
    def __init__(self):
        self.cards, self.raw, self.commands = [], [], []
        self._cb = None
    def connect(self): return {"emulated": True}
    def disconnect(self): pass
    def load_lua_app(self, root): pass
    def send_command(self, kind, payload=None): self.commands.append(kind)
    def send_card(self, payload, event="answer_ready"):
        self.cards.append((event, payload))
    def send_raw(self, obj): self.raw.append(obj)
    def inject_event(self, name, payload=None): pass
    def on_event(self, cb): self._cb = cb


def make_orc(db_path=":memory:"):
    from dreamlayer.orchestrator.orchestrator import Orchestrator
    orc = Orchestrator(FakeBridge(), db_path=db_path)
    orc._clock = lambda: NOW
    return orc


def think_out_loud(orc):
    orc.ring.append(MemoryEvent(kind="memory",
                                summary="testing the hinge bracket",
                                confidence=0.7), ts=NOW - 60)
    orc.ring.append(MemoryEvent(kind="memory", summary="a private aside",
                                confidence=0.7, meta={"private": True}),
                    ts=NOW - 40)
    orc._stasis_last_utterance = (UTTER, NOW - 5)


class TestFreeze:
    def test_double_nod_freezes_with_zero_words(self):
        orc = make_orc(); think_out_loud(orc)
        res = orc.on_imu_gesture("DOUBLE_NOD")
        assert res["gesture"] == "DOUBLE_NOD"        # contract kept
        assert res["stasis"]["ok"] and res["stasis"]["depth"] == 1
        assert orc.bridge.raw[-1] == {"t": "stasis", "mode": "freeze"}

    def test_the_snapshot_is_semantic_and_private_stays_out(self):
        orc = make_orc(); think_out_loud(orc)
        orc.freeze_context()
        f = orc.stasis.top()
        assert f.final_utterance == UTTER, "verbatim, dash and all"
        assert all("private aside" not in e["summary"] for e in f.ring_window)
        assert all(set(e) <= {"kind", "summary", "confidence", "ts", "source"}
                   for e in f.ring_window), "nothing raw, ever"

    def test_veiled_freeze_is_a_silent_no_op(self):
        orc = make_orc(); think_out_loud(orc)
        orc.pause()
        assert orc.on_imu_gesture("DOUBLE_NOD")["stasis"] is None
        assert orc.bridge.raw == [], "the shutter never closes"
        assert len(orc.stasis) == 0 and orc.db.memories(kind="stasis") == []

    def test_voice_freeze_is_the_same_gesture(self):
        orc = make_orc(); think_out_loud(orc)
        res = orc.handle_voice("hold that thought")
        assert res["intent"] == "stasis_freeze" and res["ok"]

    def test_a_fourth_freeze_composts_the_oldest_early(self):
        orc = make_orc()
        for i in range(4):
            orc._stasis_last_utterance = (f"thought number {i}", NOW - 1)
            orc.freeze_context()
        assert len(orc.stasis) == 3
        composted = [m for m in orc.db.memories(kind="memory")
                     if json.loads(m["meta"]).get("stasis_compost")]
        assert len(composted) == 1 and "thought number 0" in composted[0]["summary"]

    def test_freeze_persists_a_stasis_row_that_recall_can_find(self):
        orc = make_orc(); think_out_loud(orc)
        orc.freeze_context()
        rows = orc.db.memories(kind="stasis")
        assert len(rows) == 1 and rows[0]["summary"] == UTTER


class TestResume:
    def test_tilt_reveal_replays_context_first_content_last(self):
        orc = make_orc(); think_out_loud(orc)
        orc.freeze_context()
        orc.bridge.cards.clear()
        res = orc.on_imu_gesture("TILT_REVEAL")["stasis"]
        assert res["ok"] and res["freshness"] == "fresh"
        cards = [c for e, c in orc.bridge.cards if e == "stasis_replay"]
        assert cards, "the choreography played"
        final = cards[-1]
        assert final["meta"]["stasis_final"] is True
        assert final["primary"] == UTTER, \
            "the last card is the unfinished sentence, verbatim — the dash is the handoff"
        assert all(c["dismiss_ms"] > 0 for c in cards[:-1]), \
            "steps self-advance; only the wearer finishes the thought"

    def test_stasis_never_summarizes(self):
        # every replayed line existed verbatim in the frozen context — an
        # AI paraphrase would replace the problem state with its own
        orc = make_orc(); think_out_loud(orc)
        orc.freeze_context()
        orc.bridge.cards.clear()
        orc.resume_stasis()
        f = orc.stasis.top()
        sources = {UTTER} | {e["summary"] for e in f.ring_window} | \
            {"moments ago", "earlier today", "yesterday"}
        replayed = [c["primary"] for e, c in orc.bridge.cards
                    if e == "stasis_replay"]
        assert UTTER in replayed
        for primary in replayed:
            assert primary in sources, f"invented line: {primary!r}"

    def test_paused_veil_blocks_resume_incognito_does_not(self):
        orc = make_orc(); think_out_loud(orc)
        orc.freeze_context()
        orc.pause()
        assert orc.resume_stasis() is None, "a full veil is deaf and blind"
        orc.resume()
        orc.set_incognito(True)
        assert orc.resume_stasis()["ok"], \
            "incognito stops keeping, not recalling"

    def test_resume_with_nothing_held_answers_honestly(self):
        orc = make_orc()
        res = orc.handle_voice("where was I")
        assert res["intent"] == "stasis_resume" and res["ok"] is False
        assert any(e == "stasis_empty" for e, _ in orc.bridge.cards)

    def test_resume_heals_the_frame(self):
        orc = make_orc(); think_out_loud(orc)
        orc.freeze_context()
        before = orc.stasis.top()
        orc._clock = lambda: NOW + 3 * DAY
        orc.resume_stasis()
        after = orc.stasis.top()
        assert after.resume_count == 1
        assert after.decay(NOW + 3 * DAY) == 0.0
        assert after.half_life_s() > before.half_life_s()

    def test_a_cool_frame_gets_an_orienting_line(self):
        orc = make_orc(); think_out_loud(orc)
        orc.freeze_context()
        orc._clock = lambda: NOW + 5 * DAY
        orc.bridge.cards.clear()
        res = orc.resume_stasis()
        assert res["freshness"] == "cool"
        first = orc.bridge.cards[0][1]
        assert "days ago" in first["primary"], \
            "cooler traces need more scaffolding"

    def test_nod_save_right_after_a_replay_pins_the_frame(self):
        orc = make_orc(); think_out_loud(orc)
        orc.freeze_context()
        orc.resume_stasis()
        res = orc.on_imu_gesture("NOD_SAVE")
        assert res["stasis"]["pinned"] == orc.stasis.top().id
        assert orc.stasis.top().meta.get("pinned")
        # ...and the row carries the immortality flag retention honors
        row = orc.db.memories(kind="stasis")[0]
        assert json.loads(row["meta"]).get("pinned") is True

    def test_nod_save_elsewhere_is_still_nod_to_remember(self):
        orc = make_orc(); think_out_loud(orc)
        res = orc.on_imu_gesture("NOD_SAVE")
        assert "pinned" in res and "stasis" not in res


class TestAmbientOffer:
    def frozen_at_bench(self, orc):
        think_out_loud(orc)
        orc.dream._ctx.place_signature = "sig-bench"
        orc.freeze_context()
        orc.bridge.raw.clear()

    def test_returning_to_the_place_relights_the_ribbon(self):
        orc = make_orc(); self.frozen_at_bench(orc)
        assert orc.stasis_on_place("sig-bench") == {"offered": orc.stasis.top().id}
        assert orc.bridge.raw[-1] == {"t": "stasis", "mode": "offer"}

    def test_it_offers_it_never_plays_unbidden(self):
        orc = make_orc(); self.frozen_at_bench(orc)
        orc.stasis_on_place("sig-bench")
        assert not any(e == "stasis_replay" for e, _ in orc.bridge.cards), \
            "an offer is a glyph, never a replay"

    def test_one_offer_per_return_debounced(self):
        orc = make_orc(); self.frozen_at_bench(orc)
        assert orc.stasis_on_place("sig-bench") is not None
        assert orc.stasis_on_place("sig-bench") is None, "cooldown holds"
        orc._clock = lambda: NOW + 300
        assert orc.stasis_on_place("sig-bench") is not None

    def test_a_veiled_return_surfaces_nothing(self):
        orc = make_orc(); self.frozen_at_bench(orc)
        orc.pause()
        assert orc.stasis_on_place("sig-bench") is None
        assert orc.bridge.raw == []

    def test_the_wrong_place_stays_silent(self):
        orc = make_orc(); self.frozen_at_bench(orc)
        assert orc.stasis_on_place("sig-kitchen") is None

    def test_gaze_on_the_frozen_object_offers_too(self):
        class Sighting:
            def key(self): return "circuit board"
        class Panel:
            sighting = Sighting()
            def to_hud_card(self): return {"type": "ObjectRecallCard",
                                           "primary": "circuit board"}
        orc = make_orc()
        orc.stasis_note_gaze(Panel())          # gaze context recorded...
        orc.freeze_context()                   # ...frozen with the frame
        orc.bridge.raw.clear()
        assert orc.stasis_note_gaze(Panel()) is not None
        assert orc.bridge.raw[-1] == {"t": "stasis", "mode": "offer"}


class TestCompost:
    def test_untouched_frames_return_to_the_soil(self):
        orc = make_orc(); think_out_loud(orc)
        orc.freeze_context()
        orc._clock = lambda: NOW + 8 * DAY
        report = orc.compost_stasis()
        assert len(report["composted"]) == 1 and report["live"] == 0
        assert orc.db.memories(kind="stasis") == [], "the bookmark dissolves"
        soil = [m for m in orc.db.memories(kind="memory")
                if json.loads(m["meta"]).get("stasis_compost")]
        assert soil and soil[0]["summary"] == UTTER, \
            "the thought stays findable; only the bookmark is gone"

    def test_pinned_frames_never_compost(self):
        orc = make_orc(); think_out_loud(orc)
        orc.freeze_context()
        orc.pin_stasis()
        orc._clock = lambda: NOW + 365 * DAY
        assert orc.compost_stasis()["live"] == 1

    def test_composting_rides_the_rem_night(self, tmp_path):
        import time as _t
        import dreamlayer.config as C
        from dreamlayer.orchestrator.orchestrator import Orchestrator
        from dreamlayer.rem.nightly import NightWatch
        night = NOW + (23 - _t.localtime(NOW).tm_hour) * 3600.0
        cfg = C.Config(); cfg.vault_dir = str(tmp_path)
        orc = Orchestrator(FakeBridge(), config=cfg)
        orc._clock = lambda: night
        orc.nightwatch = NightWatch(tmp_path, now_fn=lambda: night)
        orc.ring.append(MemoryEvent(kind="promise", summary="send the lease",
                                    confidence=0.9), ts=night - 3600)
        orc.ring.append(MemoryEvent(kind="memory", summary="hinge bracket",
                                    confidence=0.8), ts=night - 1800)
        orc._stasis_last_utterance = (UTTER, night - 10)
        # a stale frame, frozen nine days before tonight
        from dreamlayer.orchestrator.stasis import FreezeFrame
        orc.stasis.push(FreezeFrame(id=0, created_ts=night - 9 * DAY,
                                    final_utterance="an old cold thread"))
        reel = orc.maybe_dream_tonight(charging=True)
        assert reel is not None
        assert orc.last_stasis_compost["live"] == 0, \
            "unresumed thoughts fold into memory while you sleep"


class TestDurability:
    def test_a_held_thought_survives_a_restart(self, tmp_path):
        db = str(tmp_path / "dreamlayer.db")
        orc = make_orc(db); think_out_loud(orc)
        orc.freeze_context()
        reborn = make_orc(db)
        assert len(reborn.stasis) == 1
        assert reborn.stasis.top().final_utterance == UTTER


class TestPluginEvents:
    def test_freeze_and_resume_publish(self):
        orc = make_orc(); think_out_loud(orc)
        seen = []
        orc.plugin_events.subscribe("stasis_freeze",
                                    lambda k, p: seen.append((k, p)))
        orc.plugin_events.subscribe("stasis_resume",
                                    lambda k, p: seen.append((k, p)))
        orc.freeze_context()
        orc.resume_stasis()
        kinds = [k for k, _ in seen]
        assert kinds == ["stasis_freeze", "stasis_resume"]
        assert seen[0][1]["has_utterance"] is True
