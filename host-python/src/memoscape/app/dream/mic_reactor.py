"""dream/mic_reactor.py — Mic FFT → palette shift commands.

Maps 32-band FFT magnitudes to YCbCr palette adjustments.
Returns a raw BLE command dict the DreamEngine sends via bridge.send_raw().

Perceptual mapping
------------------
  Silence         → cool cyan baseline (ACCENT_MEMORY hue)
  Sub-100Hz bass  → deep blue, low saturation, slow drift
  200-800Hz voice → warm amber mid-tones
  1kHz+ bright    → red/violet surge, high contrast
  Own voice       → gold highlight (detected via IMU bone-cond. vibration)

Palette encoding
----------------
YCbCr values for frame.display.assign_color_ycbcr() are 0-1023 ints:
  Y  = luma  (0=black, 1023=white)
  Cb = blue-difference chroma (512=neutral)
  Cr = red-difference chroma  (512=neutral)
"""
from __future__ import annotations

import math
from typing import Optional

from ..recall_context import RecallContext

# Band index boundaries in a 32-band FFT at 16kHz sample rate
# Each band ≈ 250Hz
_BASS_BANDS   = slice(0, 1)    # 0-250 Hz
_MID_BANDS    = slice(1, 4)    # 250-1000 Hz
_BRIGHT_BANDS = slice(4, 8)    # 1000-2000 Hz
_AIR_BANDS    = slice(8, 16)   # 2000-4000 Hz

# Palette slots used for ambient color (slots 1-4 are dream ambient)
_AMBIENT_SLOTS = [1, 2, 3, 4]

# Neutral baseline: cool cyan (matches ACCENT_MEMORY)
_BASE_Y  = 420
_BASE_CB = 560
_BASE_CR = 450


class MicReactor:
    """Converts mic FFT data into palette shift BLE commands."""

    def __init__(self, smoothing: float = 0.25) -> None:
        # EWM smoothing on band energies (0=no smoothing, 1=frozen)
        self._alpha = smoothing
        self._bass  = 0.0
        self._mid   = 0.0
        self._bright = 0.0
        self._prev_cmd: Optional[dict] = None

    def tick(self, ctx: RecallContext) -> Optional[dict]:
        """Compute palette shift from current mic data. Returns BLE cmd or None."""
        if not ctx.has_mic():
            return None

        fft = ctx.mic_fft or [0.0] * 32
        amp = ctx.mic_amplitude or 0.0

        # Band energies (mean of each slice)
        bass   = _mean(fft[_BASS_BANDS])
        mid    = _mean(fft[_MID_BANDS])
        bright = _mean(fft[_BRIGHT_BANDS])

        # Smooth
        self._bass   = _ewm(self._bass,   bass,   self._alpha)
        self._mid    = _ewm(self._mid,    mid,    self._alpha)
        self._bright = _ewm(self._bright, bright, self._alpha)

        colors = self._compute_palette(amp)
        cmd = {
            "t":           "palette",
            "colors":      colors,
            "duration_ms": 2000,
        }
        self._prev_cmd = cmd
        return cmd

    def _compute_palette(self, amp: float) -> list[dict]:
        """Map band energies to YCbCr palette entries for ambient slots."""
        b = self._bass
        m = self._mid
        br = self._bright

        # Luma: brighter with overall amplitude
        y_boost = int(amp * 180)

        # Chroma: bass → blue shift, mid → amber, bright → red/violet
        cb_shift = int(b * 120)        # bass pushes Cb up (blue)
        cr_shift = int(br * 140)       # bright pushes Cr up (red)
        mid_warm = int(m * 80)         # mid warms Y slightly

        colors = []
        for i, slot in enumerate(_AMBIENT_SLOTS):
            phase = i * math.pi / 2
            y  = _clamp(_BASE_Y  + y_boost  + mid_warm + int(20 * math.sin(phase)), 80, 900)
            cb = _clamp(_BASE_CB + cb_shift - int(br * 60) + int(10 * math.cos(phase)), 300, 800)
            cr = _clamp(_BASE_CR + cr_shift - int(b * 40)  + int(10 * math.sin(phase + 1)), 300, 800)
            colors.append({"idx": slot, "y": y, "cb": cb, "cr": cr})

        return colors


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mean(vals) -> float:
    lst = list(vals)
    return sum(lst) / len(lst) if lst else 0.0

def _ewm(prev: float, new: float, alpha: float) -> float:
    return prev + alpha * (new - prev)

def _clamp(v: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, v))
