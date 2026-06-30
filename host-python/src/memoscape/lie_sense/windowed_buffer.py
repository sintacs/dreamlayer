"""lie_sense/windowed_buffer.py — Rolling audio window manager.

Collects individual mic frames and groups them into analysis windows.
Each window is a fixed number of frames; older windows are discarded
beyond the history limit.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Optional

import numpy as np


@dataclass
class AudioFrame:
    fft: Optional[np.ndarray]   # FFT magnitude spectrum
    amplitude: float            # RMS amplitude (0-1 float)


class WindowedBuffer:
    """Accumulates AudioFrames and yields fixed-size analysis windows.

    Parameters
    ----------
    frames_per_window : int
        Number of mic frames per analysis window (default 40 ≈ ~250ms at
        ~160 frames/sec).
    max_windows : int
        Maximum number of completed windows to retain in history.
    """

    def __init__(self, frames_per_window: int = 40, max_windows: int = 20):
        self.frames_per_window = frames_per_window
        self.max_windows = max_windows
        self._pending: list[AudioFrame] = []
        self._windows: deque[list[AudioFrame]] = deque(maxlen=max_windows)

    def feed(self, fft: Optional[np.ndarray], amplitude: float) -> bool:
        """Add one audio frame. Returns True when a new window is completed."""
        self._pending.append(AudioFrame(fft=fft, amplitude=amplitude))
        if len(self._pending) >= self.frames_per_window:
            self._windows.append(self._pending[: self.frames_per_window])
            self._pending = self._pending[self.frames_per_window:]
            return True
        return False

    @property
    def windows(self) -> list[list[AudioFrame]]:
        return list(self._windows)

    @property
    def window_count(self) -> int:
        return len(self._windows)

    def clear(self) -> None:
        self._pending.clear()
        self._windows.clear()
