# Stasis — save states for your mind

> It doesn't remind you that you were doing something.
> It puts you back inside the doing.

When you're interrupted mid-task, three things die at once: the **goal
stack** (what you were doing and why), the **problem state** (the half-formed
sentence, the hypothesis mid-test — the expensive part; Gloria Mark's studies
put full resumption at ~23 minutes, and Altmann & Trafton's memory-for-goals
model explains why: goal activation decays in seconds), and the **context
binding** (what you were looking at, where you stood — retrieval is
context-dependent, Godden & Baddeley). Every reminder tool attacks the first
and ignores the other two, because no device *has* the other two. DreamLayer
does: the ring buffer already holds your last minute of thinking out loud,
**before** the interruption happens.

So Stasis is not a note-taking feature. You never author anything. The
freeze gesture takes zero seconds and zero words — the moment of interruption
is exactly the moment you have no spare cognition to spend describing your
state. The system already holds the state; the gesture just says *keep this*.
And the anxious rehearsal loop it replaces ("hinge torque, hinge torque…")
has a documented off-switch: the Zeigarnik intrusion releases the moment a
concrete plan for the unfinished task exists (Masicampo & Baumeister, 2011).
The shutter closing IS that plan, mechanized.

The loop, as the wearer lives it:

1. **Freeze** — double-nod (or *"hold that thought"*). The edge of vision
   dims for 400ms like a slow camera shutter; a ribbon glyph settles into
   the periphery and fades. Nothing to read, nothing to decide.
2. **The interval** — nothing. No badge, no count, no ambient nag. A
   dormant bookmark waits like a ribbon in a closed book.
3. **Resume** — tilt-reveal (the natural "settle back in" posture), say
   *"where was I"*, or just come back: same place signature or gaze landing
   on the same object re-lights the ribbon. **It offers; it never plays
   unbidden.** The replay is 8–12 seconds, ordered by how context
   reinstatement works — context first, content last: the scene, your
   overlays and anchors, the transcript tail, and finally your last
   sentence — larger, **verbatim**, unfinished: *"…so if the hinge is
   binding, the torque spike should show up when—"*. Then a beat of
   silence. The dash is the handoff; your brain finishes the sentence.
4. **Decay** — a frame is fresh for hours, fading for days; after ~7 days
   untouched it **composts**: the bookmark dissolves and its final
   utterance becomes an ordinary warm memory — findable by recall search,
   no longer an active bookmark. Frames you resume earn a longer half-life;
   NOD_SAVE on a replay card pins one forever (the "next month" hatch).

Stasis never summarizes or completes your thought. An AI paraphrase would
replace your problem state with its own — helpful-sounding, subtly wrong,
and a violation of the product's soul. Stasis returns your cues and trusts
your cognition — which is also why the phone tier alone is the full product:
no LLM in the loop, ever, and the cloud has no role because Stasis never has
a reason to leave the house.

## Architecture

```
   the ring already holds the state          the interruption arrives
  ┌───────────────────────────────┐                    │
  │ SemanticRingBuffer (90s tail) │   DOUBLE_NOD / "hold that thought"
  │ + one verbatim utterance      │────▶ freeze_context (ops_stasis.py)
  │ + gaze panel + place + anchors│         │ allow_capture() or silent no-op
  └───────────────────────────────┘         ▼
                              FreezeFrame → StasisStack (3 deep)
                              + kind="stasis" memories row (survives restart)
                                            │
        {t="stasis", mode="freeze"} ────────┘ shutter + ribbon
                 (host_comm_stasis.lua → display/stasis.lua)

  TILT_REVEAL / "where was I" / same-place / same-object return
        │                                   │
        ▼                                   ▼ debounced, one per return
  resume_stasis ──▶ choreography as    {t="stasis", mode="offer"}
  TimeScrubNodeCards (a scrub pointed       (ribbon glow only)
  at a frozen window — time_scrub.py)
        │
        ▼ untouched past its half-life, during the REM night
  compost_stasis ──▶ warm memory (meta.stasis_compost)
```

## The FreezeFrame

One object, deliberately just a bundle of things already dict-serializable:
the ring window (semantic events only, `meta.private` excluded at snapshot
time), one **verbatim** final utterance (the deliberate, scoped loosening of
the ring's semantic-only contract — a paraphrase kills the retrieval cue),
the gaze context (the ObjectPanel card Juno had open), active overlays and
ghost-layer anchors, the place signature, and the decay state. Persisted in
`meta.stasis` of a `kind="stasis"` memories row — embedded and ANN-indexed
like every ingest path, so a live bookmark is also recallable. **No new
tables, no raw media, ever.**

## Depth and decay are features

- **Three live frames, never more.** Interruptions nest (the doorbell
  interrupts the workbench; the phone interrupts the doorbell), so Stasis
  holds a stack — but beyond three, the oldest unpinned frame composts
  early. A tool for holding infinite open loops would recreate the disease
  it treats.
- **Composting rides the REM night** (`maybe_dream_tonight`): unresumed
  thoughts fold into memory while you sleep. Nothing nags; things quietly
  return to the soil.
- **Resume = heal.** Each resume resets the decay clock and extends the
  half-life by a week — the system learns which threads are alive.
- Cooler frames replay with one extra orienting line ("2 days ago ·
  workbench"): context reinstatement needs more scaffolding as traces cool.

## Tier behavior

| Tier | Role |
|---|---|
| Phone | The full product: freeze, decay, resume choreography, verbatim utterance. |
| + Mac mini | Nice-to-haves only: richer transcription upstream, and the compost pass rides the existing overnight sweep. |
| Cloud | No role. Stasis never has a reason to leave the house. |

Honest caveat, inherited not created: the host's live audio-capture path is
a seam awaiting the bridge layer (see `asr_faster_whisper.py`'s own note).
With no ASR feed, a freeze-frame still captures gaze, place, anchors, and
ring events — degraded but real.

## The Privacy Veil contract (all five, mechanically checkable)

1. **Freeze while veiled is a silent no-op** — `allow_capture()` false means
   the shutter never closes and nothing is stored.
2. **Resume is a read** — gated on `allow_recall()`: incognito can still
   resume old bookmarks; the full veil cannot.
3. **`meta.private` events never enter a snapshot** (same rule Commitment
   Drift's observer follows).
4. **Nothing raw** — semantic events and card dicts only; the serializer is
   structurally unable to carry a frame.
5. **A veiled return surfaces nothing** — the ambient-offer path sits behind
   the same gates as `on_place` itself, and the offer side re-checks
   `allow_recall()`.

## Plugin surface

`stasis_freeze` and `stasis_resume` are published on the plugin event bus —
a Pomodoro lens, a standup-notes lens, and a "focus room" lens all fall out
of these two moments for free.

## Testing

```
host-python:  pytest src/dreamlayer/tests/test_stasis_core.py \
                     test_stasis_ops.py test_stasis_lua.py
halo-lua:     luacheck .   (the shutter/ribbon draw through the real
                            renderer inside the frame budget)
```

The invariants the suites pin: veiled freeze stores nothing and sends
nothing; the snapshot is semantic-only and private-free; the final replay
card is the wearer's own sentence, verbatim, and nothing replayed was
invented; offers debounce to one per return and never auto-play; three
frames maximum; pinned frames never compost; a held thought survives a
restart; and the dormant state draws zero pixels.

---

*Ember is what DreamLayer does for memory across seasons; Stasis is what it
does for memory across minutes. Same tagline, opposite time scale.*
