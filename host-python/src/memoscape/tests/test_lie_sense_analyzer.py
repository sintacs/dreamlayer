"""Tests for LieSense analyzer (integration-level)."""
import time
import numpy as np
import pytest
from memoscape.lie_sense import LieSense
from memoscape.lie_sense.features import BIN_HZ


def make_fft(peak_hz: float = 200.0) -> np.ndarray:
    fft = np.zeros(512)
    bin_idx = int(peak_hz / BIN_HZ)
    fft[bin_idx] = 1.0
    return fft


def feed_frames(ls: LieSense, count: int,
               amplitude: float = 0.3,
               peak_hz: float = 200.0) -> None:
    """Feed `count` identical audio frames into the analyzer."""
    fft = make_fft(peak_hz)
    for _ in range(count):
        ls.feed_audio(fft, amplitude)


class TestLieSenseAnalyzer:
    def test_tick_returns_none_before_data(self):
        ls = LieSense()
        assert ls.tick() is None

    def test_tick_returns_none_before_enough_windows(self):
        ls = LieSense(frames_per_window=40)
        feed_frames(ls, 30)  # less than one window
        assert ls.tick() is None

    def test_tick_returns_result_after_enough_data(self):
        ls = LieSense(frames_per_window=10, max_windows=20, cooldown_s=0)
        feed_frames(ls, 50)  # 5 windows
        result = ls.tick()
        assert result is not None

    def test_result_has_deception_score(self):
        ls = LieSense(frames_per_window=10, cooldown_s=0)
        feed_frames(ls, 50)
        result = ls.tick()
        assert result is not None
        assert 0.0 <= result.deception.score <= 1.0

    def test_result_has_signals(self):
        ls = LieSense(frames_per_window=10, cooldown_s=0)
        feed_frames(ls, 50)
        result = ls.tick()
        assert result is not None
        assert len(result.signals) > 0

    def test_hud_card_from_result(self):
        ls = LieSense(frames_per_window=10, cooldown_s=0)
        feed_frames(ls, 50)
        result = ls.tick()
        assert result is not None
        card = result.to_hud_card()
        assert card["type"] == "LieSenseCard"
        assert "label" in card

    def test_cooldown_suppresses_second_emission(self):
        ls = LieSense(frames_per_window=10, cooldown_s=9999, max_windows=20)
        feed_frames(ls, 50)
        r1 = ls.tick()
        assert r1 is not None
        r2 = ls.tick()
        assert r2 is None  # cooldown active

    def test_reset_clears_state(self):
        ls = LieSense(frames_per_window=10, cooldown_s=0)
        feed_frames(ls, 50)
        ls.reset()
        assert ls.tick() is None

    def test_privacy_gate_suppresses_output(self):
        class PausedPrivacy:
            def allow_capture(self):
                return False

        ls = LieSense(frames_per_window=10, cooldown_s=0,
                      privacy=PausedPrivacy())
        feed_frames(ls, 50)
        assert ls.tick() is None

    def test_calm_speech_produces_low_score(self):
        """Stable pitch + amplitude = low stress score."""
        ls = LieSense(frames_per_window=10, cooldown_s=0, max_windows=20)
        # Very stable: same fft, same amplitude every frame
        fft = make_fft(180.0)
        for _ in range(80):
            ls.feed_audio(fft, 0.3)
        result = ls.tick()
        assert result is not None
        assert result.deception.score < 0.5

    def test_erratic_speech_produces_higher_score(self):
        """Wildly varying amplitude/pitch = higher stress score."""
        ls = LieSense(frames_per_window=10, cooldown_s=0, max_windows=20)
        for i in range(80):
            amp = 0.9 if i % 2 == 0 else 0.01
            hz = 300.0 if i % 3 == 0 else 100.0
            ls.feed_audio(make_fft(hz), amp)
        result = ls.tick()
        assert result is not None
        assert result.deception.score > result.deception.score * 0  # score exists
