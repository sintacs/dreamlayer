# Cinema v2 — Attacks

Phase 6: adversarial pass on the shipped set. For each element: five
ways it fails on a real wearer in a real environment, five ways the
wearer misreads it, five ways a competitor copies it — with the moat
named or the absence of one admitted. Every failure/misread carries a
mitigation that ships in this PR or an explicit deferral with a reason.
"Shipped" cites where; "Deferred" says why it can wait.

---

## 1. The Horizon

### Failure modes (real wearer, real environment)

1. **Bright daylight washes out ghost-tier marks.** Outdoors on an
   additive microOLED, `border_subtle`-track and dim-tier ticks may drop
   below perceptual threshold, leaving only the notch — the instrument
   silently amputates its data. *Shipped:* luma tiers are palette
   tokens, so a future ambient-light gain pass is one token table away;
   the notch (2px, full accent) survives worst-case. *Deferred:*
   ambient-light-servo luma (needs the device's light sensor readings —
   no sensor API for it exists in the repo to cite, so building it now
   would violate the hardware envelope).
2. **A hyper-documented day floods the dial.** 48 marks at 30°/hour can
   put ~10 marks per busy hour; merge turns them into long undifferentiated
   ticks and the "rhythm" reading collapses into a smear. *Shipped:*
   merge cap (+8px max), composer cap with lowest-confidence-first drop,
   and the elder tick absorbing overflow (`horizon_composer.py`,
   `horizon.lua`).
3. **Clock disagreement between host and device.** If the device
   re-derived times, a skewed RTC would shear the whole dial. *Shipped
   structurally:* the device does zero clock math — angles arrive
   precomputed in deci-degrees; skew cannot exist on the plotting side
   (`horizon.lua` header contract).
4. **Stale link masquerading as a quiet day.** BLE drops for an hour;
   the rim keeps showing the morning as if fresh. *Shipped:* 30s
   staleness rule drops every mark one luma tier while the notch keeps
   breathing — "device alive, memory stale" is a distinct visual state
   (`horizon.lua` tier_drop; golden `idle_stale`).
5. **Privacy pause leaking yesterday's rhythm.** Paused capture with a
   populated rim would still *display* captured signal. *Shipped:* the
   composer emits an empty pause frame, the bridges pass ONLY the empty
   frame while paused (`bridge/base.py pause_allows_raw`), and the
   device draws no marks + a `status_paused` notch (golden
   `idle_paused`).

### Wearer misreads

1. **Reading the dial as a clock.** 12 o'clock = now, so 3 o'clock
   reads as "3:00" instead of "3 hours ago." *Shipped:* the seam and the
   moving frame (marks crawl clockwise as they age) break the clock
   gestalt within a session; the notch never moves, which no clock does.
   *Deferred:* an onboarding overlay on the phone (companion-app
   tutorial surface doesn't exist yet; one screen among zero screens is
   a product decision, not a patch).
2. **Mark density read as importance.** A chatty hour looks heavier
   than a critical single event. *Shipped:* luma tier carries
   confidence independently of density; a lone full-tier tick outshines
   a dim cluster.
3. **The elder tick read as an event.** *Accepted:* it IS an event
   ("more, earlier") — the misread is shallow and self-correcting on
   focus; its fixed position (+58°, always the same door) teaches
   itself.
4. **The seam read as dead pixels / a rendering bug.** *Shipped:* the
   track terminates cleanly at both cap angles (no fade), and the seam
   is symmetric about 6 o'clock — deliberate geometry reads as design,
   noise doesn't. Watch on-glass; if it still reads as damage, the caps
   get boundary ticks (one-line change, noted for the wear test).
5. **Paused state read as "nothing happened."** An empty rim could mean
   quiet day or paused capture. *Shipped:* the notch color flips to
   `status_paused` — the two states differ at the single most-looked-at
   pixel cluster; plus PrivacyPausedCard occupies center stage at pause
   onset (v1 behavior, kept).

### Competitor copy vectors + moat

1. *A watch-face vendor ships a "day ring" complication.* Trivial to
   copy visually; a watch face doesn't sit in your visual field all day
   and has no capture pipeline feeding it. The moat is the **substrate**
   (passive semantic capture → ring buffer → composer), not the ring.
2. *Meta/Snap overlay a timeline HUD.* They have the sensors; what they
   don't have is local-first ambient memory (their capture is
   cloud-first by architecture and policy). Moat: the privacy contract
   as a *product* property — DreamLayer's rim can exist because nothing
   leaves the host.
3. *An open-source Frame/Halo hobbyist clones the dial from this repo.*
   Nothing stops them — the repo is the spec. Admitted: the drawing has
   no moat; the composed day does (it requires the whole memory engine).
4. *A phone widget shows the same dial.* Fine — that's our
   `HorizonPreview` and it's a companion, not a competitor; glanceable
   in-eye peripheral vision is the physical moat a pocket screen cannot
   cross.
5. *A big player copies time-as-angle + attention-as-radius as an
   interaction grammar.* Grammars can't be owned. The defensible asset
   is the **corpus binding**: every arrival/recession physically
   teaches *your* day's geography; a copied grammar with no persistent
   personal corpus is a screensaver. Execution moat, admitted as such.

---

## 2. Focus (condensation / recession)

### Failure modes

1. **20fps ceiling makes the 140ms travel a 3-frame event.** On a slow
   tick the head teleports rim→core and the origin reading is lost.
   *Shipped:* the landing ring + the lit origin mark carry the same
   reading statically (mark brightens at launch, stays lit through
   hold); the travel is redundant encoding by design.
2. **Recession into a BLE-dead rim.** If the horizon frame is stale,
   content recedes to a mark that isn't there (empty rim). *Shipped:*
   `pulse_mark` draws its own mark for `MER_ARRIVAL_PULSE_MS`
   regardless of frame state — the destination exists at least for the
   landing; staleness rules take over after.
3. **Queue churn: three URGENT cards in 500ms.** Two simultaneous
   recessions would double motion. *Shipped:* a third card hard-cuts
   the receding one — never two recessions (`renderer.show_card`
   comment + logic); bounded motion complexity per frame is a stated
   invariant.
4. **Origin angle for an answer the composer never saw** (memory
   older than the buffer, DB-only). `angle_for_ts` clamps to the elder
   door — arrivals from "earlier" all use the same door, which is
   honest. *Shipped* (`horizon_composer.angle_for_ts`).
5. **reduce_motion set mid-flight.** Setting flips while a card is
   condensing → next frame the reduce path renders (content complete);
   the in-flight head vanishes. *Shipped:* acceptable single-frame
   discontinuity; both endpoints carry full information by the parity
   contract. Verified by the reduce tests (`test_transitions.py`).

### Wearer misreads

1. **Ring sweep read as a timer** (arc = time remaining). *Shipped:*
   the ring never animates during hold — timers move, gauges don't; one
   dwell disambiguates. Residual risk noted for the wear test.
2. **Focus ring confused with the rim track.** *Shipped:* 8px radial
   separation + different colors (accent vs `border_subtle`) + the ring
   only exists when content does.
3. **Recede-to-mark read as "the answer was filed/saved"** (it was
   already saved; recession is just release). *Accepted:* this misread
   is *correct enough* — the mental model "it went back to my day"
   is the intended one; precision about DB semantics is not a HUD job.
4. **Low-confidence sliver read as broken ring.** v1's risk register
   raised this for the orbiting halo. *Shipped:* the static sliver
   starts at 12 o'clock every time — a consistent anchor point reads as
   a gauge zero, not damage; plus the amber low-tier color says
   "caution" redundantly.
5. **Origin angle read as importance** ("it came from the right, so
   right = answers"). *Shipped:* origins vary with actual event times;
   the mapping self-corrects with use — and the reduce_motion origin
   tick gives the same reading to motion-averse users.

### Copy vectors + moat

1. *"Cards fly in from the edge" — every AR demo reel since 2016.*
   Copying the motion without the persistent rim copies nothing: the
   angle means nothing without marks to come from. The moat is the
   *binding*, not the tween.
2. *Apple ships a radial reveal on watchOS.* Radial reveals aren't
   ownable (v1's iris wasn't either). The unified reveal-ring-becomes-
   confidence-gauge is a design idea a competitor can lift in a week.
   No moat; competes on execution. Admitted.
3. *A launcher copies "dismiss = shrink toward its source."* Common on
   phones already (window minimize). In-eye with a semantic time-source
   is the differentiator; without the horizon it's window management.
4. *Someone patents continuous-existence HUD elements.* Prior art risk
   runs both ways; this repo's docs + goldens are dated public prior
   art the day they merge. That is itself a defensive moat.
5. *A copycat clones the whole grammar with cloud memory.* Their
   version has to upload your day to draw it. Ours doesn't. Moat:
   the local-first path is load-bearing, not marketing.

---

## 3. The Promise Arc

### Failure modes

1. **Vague dues ("by Friday" unparsed) pile at the future cap.** Three
   collapsed dots at +122° tell the wearer nothing. *Shipped:* the
   48h-lifetime decay still advances their *state* (the ladder is
   visible even at the cap via color/shape); *Deferred:* better due
   parsing (it belongs to the extraction pipeline, not the HUD; the
   drift engine already owns the fallback).
2. **A promise due in 4 minutes.** At 30°/hour it sits 2° from the
   notch — indistinguishable from "now" and easy to miss entirely.
   *Shipped:* by then the drift ladder has it cracking (slipped inward
   + amber), and the one-shot alert card still fires (v1 path kept) —
   the arc is the ambient layer, not the only layer.
3. **Chronic overdue clutter** — six shattered ticks aging around the
   past side is guilt wallpaper. *Shipped:* shattered goes cold
   (`status_paused`), reads as history; marks age off the 5h window
   into the elder door like everything else. The rim forgets at the
   same rate the dial does.
4. **Same-hour promise stacks beyond three.** Radial stacking below
   r=91 would collide with the focus ring layer. *Shipped:* stack
   capped at 3 visible (`horizon.lua` stack clamp); the count beyond
   is the phone's job.
5. **Drift state flapping** (a record oscillating at a ladder
   boundary as decay recomputes). *Shipped:* states derive from
   monotonically increasing decay (`commitment_drift.py` — elapsed/span
   never decreases), so the ladder can only move one way; no flap is
   possible without a due-date edit, which is a legitimate state
   change.

### Wearer misreads

1. **Amber dot read as an alert rather than ambient pressure.**
   *Shipped:* blooming/healthy use `confidence_low` (soft amber),
   reserving `warning_amber` for drifting/cracking — two-step color
   escalation under-plays the calm states deliberately.
2. **The slip (r 105→95) read as a rendering glitch.** *Shipped:* the
   slipped dot keeps its stem-less amber identity and its angle; only
   radius changes — the golden `ladder` confirms the displacement reads
   as *position*, not error, against the track reference line.
3. **Shattered's cold color read as "resolved."** Risk is real: gray
   can read as done. *Shipped:* resolved promises LEAVE the rim
   (record removed → mark gone); anything still visible is by
   definition unresolved, and the fracture glyph is not a checkmark.
   Residual noted for the wear test.
4. **Future side read as the past** (mirror confusion). *Shipped:* the
   promise side is all dots/amber, the past side all ticks/teal — kind
   grammar disambiguates the sides redundantly with direction.
5. **"My promise to call Mom is visible to everyone I demo to."**
   Not a misread — a real social exposure. *Shipped:* marks carry no
   text; a bystander sees an amber dot, only the wearer knows what it
   is. The rim is legible to its owner and gibberish to a camera —
   this is the privacy contract at the pixel level.

### Copy vectors + moat

1. *To-do apps ship "deadline rings" tomorrow.* They already exist; on
   a phone they're pull-media. The moat is ambient wear: pressure you
   see *without asking* changes behavior (founder-reaction #3).
2. *A competitor copies the five-state strain grammar.* The grammar is
   copyable; the drift engine's decay model bound to real captured
   promises (regex/NER/LLM extraction pipeline) is the work.
3. *Calendar apps map due-times radially.* Calendars know appointments,
   not promises — the corpus differs. Promises are extracted from
   speech, unowned by any calendar. Data moat.
4. *A watch vendor ships "commitment complications."* Same as #1 —
   glanceability parity requires eyewear; wrist ≠ peripheral field.
5. *Someone copies "broken promises go cold and age into your past."*
   It's a *stance* (refuse to nag, refuse to lie) more than a feature.
   Stances are free to copy and hard to keep. Execution moat, admitted.

---

## 4. The Testimony Thread

### Failure modes

1. **Two adjacent torn stages read as one long tear.** Slot ticks are
   the only separator at ghost tier. *Shipped:* tears alternate radial
   offset (−3/+3/−3) per stage independently, so adjacent tears break
   phase at the boundary; the goldens (`elevated_mixed`) show two tears
   resolving as two.
2. **All-truthful low-confidence** (every stage truthful at 0.15):
   thread renders as nine slivers — sparse green dust that could read
   as torn-ish texture. *Shipped:* sliver strokes below span≤1° are
   dropped; what remains is *gaps*, and gaps mean insufficient — which
   at conf 0.15 is the truthful summary of the situation.
3. **Verdict word longer than the capsule budget** (localized verdicts,
   e.g. German). *Shipped:* capsule width derives from glyph metrics
   (`T.avg_w_with_tracking`), not a constant; at r=64 the clearance
   holds to ~14 characters. *Deferred:* localization (no i18n exists
   anywhere in the repo; inventing it for one word is scope theater).
4. **Ripple origin off-display** (eye landmark projected outside the
   circle during head motion). *Shipped:* v1's fallback kept — origin
   defaults to (128, 96) when absent; ripple math clamps by geometry.
5. **Pipeline timeout mid-card** (stages 7–9 never report). *Shipped:*
   reported stages draw, missing ones stay empty slots; absence is
   rendered, never faked (`draw_testimony` gates on `stages[i]`).

### Wearer misreads

1. **Torn = "they lied."** The gravest misread — the system reports
   *signal deviation*, not lies. *Shipped:* verdict vocabulary stays
   the fused word (ELEVATED, not LIAR) and per-stage tears carry no
   labels in-eye; *Deferred:* the phone detail view naming stages with
   plain-language caveats (needs the phone truth-lens screen, which
   doesn't exist yet — flagged as the first thing that screen must do).
2. **Thread completeness read as "how true"** rather than "how much
   evidence." *Shipped:* the confidence dot (amount of trust) sits
   separately from the thread (evidence account); two channels, two
   questions. Residual conflation risk accepted — it exists in v1's
   gauge and every confidence UI ever shipped.
3. **Slot ticks read as measurement gradations** (a 9-point scale).
   *Accepted:* they ARE ordinal gradations of the pipeline; the misread
   is approximately the truth.
4. **A single early tear read as damning** (face stage deviates on a
   stranger with glasses/beard changes). *Shipped:* the stranger case
   pins fusion confidence at 0.2 (`truth_lens/fusion.py`, v1 rule kept)
   → mostly-empty thread + UNKNOWN; one tear in a sparse thread reads
   as weak evidence because it is.
5. **Reading it on a friend and treating it as truth machine.**
   Product-level misuse, not a pixel problem. *Shipped:* everything the
   privacy model already enforces (contacts-only baselines, no stranger
   identification); *Deferred:* usage framing belongs in onboarding
   copy, which belongs to the phone app milestone.

### Copy vectors + moat

1. *Any dashboard vendor draws serrated arcs.* The tear glyph is
   copyable in an afternoon. The nine-stage pipeline behind it
   (face/AU/voice/prosody/linguistic/narrative/fusion) is the asset.
2. *An AI-glasses competitor ships "lie detection ring."* If they ship
   the dashboard version, they ship v1's mistake — nine channels no eye
   can read. The insight (serialize the pipeline along one path) is
   free to steal once seen. Admitted: no moat on the encoding.
3. *Academic HCI paper generalizes "evidence threads."* Good — cite the
   repo. Defensive prior art again.
4. *A competitor with cloud compute runs deeper models.* Their thread
   is better-fed but needs upload of your conversations; the
   contacts-only local baseline is the structural differentiator.
5. *Someone copies "absence is rendered."* The principle costs nothing
   to copy and everything to obey (their product roadmap must refuse to
   hide unknowns). Stance moat, same as the promise arc's.

---

## 5. Weather Through the Horizon

### Failure modes

1. **Palette starvation freezes the sky mid-storm** (BLE congestion —
   v1 risk #2's descendant). *Shipped:* device interpolates toward the
   last target and freezes rather than resetting (stale weather is
   visibly stale, never a jarring snap); the horizon frame is ~600B at
   0.2Hz and cannot meaningfully compete with palette frames.
2. **Field vectors crossing marks at equal luma** (quiet mood, dim
   marks). *Shipped:* dream mode forces memory marks to floor tier and
   the field draws in the `sky` slot which quiet weather keeps darker
   than the static track token; promise amber stays above both.
   Verified on the `dream_quiet` golden.
3. **Particle clip creating a visible wall at r=96** (particles
   bouncing off an invisible circle reads as a cage). *Shipped:* bounce
   damping (velocity halved + reflected) makes the boundary read as
   viscosity, not a wall; particles spend most time drifting, not
   colliding.
4. **dream_enter during an active recession** — the light change and a
   flight at once. *Shipped:* recessions complete as hard cuts when the
   mode flips (`renderer.show_card`/tick recede path); slots 3/4 single
   ownership means no palette fight is possible (the v1 hole, closed).
5. **Anchor echo for an event with no time-angle** (legacy anchors
   without `origin_deg`). *Shipped:* text-only degradation, no
   highlight — degraded, never wrong (`render_world_anchor` guard).

### Wearer misreads

1. **Storm chroma read as an alert.** *Shipped:* weather lives
   entirely in Air-tier ambience (no solid-tier element changes);
   alerts always arrive as cards via the focus law — the channel
   separation is the disambiguation.
2. **The dimmed day read as data loss on dream entry.** *Shipped:* the
   300ms `MER_DREAM_ENTER_MS` ramp shows the marks dimming in place
   (continuity, not removal); promises pointedly do not dim.
3. **Field motion read as system activity** ("it's processing").
   *Accepted:* the field IS live signal (your motion, the room's
   sound); "the system is alive to the room" is the intended read.
4. **Mistaking dream mode for privacy pause** (both are "different").
   *Shipped:* pause kills marks + flips the notch color; dream keeps
   the day visible under new light. The states share no visual
   signature.
5. **Hearing-impaired wearers get a sky that never storms.**
   Not a misread — an equity gap: mic-driven weather carries less for
   them. *Shipped:* IMU field and place chroma still drive the dream;
   *Deferred:* transcript-driven weather (speech events as gusts) —
   needs design work against the privacy model (transcripts are
   sensitive; ambient display of them must be thought through, not
   bolted on).

### Copy vectors + moat

1. *Every ambient-computing demo has a mood field.* Copyable; carrying
   *situated* information (your day dimmed under it) is the difference
   between weather and a lava lamp.
2. *Spotify/Apple ship audio-reactive visualizers.* Reactive ≠
   situated; no terrain, no memory. Different product.
3. *A competitor copies two-band FFT → chroma mapping.* The mapping is
   one page of code (mic_reactor). The privacy-preserving mic path
   (bands, never audio) is the differentiator worth defending loudly.
4. *Game HUDs have done weather-as-state for decades.* True, and it's
   the correct lineage to admit — the novelty is what the weather is
   *about* (the wearer's real room), not the technique.
5. *Cloning the whole dream mode.* Requires the reactor pipeline, the
   palette slot discipline, and the terrain. By then they've rebuilt
   DreamLayer. The moat is the system, not the mode.

---

## 6. The Horizon Frame (wire + phone mirror)

### Failure modes

1. **Frame loss on flaky BLE.** *Shipped:* full-state frames — any
   single frame fully heals; seq guard drops out-of-order deliveries
   (`horizon.lua on_frame`).
2. **Malformed frame from a buggy host build.** *Shipped:* arity and
   range validation; the device keeps the previous day rather than
   blanking (`on_frame` returns false, state untouched; tested in
   Phase 7).
3. **A future kind/state code the device doesn't know.** *Shipped:*
   kind range check rejects the frame whole — refusing to draw unknown
   semantics is safer than guessing; the seq guard means the next valid
   frame heals. Forward-compat versioning *Deferred* until a second
   schema version actually exists (YAGNI, stated).
4. **Composer emitting during privacy pause due to a future refactor
   moving the gate.** *Shipped:* defense in depth — the composer checks
   paused, AND both bridges gate marks-bearing horizon frames
   independently (`pause_allows_raw`). Two mistakes are required, in
   two files, with tests on each.
5. **Phone preview drifting from device rendering** (the v1 disease).
   *Shipped:* `HorizonPreview` consumes the same geometry constants via
   `theme/motion.ts meridian` with the parity doctrine comment; Phase 7
   adds the constant-parity test between `animations.lua` and
   `motion.ts` so drift breaks CI, not trust.

### Wearer misreads

Not a wearer-facing surface (transport + companion mirror). The five
that matter are developer misreads, and the mitigations are the frame
doc (`docs/cinema_v2/horizon_frame.md`), the codec tests, the parity
test, the lockstep comments in both message-type files, and the
composer docstring carrying the dial geometry so nobody re-derives it
differently.

### Copy vectors + moat

Plumbing has no moat and needs none; its job is to make the other five
elements real. The one defensible property: the frame format proves the
whole feature runs in ≤600 bytes per 5 seconds of BLE — anyone copying
the feature with a cloud round-trip is copying it worse.

---

## Standing mitigations (cross-element)

- Every deferral above names its blocking dependency; none is a
  disguised "never."
- The wear test (first week on real glass) has a named checklist from
  this document: seam-as-damage, sliver-as-broken, shattered-as-done,
  ring-as-timer, daylight luma. Each has a cheap pre-planned response
  (boundary ticks, zero-anchor, glyph swap, dwell rule, token table).
- The three stance moats (never nag, never hide unknowns, never leave
  the host) are written into tests where testable and into these docs
  where not.
