"""lie_lens — 9-stage multimodal deception analysis for Halo.

Public API
----------
    from memoscape.lie_lens import LieLens

    ll = LieLens(narrative_store)
    ll.feed_frame(camera_frame)                  # each camera frame
    ll.feed_audio(mic_fft, mic_amplitude)        # each audio frame
    ll.feed_transcript(text, contact_id)         # each utterance
    result = ll.tick()                           # each display tick
    if result:
        card = result.to_hud_card()              # → HUD renderer

Architecture
------------
Stage 1  face_embed      — face detection + 512-d embedding
Stage 2  au_detector     — 17 facial action units (micro-expressions)
Stage 3  prosody         — voice stress (pitch, jitter, shimmer, hesitation)
Stage 4  linguistic      — hedging, pronoun use, complexity
Stage 5  fusion          — z-score multi-signal → CredibilityVector
Stage 6  renderer        — HUD card (chromatic stress bar + confidence)
Stage 7  narrative_store — per-contact baseline + anomaly log
Stage 8  fact_check      — optional cloud claim verification (via phone bridge)
"""
from .analyzer import LieLens
from .schema import (
    CredibilityVector, ContactBaseline, AnomalyLog,
    FaceEmbedding, ActionUnits, ProsodyFeatures, LinguisticFeatures,
    LieLensResult,
)

__all__ = [
    "LieLens",
    "CredibilityVector",
    "ContactBaseline",
    "AnomalyLog",
    "FaceEmbedding",
    "ActionUnits",
    "ProsodyFeatures",
    "LinguisticFeatures",
    "LieLensResult",
]
