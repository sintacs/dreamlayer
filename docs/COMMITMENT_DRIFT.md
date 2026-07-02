# Commitment Drift — promises as physics objects

A commitment on the Horizon is not a static tick. It is a small object
under two forces, and it *behaves* under them:

- **time pressure** — the clock pushes the object toward its deadline
- **behavior** — what you actually do pushes back: tending a promise
  *heals* it toward bloom; abandoning it *shatters* it

The result is a rim instrument you can read at a glance: the shape of a
promise tells you not just when it is due, but whether it is thriving.

## The state ladder

Decay is a single 0–1 float after both forces resolve, classified into
five states (`orchestrator/commitment_drift.py`):

| decay | state | on the Horizon |
|---|---|---|
| `< 0.20` | **blooming** | a dot that breathes — drawing sap |
| `0.20–0.50` | **healthy** | a steady dot |
| `0.50–0.75` | **drifting** | an amber dot with a stem |
| `0.75–1.00` | **cracking** | the dot trembles; a hairline fissure grows |
| `≥ 1.00` | **shattered** | a fractured tick whose halves drift apart, throwing shards |

The five states already ship in the Horizon wire as the promise state
digit of `code = kind*100 + state*10 + luma`, so Commitment Drift adds no
new BLE type — it makes the states *live*.

## The behavior model

Time decay is `elapsed / span`, exactly as before. Behavior enters as
**heal credit** that subtracts from it:

```
decay = max(0, time_decay − heal_credit)
```

Heal credit is not permanent. It relaxes on a half-life
(`PROGRESS_HALFLIFE_S`, 6 h), so a commitment you stop tending slides
back under time pressure — momentum bleeds, like a real object. Progress
arrives two ways:

- **explicitly** — `nudge()`, `keep()`, `break_()` (surfaced on the
  orchestrator as `nudge_commitment` / `keep_commitment` /
  `break_commitment`), driven by a phone tap or a resolved rehearsal
- **ambiently** — every `tick()` scans the memory stream, and any event
  that plainly refers to a commitment (shared keywords, or the same
  person) nudges it. Simply living near a promise keeps it alive.

Two verbs are terminal and override the forces: `keep()` blooms and pins
(it never shatters, even past due), `break_()` shatters and pins.

**Privacy.** Private events (`meta.private`) are never observed — a
private moment cannot tend or expose a commitment. This is the same
silence contract the rest of the system honors.

## Rendering (`halo-lua/display/horizon.lua`)

`draw_promise` animates each state on its own phase, seeded from the
mark's angle, driven by `now_ms`:

- **blooming** breathes (the dot radius grows and settles)
- **cracking** trembles (a small, fast radial jitter) and grows a fissure
- **shattered** throws its two halves apart and sheds shards

`reduce_motion` freezes every state to a still, information-preserving
pose — the crack still reads as a crack, it just stops shaking.

## Try it

```
python scripts/run_demo_commitment_drift.py
```

One commitment is made, neglected until it cracks, tended until it blooms
back, and finally kept; a second is abandoned and shatters. The state
ladder prints at each beat.

## Tests

- `host-python/src/dreamlayer/tests/test_commitment_drift.py` —
  `TestBehaviorDimension`: healing, keep/break terminals, half-life
  relaxation, re-alert after heal-then-slip, ambient stream progress, and
  the private-events-are-never-observed contract.
- `host-python/src/dreamlayer/tests/test_horizon.py` — the physics:
  blooming breathes, cracking trembles, shattered fractures and drifts,
  each frozen under `reduce_motion`.
