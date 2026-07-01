"""Tests for the fusion engine."""
import pytest
from memoscape.lie_lens.fusion import fuse


class TestFusion:
    def test_zero_z_scores_low_prob(self):
        cv = fuse(0.0, 0.0, 0.0)
        assert cv.deception_prob < 0.4

    def test_high_z_scores_high_prob(self):
        cv = fuse(4.0, 4.0, 4.0)
        assert cv.deception_prob > 0.6

    def test_stranger_penalty_suppresses_partial_signal(self):
        # Only one high z-score — stranger mode should cap the result
        cv = fuse(4.0, 0.0, 0.0, is_stranger=True)
        assert cv.deception_prob <= 0.45

    def test_stranger_all_high_passes(self):
        cv = fuse(3.0, 3.0, 3.0, is_stranger=True)
        assert cv.deception_prob > 0.45

    def test_confidence_rises_with_windows(self):
        cv1 = fuse(1.0, 1.0, 1.0, window_count=1)
        cv10 = fuse(1.0, 1.0, 1.0, window_count=10)
        assert cv10.confidence > cv1.confidence

    def test_confidence_saturates_at_one(self):
        cv = fuse(1.0, 1.0, 1.0, window_count=100)
        assert cv.confidence == 1.0

    def test_dominant_signal_is_string(self):
        cv = fuse(2.0, 1.0, 0.5)
        assert isinstance(cv.dominant_signal, str)
        assert len(cv.dominant_signal) > 0

    def test_is_stranger_flag_propagated(self):
        cv = fuse(1.0, 1.0, 1.0, is_stranger=True)
        assert cv.is_stranger is True

    def test_score_bounded_0_to_1(self):
        cv = fuse(99.0, 99.0, 99.0)
        assert 0.0 <= cv.deception_prob <= 1.0

    def test_voice_stress_weighted_highest(self):
        # voice_stress weight=0.40 is highest
        cv_voice = fuse(0.0, 4.0, 0.0)
        cv_micro = fuse(4.0, 0.0, 0.0)
        cv_ling  = fuse(0.0, 0.0, 4.0)
        assert cv_voice.deception_prob >= cv_micro.deception_prob
        assert cv_voice.deception_prob >= cv_ling.deception_prob
