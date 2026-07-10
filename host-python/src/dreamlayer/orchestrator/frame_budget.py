"""orchestrator/frame_budget.py — camera frames cost something; budget them.

On real hardware every frame is a capture + a multi-second BLE transfer +
battery. The lens logic was written in a world with free transport; this
module is the one place that owns the truth:

  deliberate   a gesture-triggered look (glance, look_at_object, Rosetta).
               Always allowed — the wearer asked. Recorded for telemetry.
  ambient      Dream Mode / passive scene frames. Duty-cycled by
               `capture_interval_ms` (the same constant the on-glass
               settings table carries) — 2 Hz ambient camera over BLE is
               fiction; ~one frame per interval is the honest budget.
  staleness    a frame older than `stale_ms` must not answer a deliberate
               look — lenses reject it and the wearer gets "couldn't see
               that clearly" instead of an answer about the past.
"""
from __future__ import annotations

import time


class FrameBudget:
    def __init__(self, ambient_interval_ms: float = 4000.0,
                 stale_ms: float = 1500.0, now_fn=None) -> None:
        self.ambient_interval_ms = float(ambient_interval_ms)
        self.stale_ms = float(stale_ms)
        self._now = now_fn or time.monotonic
        self._last_ambient = -1e12
        self.deliberate_count = 0
        self.ambient_count = 0
        self.ambient_dropped = 0

    # -- ambient duty cycle -------------------------------------------------

    def allow_ambient(self, now: float | None = None) -> bool:
        """One ambient frame per interval; the rest are dropped at the door
        (and counted, so the budget is visible rather than silent)."""
        now = self._now() if now is None else now
        if (now - self._last_ambient) * 1000.0 >= self.ambient_interval_ms:
            self._last_ambient = now
            self.ambient_count += 1
            return True
        self.ambient_dropped += 1
        return False

    # -- deliberate looks ----------------------------------------------------

    def note_deliberate(self) -> None:
        self.deliberate_count += 1

    # -- staleness -----------------------------------------------------------

    def fresh(self, frame_ts: float, now: float | None = None) -> bool:
        """Is a frame captured at `frame_ts` still allowed to answer a
        deliberate look?"""
        now = self._now() if now is None else now
        return (now - frame_ts) * 1000.0 <= self.stale_ms

    def stats(self) -> dict:
        return {"deliberate": self.deliberate_count,
                "ambient": self.ambient_count,
                "ambient_dropped": self.ambient_dropped}
