"""dream/imu_reactor.py — IMU angular velocity → geometry distortion commands.

Maps head movement (from 6-axis IMU) to display distortion intensity.
Returns a raw BLE command dict the DreamEngine sends via bridge.send_raw().

Mapping
-------
  Still              → nothing; palette breathes on its own
  Slow drift (<5°/s) → gentle line-field rotation command
  Medium (5-20°/s)   → faster rotation + increased particle scatter radius
  Fast (>20°/s)      → scatter burst: pre-baked "scatter" geometry frame
  Tap detected       → dream anchor drop (WorldAnchorCard via GhostLayer)

The Lua dream_renderer interprets:
  t="geometry"  with {mode, yaw_rate, pitch_rate, intensity}
"""
from __future__ import annotations

import math
import time
from typing import Optional

from ..recall_context import RecallContext

_SLOW_THRESHOLD   = 5.0    # deg/s
_FAST_THRESHOLD   = 20.0   # deg/s
_SCATTER_COOLDOWN = 1.5    # seconds between scatter bursts


class ImuReactor:
    """Converts IMU delta pose into geometry distortion BLE commands."""

    def __init__(self) -> None:
        self._last_scatter_t: float = 0.0
        self._yaw_rate_smooth: float = 0.0
        self._pitch_rate_smooth: float = 0.0

    def tick(self, ctx: RecallContext) -> Optional[dict]:
        """Compute geometry command from IMU delta. Returns BLE cmd or None."""
        if not ctx.has_imu() or ctx.imu_delta is None:
            return None

        delta = ctx.imu_delta
        yaw_rate   = abs(float(delta.get("yaw",   0.0)))
        pitch_rate = abs(float(delta.get("pitch", 0.0)))
        speed = math.sqrt(yaw_rate**2 + pitch_rate**2)

        # Smooth
        self._yaw_rate_smooth   = _ewm(self._yaw_rate_smooth,   yaw_rate,   0.30)
        self._pitch_rate_smooth = _ewm(self._pitch_rate_smooth, pitch_rate, 0.30)

        if speed < _SLOW_THRESHOLD:
            return None   # too slow to bother

        now = time.monotonic()
        if speed >= _FAST_THRESHOLD:
            if (now - self._last_scatter_t) >= _SCATTER_COOLDOWN:
                self._last_scatter_t = now
                return {
                    "t":         "geometry",
                    "mode":      "scatter",
                    "intensity": _clamp01((speed - _FAST_THRESHOLD) / 40.0),
                    "yaw_rate":  round(self._yaw_rate_smooth, 2),
                    "pitch_rate": round(self._pitch_rate_smooth, 2),
                }

        # Medium speed — rotation
        return {
            "t":         "geometry",
            "mode":      "rotate",
            "intensity": _clamp01((speed - _SLOW_THRESHOLD) / (_FAST_THRESHOLD - _SLOW_THRESHOLD)),
            "yaw_rate":  round(self._yaw_rate_smooth, 2),
            "pitch_rate": round(self._pitch_rate_smooth, 2),
        }


def _ewm(prev: float, new: float, alpha: float) -> float:
    return prev + alpha * (new - prev)

def _clamp01(v: float) -> float:
    return max(0.0, min(1.0, v))
