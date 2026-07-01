"""lie_lens/renderer.py — HUD card renderer for Lie Lens.

Converts a LieLensResult into a HUD card dict ready for the
existing Halo display pipeline.

The sub-perceptual rendering described in the Lua spec
(chromatic aberration shader, particle system, bone-conduction
audio delay line) is defined here as structured metadata
that the Lua bridge on the Halo side interprets.
"""
from __future__ import annotations
from .schema import LieLensResult, CredibilityVector

# Thresholds matching the Lua CONFIG
DECEPTION_THRESHOLD = 0.65
CONFIDENCE_THRESHOLD = 0.30


def render(result: LieLensResult) -> dict:
    """Return a complete HUD + sub-perceptual render payload.

    The returned dict contains:
    - 'card'            : LieLensCard for the HUD renderer
    - 'sub_perceptual'  : chromatic/particle/audio metadata for Lua bridge
    """
    card = result.to_hud_card()
    sub = _sub_perceptual(result.credibility)
    return {"card": card, "sub_perceptual": sub}


def _sub_perceptual(c: CredibilityVector) -> dict:
    """Build sub-perceptual cue metadata.

    Sub-perceptual cues are rendered by the Lua layer on-device.
    They are suppressed when confidence is below threshold or
    deception probability is low.
    """
    active = (
        c.deception_prob >= DECEPTION_THRESHOLD
        and c.confidence >= CONFIDENCE_THRESHOLD
    )

    if not active:
        return {"active": False}

    # Chromatic aberration: stress → RGB fringe at face edges
    stress_strength = c.voice_stress_z * 0.002

    # Particle color: red if very high signal, amber if elevated
    if c.deception_prob >= 0.85:
        particle_color = 0xF800   # red
    elif c.deception_prob >= 0.65:
        particle_color = 0xFD20   # orange
    else:
        particle_color = 0x07E0   # green (reading / calm)

    # Bone conduction audio delay: hesitation → 10-15ms variable delay
    # (Only meaningful if Halo bone conduction bridge is active)
    delay_ms = min(c.linguistic_hedge_z * 5.0, 15.0)

    return {
        "active": True,
        "chromatic_aberration": round(stress_strength, 4),
        "particle_density": round(min(c.confidence * 0.8, 1.0), 2),
        "particle_color": particle_color,
        "bone_conduction_delay_ms": round(delay_ms, 1),
        "dismiss_ms": 5000,
    }
