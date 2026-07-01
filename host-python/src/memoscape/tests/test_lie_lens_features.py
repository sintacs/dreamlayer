"""Tests for AU detector, prosody extractor, and linguistic extractor."""
import numpy as np
import pytest
from memoscape.lie_lens.au_detector import (
    vector_to_aus, compute_au_z_score, deception_au_score
)
from memoscape.lie_lens.prosody import (
    ProsodyExtractor, estimate_f0, amplitude_to_db, BIN_HZ
)
from memoscape.lie_lens.linguistic import extract_linguistic
from memoscape.lie_lens.schema import ContactBaseline


class TestAUDetector:
    def test_vector_to_aus_length(self):
        aus = vector_to_aus([0.5] * 17)
        assert len(aus.as_vector()) == 17

    def test_vector_to_aus_short_padded(self):
        aus = vector_to_aus([0.5] * 5)
        assert aus.au45 == 0.0  # padded

    def test_deception_au_score_zero_neutral(self):
        aus = vector_to_aus([0.0] * 17)
        assert deception_au_score(aus) == 0.0

    def test_deception_au_score_high_mask_smile(self):
        vec = [0.0] * 17
        vec[8] = 1.0   # au12 = lip corner puller
        vec[4] = 0.0   # au6 = cheek raiser (absent)
        aus = vector_to_aus(vec)
        assert deception_au_score(aus) > 0.2

    def test_no_baseline_z_score_zero(self):
        aus = vector_to_aus([0.5] * 17)
        assert compute_au_z_score(aus, None) == 0.0

    def test_uncalibrated_baseline_z_score_zero(self):
        bl = ContactBaseline(contact_id="x", sample_count=5)
        aus = vector_to_aus([0.5] * 17)
        assert compute_au_z_score(aus, bl) == 0.0

    def test_calibrated_baseline_z_score_numeric(self):
        bl = ContactBaseline(
            contact_id="x",
            au_mean=[0.1] * 17,
            au_std=[0.05] * 17,
            sample_count=15,
        )
        aus = vector_to_aus([0.5] * 17)  # far from mean
        z = compute_au_z_score(aus, bl)
        assert z > 1.0


class TestProsodyExtractor:
    def _make_fft(self, peak_hz=200.0):
        fft = np.zeros(512)
        fft[int(peak_hz / BIN_HZ)] = 1.0
        return fft

    def test_no_output_before_window(self):
        pe = ProsodyExtractor(frames_per_window=40)
        for _ in range(30):
            result = pe.feed(self._make_fft(), 0.3)
        assert result is None

    def test_output_after_window(self):
        pe = ProsodyExtractor(frames_per_window=10)
        result = None
        for _ in range(10):
            result = pe.feed(self._make_fft(), 0.3)
        assert result is not None

    def test_silent_frame_produces_features(self):
        pe = ProsodyExtractor(frames_per_window=10)
        result = None
        for _ in range(10):
            result = pe.feed(None, 0.0)
        assert result is not None
        assert result.pitch_mean_hz == 0.0

    def test_estimate_f0_detects_pitch(self):
        fft = self._make_fft(200.0)
        f0 = estimate_f0(fft)
        assert f0 is not None
        assert 180 <= f0 <= 220

    def test_estimate_f0_none_for_silence(self):
        assert estimate_f0(np.zeros(512)) is None

    def test_amplitude_to_db_floor(self):
        assert amplitude_to_db(0.0) == -60.0


class TestLinguisticExtractor:
    def test_no_hedge_in_direct_statement(self):
        lf = extract_linguistic("I went to the store and bought milk.")
        assert lf.hedging_rate == 0.0

    def test_hedge_detected(self):
        lf = extract_linguistic("Maybe I was there. I think it could have been me.")
        assert lf.hedging_rate > 0.0

    def test_first_person_rate_present(self):
        lf = extract_linguistic("I saw her. I told her. I left.")
        assert lf.first_person_rate > 0.0

    def test_negation_detected(self):
        lf = extract_linguistic("I never said that. I did not go there.")
        assert lf.negation_rate > 0.0

    def test_qualifier_detected(self):
        lf = extract_linguistic("Honestly I have no idea. To be honest I wasn't there.")
        assert lf.qualifier_rate > 0.0

    def test_empty_string(self):
        lf = extract_linguistic("")
        assert lf.hedging_rate == 0.0
        assert lf.first_person_rate == 0.0
