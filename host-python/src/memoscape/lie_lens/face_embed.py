"""lie_lens/face_embed.py — Face detection and 512-d embedding.

In production this wraps the NPU call to MobileFaceNet INT8.
In the host-Python layer we work with pre-computed embedding vectors
passed in from the camera pipeline (same pattern as the rest of the
pipelines module).
"""
from __future__ import annotations
from typing import Optional
import numpy as np
from .schema import FaceEmbedding

FACE_THRESHOLD = 0.65   # cosine similarity threshold for contact match
EMBEDDING_DIM = 512


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity between two 1-D float vectors."""
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


class FaceEmbedder:
    """Wraps face detection + embedding.

    Parameters
    ----------
    contacts : dict[str, np.ndarray]
        Mapping of contact_id → 512-d embedding vector.
        Loaded from the narrative store at startup.
    threshold : float
        Minimum cosine similarity to count as a match.
    """

    def __init__(self,
                 contacts: Optional[dict[str, np.ndarray]] = None,
                 threshold: float = FACE_THRESHOLD):
        self._contacts: dict[str, np.ndarray] = contacts or {}
        self._threshold = threshold

    def update_contacts(self, contacts: dict[str, np.ndarray]) -> None:
        self._contacts = contacts

    def process(self,
                embedding: np.ndarray,
                detection_confidence: float = 1.0) -> FaceEmbedding:
        """Given a raw 512-d embedding, find the best matching contact.

        Parameters
        ----------
        embedding : np.ndarray
            512-d float32 vector from the NPU face model.
        detection_confidence : float
            Face detection confidence from the NPU (0-1).

        Returns
        -------
        FaceEmbedding
            Populated with contact_id + match_score if a match is found.
        """
        if embedding is None or len(embedding) != EMBEDDING_DIM:
            return FaceEmbedding(
                embedding=np.zeros(EMBEDDING_DIM, dtype=np.float32),
                confidence=0.0,
            )

        best_id: Optional[str] = None
        best_score: float = 0.0

        for contact_id, contact_emb in self._contacts.items():
            score = cosine_similarity(embedding, contact_emb)
            if score > best_score:
                best_score = score
                best_id = contact_id

        if best_score >= self._threshold:
            return FaceEmbedding(
                embedding=embedding,
                confidence=detection_confidence,
                contact_id=best_id,
                match_score=best_score,
            )

        return FaceEmbedding(
            embedding=embedding,
            confidence=detection_confidence,
            contact_id=None,
            match_score=best_score,
        )
