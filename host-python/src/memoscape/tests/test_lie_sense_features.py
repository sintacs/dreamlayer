"""Tests for lie_sense feature extractors."""
import numpy as np
import pytest
from memoscape.lie_sense.features import (
    estimate_f0, amplitude_to_db,
    extract_jitter, extract_shimmer,
    extract_pause_ratio, extract_speech_rate,
    F0_MIN_HZ, F0_MAX_HZ, BIN_HZ, SILENCE_THRESHOLD,
)


class TestEstimateF0:
    def make_fft(self, peak_hz: float) -> np.ndarray:
        fft = np.zeros(512)
        bin_idx = int(peak_hz / BIN_HZ)
        fft[bin_idx] = 1.0
        return fft

    def test_detects_pitch_in_range(self):
        fft = self.make_fft(200)
        f0 = estimate_f0(fft)
        assert f0 is not None
        assert 180 <= f0 <= 220

    def test_returns_none_for_silent_frame(self):
        fft = np.zeros(512)
        assert estimate_f0(fft) is None

    def test_returns_none_for_none_input(self):
        assert estimate_f0(None) is None

    def test_ignores_peak_below_f0_min(self):
        fft = np.zeros(512)
        fft[1] = 10.0  # below F0_MIN_BIN
        result = estimate_f0(fft)
        # May return None or a value in range, but not below F0_MIN_HZ
        if result is not None:
            assert result >= F0_MIN_HZ


class TestAmplitudeToDb:
    def test_zero_returns_floor(self):
        assert amplitude_to_db(0.0) == -60.0

    def test_one_returns_zero_db(self):
        assert abs(amplitude_to_db(1.0)) < 0.01

    def test_negative_clamped(self):
        assert amplitude_to_db(-1.0) == -60.0

    def test_half_amplitude(self):
        db = amplitude_to_db(0.5)
        assert -7 < db < -5   # ~-6 dB


class TestExtractJitter:
    def test_stable_pitch_low_jitter(self):
        series = [200.0] * 10
        assert extract_jitter(series) == 0.0

    def test_variable_pitch_high_jitter(self):
        series = [150.0, 250.0, 150.0, 250.0, 150.0]
        assert extract_jitter(series) > 30.0

    def test_empty_series(self):
        assert extract_jitter([]) == 0.0

    def test_single_element(self):
        assert extract_jitter([200.0]) == 0.0


class TestExtractShimmer:
    def test_stable_amplitude_low_shimmer(self):
        series = [0.5] * 10
        assert extract_shimmer(series) == 0.0

    def test_variable_amplitude_high_shimmer(self):
        series = [0.1, 0.9, 0.1, 0.9, 0.1]
        assert extract_shimmer(series) > 60.0

    def test_empty_series(self):
        assert extract_shimmer([]) == 0.0


class TestExtractPauseRatio:
    def test_all_voiced(self):
        series = [0.5] * 10
        assert extract_pause_ratio(series) == 0.0

    def test_all_silent(self):
        series = [0.0] * 10
        assert extract_pause_ratio(series) == 1.0

    def test_half_silent(self):
        series = [0.0, 0.5] * 5
        assert extract_pause_ratio(series) == 0.5

    def test_empty(self):
        assert extract_pause_ratio([]) == 0.0


class TestExtractSpeechRate:
    def test_normal_rate_near_one(self):
        # ~75% voiced = baseline
        series = [0.5] * 75 + [0.0] * 25
        rate = extract_speech_rate(series)
        assert 0.9 <= rate <= 1.1

    def test_all_voiced_above_one(self):
        series = [0.5] * 100
        assert extract_speech_rate(series) > 1.0

    def test_all_silent_below_one(self):
        series = [0.0] * 100
        assert extract_speech_rate(series) < 1.0
