"""Earcon & Haptic Packs — sound design as a plugin genre (INNOVATION_SESSION 1.5).

A pack is a data artifact that reskins the platform's *feel*: a haptic table
(mirroring phone-app/src/services/haptics.ts — weight × pattern × repetition) and
earcon families (mirroring sound.ts). This module is the store-gate authority
that enforces the sensory rules a pack must obey, so the phone can trust any pack
it loads. The pack *picker* is the phone half (a follow-on).

Pack shape (JSON):
    {
      "name": "Analog",
      "haptics": { "confirm": [{"at": 0}, {"at": 120}], "answer_ahead": [] },
      "earcons": { "listen": ["listen1.mp3", "listen2.mp3"] }
    }

Rules enforced (from haptics.ts's own grammar):
  - every haptic pattern spans ≤ 400 ms (a pocket must never feel like a pager);
  - ``answer_ahead`` stays silent by design (it must be an empty pattern);
  - earcon families carry ≥ 2 variants so the never-repeat rotation holds.
"""
from __future__ import annotations

# The single silent-by-design signal (haptics.ts: answer_ahead is a no-op).
SILENT_SIGNALS = frozenset({"answer_ahead"})
MAX_PATTERN_MS = 400


def validate_pack(pack: dict) -> tuple[bool, list[str]]:
    """Return (ok, reasons). Empty reasons ⇢ the pack passes the sensory gate."""
    reasons: list[str] = []
    if not isinstance(pack, dict):
        return False, ["pack must be a JSON object"]
    if not (pack.get("name") or "").strip():
        reasons.append("pack has no name")

    haptics = pack.get("haptics") or {}
    if not isinstance(haptics, dict):
        reasons.append("'haptics' must be a table of signal → beats")
        haptics = {}
    for sig, beats in haptics.items():
        if not isinstance(beats, list):
            reasons.append(f"haptic {sig!r}: pattern must be a list of beats")
            continue
        if sig in SILENT_SIGNALS:
            if beats:
                reasons.append(f"haptic {sig!r} must stay silent by design "
                               f"(answer-ahead is a deliberate no-op)")
            continue
        span = max((int(b.get("at", 0)) for b in beats if isinstance(b, dict)),
                   default=0)
        if span > MAX_PATTERN_MS:
            reasons.append(f"haptic {sig!r}: pattern spans {span}ms > {MAX_PATTERN_MS}ms "
                           f"(a pocket shouldn't feel like a pager)")

    earcons = pack.get("earcons") or {}
    if not isinstance(earcons, dict):
        reasons.append("'earcons' must be a table of family → clips")
        earcons = {}
    for fam, clips in earcons.items():
        if not isinstance(clips, list) or not clips:
            reasons.append(f"earcon family {fam!r} is empty")
        elif len(clips) < 2:
            reasons.append(f"earcon family {fam!r} needs ≥2 variants for the "
                           f"never-repeat rotation")

    return (not reasons, reasons)
