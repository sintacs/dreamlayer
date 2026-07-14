"""Stasis core — the decay ladder is gentle and deterministic, the stack
admits three, pinning is the escape hatch, and payloads round-trip."""

from dreamlayer.orchestrator.stasis import (
    COMPOST_HALF_LIFE_DAYS, DAY, MAX_LIVE, FreezeFrame, StasisStack,
)

NOW = 1_700_000_000.0
H = 3600.0


def frame(fid=1, created=NOW, place="", gaze="", pinned=False, resumes=0):
    return FreezeFrame(
        id=fid, created_ts=created, place_signature=place, gaze_key=gaze,
        ring_window=[{"kind": "memory", "summary": "hinge torque",
                      "confidence": 0.7, "ts": created - 30, "source": "passive"}],
        final_utterance="so if the hinge is binding, the torque spike should show up when",
        resume_count=resumes,
        last_resumed_ts=created if resumes else 0.0,
        meta={"pinned": True} if pinned else {},
    )


class TestDecayLadder:
    def test_fresh_then_fading_then_cool_then_compost(self):
        f = frame()
        assert f.freshness(NOW + 1 * H) == "fresh"
        assert f.freshness(NOW + 2 * DAY) == "fading"
        assert f.freshness(NOW + 5 * DAY) == "cool"
        assert not f.compost_due(NOW + 6 * DAY)
        assert f.compost_due(NOW + COMPOST_HALF_LIFE_DAYS * DAY)

    def test_resume_heals_and_earns_a_longer_life(self):
        f = frame()
        healed = f.resumed(NOW + 3 * DAY)
        assert healed.decay(NOW + 3 * DAY) == 0.0, "a resume resets the clock"
        assert healed.resume_count == 1
        assert healed.half_life_s() > f.half_life_s(), \
            "threads you return to earn time"

    def test_pinned_never_composts(self):
        f = frame(pinned=True)
        assert f.decay(NOW + 365 * DAY) == 0.0
        assert not f.compost_due(NOW + 365 * DAY)

    def test_pinning_is_nondestructive(self):
        f = frame()
        p = f.pinned()
        assert p.meta.get("pinned") and not f.meta.get("pinned")
        assert p.final_utterance == f.final_utterance

    def test_payload_round_trip(self):
        f = frame(fid=7, place="sig-bench", gaze="circuit board", resumes=2)
        back = FreezeFrame.from_payload(7, f.to_payload())
        assert back == f


class TestStack:
    def test_newest_first_and_top(self):
        st = StasisStack()
        st.push(frame(1, NOW))
        st.push(frame(2, NOW + 60))
        assert [f.id for f in st.frames()] == [2, 1]
        assert st.top().id == 2

    def test_three_deep_is_a_feature(self):
        # a tool for holding infinite open loops would recreate the disease
        st = StasisStack()
        evicted = []
        for i in range(1, MAX_LIVE + 2):
            evicted += st.push(frame(i, NOW + i))
        assert len(st) == MAX_LIVE
        assert [f.id for f in evicted] == [1], "the oldest composts early"

    def test_pinned_frames_survive_the_depth_squeeze(self):
        st = StasisStack()
        st.push(frame(1, NOW, pinned=True))
        st.push(frame(2, NOW + 1))
        st.push(frame(3, NOW + 2))
        evicted = st.push(frame(4, NOW + 3))
        assert [f.id for f in evicted] == [2], \
            "the oldest UNPINNED frame yields first"
        assert st.get(1) is not None

    def test_all_pinned_stack_still_bounds_itself(self):
        st = StasisStack()
        for i in range(1, MAX_LIVE + 2):
            st.push(frame(i, NOW + i, pinned=True))
        assert len(st) == MAX_LIVE

    def test_match_context_prefers_the_newest_thread(self):
        st = StasisStack()
        st.push(frame(1, NOW, place="sig-bench"))
        st.push(frame(2, NOW + 60, place="sig-bench"))
        st.push(frame(3, NOW + 120, gaze="circuit board"))
        assert st.match_context(place_signature="sig-bench").id == 2
        assert st.match_context(gaze_key="circuit board").id == 3
        assert st.match_context(place_signature="sig-kitchen") is None
        assert st.match_context() is None, "empty context matches nothing"

    def test_compost_due_removes_and_returns(self):
        st = StasisStack()
        st.push(frame(1, NOW))
        st.push(frame(2, NOW + 5 * DAY))
        due = st.compost_due(NOW + 8 * DAY)
        assert [f.id for f in due] == [1]
        assert [f.id for f in st.frames()] == [2]

    def test_load_restores_bounded_and_ordered(self):
        st = StasisStack()
        st.load([frame(i, NOW + i) for i in range(1, 6)])
        assert len(st) == MAX_LIVE
        assert st.top().id == 5
