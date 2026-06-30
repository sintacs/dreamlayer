"""lie_sense/scorer.py — Multi-signal deception score engine.

Consumes a list of StressSignal objects (one per completed window) and
produces a single DeceptionScore aggregating all signals.
"""
from __future__ import annotations

from .schema import StressSignal, DeceptionScore

# Minimum number of windows before we report a real score
MIN_WINDOWS_FOR_CONFIDENCE = 4

# Signal weight labels (must match StressSignal field names conceptually)
_SIGNAL_NAMES = [
    "pitch_variance",
    "jitter",
    "shimmer",
    "pause_pattern",
    "speech_rate",
]


def _dominant_signal(signal: StressSignal) -> str:
    """Return the name of the feature contributing most to the stress score."""
    contributions = {
        "pitch_variance": min(signal.pitch_variance / 500.0, 0.25),
        "jitter":         min(signal.jitter_pct / 5.0, 0.20),
        "shimmer":        min(signal.shimmer_pct / 8.0, 0.20),
        "pause_pattern":  min(abs(signal.pause_ratio - 0.25) / 0.25, 0.20),
        "speech_rate":    min(abs(signal.speech_rate_norm - 1.0) / 0.5, 0.15),
    }
    return max(contributions, key=contributions.get)


def score_windows(signals: list[StressSignal]) -> DeceptionScore:
    """Aggregate a list of StressSignals into a single DeceptionScore."""
    n = len(signals)
    if n == 0:
        return DeceptionScore(
            score=0.0, confidence=0.0,
            dominant_signal="none", window_count=0
        )

    raw_scores = [s.stress_score() for s in signals]

    # Exponential recency weighting — recent windows count more
    weights = [0.85 ** (n - 1 - i) for i in range(n)]
    total_weight = sum(weights)
    weighted_score = sum(s * w for s, w in zip(raw_scores, weights)) / total_weight

    # Confidence rises with window count, saturates at max_windows
    confidence = min(n / MIN_WINDOWS_FOR_CONFIDENCE, 1.0)

    # Dominant signal from the most recent window
    dominant = _dominant_signal(signals[-1])

    return DeceptionScore(
        score=round(weighted_score, 3),
        confidence=round(confidence, 3),
        dominant_signal=dominant,
        window_count=n,
    )
