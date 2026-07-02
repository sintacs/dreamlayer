# Cinema v2 — Prototype Review

Phase 3 record. Every Meridian element was prototyped in isolation under
`halo-lua/display/cinema_v2_prototypes/`, rendered through the raster
harness (`host-python/src/dreamlayer/bridge/lua_raster.py` — the device
Lua drawing real pixels; see the harness docstring for the fidelity
model), exported to `assets/cinema_v2/prototypes/<element>/`, and
**looked at**. Critiques below are from inspecting the exports, not the
code. Where an export failed the bar, the prototype was changed and
re-exported; iteration notes live as comments at the exact lines in
`proto_lib.lua` / the element prototypes.

## Harness note (honesty about the pixels)

The raster harness draws geometry pixel-accurately and models the
dynamic palette bank (YCbCr slot reassignment, base-hex → live-slot
resolution). Two known gaps, both conservative: PIL's 13px font is
heavier than the device glyphs (text reads *louder* here than on
glass — if text overwhelms here it certainly will there), and static
tokens that share a hex with a dynamic slot's base resolve to the slot.
The prototypes avoid the second by construction (dream marks use floor
tier, never the sky base). Flagged again in `CINEMA_V2_RISKS.md`.

## Horizon (`horizon/*.png`)

**Pass 1 — failed.** `typical_day` read as scattered dust: 1px marks
floating in a void, no circle legible, and the seam indistinguishable
from empty sky — the "instrument" was invisible ink. This was the
biggest miss between spec and pixels: the design doc's dial only exists
if something *draws the dial*.
**Pass 2 — the track.** Added the rim track: a 1px `border_subtle` arc
across the active window only (`proto_lib.lua`, `draw_track`). The seam
became a legible absence, the marks became readings *on* something, and
`empty_boot` went from "dead display" to "instrument at rest." Marks
lengthened (3/6/9px by tier), promise dots to 2–3px, the notch to a 2px
tick crossing the track (the only mark that crosses — it reads as the
cursor it is). Re-inspected: `typical_day` now shows the morning
cluster, lunch pair, person pin, two amber promises, and the seam in
one glance.
**Pass 3 — residual accepts.** The elder tick (+58°, `text_ghost`) is a
whisper — deliberate; it is the door to "earlier," not a datum.
`stale_link` is only obviously distinct side-by-side with `typical_day`
— accepted because staleness also has the 30s temporal signature on
device (marks visibly step down), and the notch/mark contrast is the
in-frame cue. Cluster merge (+2px) is subtle at one absorbed mark;
acceptable — merge exists to prevent overdraw, not to be a precise
count.

## Focus (`focus/*.png`)

**Pass 1 — travel failed, everything else held.** `hold_conf090` was
right on first render: content clean in the core, ring at r=92 with a
readable gap, dimmed day at the rim — three layers, no collisions. But
the condensation head (2px + 2 faint tail samples) was sub-visible
against the dial; at t=90ms the "arrival from the past" read as a stray
pixel.
**Pass 2 — head 3px, tail 3 samples** (brightest shade leading). Redone:
`condense_t045` now shows the departure clearly leaving the lit origin
mark; `condense_t180` shows the landing ring gating content mid-bloom
with the eyebrow and primary up — the two-phase grammar (travel, then
landing) is legible in stills, which means it will be legible at 20fps.
**Pass 3 — judgment calls.** `hold_conf020`'s amber sliver reads
instantly as "thin evidence" — the tri-color + sweep double coding
stays. `recede_t100` shows content already cut with the head flying
home — correct per the kill-list #2 text rule. `reduce_motion.png`
carries every reading (content, ring sweep, origin tick) in one static
frame — the parity contract holds. Accepted residual: at conf ≥ 0.9 the
ring's gap approaches the notch angle and could be misread as a track
segment for ~a second; the ring lives at r=92 vs track 100 — 8px of
separation is the mitigation, verified adequate in the stills.

## Promise Arc (`promise_arc/*.png`)

**Pass 1 — two failures.** `stacked` blobbed: three same-hour promises
at 5px radial pitch merged into one amber smear — worse than useless, it
miscounted the wearer's obligations. `shattered_past`'s cold tick
vanished against the track (2px `status_paused` next to `border_subtle`
pixels).
**Pass 2 — stack pitch 7px, stacked dots one step smaller.** Three
distinct, countable dots descending inward. Legible.
**Pass 3 — the broken tick.** Solid-but-longer still hid; the fix that
worked is semantic: shattered renders as a *fractured* tick — two 5px
segments with a 3px gap. It is the only broken shape on the display,
findable in one scan of `shattered_past.png`, and it means exactly what
it looks like. `ladder.png` now shows all five states countable in one
glance: dot → bigger dot → dot-with-stem → slipped dot → fracture.

## Testimony Thread (`testimony/*.png`)

**Pass 1 — failed structurally.** At r=48 the verdict capsule erased the
thread at 3 and 9 o'clock — the armor was destroying slots 3 and 7,
which is precisely the gauge disease this element exists to cure
(evidence losing to its own chrome).
**Pass 2 — r=64, tear jitter ±3px.** The thread clears the widest
verdict word with margin. `elevated_mixed` now reads: green thread,
torn twice early, one empty slot, ELEVATED — one fixation. The tears
read as *damage*, not decoration, which is the intended pre-conscious
reading. `stranger_insufficient` is nine empty slots around UNKNOWN — a
compass rose of ignorance; honest and slightly unsettling, as it should
be. `clean_truthful` is one quiet green ring — boring on purpose:
that's what "nothing is wrong" should cost.
**Pass 3 — enter sequence.** `enter_t0440..1120` show the stage-ordered
accumulation with the verdict up first — headline then evidence.
Accepted residual: at 13px PIL font the verdict is heavier than device
glyphs will be (harness note above); the capsule width derives from
character count and is re-verified in the Phase 5 goldens.

## Weather (`weather/*.png`)

**Pass 1 — the decagon problem.** Even 30° vector spacing with mild
wobble made the "field" read as a broken regular polygon — geometry,
not weather. Exactly the failure the design doc warned against.
**Pass 2 — variance widened** (spacing ±26°, radius 74±18, length
15±9). `dream_quiet` now reads as flow around the rim; `dream_storm`'s
ember field over the dimmed day is an unmistakable mood shift with the
promises still legible — the "promises don't sleep" rule visibly holds.
`memory_idle` vs `dream_quiet` side by side confirms the thesis claim:
same terrain, different light — the scene cut is gone.
**Pass 3 — accepted residuals.** Field vectors near the top cross the
track at equal intensity; on device the field draws in the `sky` slot,
which the weather keeps dimmer than the track's static token in quiet
moods — accepted here, re-judged on the integrated goldens. The
`anchor_echo` ghost rows read loud in the harness font; the provenance
brighten (the lit lunch mark) reads clearly, which is the new
information this composition had to prove.

## Verdict

All five visual elements clear the bar as prototypes; the sixth
(Horizon Frame) has no pixels of its own and is exercised in
integration tests. Iteration counts: horizon 2 passes to clear + 1
accept pass, focus 2+1, promise arc 3 (two real failures), testimony
2+1, weather 2+1. Nothing was promoted to the main render paths before
this document existed — and the promotion (Phase 4) re-uses the
prototype geometry constants verbatim, moved into
`display/animations.lua` under the `MER_*`/`SIG_FOCUS_*`/`TESTIMONY_*`
banks.
