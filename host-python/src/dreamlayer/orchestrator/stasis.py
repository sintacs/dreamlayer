"""stasis.py — save states for your mind.

When you're interrupted mid-task, three things die at once: the goal stack
(what you were doing and why), the problem state (the half-formed sentence,
the hypothesis mid-test — the expensive part; Altmann & Trafton's
memory-for-goals model says its activation decays in seconds), and the
context binding (what you were looking at, where you stood — and retrieval
is context-dependent, Godden & Baddeley). Every reminder tool attacks the
first and ignores the other two, because no device *has* the other two.
This one does: the ring buffer already holds your last minute of thinking
out loud, before the interruption happens.

So a freeze-frame is never authored. The gesture costs zero words and zero
decisions — the moment of interruption is exactly the moment you have no
spare cognition to spend describing your state. The system already holds
the state; the gesture just says *keep this*. And the payoff is documented
cognition: the Zeigarnik intrusion loop ("hinge torque, hinge torque…")
releases the moment a concrete plan for the unfinished task exists
(Masicampo & Baumeister, 2011). The shutter closing IS that plan.

This module is the pure core: the FreezeFrame record, the three-deep
StasisStack, and the decay ladder (fresh → fading → cool → compost),
borrowed in spirit from Commitment Drift. No I/O, no clock reads — every
function takes `now`, so the ops layer and the tests drive the same math.

Two deliberate limits, both features:

  * At most MAX_LIVE (3) freeze-frames. A tool for holding infinite open
    loops would recreate the disease it treats; beyond three, the oldest
    composts early.
  * Frames compost (~7 days untouched): the bookmark dissolves and only
    its final utterance survives as an ordinary warm memory. Nothing nags;
    things quietly return to the soil. Resuming a frame extends its
    half-life — the system learns which threads are alive — and
    meta.pinned is the "next month" escape hatch.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace

DAY = 86400.0

MAX_LIVE = 3                  # the stack admits three live frames, never more
TAIL_S = 90.0                 # how much ring history a freeze snapshots
COMPOST_HALF_LIFE_DAYS = 7.0  # untouched frames dissolve after ~a week…
RESUME_HALF_LIFE_BONUS = 1.0  # …plus a week per resume (a live thread earns time)

# Decay checkpoints on the 0..1 ladder (elapsed / half-life):
FRESH_BELOW = 0.15            # a few hours: replay at full trust
FADING_BELOW = 0.60           # a few days: replay adds an orienting line


@dataclass(frozen=True)
class FreezeFrame:
    """One held thought: the problem state and its context binding, bundled.

    Everything inside is already dict-serializable semantic data — ring
    events, card dicts, anchor dicts. Nothing raw, ever: the ring's
    "structured, never raw" contract is inherited wholesale, and the one
    deliberate loosening is `final_utterance` — a single verbatim transcript
    segment, because a paraphrase would kill the retrieval cue (the whole
    point is handing back *your* unfinished sentence, dash included)."""
    id: int                        # memories-row id (kind="stasis")
    created_ts: float
    place_signature: str = ""
    imu_pose: dict | None = None
    ring_window: list = field(default_factory=list)   # serialized events
    final_utterance: str = ""      # verbatim; scoped to exactly one utterance
    gaze_context: dict | None = None                  # ObjectPanel card dict
    gaze_key: str = ""             # sighting key for ambient context-match
    overlays: list = field(default_factory=list)      # active card dicts
    anchors: list = field(default_factory=list)       # ghost-layer anchors
    last_resumed_ts: float = 0.0
    resume_count: int = 0
    meta: dict = field(default_factory=dict)          # pinned? private?

    # -- the decay ladder ---------------------------------------------------

    def half_life_s(self) -> float:
        """A week untouched, plus a week per resume: threads you keep
        returning to earn longer lives; threads you don't, compost."""
        return (COMPOST_HALF_LIFE_DAYS
                + RESUME_HALF_LIFE_BONUS * self.resume_count) * DAY

    def touched_ts(self) -> float:
        return max(self.created_ts, self.last_resumed_ts)

    def decay(self, now: float) -> float:
        """0.0 the moment it's touched → 1.0 at compost. Pinned frames sit
        at 0 forever (the "I'll get back to this next month" escape hatch)."""
        if self.meta.get("pinned"):
            return 0.0
        elapsed = max(0.0, now - self.touched_ts())
        return min(1.0, elapsed / self.half_life_s())

    def freshness(self, now: float) -> str:
        d = self.decay(now)
        if d < FRESH_BELOW:
            return "fresh"
        if d < FADING_BELOW:
            return "fading"
        return "cool"

    def compost_due(self, now: float) -> bool:
        return self.decay(now) >= 1.0

    def resumed(self, now: float) -> "FreezeFrame":
        """A resume is both a read and a heal: the trace was reinstated in
        the wearer, so the bookmark earns a fresh clock and a longer life."""
        return replace(self, last_resumed_ts=now,
                       resume_count=self.resume_count + 1)

    def pinned(self) -> "FreezeFrame":
        return replace(self, meta={**self.meta, "pinned": True})

    # -- serialization (rides a memories row's meta column) ------------------

    def to_payload(self) -> dict:
        return {
            "created_ts": self.created_ts,
            "place_signature": self.place_signature,
            "imu_pose": self.imu_pose,
            "ring_window": self.ring_window,
            "final_utterance": self.final_utterance,
            "gaze_context": self.gaze_context,
            "gaze_key": self.gaze_key,
            "overlays": self.overlays,
            "anchors": self.anchors,
            "last_resumed_ts": self.last_resumed_ts,
            "resume_count": self.resume_count,
            "meta": self.meta,
        }

    @classmethod
    def from_payload(cls, row_id: int, payload: dict) -> "FreezeFrame":
        return cls(
            id=int(row_id),
            created_ts=float(payload.get("created_ts") or 0.0),
            place_signature=payload.get("place_signature") or "",
            imu_pose=payload.get("imu_pose"),
            ring_window=list(payload.get("ring_window") or []),
            final_utterance=payload.get("final_utterance") or "",
            gaze_context=payload.get("gaze_context"),
            gaze_key=payload.get("gaze_key") or "",
            overlays=list(payload.get("overlays") or []),
            anchors=list(payload.get("anchors") or []),
            last_resumed_ts=float(payload.get("last_resumed_ts") or 0.0),
            resume_count=int(payload.get("resume_count") or 0),
            meta=dict(payload.get("meta") or {}),
        )


class StasisStack:
    """The three-deep stack of live freeze-frames. Pure in-memory (the ops
    layer owns persistence, exactly as CommitmentDriftEngine leaves rows to
    the coordinator); every mutator returns what changed so the caller can
    mirror it to disk."""

    def __init__(self, max_live: int = MAX_LIVE):
        self._max = max(1, int(max_live))
        self._frames: list[FreezeFrame] = []   # oldest → newest

    # -- reading -------------------------------------------------------------

    def frames(self) -> list[FreezeFrame]:
        """Live frames, newest first (the top is what tilt-reveal resumes)."""
        return list(reversed(self._frames))

    def top(self) -> FreezeFrame | None:
        return self._frames[-1] if self._frames else None

    def get(self, frame_id: int) -> FreezeFrame | None:
        return next((f for f in self._frames if f.id == frame_id), None)

    def __len__(self) -> int:
        return len(self._frames)

    def match_context(self, place_signature: str | None = None,
                      gaze_key: str | None = None) -> FreezeFrame | None:
        """The ambient-offer matcher: has the wearer returned to a frozen
        context? Same place signature, or gaze landing on the same object.
        Newest match wins (the thread they left most recently)."""
        for f in reversed(self._frames):
            if place_signature and f.place_signature and \
                    f.place_signature == place_signature:
                return f
            if gaze_key and f.gaze_key and f.gaze_key == gaze_key:
                return f
        return None

    # -- mutating ------------------------------------------------------------

    def push(self, frame: FreezeFrame) -> list[FreezeFrame]:
        """Add a frame; returns frames evicted to honor the depth limit
        (oldest unpinned composts early — beyond three, holding more open
        loops is the disease, not the cure). A stack of all-pinned frames
        evicts the oldest pinned one rather than growing unbounded."""
        self._frames.append(frame)
        evicted: list[FreezeFrame] = []
        while len(self._frames) > self._max:
            victim = next((f for f in self._frames
                           if not f.meta.get("pinned")), self._frames[0])
            self._frames.remove(victim)
            evicted.append(victim)
        return evicted

    def replace_frame(self, frame: FreezeFrame) -> None:
        self._frames = [frame if f.id == frame.id else f
                        for f in self._frames]

    def remove(self, frame_id: int) -> FreezeFrame | None:
        f = self.get(frame_id)
        if f is not None:
            self._frames.remove(f)
        return f

    def compost_due(self, now: float) -> list[FreezeFrame]:
        """Remove and return every frame past its half-life. The caller
        writes each one's final utterance to warm memory — the bookmark
        dissolves; the thought stays findable."""
        due = [f for f in self._frames if f.compost_due(now)]
        for f in due:
            self._frames.remove(f)
        return due

    def load(self, frames: list[FreezeFrame]) -> None:
        """Restore live frames (e.g. from kind="stasis" rows at boot),
        oldest first, honoring the depth limit."""
        self._frames = []
        for f in sorted(frames, key=lambda x: x.created_ts)[-self._max:]:
            self._frames.append(f)
