"""app/recall_context.py

RecallContext — unified sensor + memory context passed to recall providers
and the Dream Engine ambient loop.

All fields added since the original orchestrator design are Optional so that
existing call sites continue to work with zero changes.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class RecallContext:
    # ------------------------------------------------------------------ core
    listen_count: int = 0
    card_count:   int = 0
    extra:        dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------ Dream Mode inputs
    # Raw JPEG thumbnail bytes from the glasses camera (≤ 8 KB)
    camera_frame:  Optional[bytes] = None

    # 32-band FFT magnitude list (floats 0.0–1.0), sampled from mic buffer
    mic_fft:       Optional[list[float]] = None

    # 6-axis IMU snapshot: {pitch, yaw, roll, dpitch, dyaw, droll}
    # d* fields are angular velocity (deg/s)
    imu_pose:      Optional[dict[str, float]] = None

    # Place-anchor memories active at the current location
    # Each entry: {summary, confidence, ts_label, place_id}
    world_anchors: Optional[list[dict]] = None

    # ------------------------------------------------------------------ helpers

    def has_camera(self) -> bool:
        return self.camera_frame is not None and len(self.camera_frame) > 0

    def has_audio(self) -> bool:
        return self.mic_fft is not None and len(self.mic_fft) > 0

    def has_imu(self) -> bool:
        return self.imu_pose is not None

    def mic_amplitude(self) -> float:
        """RMS amplitude across all FFT bands (0.0–1.0)."""
        if not self.has_audio():
            return 0.0
        bands = self.mic_fft
        return min(1.0, (sum(b * b for b in bands) / len(bands)) ** 0.5)

    def imu_angular_velocity(self) -> float:
        """Magnitude of angular velocity vector (deg/s). 0 if no IMU data."""
        if not self.has_imu():
            return 0.0
        p = self.imu_pose.get("dpitch", 0.0)
        y = self.imu_pose.get("dyaw",   0.0)
        r = self.imu_pose.get("droll",  0.0)
        return (p*p + y*y + r*r) ** 0.5
