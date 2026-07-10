"""Figment Golf — the community sport of proof-carrying machines
(INNOVATION_SESSION 1.3).

The sandbox limits (≤32 scenes, ≤8 counters, ≤5 lines × 24 chars, ≤4 Hz pulse,
emit burst 5 / refill 1/s) are public and provable, so "the most expressive
behavior in the fewest bytes" is a real competitive format — and the compiler is
the referee: an entry is only *eligible* if `budgets.verify()` passes. This
module scores an eligible figment's expressiveness per byte; no new runtime code,
it reads the existing model.
"""
from __future__ import annotations

from .budgets import verify
from .figment import Figment


def score(fig: Figment) -> dict:
    """Expressiveness-per-byte breakdown. `golf_score` is expressiveness per
    1000 canonical bytes — higher is better (more machine, fewer bytes)."""
    events: set[str] = set()
    emits = pulses = lines = 0
    for s in fig.scenes.values():
        events.update(s.on.keys())
        if s.on_timeout:
            events.add("timeout")
        if s.tick:
            events.add(f"tick:{s.tick}")
        if s.pulse:
            pulses += 1
        lines += len(s.lines)
        for tr in list(s.on.values()) + list(s.on_timeout):
            if getattr(tr, "emit", None):
                emits += 1
    scenes = len(fig.scenes)
    counters = len(fig.counters)
    nbytes = len(fig.canonical_json().encode("utf-8"))
    # The rubric (doc 1.3): scenes reached, counters used, event types handled —
    # plus emphasis (pulses) and copy (lines, weight-capped so text can't pad).
    expressiveness = (scenes + len(events) + counters + pulses + emits
                      + min(lines, scenes * 2))
    golf = round(expressiveness * 1000.0 / nbytes, 2) if nbytes else 0.0
    return {
        "bytes": nbytes,
        "scenes": scenes,
        "event_types": sorted(events),
        "distinct_events": len(events),
        "counters": counters,
        "pulses": pulses,
        "emits": emits,
        "lines": lines,
        "expressiveness": expressiveness,
        "golf_score": golf,
    }


def referee(fig: Figment) -> dict:
    """Run the gate + the score. `ok` is the eligibility verdict; a figment that
    violates a budget is disqualified regardless of how clever it is."""
    rep = verify(fig)
    return {
        "ok": rep.ok,
        "violations": [str(v) for v in rep.violations],
        "warnings": [str(w) for w in rep.warnings],
        "proof": {
            "scene_count": rep.scene_count,
            "worst_display_hz": rep.worst_display_hz,
            "worst_emit_per_sec": rep.worst_emit_per_sec,
        },
        "score": score(fig),
    }
