"""Tests for the NarrativeStore."""
import pytest
from memoscape.lie_lens.narrative_store import NarrativeStore
from memoscape.lie_lens.schema import (
    ActionUnits, ProsodyFeatures, LinguisticFeatures, CredibilityVector
)


def make_aus(val=0.3):
    return ActionUnits(**{f: val for f in [
        "au1","au2","au4","au5","au6","au7",
        "au9","au10","au12","au14","au15","au17",
        "au20","au23","au25","au26","au45"
    ]})


def make_prosody(jitter=1.0, shimmer=1.5):
    return ProsodyFeatures(
        pitch_mean_hz=180.0, pitch_variance=50.0,
        jitter_pct=jitter, shimmer_pct=shimmer,
        hesitation_rate=0.5, speech_rate_norm=1.0,
        energy_db=-20.0, window_ms=1000,
    )


def make_linguistic(hedging=0.1):
    return LinguisticFeatures(
        hedging_rate=hedging, first_person_rate=0.05,
        complexity_score=8.0, negation_rate=0.1,
        qualifier_rate=0.05,
    )


class TestNarrativeStore:
    def test_get_baseline_none_initially(self):
        ns = NarrativeStore()
        assert ns.get_baseline("alice") is None

    def test_update_baseline_creates_entry(self):
        ns = NarrativeStore()
        bl = ns.update_baseline("alice", aus=make_aus())
        assert bl.contact_id == "alice"
        assert bl.sample_count == 1

    def test_update_baseline_increments_count(self):
        ns = NarrativeStore()
        for _ in range(5):
            ns.update_baseline("alice", aus=make_aus())
        assert ns.get_baseline("alice").sample_count == 5

    def test_calibrated_after_10_samples(self):
        ns = NarrativeStore()
        for _ in range(10):
            ns.update_baseline("alice", aus=make_aus())
        assert ns.get_baseline("alice").is_calibrated()

    def test_not_calibrated_before_10(self):
        ns = NarrativeStore()
        for _ in range(9):
            ns.update_baseline("alice", aus=make_aus())
        assert not ns.get_baseline("alice").is_calibrated()

    def test_prosody_baseline_stored(self):
        ns = NarrativeStore()
        ns.update_baseline("bob", prosody=make_prosody())
        bl = ns.get_baseline("bob")
        assert "jitter_pct" in bl.prosody_mean

    def test_linguistic_baseline_stored(self):
        ns = NarrativeStore()
        ns.update_baseline("bob", linguistic=make_linguistic())
        bl = ns.get_baseline("bob")
        assert "hedging_rate" in bl.linguistic_mean

    def test_log_anomaly_stores_entry(self):
        ns = NarrativeStore()
        cv = CredibilityVector(0.8, 0.9, 2.0, 2.5, 1.5, "voice_stress")
        ns.log_anomaly("alice", cv, user_label="confirmed")
        logs = ns.get_anomalies("alice")
        assert len(logs) == 1
        assert logs[0].user_label == "confirmed"

    def test_get_anomalies_empty_initially(self):
        ns = NarrativeStore()
        assert ns.get_anomalies("nobody") == []

    def test_contact_embeddings_roundtrip(self):
        import numpy as np
        ns = NarrativeStore()
        emb = {"alice": np.ones(512, dtype=np.float32)}
        ns.set_contact_embeddings(emb)
        assert "alice" in ns.get_contact_embeddings()
