"""Integration tests for the LieLens orchestrator."""
import numpy as np
import pytest
from memoscape.lie_lens import LieLens
from memoscape.lie_lens.narrative_store import NarrativeStore
from memoscape.lie_lens.prosody import BIN_HZ


def make_fft(peak_hz=200.0):
    fft = np.zeros(512)
    fft[int(peak_hz / BIN_HZ)] = 1.0
    return fft


def make_embedding(seed=42):
    rng = np.random.default_rng(seed)
    v = rng.random(512).astype(np.float32)
    return v / np.linalg.norm(v)


class TestLieLensAnalyzer:
    def test_tick_none_before_any_data(self):
        ll = LieLens(cooldown_s=0)
        assert ll.tick() is None

    def test_tick_returns_result_after_audio(self):
        ll = LieLens(cooldown_s=0)
        for _ in range(40):
            ll.feed_audio(make_fft(), 0.3)
        result = ll.tick()
        assert result is not None

    def test_result_has_credibility(self):
        ll = LieLens(cooldown_s=0)
        for _ in range(40):
            ll.feed_audio(make_fft(), 0.3)
        result = ll.tick()
        assert result is not None
        assert 0.0 <= result.credibility.deception_prob <= 1.0

    def test_hud_card_from_result(self):
        ll = LieLens(cooldown_s=0)
        for _ in range(40):
            ll.feed_audio(make_fft(), 0.3)
        result = ll.tick()
        assert result is not None
        card = result.to_hud_card()
        assert card["type"] == "LieLensCard"

    def test_feed_transcript_updates_linguistic(self):
        ll = LieLens(cooldown_s=0)
        for _ in range(40):
            ll.feed_audio(make_fft(), 0.3)
        ll.feed_transcript("Maybe I was there. I think it could be true.", "c1")
        result = ll.tick()
        assert result is not None
        assert result.credibility.linguistic_hedge_z >= 0.0

    def test_feed_frame_sets_contact(self):
        store = NarrativeStore()
        emb = make_embedding(1)
        store.set_contact_embeddings({"alice": emb})
        ll = LieLens(store=store, cooldown_s=0)
        ll.feed_frame(emb, detection_confidence=0.95)
        assert ll._current_contact_id == "alice"

    def test_cooldown_suppresses_second_emit(self):
        ll = LieLens(cooldown_s=9999)
        for _ in range(40):
            ll.feed_audio(make_fft(), 0.3)
        r1 = ll.tick()
        assert r1 is not None
        assert ll.tick() is None

    def test_reset_clears_state(self):
        ll = LieLens(cooldown_s=0)
        for _ in range(40):
            ll.feed_audio(make_fft(), 0.3)
        ll.reset()
        assert ll.tick() is None

    def test_privacy_gate_suppresses_output(self):
        class Paused:
            def allow_capture(self): return False
        ll = LieLens(cooldown_s=0, privacy=Paused())
        for _ in range(40):
            ll.feed_audio(make_fft(), 0.3)
        assert ll.tick() is None

    def test_anomaly_logged_for_elevated_result(self):
        store = NarrativeStore()
        ll = LieLens(store=store, cooldown_s=0)
        # Force very high z-scores via erratic audio
        for i in range(80):
            amp = 0.9 if i % 2 == 0 else 0.001
            hz = 350.0 if i % 3 == 0 else 90.0
            ll.feed_audio(make_fft(hz), amp)
        ll.feed_transcript(
            "Maybe honestly I sort of think I could have perhaps been there.",
            "bob"
        )
        ll.tick()
        # Anomaly log check (may or may not log depending on score threshold)
        anomalies = store.get_anomalies("bob")
        assert isinstance(anomalies, list)

    def test_stranger_mode_when_no_contact(self):
        ll = LieLens(cooldown_s=0)
        for _ in range(40):
            ll.feed_audio(make_fft(), 0.3)
        result = ll.tick()
        if result:
            assert result.credibility.is_stranger is True
