# Cinema v2 — Deltas

Every v1 element v2 removes or replaces, with a defense. Format per the
v2 mandate: what died, what replaces it, why the replacement is not just
different but better, and what the founder loses if the replacement
fails in the field. These are arguments, not a changelog. If a defense
would not survive a hostile reviewer, the v1 element was kept — see the
survivor list at the end of `CINEMA_V2_THESIS.md`.

---

## §1 — Iris Bloom (S1)

**Died:** the standalone ENTER signature — an accent ring collapsing
from r=112 to r=36 around content that materializes at dead center
(`halo-lua/display/transitions.lua:104-120`).

**Replaced by:** Focus condensation's landing ring. The reveal mechanism
is preserved — a collapsing ring that gates content by radius is the
correct primitive for a 4bpp display with no alpha — but it now
collapses along a path *from the focused thing's horizon angle*, and
when it lands it stays, carrying confidence as its sweep.

**Why better, not just different:** v1's ring was pure theater: it
carried zero bits (same ring for every card, every confidence, every
origin) and was thrown away on landing. The same ring now carries three
readings — where the thing lives in time (approach angle), how sure the
system is (landed sweep), and whether focus is held (its presence). Same
primitive count, three data channels instead of none.

**If it fails in the field:** the founder loses the clean, symmetric
bloom — an off-angle condensation could read as lopsided on real glass
if the travel is too fast to track. Mitigation path: the travel phase
degrades to the pure radial collapse (v1 behavior) when the origin angle
is unknown, so the failure mode *is* v1.

## §2 — Prism Slide (S3)

**Died:** the card→card crossfade drawing the outgoing card twice at
±2px with chromatically split palette slots
(`halo-lua/display/transitions.lua:164-183`).

**Replaced by:** recession and condensation overlapping — the outgoing
card contracts toward its horizon home while the incoming one condenses
from its own angle. No dedicated mechanism, no reserved fringe slots.

**Why better, not just different:** Prism Slide was v1's most
technically clever and least informative moment: the fringes said
nothing about either card. The overlap says where the old thought went
(it is *there*, on the rim, retrievable) and where the new one came
from. It also retires the worst hazard in v1's own risk register — the
prism fringes alias dream drift slots 3/4, and a `dream_exit` mid-
crossfade repaints a fringe mid-signature
(`docs/HALO_CINEMA_V1_RISKS.md:13-33`). v2 deletes the alias instead of
patching around it.

**If it fails in the field:** the founder loses the one purely beautiful
flourish v1 had; two simultaneous radial motions could read as busy
during rapid card sequences. Mitigation: recession is dimmer than
condensation by contract (ghost tier vs solid) so the eye has exactly
one primary motion; and under `reduce_motion` both collapse to a hard
cut, which is v1's own reduce path.

## §3 — Confidence Halo orbit (S4)

**Died:** the orbital arc circling recall cards once per 3.2s
(`halo-lua/display/transitions.lua:190-199`).

**Replaced by:** the landed focus ring: static arc at the content edge,
sweep = confidence × 360°, drawn once. The information encoding is
*strengthened* — sweep alone was already the redundant channel; radius
now belongs to the focus law (in/out), so the two encodings no longer
share one object.

**Why better, not just different:** v1's own risk doc names the doubt:
"a moving 1px arc behind text may read as flicker near the fovea," and
at conf≈0.5 the moving half-halo "can look like a rendering bug"
(`docs/HALO_CINEMA_V1_RISKS.md:78-88`). A static arc cannot flicker,
and a static half-arc at a consistent position reads as a gauge, not a
glitch. It is also the first signature whose `reduce_motion` variant is
*identical* to its full variant — the honest endpoint of v1's own
accessibility law (information without motion).

**If it fails in the field:** the founder loses the "alive" quality of
the idle card — a fully static hold might read as frozen. Mitigation:
the now-notch on the horizon continues breathing at BREATHE_CYCLE_MS in
every mode, so the frame is never dead even when the focused card is
still.

## §4 — Memory Comet (S6)

**Died:** the bezier comet flying in from a recency-encoded edge angle
for ProactiveMemoryCards only
(`halo-lua/display/transitions.lua:243-295`).

**Replaced by:** nothing — it won. Condensation *is* the comet,
generalized from one card type to every focus event, with the angle
mapping upgraded from "30° per week, proactive cards only" to "the
mark's actual position on the horizon the wearer can already see."

**Why better, not just different:** v1 invented the right idea and then
confined it to one card type and threw the mapping away after 280ms.
The judgment calls this out as the orphaned fragment of a spatial model
(`docs/CINEMA_V1_JUDGMENT.md`, "the one thing v1 didn't attempt"). v2
promotes it to the motion law of the whole system, and the entry angle
stops being a code to memorize (was anyone going to learn 30°/week?)
and becomes a pointer to a visible object.

**If it fails in the field:** nothing is lost that v1 had — the
reduce_motion recency tick survives as the mark itself, which is
strictly more persistent than v1's 8px tick that vanished with the card.

## §5 — Truth Lens 9-ring gauge

**Died:** nine concentric rings at 4px pitch, one per pipeline stage,
identity positional and unlabeled
(`halo-lua/display/renderer.lua:709-764`).

**Replaced by:** the Testimony Thread — one arc accumulating clockwise
around the verdict as the pipeline reports in stage order: steady
stroke through truthful stages, serrated tear at deceptive stages, gap
where evidence is insufficient. Stage angular span is proportional to
stage confidence; the thread's overall completeness *is* the aggregate.

**Why better, not just different:** identical information content —
per-stage direction × confidence in pipeline order — moved from nine
parallel channels the eye cannot separate at 4px pitch to one serial
channel along one learnable path. The gauge failed the product spec's
own laws ("glanceable in under 2 seconds," "no dense dashboards
in-eye," `docs/PRODUCT_SPEC.md:14,34`) and needed two symptomatic
patches in v1's review (rings pushed outward, black capsule armor
behind the verdict, `docs/HALO_CINEMA_V1_REVIEW.md:27-35`). A thread
that holds, tears, or runs out is readable pre-consciously — the same
claim v1's review made for the gauge's colors, now true of its geometry
too.

**If it fails in the field:** the founder loses per-stage *addressability*
— with nine rings a trained eye could in principle check "ring 4 =
prosody" directly; on the thread, stage identity is ordinal (position
along the path). If wearers turn out to genuinely need random access to
named stages in-eye, the thread is the wrong compression. The wager,
argued in `docs/cinema_v2/testimony.md`: nobody reads ring 4 on glass;
everyone reads "the thread tore twice early" — and the full stage table
lives one glance away on the phone.

## §6 — ReadyCard idle glyph

**Died:** the hex-core-and-orbits glyph as the resting state
(`halo-lua/display/renderer.lua:204-232`).

**Replaced by:** the Horizon. The resting display is the day itself —
marks, now-notch, promise arc — rendered at Air/Ghost tier.

**Why better, not just different:** the glyph encoded exactly one bit
(system on) and spent four draw layers saying it. The horizon encodes
the wearer's actual state — event density, promise pressure, time since
last memory — in the same visual budget, and it is the load-bearing
surface the whole paradigm stands on: condensation and recession need a
persistent *somewhere* for things to come from and return to.

**If it fails in the field:** the founder loses instant "is it on?"
legibility — a sparse horizon (new device, quiet day) could read as a
dead display. Mitigation: the now-notch breathes unconditionally; a
breathing notch at 12 o'clock is the new "system on," cheaper and more
honest than the old glyph.

## §7 — Dismissal as annihilation

**Died:** the semantics of `DISMISS_MS` — existence ends when the timer
fires (`halo-lua/display/animations.lua:59-72`, consumed by
`halo-lua/app/card_queue.lua:107-115`).

**Replaced by:** the same timers now time the *release of focus*.
Expiry triggers recession, not clearing: the content contracts back to
its mark on the horizon. `card_queue.lua` keeps its priorities, dwell
table, and preemption logic untouched — what changes is what the
renderer does when the queue says a card's time is up.

**Why better, not just different:** this is the paradigm stated as a
scheduling rule. In v1, dismissing an answer destroys it — asking again
costs a full round trip and a fresh materialization. In v2 the answer
remains addressable as a mark; a glance-and-recall (tilt toward its
angle, or re-query) is a recondensation from something visibly still
there. Continuity of existence is also what makes the display *learnable*
— the wearer's spatial memory can only bind to things that persist.

**If it fails in the field:** the founder loses the guarantee that a
dismissed thing is *visually gone* — on a crowded day, every expired
card leaves a residue mark, and residue is one bad tuning away from
clutter. Mitigation: marks are capped (48), ghost-tier, 1–3px, and decay
in luma with age; and privacy-class cards (PrivacyPaused, Consent,
ForgetLast) are contractually exempt — they never leave marks.

## §8 — Dream Mode as a separate visual world

**Died:** the composition where dream mode is its own scene — center
line field, free particles, anchor text in fixed bottom rows
(`halo-lua/display/dream_renderer.lua:271-279`, `:202-227`).

**Replaced by:** the same reactors rendering through the shared
geography: palette weather colors the horizon's air slots, the line
field bends around the rim, anchors ghost-wake from their time-angle,
and the mode transition is a weather change over terrain that never
cuts away.

**Why better, not just different:** v1's dream mode already had the
right *inputs* (mic bands, IMU curl noise, place chroma — all real
signal) attached to the wrong *ontology*: a scene cut into a world
where, per the material contract, nothing on screen is allowed to mean
anything (`Air: never information-bearing`,
`halo-lua/display/materials.lua:6-8`). Rendering the weather over the
horizon keeps every reactor and makes the ambient layer situated: the
wearer still sees *their day* through the weather. It also closes the
mode-transition slot-contention hole structurally — one geography means
the drift slots never change owners mid-frame
(`docs/HALO_CINEMA_V1_RISKS.md:13-33`).

**If it fails in the field:** the founder loses dream mode's total
otherworldliness — the clean "I stepped somewhere else" of a full scene
cut. If the weather-over-terrain reads as "memory mode with extra
color" instead of a state change, the dream has lost its door.
Mitigation: on `dream_enter` the memory marks drop to their lowest luma
tier and the field gets the full particle budget — the terrain stays,
but the *light* changes completely; the golden pass (Phase 5) judges
whether the door survives.
