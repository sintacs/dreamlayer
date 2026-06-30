"""dream/scene_describer.py — Camera frame → LFM2-VL → SynesthesiaCard text.

Every SCENE_INTERVAL seconds (controlled by DreamEngine), a compressed
JPEG thumbnail from the glasses camera is sent to the phone's vision
pipeline.  Instead of extracting a structured memory, it asks the VLM
for a 6-word poetic description of the scene.

The result is a SynesthesiaCard — six words rendered in hero text size
with the current emotional palette color.  It updates every ~4 seconds.

VLM prompt
----------
"Describe this scene in exactly 6 evocative words. No punctuation."

Fallback
--------
If no vision model is available (offline / no API key), SceneDescriber
falls back to a mood word derived from the current mic FFT energy.
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Optional

from ..recall_context import RecallContext
from ...hud import cards as C

log = logging.getLogger(__name__)

_FALLBACK_MOODS = [
    "soft light, still breathing, here",
    "familiar geometry, patient silence",
    "edges dissolving into ambient warmth",
    "motion arrested, memory accumulating",
    "ordinary miracle, unremarkable and vast",
]
_POETIC_PROMPT = (
    "Describe this scene in exactly 6 evocative words. "
    "Be poetic, not literal. No punctuation."
)


class SceneDescriber:
    """Async VLM scene description → SynesthesiaCard."""

    def __init__(self, vision_fn=None) -> None:
        """vision_fn: async callable(jpeg_bytes, prompt) -> str, or None for fallback."""
        self._vision_fn = vision_fn
        self._fallback_idx = 0
        self._last_description: str = ""

    def set_vision_fn(self, fn) -> None:
        """Wire in the actual VLM callable at runtime (avoids import-time deps)."""
        self._vision_fn = fn

    async def tick(self, ctx: RecallContext) -> Optional[dict]:
        """Generate a SynesthesiaCard from the current camera frame."""
        if not ctx.has_camera():
            return None

        description = await self._describe(ctx.camera_frame)
        if not description:
            return None

        self._last_description = description
        return C.synesthesia_card(
            description=description,
            confidence=None,   # VLM descriptions don't have a confidence score
        )

    async def _describe(self, jpeg_bytes: bytes) -> str:
        if self._vision_fn is not None:
            try:
                result = await asyncio.wait_for(
                    self._vision_fn(jpeg_bytes, _POETIC_PROMPT),
                    timeout=5.0,
                )
                return result.strip()[:80]   # hard cap
            except asyncio.TimeoutError:
                log.warning("SceneDescriber: VLM timeout, using fallback")
            except Exception as exc:
                log.warning("SceneDescriber: VLM error %s, using fallback", exc)

        # Fallback: cycle through mood phrases
        mood = _FALLBACK_MOODS[self._fallback_idx % len(_FALLBACK_MOODS)]
        self._fallback_idx += 1
        return mood

    @property
    def last_description(self) -> str:
        return self._last_description
