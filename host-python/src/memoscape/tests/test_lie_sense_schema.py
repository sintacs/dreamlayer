"""Tests for LieSense schema dataclasses."""
import pytest
from memoscape.lie_sense.schema import StressSignal, DeceptionScore, LieSenseResult


def make_signal(pitch_var=100.0, jitter=1.0, shimmer=1.5,
               pause_ratio=0.25, rate=1.0, energy=-20.0):
    return StressSignal(
        pitch_mean_hz=180.0,
        pitch_variance=pitch_var,
        jitter_pct=jitter,
        shimmer_pct=shimmer,
        pause_ratio=pause_ratio,
        speech_rate_norm=rate,
        energy_db=energy,
        window_ms=1000,
    )


class TestStressSignal:
    def test_calm_score_is_low(self):
        s = make_signal(pitch_var=10, jitter=0.2, shimmer=0.3,
                        pause_ratio=0.25, rate=1.0)
        assert s.stress_score() < 0.25

    def test_high_stress_score(self):
        s = make_signal(pitch_var=600, jitter=8.0, shimmer=12.0,
                        pause_ratio=0.7, rate=2.0)
        assert s.stress_score() > 0.7

    def test_score_clamped_to_one(self):
        s = make_signal(pitch_var=9999, jitter=99, shimmer=99,
                        pause_ratio=1.0, rate=5.0)
        assert s.stress_score() == 1.0

    def test_score_zero_minimum(self):
        s = make_signal(pitch_var=0, jitter=0, shimmer=0,
                        pause_ratio=0.25, rate=1.0)
        assert s.stress_score() >= 0.0


class TestDeceptionScore:
    def test_label_calm(self):
        d = DeceptionScore(score=0.2, confidence=0.8,
                           dominant_signal="jitter", window_count=5)
        assert d.label == "CALM"

    def test_label_elevated(self):
        d = DeceptionScore(score=0.5, confidence=0.8,
                           dominant_signal="pitch_variance", window_count=5)
        assert d.label == "ELEVATED"

    def test_label_high_stress(self):
        d = DeceptionScore(score=0.72, confidence=0.8,
                           dominant_signal="shimmer", window_count=5)
        assert d.label == "HIGH STRESS"

    def test_label_reading_when_low_confidence(self):
        d = DeceptionScore(score=0.9, confidence=0.1,
                           dominant_signal="jitter", window_count=1)
        assert d.label == "READING"

    def test_color_green_for_calm(self):
        d = DeceptionScore(score=0.1, confidence=0.9,
                           dominant_signal="jitter", window_count=8)
        assert d.color == 0x07E0

    def test_color_grey_for_low_confidence(self):
        d = DeceptionScore(score=0.9, confidence=0.1,
                           dominant_signal="jitter", window_count=1)
        assert d.color == 0x7BEF


class TestLieSenseResult:
    def test_to_hud_card_type(self):
        d = DeceptionScore(score=0.5, confidence=0.8,
                           dominant_signal="pitch_variance", window_count=6)
        result = LieSenseResult(deception=d)
        card = result.to_hud_card()
        assert card["type"] == "LieSenseCard"

    def test_to_hud_card_has_required_keys(self):
        d = DeceptionScore(score=0.3, confidence=0.9,
                           dominant_signal="shimmer", window_count=8)
        result = LieSenseResult(deception=d)
        card = result.to_hud_card()
        for key in ["type", "dismiss_ms", "label", "score",
                    "confidence", "color", "primary", "eyebrow",
                    "detail", "footer", "opacity", "lines", "layout"]:
            assert key in card, f"Missing key: {key}"

    def test_to_hud_card_eyebrow(self):
        d = DeceptionScore(score=0.3, confidence=0.9,
                           dominant_signal="shimmer", window_count=8)
        result = LieSenseResult(deception=d)
        assert result.to_hud_card()["eyebrow"] == "LIE SENSE"

    def test_low_confidence_fades_opacity(self):
        d = DeceptionScore(score=0.5, confidence=0.2,
                           dominant_signal="jitter", window_count=2)
        result = LieSenseResult(deception=d)
        assert result.to_hud_card()["opacity"] == 0.4
