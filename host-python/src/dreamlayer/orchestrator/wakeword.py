"""orchestrator/wakeword.py — acoustic wake-word spotting seam.

Wake today is a regex over an already-transcribed line (`voice.detect_wake`) —
which means the whole ASR pipeline runs before the glasses know you wanted them.
An acoustic spotter closes that gap: it listens to raw audio and fires on the
wake phrase alone, so ASR only runs once the wearer actually addressed the
device.

`OpenWakeWordEngine` wraps openWakeWord (lazy, extras `voice`). When it's not
installed, `available` is False and the caller keeps using the text-level
`voice.detect_wake` after ASR — same graceful fallback as every seam. The engine
never transcribes; it only answers "was the wake phrase spoken in this audio?".
"""
from __future__ import annotations

import logging

log = logging.getLogger("dreamlayer.wakeword")

try:  # optional dep — extras group `voice`
    from openwakeword.model import Model as _OWWModel  # type: ignore
    _HAS_OWW = True
except Exception:
    _HAS_OWW = False


class OpenWakeWordEngine:
    """`detect(samples) -> (bool, score)` on a mono 16k PCM window.

    Parameters
    ----------
    threshold : float
        Score above which the wake phrase is considered spoken.
    model_paths : list | None
        Custom .onnx/.tflite wake models; None uses the packaged defaults.
    """
    available = _HAS_OWW

    def __init__(self, threshold: float = 0.5, model_paths=None):
        self.threshold = threshold
        self._model = None
        if _HAS_OWW:
            try:
                self._model = (_OWWModel(wakeword_models=model_paths)
                               if model_paths else _OWWModel())
            except Exception as exc:
                log.error("[wakeword] openWakeWord load failed: %s; "
                          "text-level detect_wake fallback", exc)
                self._model = None

    def detect(self, samples) -> tuple[bool, float]:
        if self._model is None:
            return (False, 0.0)
        try:
            import numpy as np
            arr = np.asarray(samples, dtype=np.float32)
            # openWakeWord expects int16-scaled audio
            if arr.size and float(np.max(np.abs(arr))) <= 1.0:
                arr = (arr * 32767.0).astype(np.int16)
            scores = self._model.predict(arr)
            best = max(scores.values()) if scores else 0.0
            return (best >= self.threshold, float(best))
        except Exception as exc:
            log.error("[wakeword] predict failed: %s", exc)
            return (False, 0.0)

    def reset(self) -> None:
        if self._model is not None and hasattr(self._model, "reset"):
            try:
                self._model.reset()
            except Exception:
                pass
