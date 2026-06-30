"""lie_sense/schema.py — Data structures for LieSense output."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class StressSignal:
    """A single stress/deception signal extracted from one audio window."""
    pitch_mean_hz: float        # mean fundamental frequency
    pitch_variance: float       # variance of F0 (high = stress marker)
    jitter_pct: float           # cycle-to-cycle pitch irregularity %
    shimmer_pct: float          # cycle-to-cycle amplitude irregularity %
    pause_ratio: float          # fraction of window that is silence
    speech_rate_norm: float     # relative speech rate (1.0 = baseline)
    energy_db: float            # RMS energy in dB
    window_ms: int              # window duration in ms

    def stress_score(self) -> float:
        """Heuristic 0-1 stress score for this window."""
        score = 0.0
        # Elevated pitch variance = stress
        score += min(self.pitch_variance / 500.0, 0.25)
        # High jitter = vocal tension
        score += min(self.jitter_pct / 5.0, 0.20)
        # High shimmer = tremor
        score += min(self.shimmer_pct / 8.0, 0.20)
        # Unusual pause ratio (too many or too few pauses)
        pause_dev = abs(self.pause_ratio - 0.25)
        score += min(pause_dev / 0.25, 0.20)
        # Abnormal speech rate
        rate_dev = abs(self.speech_rate_norm - 1.0)
        score += min(rate_dev / 0.5, 0.15)
        return min(score, 1.0)


@dataclass
class DeceptionScore:
    """Aggregated deception likelihood from a rolling window of StressSignals."""
    score: float                # 0.0 (no signal) → 1.0 (high stress)
    confidence: float           # how much data we have (0.0 = too little)
    dominant_signal: str        # which feature is driving the score
    window_count: int           # number of windows averaged

    @property
    def label(self) -> str:
        if self.confidence < 0.4:
            return "READING"
        if self.score < 0.35:
            return "CALM"
        if self.score < 0.60:
            return "ELEVATED"
        if self.score < 0.80:
            return "HIGH STRESS"
        return "VERY HIGH"

    @property
    def color(self) -> int:
        """Halo 16-bit RGB565 color for the HUD indicator."""
        if self.confidence < 0.4:
            return 0x7BEF   # grey
        if self.score < 0.35:
            return 0x07E0   # green
        if self.score < 0.60:
            return 0xFFE0   # yellow
        if self.score < 0.80:
            return 0xFD20   # orange
        return 0xF800       # red


@dataclass
class LieSenseResult:
    """Output emitted by LieSense.tick() when a displayable result is ready."""
    deception: DeceptionScore
    signals: list[StressSignal] = field(default_factory=list)
    speaker_id: Optional[str] = None

    def to_hud_card(self) -> dict:
        """Render as a Halo HUD card dict (compatible with hud/cards system)."""
        d = self.deception
        return {
            "type": "LieSenseCard",
            "dismiss_ms": 4000,
            "label": d.label,
            "score": round(d.score, 2),
            "confidence": round(d.confidence, 2),
            "dominant_signal": d.dominant_signal,
            "color": d.color,
            "primary": d.label,
            "eyebrow": "LIE SENSE",
            "detail": f"{d.dominant_signal}  •  {round(d.score * 100)}%",
            "footer": f"{d.window_count} windows",
            "opacity": 0.85 if d.confidence >= 0.4 else 0.4,
            "lines": ["LIE SENSE", d.label, f"{round(d.score * 100)}% stress"],
            "layout": {
                "eyebrow": {"x": 128, "y": 200, "size": "sm",
                            "color": d.color, "tracking": 3},
                "primary": {"x": 128, "y": 220, "size": "sm", "color": d.color},
                "detail":  {"x": 128, "y": 236, "size": "sm", "color": 0x5EF7},
            },
        }
