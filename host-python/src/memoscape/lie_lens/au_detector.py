"""lie_lens/au_detector.py — Facial Action Unit detector.

In production, ActionUnits are produced by OpenFace MobileNetV3 INT8
running on the Alif B1 NPU. In the host-Python layer we accept an
AU vector directly from the camera pipeline and wrap it into the
ActionUnits schema, then compute deception-relevant z-scores against
a per-contact baseline.
"""
from __future__ import annotations
import math
from typing import Optional
from .schema import ActionUnits, ContactBaseline

AU_FIELDS = [
    "au1", "au2", "au4", "au5", "au6", "au7",
    "au9", "au10", "au12", "au14", "au15", "au17",
    "au20", "au23", "au25", "au26", "au45",
]


def vector_to_aus(vec: list[float]) -> ActionUnits:
    """Convert a 17-element float list to an ActionUnits dataclass."""
    if len(vec) < 17:
        vec = vec + [0.0] * (17 - len(vec))
    kwargs = {field: vec[i] for i, field in enumerate(AU_FIELDS)}
    return ActionUnits(**kwargs)


def compute_au_z_score(aus: ActionUnits,
                       baseline: Optional[ContactBaseline]) -> float:
    """Return a scalar z-score representing AU deviation from baseline.

    Higher = more unusual expression pattern relative to this person's norm.
    If no baseline, returns 0.0 (unknown).
    """
    if baseline is None or not baseline.is_calibrated():
        return 0.0

    vec = aus.as_vector()
    z_scores = []
    for i, (v, mean, std) in enumerate(
        zip(vec, baseline.au_mean, baseline.au_std)
    ):
        if std > 0:
            z_scores.append(abs(v - mean) / std)

    return sum(z_scores) / len(z_scores) if z_scores else 0.0


def deception_au_score(aus: ActionUnits) -> float:
    """Heuristic deception score from raw AU values (no baseline required).

    Based on FACS deception literature:
    - Duchenne vs. non-Duchenne smile (AU12 without AU6)
    - Brow suppression (low AU1+AU2 during negative emotion cues)
    - Lip tightening (AU23)
    - Nose wrinkle (AU9)
    """
    score = 0.0
    ind = aus.deception_indicators()
    score += min(ind["mask_smile"] * 0.35, 0.35)
    score += min(ind["brow_furrow"] * 0.25, 0.25)
    score += min(ind["lip_tighten"] * 0.20, 0.20)
    score += min(ind["nose_wrinkle"] * 0.15, 0.15)
    score += min(ind["gaze_aversion"] * 0.05, 0.05)
    return min(score, 1.0)
