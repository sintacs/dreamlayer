"""Tests for lie_sense scorer."""
import pytest
from memoscape.lie_sense.schema import StressSignal
from memoscape.lie_sense.scorer import score_windows


def make_signal(pitch_var=50.0, jitter=0.5, shimmer=1.0,
               pause_ratio=0.25, rate=1.0):
    return StressSignal(
        pitch_mean_hz=180.0,
        pitch_variance=pitch_var,
        jitter_pct=jitter,
        shimmer_pct=shimmer,
        pause_ratio=pause_ratio,
        speech_rate_norm=rate,
        energy_db=-20.0,
        window_ms=1000,
    )


class TestScoreWindows:
    def test_empty_returns_zero(self):
        result = score_windows([])
        assert result.score == 0.0
        assert result.confidence == 0.0
        assert result.window_count == 0

    def test_one_window_low_confidence(self):
        result = score_windows([make_signal()])
        assert result.confidence < 1.0
        assert result.window_count == 1

    def test_four_windows_full_confidence(self):
        signals = [make_signal()] * 4
        result = score_windows(signals)
        assert result.confidence == 1.0

    def test_calm_signals_produce_low_score(self):
        signals = [make_signal(pitch_var=5, jitter=0.1, shimmer=0.2,
                               pause_ratio=0.25, rate=1.0)] * 6
        result = score_windows(signals)
        assert result.score < 0.3

    def test_stressed_signals_produce_high_score(self):
        signals = [make_signal(pitch_var=800, jitter=9.0, shimmer=15.0,
                               pause_ratio=0.8, rate=2.5)] * 6
        result = score_windows(signals)
        assert result.score > 0.6

    def test_recency_weighting_recent_stress_higher(self):
        calm = make_signal(pitch_var=5, jitter=0.1, shimmer=0.2)
        stressed = make_signal(pitch_var=800, jitter=9.0, shimmer=15.0)
        # Old calm then sudden stress
        result_late_stress = score_windows([calm, calm, calm, stressed])
        # Old stress then calm
        result_early_stress = score_windows([stressed, calm, calm, calm])
        # Recent stress should score higher
        assert result_late_stress.score > result_early_stress.score

    def test_dominant_signal_is_string(self):
        result = score_windows([make_signal(pitch_var=800)])
        assert isinstance(result.dominant_signal, str)
        assert len(result.dominant_signal) > 0

    def test_score_bounded(self):
        signals = [make_signal(pitch_var=9999, jitter=99, shimmer=99,
                               pause_ratio=1.0, rate=5.0)] * 10
        result = score_windows(signals)
        assert 0.0 <= result.score <= 1.0
