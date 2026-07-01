"""lie_lens/schema.py — All dataclasses for Lie Lens."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import numpy as np


# ---------------------------------------------------------------------------
# Stage outputs
# ---------------------------------------------------------------------------

@dataclass
class FaceEmbedding:
    embedding: np.ndarray       # 512-d float32 vector
    confidence: float           # face detection confidence 0-1
    contact_id: Optional[str] = None  # matched contact, if any
    match_score: float = 0.0


@dataclass
class ActionUnits:
    """17 facial action unit activations (0-1 each)."""
    au1:  float = 0.0   # inner brow raise
    au2:  float = 0.0   # outer brow raise
    au4:  float = 0.0   # brow lowerer
    au5:  float = 0.0   # upper lid raiser
    au6:  float = 0.0   # cheek raiser
    au7:  float = 0.0   # lid tightener
    au9:  float = 0.0   # nose wrinkler
    au10: float = 0.0   # upper lip raiser
    au12: float = 0.0   # lip corner puller
    au14: float = 0.0   # dimpler
    au15: float = 0.0   # lip corner depressor
    au17: float = 0.0   # chin raiser
    au20: float = 0.0   # lip stretcher
    au23: float = 0.0   # lip tightener
    au25: float = 0.0   # lips part
    au26: float = 0.0   # jaw drop
    au45: float = 0.0   # blink

    def as_vector(self) -> list[float]:
        return [
            self.au1, self.au2, self.au4, self.au5, self.au6,
            self.au7, self.au9, self.au10, self.au12, self.au14,
            self.au15, self.au17, self.au20, self.au23, self.au25,
            self.au26, self.au45,
        ]

    def deception_indicators(self) -> dict[str, float]:
        """AUs associated with deception / masking in FACS literature."""
        return {
            "mask_smile":    self.au12 * (1 - self.au6),  # lip smile without eye
            "brow_furrow":   self.au4,
            "lip_tighten":   self.au23,
            "gaze_aversion": self.au5 * self.au7,         # lid raise + tighten
            "nose_wrinkle":  self.au9,
        }


@dataclass
class ProsodyFeatures:
    pitch_mean_hz: float
    pitch_variance: float
    jitter_pct: float
    shimmer_pct: float
    hesitation_rate: float   # pauses per second
    speech_rate_norm: float  # relative to speaker baseline
    energy_db: float
    window_ms: int


@dataclass
class LinguisticFeatures:
    hedging_rate: float      # "maybe", "I think", "sort of" per sentence
    first_person_rate: float # "I" usage (distancing = less "I")
    complexity_score: float  # avg words per clause
    negation_rate: float     # "not", "never", "no" per sentence
    qualifier_rate: float    # "very", "actually", "honestly" per sentence
    utterance: str = ""


# ---------------------------------------------------------------------------
# Fusion output
# ---------------------------------------------------------------------------

@dataclass
class CredibilityVector:
    """Output of the fusion engine — one per analysis cycle."""
    deception_prob: float        # 0.0 = very credible, 1.0 = high deception signal
    confidence: float            # data quality / quantity 0-1
    micro_exp_z: float           # AU z-score vs baseline
    voice_stress_z: float        # prosody z-score vs baseline
    linguistic_hedge_z: float    # linguistic z-score vs baseline
    dominant_signal: str         # which dimension is driving the score
    is_stranger: bool = False    # no baseline available

    @property
    def label(self) -> str:
        if self.confidence < 0.3:
            return "READING"
        if self.deception_prob < 0.40:
            return "CREDIBLE"
        if self.deception_prob < 0.65:
            return "UNCERTAIN"
        if self.deception_prob < 0.85:
            return "ELEVATED"
        return "HIGH SIGNAL"

    @property
    def hud_color(self) -> int:
        """Halo RGB565 color."""
        if self.confidence < 0.3:
            return 0x7BEF   # grey
        if self.deception_prob < 0.40:
            return 0x07E0   # green
        if self.deception_prob < 0.65:
            return 0xFFE0   # yellow
        if self.deception_prob < 0.85:
            return 0xFD20   # orange
        return 0xF800       # red


# ---------------------------------------------------------------------------
# Narrative memory
# ---------------------------------------------------------------------------

@dataclass
class ContactBaseline:
    contact_id: str
    au_mean: list[float] = field(default_factory=lambda: [0.0] * 17)
    au_std:  list[float] = field(default_factory=lambda: [0.1] * 17)
    prosody_mean: dict = field(default_factory=dict)
    prosody_std:  dict = field(default_factory=dict)
    linguistic_mean: dict = field(default_factory=dict)
    linguistic_std:  dict = field(default_factory=dict)
    sample_count: int = 0

    def is_calibrated(self) -> bool:
        return self.sample_count >= 10


@dataclass
class AnomalyLog:
    contact_id: str
    timestamp: float
    credibility: CredibilityVector
    user_label: Optional[str] = None   # "false_positive", "confirmed", etc.


# ---------------------------------------------------------------------------
# Top-level result
# ---------------------------------------------------------------------------

@dataclass
class LieLensResult:
    credibility: CredibilityVector
    face: Optional[FaceEmbedding] = None
    aus: Optional[ActionUnits] = None
    prosody: Optional[ProsodyFeatures] = None
    linguistic: Optional[LinguisticFeatures] = None

    def to_hud_card(self) -> dict:
        c = self.credibility
        detail_parts = []
        if self.prosody:
            detail_parts.append(f"voice {round(self.prosody.jitter_pct, 1)}%j")
        if self.aus:
            ind = self.aus.deception_indicators()
            top = max(ind, key=ind.get)
            detail_parts.append(f"AU:{top}")
        if self.linguistic:
            detail_parts.append(f"hedge {round(self.linguistic.hedging_rate, 2)}")

        return {
            "type": "LieLensCard",
            "dismiss_ms": 5000,
            "eyebrow": "LIE LENS" + (" · STRANGER" if c.is_stranger else ""),
            "primary": c.label,
            "detail": "  ·  ".join(detail_parts) if detail_parts else c.dominant_signal,
            "footer": f"conf {round(c.confidence * 100)}%",
            "score": round(c.deception_prob, 3),
            "confidence": round(c.confidence, 3),
            "color": c.hud_color,
            "dominant_signal": c.dominant_signal,
            "opacity": 0.9 if c.confidence >= 0.3 else 0.4,
            "lines": ["LIE LENS", c.label,
                      f"{round(c.deception_prob * 100)}% signal"],
            "layout": {
                "eyebrow": {"x": 128, "y": 196, "size": "sm",
                            "color": c.hud_color, "tracking": 3},
                "primary": {"x": 128, "y": 216, "size": "sm",
                            "color": c.hud_color},
                "detail":  {"x": 128, "y": 232, "size": "sm",
                            "color": 0x5EF7},
            },
        }
