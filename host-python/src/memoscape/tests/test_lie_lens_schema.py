"""Tests for LieLens schema dataclasses."""
import pytest
from memoscape.lie_lens.schema import (
    ActionUnits, CredibilityVector, LieLensResult, ContactBaseline
)


class TestActionUnits:
    def test_as_vector_length(self):
        au = ActionUnits()
        assert len(au.as_vector()) == 17

    def test_deception_indicators_keys(self):
        au = ActionUnits(au12=0.8, au6=0.1)
        ind = au.deception_indicators()
        assert "mask_smile" in ind
        assert "brow_furrow" in ind
        assert "lip_tighten" in ind

    def test_mask_smile_without_eye(self):
        # high AU12 (lip) + low AU6 (eye) = mask smile
        au = ActionUnits(au12=1.0, au6=0.0)
        assert au.deception_indicators()["mask_smile"] > 0.8

    def test_no_mask_smile_with_duchenne(self):
        # AU12 + AU6 = genuine smile
        au = ActionUnits(au12=1.0, au6=1.0)
        assert au.deception_indicators()["mask_smile"] < 0.1


class TestCredibilityVector:
    def test_label_credible(self):
        cv = CredibilityVector(0.2, 0.8, 0.1, 0.1, 0.1, "voice_stress")
        assert cv.label == "CREDIBLE"

    def test_label_elevated(self):
        cv = CredibilityVector(0.7, 0.8, 1.5, 1.5, 1.5, "micro_exp")
        assert cv.label == "ELEVATED"

    def test_label_reading_low_confidence(self):
        cv = CredibilityVector(0.9, 0.1, 3.0, 3.0, 3.0, "micro_exp")
        assert cv.label == "READING"

    def test_color_green_credible(self):
        cv = CredibilityVector(0.2, 0.9, 0.0, 0.0, 0.0, "voice_stress")
        assert cv.hud_color == 0x07E0

    def test_color_red_high_signal(self):
        cv = CredibilityVector(0.9, 0.9, 3.0, 3.0, 3.0, "micro_exp")
        assert cv.hud_color == 0xF800

    def test_color_grey_low_confidence(self):
        cv = CredibilityVector(0.9, 0.1, 3.0, 3.0, 3.0, "micro_exp")
        assert cv.hud_color == 0x7BEF


class TestLieLensResult:
    def _make_result(self, prob=0.5, conf=0.8):
        cv = CredibilityVector(prob, conf, 1.0, 1.0, 1.0, "voice_stress")
        return LieLensResult(credibility=cv)

    def test_to_hud_card_type(self):
        assert self._make_result().to_hud_card()["type"] == "LieLensCard"

    def test_to_hud_card_required_keys(self):
        card = self._make_result().to_hud_card()
        for k in ["type", "dismiss_ms", "eyebrow", "primary", "detail",
                  "footer", "score", "confidence", "color",
                  "opacity", "lines", "layout"]:
            assert k in card

    def test_stranger_eyebrow(self):
        cv = CredibilityVector(0.5, 0.8, 1.0, 1.0, 1.0, "voice_stress",
                               is_stranger=True)
        card = LieLensResult(credibility=cv).to_hud_card()
        assert "STRANGER" in card["eyebrow"]

    def test_low_confidence_fades_opacity(self):
        card = self._make_result(conf=0.1).to_hud_card()
        assert card["opacity"] == 0.4
