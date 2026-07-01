"""lie_lens/fusion.py — Multi-signal z-score fusion engine.

Combines AU z-score, prosody z-score, and linguistic z-score into a
single CredibilityVector using recency-weighted signal averaging.

In production, a Phi-3-mini-4k LoRA INT4 model on the Alif NPU provides
richer contextual fusion; this implementation provides the host-side
equivalent using the same signal inputs and output schema.
"""
from __future__ import annotations
from .schema import CredibilityVector

# How many signal dimensions we have
_N_SIGNALS = 3

# Per-signal weights (must sum to 1.0)
_WEIGHTS = {
    "micro_exp":       0.35,   # facial AUs — hardest to fake
    "voice_stress":    0.40,   # prosody — most continuous signal
    "linguistic_hedge":0.25,   # linguistic — easiest to fake
}

# Z-score normalisation: map z=3 → p≈0.85, z=0 → p≈0.0
_Z_SCALE = 3.0


def _z_to_prob(z: float) -> float:
    """Map a z-score to a 0-1 probability using a simple sigmoid."""
    return 1.0 / (1.0 + 2.718 ** -(z - 1.5))


def fuse(
    micro_exp_z: float,
    voice_stress_z: float,
    linguistic_hedge_z: float,
    is_stranger: bool = False,
    window_count: int = 1,
) -> CredibilityVector:
    """Fuse three z-scores into a CredibilityVector.

    Parameters
    ----------
    micro_exp_z : float
        AU deviation z-score vs contact baseline.
    voice_stress_z : float
        Prosody deviation z-score vs contact baseline.
    linguistic_hedge_z : float
        Linguistic feature z-score vs contact baseline.
    is_stranger : bool
        True if no baseline available; applies conservative threshold.
    window_count : int
        Number of analysis windows processed (drives confidence).

    Returns
    -------
    CredibilityVector
    """
    probs = {
        "micro_exp":        _z_to_prob(micro_exp_z),
        "voice_stress":     _z_to_prob(voice_stress_z),
        "linguistic_hedge": _z_to_prob(linguistic_hedge_z),
    }

    weighted = sum(probs[k] * _WEIGHTS[k] for k in probs)

    # Stranger penalty: require all three signals to be high
    if is_stranger:
        all_high = all(z > 2.5 for z in
                       [micro_exp_z, voice_stress_z, linguistic_hedge_z])
        if not all_high:
            weighted = min(weighted, 0.45)

    # Confidence: rises with window count, saturates at 10
    confidence = min(window_count / 10.0, 1.0)

    dominant = max(probs, key=probs.get)

    return CredibilityVector(
        deception_prob=round(min(weighted, 1.0), 3),
        confidence=round(confidence, 3),
        micro_exp_z=round(micro_exp_z, 3),
        voice_stress_z=round(voice_stress_z, 3),
        linguistic_hedge_z=round(linguistic_hedge_z, 3),
        dominant_signal=dominant,
        is_stranger=is_stranger,
    )
