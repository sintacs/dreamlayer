"""lie_sense — Passive voice stress + speech deception analysis for Halo.

Public API
----------
    from memoscape.lie_sense import LieSense

    ls = LieSense()
    ls.feed_audio(mic_fft, mic_amplitude)   # call each audio frame
    result = ls.tick()                       # call each display tick
    if result:
        # result is a LieSenseResult — emit as HUD card

Design
------
- Zero external ML dependencies (numpy only)
- Works entirely on the numpy FFT data already produced by the mic pipeline
- Privacy: all processing on-device, nothing leaves the phone
- Passive: runs silently in Dream Mode, never prompts user
"""
from .analyzer import LieSense
from .schema import LieSenseResult, StressSignal, DeceptionScore

__all__ = ["LieSense", "LieSenseResult", "StressSignal", "DeceptionScore"]
