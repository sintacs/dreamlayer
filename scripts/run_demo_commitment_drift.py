#!/usr/bin/env python3
"""scripts/run_demo_commitment_drift.py — a commitment lived as a physics object.

Tells one commitment's life as it bends under two forces — the clock
pushing it toward the deadline, and your behavior pushing back. You make
a promise, neglect it (it drifts, then cracks), tend it (it blooms back
down the ladder), and finally keep it (it blooms and pins). A second
promise is simply abandoned, and shatters.

Prints the state ladder at each beat so the drift is legible without a
display.

Run:  python scripts/run_demo_commitment_drift.py
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "host-python" / "src"))

from dreamlayer.memory.ring_buffer import SemanticRingBuffer          # noqa: E402
from dreamlayer.pipelines.ingest import MemoryEvent                   # noqa: E402
from dreamlayer.orchestrator.commitment_drift import (                # noqa: E402
    CommitmentDriftEngine,
)

H = 3600.0
BASE = 1_700_000_000.0

_GLYPH = {
    "blooming": "🌱 blooming",
    "healthy":  "🌿 healthy ",
    "drifting":  "🍂 drifting ",
    "cracking": "⚡ cracking",
    "shattered": "💥 shattered",
}


def bar(decay: float) -> str:
    n = max(0, min(20, round(decay * 20)))
    return "[" + "█" * n + "·" * (20 - n) + "]"


def show(eng, subject, now, note):
    rec = next(r for r in eng.all_records()
               if subject.lower() in (r.event.summary or "").lower())
    hrs = (now - BASE) / H
    print(f"  +{hrs:4.1f}h  {_GLYPH[rec.state]}  {bar(rec.decay)} "
          f"decay={rec.decay:.2f}  — {note}")


def main() -> int:
    ring = SemanticRingBuffer(capacity=50)
    ring.append(MemoryEvent(kind="task", summary="send Marcus the contract",
                            confidence=0.9,
                            meta={"person": "Marcus", "due": "6h"}),
                ts=BASE)
    ring.append(MemoryEvent(kind="task", summary="water the office plants",
                            confidence=0.6, meta={"due": "6h"}),
                ts=BASE)
    eng = CommitmentDriftEngine(ring)

    print("\nCommitment Drift — two promises, one afternoon\n")
    print("The contract: tended, then kept.")
    eng.tick(now=BASE + 0.2 * H);  show(eng, "contract", BASE + 0.2 * H, "just made")
    eng.tick(now=BASE + 3.0 * H);  show(eng, "contract", BASE + 3.0 * H, "neglected — drifting")
    eng.tick(now=BASE + 4.8 * H);  show(eng, "contract", BASE + 4.8 * H, "the deadline looms — cracking")

    # you do the work: an event in the stream that plainly refers to it
    ring.append(MemoryEvent(kind="memory",
                            summary="drafted the contract for Marcus",
                            confidence=0.85),
                ts=BASE + 4.9 * H)
    eng.tick(now=BASE + 4.9 * H)
    show(eng, "contract", BASE + 4.9 * H, "you worked on it — bloomed back")

    eng.keep("contract", now=BASE + 5.4 * H)
    eng.tick(now=BASE + 7.0 * H)   # past due, but kept
    show(eng, "contract", BASE + 7.0 * H, "kept — blooms and pins, even past due")

    print("\nThe plants: abandoned.")
    eng.tick(now=BASE + 3.0 * H);  show(eng, "plants", BASE + 3.0 * H, "drifting")
    eng.break_("plants", now=BASE + 3.1 * H)
    eng.tick(now=BASE + 3.2 * H);  show(eng, "plants", BASE + 3.2 * H, "let go — shattered")

    print("\nOn the Horizon these render as living objects: the bloom breathes,"
          "\nthe crack trembles, the shatter throws shards — behavior and time,"
          "\nvisible at a glance.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
