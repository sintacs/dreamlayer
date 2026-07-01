"""lie_lens/analyzer.py — LieLens orchestrator.

This is the public entry point. The orchestrator or Dream Engine
instantiates LieLens and calls:

    ll.feed_frame(embedding, au_vector, detection_confidence)
    ll.feed_audio(mic_fft, mic_amplitude)
    ll.feed_transcript(text, contact_id)
    result = ll.tick()    # each display update cycle

When enough multimodal data has accumulated, tick() returns a
LieLensResult ready for the HUD renderer.
"""
from __future__ import annotations
import time
from typing import Optional
import numpy as np

from .schema import LieLensResult, FaceEmbedding, ActionUnits
from .face_embed import FaceEmbedder
from .au_detector import compute_au_z_score, vector_to_aus, deception_au_score
from .prosody import ProsodyExtractor, compute_prosody_z_score
from .linguistic import extract_linguistic, compute_linguistic_z_score
from .fusion import fuse
from .narrative_store import NarrativeStore
from .renderer import render

EMIT_COOLDOWN_S = 3.0


class _AlwaysOn:
    def allow_capture(self) -> bool:
        return True


class LieLens:
    """9-stage multimodal deception analysis pipeline.

    Parameters
    ----------
    store : NarrativeStore
        Shared narrative memory store (baselines + anomaly log).
    cooldown_s : float
        Minimum seconds between HUD card emissions.
    privacy : object
        Optional privacy controller with allow_capture() -> bool.
    """

    def __init__(
        self,
        store: Optional[NarrativeStore] = None,
        cooldown_s: float = EMIT_COOLDOWN_S,
        privacy=None,
    ):
        self._store = store or NarrativeStore()
        self._embedder = FaceEmbedder(
            self._store.get_contact_embeddings()
        )
        self._prosody = ProsodyExtractor()
        self._cooldown_s = cooldown_s
        self._last_emit: float = 0.0
        self._privacy = privacy or _AlwaysOn()
        self._window_count: int = 0

        # Latest signals
        self._last_face: Optional[FaceEmbedding] = None
        self._last_aus: Optional[ActionUnits] = None
        self._latest_au_z: float = 0.0
        self._latest_prosody_z: float = 0.0
        self._latest_linguistic_z: float = 0.0
        self._current_contact_id: Optional[str] = None

    # ------------------------------------------------------------------
    # Feed methods
    # ------------------------------------------------------------------

    def feed_frame(
        self,
        embedding: Optional[np.ndarray],
        au_vector: Optional[list[float]] = None,
        detection_confidence: float = 1.0,
    ) -> None:
        """Ingest one camera frame (embedding + AU vector)."""
        if embedding is None:
            return
        face = self._embedder.process(embedding, detection_confidence)
        self._last_face = face
        if face.contact_id:
            self._current_contact_id = face.contact_id

        if au_vector:
            aus = vector_to_aus(au_vector)
            self._last_aus = aus
            baseline = (
                self._store.get_baseline(self._current_contact_id)
                if self._current_contact_id else None
            )
            self._latest_au_z = compute_au_z_score(aus, baseline)

    def feed_audio(
        self,
        mic_fft: Optional[np.ndarray],
        mic_amplitude: Optional[float],
    ) -> None:
        """Ingest one audio frame from the mic pipeline."""
        amp = mic_amplitude or 0.0
        prosody = self._prosody.feed(mic_fft, amp)
        if prosody:
            self._window_count += 1
            baseline = (
                self._store.get_baseline(self._current_contact_id)
                if self._current_contact_id else None
            )
            self._latest_prosody_z = compute_prosody_z_score(prosody, baseline)
            # Update baseline (calibration)
            if self._current_contact_id:
                self._store.update_baseline(
                    self._current_contact_id, prosody=prosody
                )

    def feed_transcript(
        self,
        text: str,
        contact_id: Optional[str] = None,
    ) -> None:
        """Ingest a transcribed utterance."""
        if not text.strip():
            return
        if contact_id:
            self._current_contact_id = contact_id
        lf = extract_linguistic(text)
        baseline = (
            self._store.get_baseline(self._current_contact_id)
            if self._current_contact_id else None
        )
        self._latest_linguistic_z = compute_linguistic_z_score(lf, baseline)
        if self._current_contact_id:
            self._store.update_baseline(
                self._current_contact_id, linguistic=lf
            )

    # ------------------------------------------------------------------
    # Tick
    # ------------------------------------------------------------------

    def tick(self) -> Optional[LieLensResult]:
        """Return a LieLensResult if ready to emit, else None."""
        if not self._privacy.allow_capture():
            return None
        now = time.monotonic()
        if now - self._last_emit < self._cooldown_s:
            return None
        if self._window_count == 0:
            return None

        is_stranger = self._current_contact_id is None
        cv = fuse(
            micro_exp_z=self._latest_au_z,
            voice_stress_z=self._latest_prosody_z,
            linguistic_hedge_z=self._latest_linguistic_z,
            is_stranger=is_stranger,
            window_count=self._window_count,
        )

        if cv.confidence < 0.15:
            return None

        self._last_emit = now

        result = LieLensResult(
            credibility=cv,
            face=self._last_face,
            aus=self._last_aus,
        )

        # Log anomaly if elevated
        if cv.deception_prob >= 0.65 and self._current_contact_id:
            self._store.log_anomaly(self._current_contact_id, cv)

        return result

    def reset(self) -> None:
        """Clear session state (call when conversation ends)."""
        self._window_count = 0
        self._last_emit = 0.0
        self._latest_au_z = 0.0
        self._latest_prosody_z = 0.0
        self._latest_linguistic_z = 0.0
        self._current_contact_id = None
        self._last_face = None
        self._last_aus = None
