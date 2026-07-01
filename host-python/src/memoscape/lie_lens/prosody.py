"""lie_lens/prosody.py — Voice stress and prosody feature extractor.

Extracts ProsodyFeatures from raw mic data (FFT + amplitude arrays)
already produced by the audio pipeline. No new hardware dependency.

Replaces the standalone lie_sense module.
"""
from __future__ import annotations
import math
from typing import Optional
import numpy as np
from .schema import ProsodyFeatures, ContactBaseline

SAMPLE_RATE_HZ = 16_000
FFT_SIZE = 512
BIN_HZ = SAMPLE_RATE_HZ / FFT_SIZE
F0_MIN_BIN = int(80 / BIN_HZ)
F0_MAX_BIN = int(400 / BIN_HZ)
SILENCE_THRESHOLD = 0.02


def estimate_f0(fft_magnitudes: np.ndarray) -> Optional[float]:
    if fft_magnitudes is None or len(fft_magnitudes) < F0_MAX_BIN:
        return None
    region = fft_magnitudes[F0_MIN_BIN:F0_MAX_BIN]
    if region.max() < 1e-4:
        return None
    return (int(np.argmax(region)) + F0_MIN_BIN) * BIN_HZ


def amplitude_to_db(amplitude: float) -> float:
    if amplitude <= 0:
        return -60.0
    return max(20.0 * math.log10(amplitude), -60.0)


class ProsodyExtractor:
    """Accumulates audio frames and emits ProsodyFeatures per window.

    Parameters
    ----------
    frames_per_window : int
        ~40 frames ≈ 250 ms at 160 fps.
    """

    def __init__(self, frames_per_window: int = 40):
        self._fpw = frames_per_window
        self._fft_buf: list[np.ndarray] = []
        self._amp_buf: list[float] = []
        self._baseline_voiced_density: float = 0.75

    def feed(self, fft: Optional[np.ndarray],
             amplitude: float) -> Optional[ProsodyFeatures]:
        """Feed one frame; returns ProsodyFeatures when window completes."""
        self._fft_buf.append(fft)
        self._amp_buf.append(amplitude)
        if len(self._amp_buf) >= self._fpw:
            result = self._extract()
            self._fft_buf.clear()
            self._amp_buf.clear()
            return result
        return None

    def _extract(self) -> ProsodyFeatures:
        f0_series = [f0 for fft in self._fft_buf
                     if fft is not None
                     and (f0 := estimate_f0(fft)) is not None]
        amp_list = self._amp_buf

        pitch_mean = sum(f0_series) / len(f0_series) if f0_series else 0.0
        pitch_var = float(np.var(f0_series)) if len(f0_series) > 1 else 0.0

        # jitter
        jitter = 0.0
        if len(f0_series) >= 2:
            diffs = [abs(f0_series[i] - f0_series[i-1])
                     for i in range(1, len(f0_series))]
            mean_f0 = pitch_mean or 1.0
            jitter = (sum(diffs) / len(diffs)) / mean_f0 * 100.0

        # shimmer
        shimmer = 0.0
        if len(amp_list) >= 2:
            diffs = [abs(amp_list[i] - amp_list[i-1])
                     for i in range(1, len(amp_list))]
            mean_amp = sum(amp_list) / len(amp_list) or 1.0
            shimmer = (sum(diffs) / len(diffs)) / mean_amp * 100.0

        # hesitation rate (pauses per second)
        silent = sum(1 for a in amp_list if a < SILENCE_THRESHOLD)
        pause_ratio = silent / len(amp_list)
        window_s = len(amp_list) / SAMPLE_RATE_HZ * FFT_SIZE
        hesitation_rate = (silent / max(window_s, 0.001))

        # speech rate
        voiced_density = 1.0 - pause_ratio
        self._baseline_voiced_density = (
            0.95 * self._baseline_voiced_density + 0.05 * voiced_density
        )
        speech_rate_norm = voiced_density / max(self._baseline_voiced_density, 0.01)

        energy_db = amplitude_to_db(
            sum(amp_list) / len(amp_list) if amp_list else 0.0
        )

        return ProsodyFeatures(
            pitch_mean_hz=round(pitch_mean, 2),
            pitch_variance=round(pitch_var, 2),
            jitter_pct=round(jitter, 3),
            shimmer_pct=round(shimmer, 3),
            hesitation_rate=round(hesitation_rate, 3),
            speech_rate_norm=round(speech_rate_norm, 3),
            energy_db=round(energy_db, 1),
            window_ms=len(amp_list) * 25,
        )


def compute_prosody_z_score(p: ProsodyFeatures,
                            baseline: Optional[ContactBaseline]) -> float:
    """Return scalar z-score of prosody vs per-contact baseline."""
    if baseline is None or not baseline.is_calibrated():
        # No baseline — use heuristic absolute score
        score = 0.0
        score += min(p.pitch_variance / 500.0, 0.25)
        score += min(p.jitter_pct / 5.0, 0.25)
        score += min(p.shimmer_pct / 8.0, 0.25)
        score += min(abs(p.speech_rate_norm - 1.0) / 0.5, 0.25)
        return score * 3.0   # scale to z-score range

    dims = [
        ("pitch_variance", p.pitch_variance),
        ("jitter_pct",     p.jitter_pct),
        ("shimmer_pct",    p.shimmer_pct),
        ("hesitation_rate",p.hesitation_rate),
        ("speech_rate_norm",p.speech_rate_norm),
    ]
    z_scores = []
    for key, val in dims:
        mean = baseline.prosody_mean.get(key, 0.0)
        std  = baseline.prosody_std.get(key, 1.0)
        if std > 0:
            z_scores.append(abs(val - mean) / std)
    return sum(z_scores) / len(z_scores) if z_scores else 0.0
