"""lie_sense/analyzer.py — LieSense main entry point.

LieSense is the public-facing class. The orchestrator or Dream Engine
calls feed_audio() on every mic frame and tick() on every display
update cycle. When enough data has accumulated, tick() returns a
LieSenseResult ready to be rendered as a HUD card.
"""
from __future__ import annotations

import time
from typing import Optional

import numpy as np

from .features import (
    estimate_f0, amplitude_to_db,
    extract_jitter, extract_shimmer,
    extract_pause_ratio, extract_speech_rate,
)
from .schema import StressSignal, LieSenseResult
from .scorer import score_windows
from .windowed_buffer import WindowedBuffer

# Minimum seconds between HUD card emissions (avoid spamming display)
EMIT_COOLDOWN_S = 3.0

# Privacy guard: do not emit if user has paused capture
class _AlwaysOn:
    def allow_capture(self) -> bool:
        return True


class LieSense:
    """Passive voice stress analyser.

    Parameters
    ----------
    frames_per_window : int
        Mic frames per analysis window (~40 ≈ 250ms).
    max_windows : int
        Rolling history depth (default 20 = ~5 seconds).
    cooldown_s : float
        Minimum seconds between HUD emissions.
    privacy : object
        Optional privacy controller with allow_capture() → bool.
    """

    def __init__(
        self,
        frames_per_window: int = 40,
        max_windows: int = 20,
        cooldown_s: float = EMIT_COOLDOWN_S,
        privacy=None,
    ):
        self._buf = WindowedBuffer(frames_per_window, max_windows)
        self._signals: list[StressSignal] = []
        self._cooldown_s = cooldown_s
        self._last_emit: float = 0.0
        self._privacy = privacy or _AlwaysOn()
        # rolling baseline for speech rate
        self._baseline_rate: float = 0.75

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def feed_audio(self,
                   mic_fft: Optional[np.ndarray],
                   mic_amplitude: Optional[float]) -> None:
        """Ingest one audio frame from the mic pipeline."""
        amp = mic_amplitude or 0.0
        completed = self._buf.feed(mic_fft, amp)
        if completed:
            signal = self._analyse_window(self._buf.windows[-1])
            self._signals.append(signal)
            # Keep signals in sync with buffer depth
            if len(self._signals) > self._buf.max_windows:
                self._signals = self._signals[-self._buf.max_windows:]

    def tick(self) -> Optional[LieSenseResult]:
        """Return a LieSenseResult if ready to emit, else None."""
        if not self._privacy.allow_capture():
            return None
        now = time.monotonic()
        if now - self._last_emit < self._cooldown_s:
            return None
        if not self._signals:
            return None

        score = score_windows(self._signals)
        if score.confidence < 0.2:
            return None

        self._last_emit = now
        return LieSenseResult(deception=score, signals=list(self._signals))

    def reset(self) -> None:
        """Clear all state — call when conversation ends."""
        self._buf.clear()
        self._signals.clear()
        self._last_emit = 0.0

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _analyse_window(self, frames) -> StressSignal:
        """Extract all stress features from one completed window."""
        fft_list = [f.fft for f in frames if f.fft is not None]
        amp_list = [f.amplitude for f in frames]

        # F0 series
        f0_series = [f0 for fft in fft_list
                     if (f0 := estimate_f0(fft)) is not None]

        pitch_mean = sum(f0_series) / len(f0_series) if f0_series else 0.0
        pitch_var = float(np.var(f0_series)) if len(f0_series) > 1 else 0.0
        jitter = extract_jitter(f0_series)
        shimmer = extract_shimmer(amp_list)
        pause_ratio = extract_pause_ratio(amp_list)
        speech_rate = extract_speech_rate(amp_list, self._baseline_rate)
        energy_db = amplitude_to_db(
            sum(amp_list) / len(amp_list) if amp_list else 0.0
        )

        # Update baseline (slow-moving average)
        voiced_density = 1.0 - pause_ratio
        self._baseline_rate = 0.95 * self._baseline_rate + 0.05 * voiced_density

        return StressSignal(
            pitch_mean_hz=round(pitch_mean, 2),
            pitch_variance=round(pitch_var, 2),
            jitter_pct=round(jitter, 3),
            shimmer_pct=round(shimmer, 3),
            pause_ratio=round(pause_ratio, 3),
            speech_rate_norm=round(speech_rate, 3),
            energy_db=round(energy_db, 1),
            window_ms=len(frames) * 25,  # ~25ms per frame at 40fps
        )
