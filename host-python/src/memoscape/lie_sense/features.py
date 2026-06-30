"""lie_sense/features.py — Extract acoustic stress features from raw mic data.

All inputs come from the existing mic pipeline (FFT magnitude array +
amplitude scalar), so there is zero new hardware dependency.
"""
from __future__ import annotations

import math
from typing import Optional

import numpy as np

# Silence threshold — frames below this amplitude are treated as pauses
SILENCE_THRESHOLD = 0.02

# FFT bin → Hz conversion assumes 16kHz sample rate, 512-point FFT
SAMPLE_RATE_HZ = 16_000
FFT_SIZE = 512
BIN_HZ = SAMPLE_RATE_HZ / FFT_SIZE   # 31.25 Hz per bin

# Fundamental frequency search range
F0_MIN_HZ = 80
F0_MAX_HZ = 400
F0_MIN_BIN = int(F0_MIN_HZ / BIN_HZ)
F0_MAX_BIN = int(F0_MAX_HZ / BIN_HZ)


def estimate_f0(fft_magnitudes: np.ndarray) -> Optional[float]:
    """Return estimated fundamental frequency in Hz, or None if no voiced frame."""
    if fft_magnitudes is None or len(fft_magnitudes) < F0_MAX_BIN:
        return None
    region = fft_magnitudes[F0_MIN_BIN:F0_MAX_BIN]
    if region.max() < 1e-4:
        return None
    peak_bin = int(np.argmax(region)) + F0_MIN_BIN
    return peak_bin * BIN_HZ


def amplitude_to_db(amplitude: float) -> float:
    """Convert linear amplitude to dB (floor at -60 dB)."""
    if amplitude <= 0:
        return -60.0
    return max(20.0 * math.log10(amplitude), -60.0)


def extract_jitter(f0_series: list[float]) -> float:
    """Compute jitter % from a series of F0 estimates (cycle-to-cycle variation)."""
    if len(f0_series) < 2:
        return 0.0
    diffs = [abs(f0_series[i] - f0_series[i - 1]) for i in range(1, len(f0_series))]
    mean_f0 = sum(f0_series) / len(f0_series)
    if mean_f0 == 0:
        return 0.0
    return (sum(diffs) / len(diffs)) / mean_f0 * 100.0


def extract_shimmer(amplitude_series: list[float]) -> float:
    """Compute shimmer % from a series of amplitude values."""
    if len(amplitude_series) < 2:
        return 0.0
    diffs = [abs(amplitude_series[i] - amplitude_series[i - 1])
             for i in range(1, len(amplitude_series))]
    mean_amp = sum(amplitude_series) / len(amplitude_series)
    if mean_amp == 0:
        return 0.0
    return (sum(diffs) / len(diffs)) / mean_amp * 100.0


def extract_pause_ratio(amplitude_series: list[float]) -> float:
    """Return fraction of frames that are below silence threshold."""
    if not amplitude_series:
        return 0.0
    silent = sum(1 for a in amplitude_series if a < SILENCE_THRESHOLD)
    return silent / len(amplitude_series)


def extract_speech_rate(amplitude_series: list[float],
                        baseline_rate: float = 1.0) -> float:
    """Estimate normalised speech rate relative to a rolling baseline.

    Proxied by voiced-frame density — denser speech = faster rate.
    Returns 1.0 at baseline, >1 for fast speech, <1 for slow/hesitant.
    """
    if not amplitude_series:
        return baseline_rate
    voiced = sum(1 for a in amplitude_series if a >= SILENCE_THRESHOLD)
    density = voiced / len(amplitude_series)
    # Calibrated so ~0.75 voiced density ≈ 1.0 (normal conversational speech)
    return density / 0.75
