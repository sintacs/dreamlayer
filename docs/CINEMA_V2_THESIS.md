# Cinema v2 — Thesis

## The claim

**Cinema v2 is Meridian: the HUD stops being a stage where cards perform
and becomes a place where the wearer's day physically exists.**

Time is angle. Attention is radius. Certainty is light. Everything the
glasses remember holds a persistent position on a rim horizon — now at
twelve o'clock, the past trailing clockwise, promises waiting on the
counterclockwise side — and "a card" is no longer a thing that appears:
it is the moment something that already lived on the horizon is drawn
inward into focus, and when the wearer is done with it, it does not die.
It goes home.

## The paradigm shift, in one paragraph

In v1, the display is empty until the glasses decide to tell you
something; a notification materializes in the center, performs a small
piece of theater, and is deleted. In v2 the display is never empty and
nothing materializes: your day is drawn as a thin ring of small lights
around the edge of your vision — each light is a memory, a promise, or a
person, sitting at the hour it belongs to — and when you ask a question
or something needs you, the answer doesn't pop up, it slides in from
where it lives on that ring, and slides back out to its place when
you're done. After a day of wearing it you know where your morning is.
That's the whole shift: the HUD stops sending you messages and starts
being a place you glance at, the way you glance at a wristwatch or a
rearview mirror.

## Why this clears the founder's ceiling

v1's specifications were choreography: *which* animation a card performs.
Every one of the founder's six signatures — including the best ones —
accepts the premise that information is an event. Meridian rejects the
premise. Existence becomes a state, position becomes semantic, and the
entire signature vocabulary collapses into two physical laws
(condense/recede) applied to a persistent geography. The founder
specified better arrivals; v2 removes arrival as the ontology. The
judgment (`docs/CINEMA_V1_JUDGMENT.md`) shows the repo already built the
orphaned fragments of this — the comet's time-angle that lasts 280ms, the
drift engine's decay ladder that no renderer draws, the ring buffer's
ordered day rendered only as disconnected 3.5-second cards. Meridian is
what those fragments are fragments *of*.

## What v2 introduces

Six elements. Each has a design doc under `docs/cinema_v2/` and each
carries information or dies in Phase 2.

1. **The Horizon** — `halo-lua/display/horizon.lua` +
   `docs/cinema_v2/horizon.md`. The persistent rim instrument: a sparse
   arc of marks at r≈100–108, one mark per ring-buffer event, placed at
   its time-angle on a 12-hour dial (now = 12 o'clock, past sweeps
   clockwise, capped ±5h with a deliberate seam at the bottom antipode).
   Mark kind = color token (memory teal / promise amber / person accent),
   mark certainty = luma tier, mark density = your day's rhythm, legible
   peripherally. The now-notch breathes at the breathe cycle. This is
   what the display *is* when nothing is happening — the ReadyCard glyph
   and the black screen both die for it.

2. **Focus** — `halo-lua/display/focus.lua` +
   `docs/cinema_v2/focus.md`. The single motion law that replaces four
   signatures. Condensation: content is revealed by a ring that
   collapses inward *from the focused thing's horizon angle*, so an
   answer from yesterday afternoon physically arrives from yesterday
   afternoon. Recession: dismissal reverses the path — the content
   contracts back to a mark at its time-angle. The focus ring does not
   vanish when it lands: it stays at the content edge with sweep =
   confidence, becoming the card's certainty gauge (this is Iris Bloom
   and Confidence Halo unified into one object, minus the orbital motion
   v1's own risk doc doubted on glass). Crossfade is recession and
   condensation overlapping — no chromatic fringes needed.

3. **The Promise Arc** — part of `horizon.lua`, host side
   `host-python/src/dreamlayer/dream_mode/horizon_composer.py` +
   `docs/cinema_v2/promise_arc.md`. Open commitments finally rendered
   between their alerts: each promise is a mark on the counterclockwise
   (future) side at its due-angle, and its drift state — the five-step
   ladder the drift engine already computes for every open promise
   (`orchestrator/commitment_drift.py`) — is drawn as physical strain:
   blooming = a quiet dot, drifting = the dot dims and elongates,
   cracking = it warms to amber and slips inward off the rim (pressure
   *is* radius), shattered = a cold fixed tick that will not move again
   until addressed. The wearer watches a promise start to slip a day
   before v1 would have shouted at them.

4. **The Testimony Thread** — replaces the Truth Lens 9-ring gauge in
   `halo-lua/display/renderer.lua` + `docs/cinema_v2/testimony.md`. The
   nine analysis stages are a pipeline, so their evidence is drawn as
   one line traveling one path: a single arc that accumulates clockwise
   around the verdict as stages report — steady stroke through truthful
   stages, a serrated tear at a deceptive stage, an honest gap where
   evidence is insufficient. Nine unlabeled nested rings become one
   thread that either holds, tears, or runs out — same per-stage
   information (order × direction × confidence), delivered serially
   along one learnable path instead of in parallel across nine channels
   the eye cannot separate at 4px pitch.

5. **Weather Through the Horizon** — `halo-lua/display/dream_renderer.lua`
   reworked + `docs/cinema_v2/weather.md`. Dream Mode stops being a
   separate visual world. Its reactors survive unchanged (mic palette
   weather, IMU line field, place chroma), but they render *through* the
   same geography: the weather colors the horizon's air slots, the line
   field bends around the rim instead of crossing the center, and world
   anchors ghost-wake from their time-angle on the horizon rather than
   from arbitrary rows. Entering dream mode is a change of weather over
   the same terrain, not a scene cut — one continuous relationship
   between the HUD and the wearer's state.

6. **The Horizon Frame** — `halo-lua/ble/message_types.lua` +
   `host_comm` handler + `phone-app/src/ui/components/HorizonPreview.tsx`
   + `docs/cinema_v2/horizon_frame.md`. The semantic BLE message
   (`{t:"horizon"}`) that streams composed horizon state — ≤48 marks × 4
   bytes fits one MTU frame like `line_field` — at ambient cadence, plus
   the phone-app mirror so the companion shows the same day-ring the
   glasses do. Local-first: the composer reads only the on-host ring
   buffer, drift records, and place signatures; no cloud in the path.

## What v2 removes (each defended in CINEMA_V2_DELTAS.md)

| v1 thing | Fate | Delta entry |
|---|---|---|
| S1 Iris Bloom (`transitions.lua:104-120`) | Absorbed: becomes Focus condensation's landing ring | DELTAS §1 |
| S3 Prism Slide (`transitions.lua:164-183`) | Killed: crossfade = recede + condense overlap | DELTAS §2 |
| S4 Confidence Halo orbit (`transitions.lua:190-199`) | Killed as motion, kept as information: static focus-ring sweep = confidence | DELTAS §3 |
| S6 Memory Comet (`transitions.lua:243-295`) | Generalized: every condensation travels from its time-angle; the comet was the special case | DELTAS §4 |
| Truth Lens 9-ring gauge (`renderer.lua:709-764`) | Replaced by the Testimony Thread | DELTAS §5 |
| ReadyCard idle glyph (`renderer.lua:204-232`) | Replaced by the Horizon as the resting state | DELTAS §6 |
| Dismiss-as-annihilation (`animations.lua:59-72` semantics) | Dismissal becomes recession; DISMISS_MS times the *release of focus*, not existence | DELTAS §7 |
| Dream Mode as a separate visual world (`dream_renderer.lua` center-field composition) | Collapsed into weather over the shared geography | DELTAS §8 |

**Survivors, deliberately:** S2 Ghost Wake (condensation *is* its
generalization to geometry; the per-character text treatment stays for
anchor text), the chime/chord/rumble acoustics analogs (small, honest,
information-bearing), the Air/Ghost/Solid material system and dynamic
slot bank (v2 is built on it), the exit-contract text-cut rule (glyphs
still never shrink through floor()), the card draw functions themselves
(what a card *shows* was never the problem; how and where it exists
was), and the entire Reality Compiler stage — a running figment still
owns the display outright.

## The count, defended

Six is not a list of features; it is one instrument (Horizon), one
motion law (Focus), two inhabitants (Promise Arc, and the memory marks
that need no element of their own), one repair of v1's worst card
(Testimony Thread), and the plumbing that makes it real on hardware and
phone (Weather, Horizon Frame). Nothing here can be cut without the
paradigm losing a load-bearing wall: a horizon with no focus law is a
decoration; a focus law with no horizon is v1 with new easing; promises
without drift rendering was exactly v1's sin of unused state; shipping
the gauge unchanged would mean v2 tolerated a dashboard it knows is
illegible; and without the BLE frame and phone mirror the whole thing is
an emulator screenshot, not a product. One element that is unforgettable
would have been the Horizon alone — but the Horizon alone, with cards
still materializing at dead center, is a screensaver. The six together
are the smallest set where the claim survives contact with the hardware.

## The founder-reaction test

Three imagined reactions from a hard-to-impress person wearing the
emulator build:

1. *"Hold on. That cluster of lights at ten o'clock — that's my standup.
   It knows where my morning went. **How did you do that?**"* — the
   Horizon making event density legible peripherally, no words on
   screen.

2. *"The answer to 'where are my keys' came in from the left side and I
   knew it was from yesterday before I read a single word. **How did you
   do that?**"* — Focus condensation traveling from the memory's
   time-angle; the geometry is the metadata.

3. *"I watched the promise to Jordan start to slip down off the ring
   over dinner, and I just… sent the invoice early. It never had to
   alert me."* — the Promise Arc turning drift from an interruption
   into ambient pressure.

## Revision log

- 2026-07-02 — Initial thesis committed (Phase 1). Revisions, if Phase 3
  or Phase 4 falsify any claim, will be logged here with dated reasons —
  never silently drifted.
