# DreamLayer — The Frontier Brief

*What this platform becomes when nothing is held back.*

This is a creative and technical brief across seven fronts: performance,
never-seen UX, the living user model, Confluence, the plugin flywheel, the
moat, and a 90-day sprint. Every proposal is labeled **[NEW]** (does not
exist) or **[ENHANCE]** (builds on shipped code), with an effort estimate:
**S** (days), **M** (1–2 weeks), **L** (a month), **XL** (a quarter+). File
paths refer to the real modules in this repo.

---

## The spine: three non-obvious truths about this architecture

Everything below hangs on three observations that are easy to miss and
change what "pushing the limits" means here.

### 1. The wire is the privacy model

DreamLayer's BLE protocol (`ble/protocol.lua` ↔ `bridge/real_bridge.py`)
carries length-prefixed JSON in 128-byte chunks, 16 KB max frame, from a
**closed registry of typed messages** (`ble/message_types.lua`). Look at
what those types actually are: sixteen palette slots. A geometry intensity.
Twelve curl-noise vectors. A Horizon mark packed as `kind*100 + state*10 +
luma` in deci-degrees. A 12-point Timbre waveform quantized 1..15. A
Confluence WeatherPacket that is *one scalar and four colors*.

The privacy guarantee is not a policy sitting on top of a rich channel —
**the channel is too narrow to betray you**. A bond that can only carry
weather cannot leak a conversation, no matter what goes wrong above it.
The same pattern repeats at capture: Social Lens enrolls only through a
closed spoken-introduction grammar; Rehearsal parses speech against a
closed offline grammar where unknown words become inert label text;
Premonition's two-Tuesdays law admits only proven rhythms. **DreamLayer
does privacy as grammar and packet shape, not as filters over data.** The
data that would need protecting is never brought into existence.

Consequence for this brief: every performance win must come from *semantic
compression* — sending smaller state machines, predictions, and deltas —
never from widening the pipe. And every new social feature (Section 4)
inherits its privacy from its packet shape, designed first.

### 2. DreamLayer is a circadian computer — and the night is half-idle

The system already schedules cognition by day and night: the hot ring
holds 24 h, the REM cycle (`rem/cycle.py`) dreams the day recombined and
votes on what to keep, `retention.py` demotes warm memories at 90 days,
Ember's TendingPass rides the same nightly pass, Premonition mines rhythms
from consolidated days. NightWatch (`rem/nightly.py`) already gates all of
this on *charging + night + rested*.

That gate is the most underused resource in the stack. A charger-night is
~8 hours of unmetered phone (or Mac-mini-class) compute against a corpus
that is already structured, private, and small. Almost everything the
product needs to feel prescient — speculative answer caches, the user
model's priors, index compaction and hot/cold placement, Figment
re-proving after an interpreter update, model calibration against your own
vocabulary — is batch work that belongs *inside the dream*. The Living
User Model in Section 3 is therefore not an online learner bolted onto the
hub; it is a **nightly consolidation artifact**, which also hands it the
"graceful death" property for free: delete the artifact and the next night
rebuilds it from whatever memory survives.

### 3. Figments are proof-carrying behavior — the first zero-trust app store

Every other platform distributes *trust*: review teams, sandboxes,
attestation. DreamLayer distributes *proofs*. A Figment
(`reality_compiler/v2/figment.py`) is a total, statically-budgeted scene
machine — ≤32 scenes, ≤24 bytes per line, timed exits ≥0.5 s, pulse ≤4 Hz,
an emit token-bucket whose worst case is proven over every cycle of the
timeout graph (`v2/budgets.py`) — signed and executed by a fixed
interpreter (`halo-lua/app/figment_stage.lua`) that re-enforces every
budget at runtime. Add the TUF/Uptane registry trust chain
(`plugins/registry_trust.py`) and you get something no app store has ever
had: **a stranger's behavior can be installed safely because the safety is
math, not reputation.** That inverts store economics — the long tail is
safe by construction, so discovery can be radical: figments passed
person-to-person like files, gifted across a Confluence bond, sold by a
chef or a curator with no review queue between them and your glasses.

---

## Section 1 — Performance breakthroughs

The current honest numbers (from `orchestrator/budgets.py`,
`orchestrator/frame_budget.py`, `docs/FIRST_DEVICE_TEST_PLAN.md`): glance
name 350 ms, glance panel 1.5 s, Juno ask 2.5 s, answer-ahead 2.0 s or
silent drop, card-send→on-screen < 250 ms, display loop 20 fps (50 ms
tick), ambient camera one frame per 4 s with 1.5 s staleness. The targets
below: **interactive card < 100 ms felt, cold card < 130 ms, Juno
first-line < 600 ms, don-to-ready < 300 ms.**

### 1.1 BLE link

- **[NEW] Card template deltas — protocol v2 `card_d`.** The Lua side
  already owns card constructors per type (`display/cards.lua`); today the
  host re-sends full JSON payloads (`{t:"card", payload, event}`) every
  time. Ship a card-type + field-delta frame: single-byte field keys, only
  changed fields cross, full payload only on first render of a type.
  Median card frame drops from several hundred bytes (3–6 MTU chunks) to
  under 64 bytes (1 chunk). Lockstep risk is real — keep the v1 `card`
  frame as the always-correct fallback and let `card_d` be an
  optimization the reassembler can reject. **S–M**
- **[NEW] Shadow slot + commit.** Two-stage render: the host pre-positions
  the most-likely next card on the glasses (`{t:"card", stage:"shadow"}`),
  and a later 6-byte `{t:"commit"}` — or a *local* button/gesture the
  figment stage already sees — promotes it to visible. This deletes the
  round trip from the interactive path entirely: tap-advance in
  Wayfinding, glance-panel reveal, and Juno wake become **~10 ms local
  promotions** instead of ~250 ms round trips. This is the single highest
  leverage/effort ratio in the codebase. **M**
- **[ENHANCE] Connection-parameter burst mode.** Request a 7.5–15 ms
  connection interval during interaction windows (glance intent fresh,
  card in flight), relax to 50–100 ms when only ambient frames flow. The
  radio spends power only when latency is being *felt*. Pairs with frame
  coalescing: palette + geometry + line_field for one dream tick travel as
  one frame; card frames preempt ambient in the send queue. **S**
- **[NEW] Sprite delta + RLE.** TxSprite is 4bpp indexed; morning-reel and
  avatar frames are mostly flat runs. RLE on the wire plus dirty-rect
  deltas between reel frames cuts sprite traffic ~3–5× with a ~30-line Lua
  decoder. **S**
- Honest non-move: general-purpose compression (zstd/deflate) on an M55-
  class Lua VM buys less than field tokenization and costs a decoder that
  can wedge the link. The `MAX_FRAME` reset discipline ("a wedged link is
  worse than a lost frame") is right — keep frames small instead of clever.

### 1.2 Speculative inference — Answer-Ahead grows into **Reverie** [ENHANCE, M–L]

The seam already exists: `ANSWER_AHEAD_MS = 2000` computes ahead and drops
silently, and `adaptive_confidence.py` already tracks per-card dismissal
rates. Reverie makes anticipation systematic:

- **Priors.** Premonition's RecurrenceModel is the behavioral prior the
  brief asks for — and it comes with a precision law (slots proven on ≥2
  distinct days, retired on misses). Speculate **only on hardened slots**,
  plus three live signals: place-signature entry (`on_place` already
  flows), glance-intent freshness, and commitments entering their deadline
  window.
- **Mechanism.** A speculation queue scored `p(trigger) × latency_saved ÷
  energy`; top-K entries pre-run on tier 1 (and tier 2 when the Brain is
  reachable) during idle ticks; results park as **shadow cards** (§1.1)
  with a TTL borrowed from `frame_budget.stale_ms` semantics. A wrong
  speculation costs nothing visible — shadow slots are never rendered
  unbidden.
- **The law.** Reverie never runs while veiled or incognito, never
  speculates over `meta.private` events, and never crosses to cloud — a
  speculative cloud call would be an ask the user never made. Dismissal
  stats feed back as negative priors so speculation *learns restraint*.
- **Payoff.** Walk into the gym at the usual hour: the workout Wayfinding
  card is already on the glass in shadow. Look at the shelf you always
  scan: the TasteLens pick renders at tap speed. The product stops
  answering and starts *having already answered*.

### 1.3 Tier handoff with zero perceptible gap

- **[ENHANCE] Escalation-band warming.** When a tier-0 `Sighting` lands in
  the ambiguous band (confidence ~0.35–0.65), open the Mac-mini HTTP
  session and ship the frame *while* the tier-0 card renders. If the user
  says "tell me more," tier 2 is already mid-inference. The
  `run_with_deadline` pool (4 workers, abandoned calls dropped) already
  supports this shape. **S–M**
- **[ENHANCE] Hedged requests.** At each tier's observed p95, fire the
  next tier without cancelling the current one; first sufficient answer
  wins, a later better answer upgrades. The health ledger already records
  deadline misses — use it to learn per-tier p95 instead of hardcoding. **S**
- **[NEW] Result shadowing = the quiet upgrade.** When a higher tier
  returns after a card is visible, refine *in place*: the confidence dot
  brightens one step, detail lines re-flow, `Answer.tier` updates the
  footer. Meridian's standing rule that text never moves or distorts makes
  this a calm reveal instead of a jarring re-render — the card appears to
  *sharpen*, like eyes adjusting. **M**
- **[NEW] First-line streaming.** Cards are atomic today. Stream the
  primary line at first-token and let detail lines arrive as they
  generate (each line is one small frame; the anatomy in
  `HUD_DESIGN_SYSTEM.md` is already line-structured). Perceived Juno
  latency collapses from 2.5 s budget to ~600 ms to first meaningful
  light. **M**

### 1.4 Cold start elimination — the don ritual

- **[ENHANCE] Don-event warm boot.** The IMU can recognize the
  pick-up-and-don signature (a distinctive two-second accelerometer
  gesture — no new hardware). On don: reconnect using the persisted bond
  and cached GATT handles (skip service discovery, ~1–2 s saved), mmap the
  usearch ANN index and the Model2Vec embedder (both are files; the
  ~30 MB static embedder loads in tens of ms), start the capture pipeline,
  and render ReadyCard. Target: **ReadyCard < 300 ms after don, full brain
  < 2 s.** **M**
- **[ENHANCE] Skip redundant Lua upload.** `load_lua_app()` uploads and
  verifies files every attach; add a version/checksum manifest so an
  unchanged app skips straight to `reset`. Saves seconds on every
  reconnect. **S**
- **[NEW] Warmth ledger.** Track what was resident at last un-don and
  restore exactly that working set (place anchors, active figment, shadow
  slots) — taking the glasses off and on again should feel like a blink,
  not a boot. **S**

### 1.5 Quantization and on-device efficiency

The Alif Balletto B1's Ethos-U55 (~46 GOPS int8, Vela/TFLite-Micro) is
MobileNet-class — perception primitives, never language. The honest plan,
per tier and lens:

| Where | Model | Precision | Serves |
|---|---|---|---|
| Halo NPU | DS-CNN wake-word (~30 KB) + VAD | int8 | Juno wake, capture gating — mic never streams for a wake-word |
| Halo NPU | person-presence / text-density / form-grid perceptor | int8 | Glance Arbiter coarse read (`PerceptSignals`), Timbre side-detect assist |
| Halo NPU | MobileNetV4-S or MobileCLIP-S0 head | int8 | Tier-0 *naming* — drops glance-name median from 350 ms budget to ~60 ms |
| Phone | Moonshine-tiny or Whisper-tiny | int8 | ASR for captions, Rehearsal beats, Ember attempts |
| Phone | Model2Vec static embedder (shipped) | keep as-is | Memory/RAG embeddings — already the right call at ~30 MB |
| Phone | Qwen2.5-1.5B-Instruct or Gemma-3n | int4 (q4_K_M-class) | card phrasing, Lucid routing, Candor/Provenance summarization |
| Mac mini | Ollama `qwen2.5-vl:7b` q4_K_M (MLX later) | q4 | `explain` tier — rich object answers, Scholar |
| Mac mini | bge-m3 / nomic-embed | int8 | whole-life + files RAG index |

Rules that prevent quality regression: perception quantizes to int8
freely (empirically lossless for these heads); generation never below
q4_K_M; embedding spaces never mix — `PersistentAnnIndex`'s
signature check already enforces this, keep it sacred; Timbre's prosody
statistics stay exact (they're a dozen floats — quantizing identity
aesthetics to save nothing would be malpractice).

### 1.6 The sub-100 ms card

Where the felt latency goes after §1.1–§1.5, trigger → pixel:

```
trigger event (button/gesture/gaze)          ~10 ms
tier-0 inference (NPU perceptor)             ~60 ms   (cold path only)
card build (hud/cards.py)                     ~5 ms
BLE transfer (card_d, burst interval)        ~25 ms
Lua layout + draw (next 50 ms tick)          ~30 ms
─────────────────────────────────────────────────────
cold card                                   ~130 ms
interactive card (shadow-slot promote)       ~10 ms
```

Two disciplines make this honest. First, **commit ≠ animation**: the
180 ms fade is chosen motion, not pipeline latency — the card must be
*committed* under budget and the fade plays from commit. Second, measure
it: extend `object_lens/bench.py`'s 350ms-Club harness to a full
trigger→pixel trace with the emulator's screenshot export as ground
truth. **[ENHANCE, M]**

### 1.7 Memory index hot/cold tiering [ENHANCE, M]

`retention.py` already defines the temperature model; make it a
*placement* model:

- **RAM (phone):** the hot ring (24 h), the entity graph, `rem_bias.json`,
  the HNSW index over warm (90 d of structured rows is small — this fits),
  and the current place's working set.
- **Flash (phone):** the SQLite store, cold entities, WeatherLedger
  history, Ember store, vaulted Figments.
- **Mac mini:** the whole-life index plus the files/mail RAG. **There is
  no cloud index in any configuration** — cloud answers hard non-personal
  questions; it never holds memory.
- **Context paging, not caching:** `on_place` pages in that place's
  anchors, its WeatherLedger band, and any Ember due at that doorway;
  Reverie's hardened Premonition slots pre-page the *next* hour's
  neighborhoods. The index warms to where your life is about to be.
- **Nightly compaction (insight 2):** REM's consolidation pass is when the
  ANN index rebuilds, temperatures re-sort, and tombstones vacuum — the
  glasses wake up with a defragmented mind.

---

## Section 2 — UX moments nobody has ever seen

Thirteen named micro-experiences. Each states the lens it extends, the
mechanical trigger, the HUD output, the feeling, and why only this
architecture can do it.

### 2.1 Threshold Echo — 🧠 Memory [NEW, M]
Cognitive science calls it the doorway effect: crossing a threshold purges
working memory. DreamLayer catches exactly what the brain drops.
**Trigger:** place-signature transition while a Stasis frame or a
drifting/cracking commitment is anchored to the room being *left*.
**HUD:** a 400 ms rim glow at the anchor's bearing in the promise's state
color, with a ≤4-word cue — never the content. **Feeling:** the room
itself taps your shoulder on the way out. **Only here:** requires local
place signatures, the pre-interruption ring buffer, and Commitment Drift's
state physics already on the Horizon wire.

### 2.2 The Grace Whisper — 👤 People [ENHANCE, S]
**Trigger:** Timbre recognizes a kept contact's voice entering from
behind or beside (`{t:"timbre", known:1, side_dd}` already ships).
**HUD:** the contact's waveform glyph at the rim on the sound's side, plus
one dossier line from the conversation ledger: *"Maya — her daughter
started college."* **Feeling:** the social terror of the forgotten name —
and the forgotten last conversation — simply dies. You turn around already
warm. **Only here:** consented voice baselines of *your own people*, held
on your own hardware, with strangers rendered as anonymous static. No
cloud assistant can hold this data without becoming surveillance; no
competitor will ship it without this consent grammar.

### 2.3 Candor Flash — ⚖️ Truth [NEW, M]
**Trigger:** ASR partials of *your own speech* match a belief whose
Provenance standing is `contested` (≥2 shared content words against a
contradiction Candor already indexed). **HUD:** a single amber dot at the
rim — nothing more unless you glance up, which reveals the Provenance
card: *"Maya said Friday; Sam said Thursday — contested."* **Feeling:**
being caught by your own conscience, kindly, *before* the sentence
finishes. **Only here:** requires a longitudinal private belief store with
genealogy (`orchestrator/provenance.py`) and an ear that answers only to
you. A cloud fact-checker checks the world; this checks *you against
yourself*, offline.

### 2.4 Premonition Handshake — 🧠 Memory [ENHANCE, S]
The RecurrenceModel already hardens a ghost when a real event lands
within ±45 min — but silently. Make the moment visible. **Trigger:** you
physically arrive inside a predicted slot's window. **HUD:** the
shimmering kind-6 ghost *solidifies* — shimmer stops, luma steps up, the
real mark takes its place with a single soft pulse. **Feeling:** the
glasses made a quiet bet on you and you watched it come true; prediction
retiring into fact, live. **Only here:** the future ghosts exist because
your rhythms never left the device — a cloud calendar shows plans; this
shows *patterns you never wrote down*.

### 2.5 Dream Gallery — 🧠 Memory [NEW, S–M]
**Trigger:** first don of the morning, then a 2-second gaze-dwell on any
low-texture surface (the perceptor's text-density/form signals already
distinguish blank walls). **HUD:** the REM morning reel (`render_reel()`
already exports one 256 px frame per dream) plays as sprites, world-fixed
on the wall: sources at their true hours, traces converging on each dream
phrase. **Feeling:** *the glasses show you what they dreamed about you.*
Nobody has ever watched a machine's dream of their own day on their
kitchen wall. **Only here:** requires an actual functional dream cycle —
which no other platform has because no other platform sleeps.

### 2.6 Chorus — 🌍 World [NEW, M]
**Trigger:** Rosetta (the eye) has a translated menu in view while Puente
(the ear) is live-captioning a speaker, and both pipelines resolve the
same entity (dish name, product, place) in the local entity space.
**HUD:** the looked-at line and the spoken caption kindle in the same hue
for 1.5 s. **Feeling:** the waiter says a word you can't parse and the
menu line you're reading *lights up* — eye and ear agreeing in front of
you. Cross-modal binding as a visible event. **Only here:** requires eye
and ear translation pipelines sharing one on-device entity space —
architecturally present (`rosetta.py` + `puente_bridge.py` +
`object_lens/translate.py`), impossible for any phone app that owns only
one modality at a time.

### 2.7 Soft Weather — Atmosphere × 🎯 Life [ENHANCE, S]
**Trigger:** InnerWeather's `inner_storm` early-warning event (it already
fires minutes before you'd name the feeling). **HUD:** nothing — that's
the move. Card density quietly drops: non-urgent glance candidates are
suppressed, commitment nags defer, Atmosphere shifts one step calmer. A
retrospective card next morning: *"The display went quiet 20 minutes
before your storm yesterday."* **Feeling:** being understood without
being watched — the room got softer and you didn't know why until later.
**Only here:** requires a fused body-state estimator that never leaves
the device and a card-arbitration layer it can modulate.

### 2.8 The Weather You Left — 🤝 Together [NEW, M]
**Trigger:** you enter a place your bonded partner left within the last
hour — matched by salted place-hash (the `crossing.py` primitive:
unlinkable across bonds, no coordinates ever cross). **HUD:** their
parting weather ghosts across your rim for ten seconds — the actual
palette their sky wore when they walked out. **Feeling:** *"she was calm
here, an hour ago."* Presence across time, in the room where it was
true. **Only here:** requires WeatherLedger ambience recording, bond-
scoped hashing, and a display medium where color *is* the message.

### 2.9 Yesterlight Duet — 🤝 Together × 🧠 Memory [NEW, M]
**Trigger:** both bonded wearers hold the Yesterlight head-roll in the
same room. **HUD:** the two scrubs synchronize to the same hour (the
deeper tilt wins); both skies replay the room's recorded ambience from
each wearer's *own* ledger — same hour, two witnesses. **Feeling:**
walking through last night's dinner together, in place, without a single
photo existing. **Only here:** two private ambience ledgers, one bond,
zero shared media — nothing crosses but the scrub hour.

### 2.10 Heirloom — 🎯 Life × 🤝 Together [ENHANCE, M]
Duet Rehearsal already lets two wearers author one figment. Heirloom is
the asynchronous, generational version. **Trigger:** gift a signed
Figment across a bond (`figment_put` with `meta.origin="shared"` — the
provenance shield already renders). **HUD:** the recipient's run-through
plays the author's performance as ghost beats to accept or correct.
**Feeling:** *"my mother's bread-kneading rhythm, performed by her
hands, now keeping time on mine."* Behavior as inheritance. **Only
here:** behavior-as-signed-data with a run-through consent step — an app
can be shared; a *performance that programs a device* has never been
giftable.

### 2.11 One Ring — 🤝 Together (GhostMode) [ENHANCE, S–M]
The Beacon already renders each member's bearing as a pulse train.
**Trigger:** every member of a GhostMode circle converges within the
nearest distance band. **HUD:** the separate pulse trains — one per
person, each at their bearing — merge into a single steady ring, held
for three seconds. **Feeling:** arrival as light. The group *feels*
complete before anyone counts heads. **Only here:** anonymous-on-the-
wire presence (bearing + band only, names local) over LE Coded PHY — no
platform can render togetherness without first knowing who everyone is;
DreamLayer renders it *because* it doesn't.

### 2.12 Shared Bench — 🤝 Together × 🧠 Memory [NEW, M]
**Trigger:** you freeze a Stasis frame at a workbench and flag it
`shareable`; your bonded partner later lands at the same place signature.
**HUD (theirs):** the ribbon glyph offers *your* frame's context replay —
scene, anchors, your unfinished sentence, verbatim, with your name on the
provenance line. **Feeling:** picking up a colleague's train of thought
mid-air: *"…so if the hinge is binding, the torque spike should show
when—"* — and finishing it. **Only here:** requires the pre-interruption
ring buffer, place-keyed resume, and bond-scoped consent. Handing someone
your working memory has never been a thing computers could do.

### 2.13 Second Voice — 🧠 Memory (Ember) [ENHANCE, S]
The tombstone resurrection exists; give the answering its ceremony.
**Trigger:** the anniversary Ember card fires at the place a burned
memory happened; the wearer speaks the recall aloud. **HUD:** the
hearth-gold cue blooms once, then a single line: *"Only you remember
this now."* **Feeling:** the archive proving it emptied itself into you.
This is the one that makes people cry. **Only here:** it requires a
system willing to *delete its own product* — retrieval-practice
scheduling, place-gated cues, and consented burn. An engagement-metric
company cannot build a feature whose success condition is the data
ceasing to exist.

---

## Section 3 — The Living User Model: **The Almanac** [NEW, L]

A privacy-preserving behavioral intelligence layer that learns who the
wearer is — built as a **nightly consolidation artifact**, not an online
learner. It rides the existing REM gate (charging + night + rested) and
distills the day into a small, inspectable prior table: `almanac.json`,
sibling to `rem_bias.json`. During the day it is read-only; it cannot
drift, thrash, or be poisoned by one weird afternoon.

### Signal capture — what crosses the line into the Almanac, and what never does

| Captured (already flowing, structurally content-free) | Never captured |
|---|---|
| Lens usage counts and hour-of-day histograms (`lenses.py` registry) | raw audio, raw frames, transcripts kept beyond the hot ring |
| Card outcomes: dwell-before-dismiss, NOD_SAVE, taps (`DismissalTracker` is the seed) | GPS or any absolute coordinate — place *signatures* only |
| Gesture cadence and IMU motion class (spectral features of accel/gyro) | who you were with (People data stays in Social Lens, never joins the Almanac) |
| Speech-cadence deviation from your own baseline (InnerWeather already computes it) | anything from veiled, incognito, or `meta.private` spans — excluded at the door, the REM rule |
| Place-signature *class* recurrence (home-like, transit-like, new) | semantic content of memories — the Almanac learns *rhythms*, not *facts* |
| mic energy-band statistics (the `mic_fft` that already drives Dream Mode palettes) | — |

### Context inference — modes without location or content

A tiny on-phone classifier (gradient-boosted trees or a ~50 KB MLP — this
is not an LLM problem) maps `(IMU spectral class, place-sig class, hour,
mic energy stats, speech-cadence dev, active lens)` to a soft distribution
over modes: **cooking, moving-through-the-world, deep work, training,
socializing, winding down**. Driving is an IMU/vibration signature, not a
GPS one; cooking is stationary-standing + intermittent hand motion + the
kitchen's place class; socializing is multi-speaker mic statistics (count,
not content) + your own cadence up. Every input is a signal the wire
already carries — the classifier adds no new capture.

### Lens priority adaptation

The Glance Arbiter already learns which lens you prefer per scene kind;
the Almanac gives it **mode-conditioned bid modifiers**:

- *Deep work:* glance candidates below high confidence are suppressed;
  Stasis trigger sensitivity rises; card `dismiss_ms` shortens (you read
  fast when focused); Atmosphere holds still.
- *Cooking:* Wayfinding timers get priority; Juno bids up on
  food-adjacent sightings; Puente bids down.
- *Socializing:* Timbre and the dossier whisper bid up; everything
  Truth-family stays **explicit-only** (Truth Lens is never passive — the
  Almanac must not change that contract); commitment nags defer.
- *Training:* rep-counting figments own the display; ambient camera duty
  cycle drops to save battery for the IMU.
- *Winding down:* Soft Weather defaults; Ember tending offers migrate to
  the phone.

Card timing adapts the same way: the Almanac learns per-mode dwell curves
and sets `dismiss_ms` per card type per mode — the HUD stops flashing
things off before you finish reading them at dinner, stops lingering when
you're mid-stride.

### Temporal learning without ossifying

- Nightly, the Almanac updates with recency-weighted counts (half-life
  ~30 days) — months of stability build confident priors, but no pattern
  is permanent.
- **Change-point detection:** a two-window divergence test (last 14 days
  vs the trailing 90) on the mode/place/hour marginals. When life changes
  — new job, new city, new person — the Almanac doesn't fight it: it
  raises its temperature (widens priors, decays old counts faster) and
  lets the new life burn in. The user-visible symptom of a life change is
  the glasses getting *humbler* for a week, not wronger.
- Premonition already implements the miss-and-retire discipline for
  time-slots; the Almanac generalizes it: any prior that mispredicts
  twice at low hit-rate goes quiet.

### The graceful death — "forget everything"

The deletion sequence, in order, verifiable at each step:

1. **Freeze** capture (`PrivacyGate` pause) so nothing new lands mid-wipe.
2. **Purge memory through the only lawful door:** `Retriever.purge_all()`
   — row *and* ANN vector, the invariant the codebase already enforces by
   having deliberately removed free-function purges.
3. **Delete derived artifacts:** `almanac.json`, `rem_bias.json`,
   `dismissal_log.json`, prosody baselines (narrative store), Timbre
   shapes, WeatherLedger, EmberStore, Stasis frames, the usearch index
   file, vaulted Figment performance history.
4. **Cryptographic erasure** for the at-rest layer: the store is encrypted
   under one user key hierarchy [NEW, M — encrypt-at-rest is the
   prerequisite]; destroying the key makes flash remnants ciphertext.
5. **VACUUM** SQLite; rewrite the files so free pages don't retain rows.
6. **The receipt:** a deletion manifest — every artifact path, byte count,
   and post-state hash — rendered on the phone and kept as the *only*
   record. What is verifiably gone: every memory row, every vector, every
   prior, every baseline. What survives: the OS, installed
   plugins/figments (they are behavior, not memory — listed on the
   receipt so the user can purge those too), and pairing.
7. **Rebirth without brokenness:** this is where the ADD-alongside
   pattern pays off. Every learned component has a shipped heuristic
   floor — `HeuristicPerceptor`, the hashing embedder, default bids,
   default `dismiss_ms`. Day zero after death behaves like day one out of
   the box: competent, generic, slightly formal. The first night's REM
   begins the rebuild. The glasses feel *new*, never *damaged*.

### Privacy proof — verifiable on-device, not promised

- **The wire-shape argument, made inspectable:** the message-type registry
  is closed (`message_types.lua` ↔ `RAW_FRAME_TYPES` lockstep). A
  **Glass Box panel** on the Mac control panel [NEW, M] shows per-day
  counters for every boundary: frames by type glasses↔phone, calls
  phone↔Brain, calls phone↔cloud — with **provable zeros** when a switch
  is off. Not a policy page; a packet ledger.
- **Egress ledger:** every socket the hub opens is logged (destination,
  tier, bytes, which Answer it served) and browsable via the existing
  Datasette seam. The `Answer.tier` field already attributes every claim;
  this attributes every byte.
- **The airplane test:** everything in this section functions with the
  radio off except the Mac tier — a user can *demonstrate* on-device-ness
  in ten seconds, which beats any audit.
- **The Almanac is readable:** it's a small JSON of rhythms and
  preferences, shown in the phone app in plain language ("mornings: you
  read slowly; Tuesdays: gym at 6"). A model you can read is a model you
  can trust — and it contains rhythms, not secrets, because that's all it
  ever ingested.

---

## Section 4 — The Confluence Multiplier

Six features. Each states both wearers' experience, the exact data flow,
and the human need. The packet shape is designed first (insight 1): in
every one of these, *what crosses the bond* is a scalar, a hash, a digit,
or a palette — never content.

### 4.1 Same Star — the one nothing else has ever done [NEW, M–L]

**The experience.** Two bonded wearers in the same room. Each looks
where they look. The moment both gazes rest on the *same thing* — the
same painting, the same dog, the same crack in the ceiling — both rims
kindle in the bond's blended hue, simultaneously. No sound, no words, no
notification. Look away and it fades. **From each side it feels
identical:** you notice something, and the sky tells you *they noticed
it too, right now, and they know you know.*

**Data flow.** Each phone computes a local embedding of its wearer's
gaze target (tier-0/1, the Juno path), quantizes to a coarse bucket, and
sends a **salted 16-byte hash** (salt = bond key — the exact `crossing.py`
construction, unlinkable across bonds). Intersection happens locally on
each side. What crosses: a hash and a seq number. What never crosses: the
image, the label, the bearing, anything a third party could dictionary-
attack without the bond key. Veil silences it; either side can disable
per-session.

**Why it matters.** Joint attention is the primitive of intimacy — it's
how infants bootstrap love and how friends say *did you see that* with
their eyes. No technology in history has been able to **prove mutual
attention silently**: FaceTime shares faces, screens share pixels, but
nothing has ever closed the loop of *we are both looking at this and we
both know it* without a word. This is the demo where two strangers to
the product grab each other's arm.

### 4.2 Keeper's Nod — promises with a witness [NEW, M]

**The experience.** You promise your partner: "I'll call the school
Monday." The promise becomes a **twin object** — a mark on both Horizons.
They watch it live: blooming when you tend it, drifting amber when you
don't. When you keep it, *both skies bloom at once* — theirs pulses at
your bearing. **Data flow:** the commitment is created locally on the
promiser's device; what crosses is the mark's packed state digit (the
`kind*100+state*10+luma` code — one byte of meaning) on change, under the
bond key. The promise *text* crosses once, at creation, only with an
explicit per-promise "share this promise" consent — this is the first
Confluence feature to carry words, and it says so plainly. **Honest
privacy cost:** your partner can now see you neglecting something. That's
the point, and it's opt-in per promise, revocable, and dissolves with the
bond. **The need:** accountability without nagging — the promise itself
does the asking, and keeping it becomes a shared physical event instead
of a text message.

### 4.3 Tandem Recall — two memories, one question [NEW, L]

**The experience.** Either wearer asks: *"when did we last see Priya?"*
Both hubs answer **locally from their own index**. Each wearer sees their
own answer immediately; a beat later, the partner's *approved* card
arrives and the two render side-by-side, each footed with whose memory it
came from — and Provenance runs *across the pair*: "yours: firsthand,
March; theirs: corroborated, February — **contested**." **Data flow:** the
query crosses (it's addressed to the bond); each side's answer crosses
only after its owner's one-tap approve (the draft→approve→send pattern
from the Mac sources, reused). Indexes never pool; `meta.private` never
answers. **The need:** couples and old friends carry a *joint* past that
lives in two heads. Every other tool makes one person's record the truth.
This shows both standings and lets the humans decide — collaborative
memory with the dignity of disagreement.

### 4.4 The Long Bond — one sky, two cities [ENHANCE, M]

**The experience.** The bond, over distance. Your entangled sky renders
the blend of your weather and theirs, continuously, all evening — calm
seeping in from someone eight time zones away. TinCan pings arrive as
pulses at the *great-circle bearing of their city*. A Weather Gift
becomes the goodnight ritual: their sky plays your morning for thirty
seconds as they wake. **Data flow:** the existing `relay_transport.py`
blind relay carries the same WeatherPackets and TinCan pings it would
carry over BLE — the relay learns nothing (HMAC'd scalars and palette
slots; it buffers, it cannot read). Bond TTL extends for remote mode;
dissolve remains unilateral. **The need:** long-distance presence today
is calls and read receipts — discrete, demanding, on/off. This is
*ambient* co-presence: not talking, just knowing their weather. The
absence of a seam in your sky is the message that you're okay.

### 4.5 The Vigil — being watched over, not watched [NEW, M]

**The experience.** Opt-in, per-bond, off by default. When your partner's
inner storm sustains past a threshold (InnerWeather's front semantics —
minutes of real climb, hysteresis-gated, never a blip), a small steady
ember appears at their bearing on *your* rim. Nothing else. You know only:
*they're having a hard hour.* What you do with that is human. **From the
stormy side:** you know the Vigil exists because you turned it on; the
ember on their side is the entire disclosure, and your Veil kills it
instantly. **Data flow:** one bit, minutes-scale, HMAC'd — the storm
threshold crossing, never the scalar stream, never why. **Honest privacy
cost:** this shares an inference about your body. It is the most intimate
single bit in the product, which is exactly why it's per-bond opt-in with
its own consent card (the Figment safety-card pattern: "this can NEVER
tell them where you are or what you said"). **The need:** every human
with an aging parent, a struggling partner, a kid at college wants
exactly this — *tell me when to call* — and today the only options are
surveillance apps or silence.

### 4.6 Duet Wayfinding — two bodies, one procedure [ENHANCE, M]

**The experience.** Cooking together, belaying, changing a tire, a
two-person kata. One Figment, two stages: each wearer sees *their own*
steps ("you: fold the egg whites" / "them: butter the pan"), and
synchronization beats gate on **both** taps — the step where you must
wait for each other says so, and releases the instant you're both ready.
The compile is one `compile_skill()` with role annotations; each device
receives its own signed, budget-verified projection. **Data flow:** step
advance events cross as figment `ble` events under the bond key — a beat
number, nothing else; the bond `near` event (already in the Figment event
vocabulary) can gate steps on physical proximity. **The need:**
coordination without barking orders. Every couple that has assembled
furniture knows the failure mode; this deletes it — the procedure itself
holds both threads, and nobody is the foreman.

---

## Section 5 — The Plugin Ecosystem Flywheel

The pieces already exist in unusual depth — manifest+module packages, a
four-line validation gate, subprocess jail, bubblewrap/nsjail OS sandbox,
a WASM zero-ambient-authority host, TUF/Uptane registry trust, an 85/15
pricing seam — and, crucially, **two tracks**: Python plugins (powerful,
gated, jailed) and Figments (provable, signable, safe by construction).
The flywheel comes from treating those as one economy with two rungs.

### What makes a 5-star DreamLayer lens

1. **One thought at a time.** ≤5 lines, one accent, glanceable — the
   design system is the law, and the store should lint for it.
2. **It earns its interruptions.** Honest Glance bids; a lens that
   over-bids gets dismissed, and `DismissalTracker` will bury it. The
   best lenses are silent for hours and exactly right once.
3. **Veil-native.** Not "handles the veil" — *designed for absence*: a
   great lens degrades to nothing without dangling state (the event bus
   already only delivers `veil` while down; a 5-star lens resumes
   gracefully).
4. **Wire-frugal.** Bytes are the scarce resource (insight 1). A lens
   that ships one packed digit beats one that ships a paragraph.
5. **Fallback-first.** The ADD-alongside pattern: work with zero optional
   deps, get better when models are present. A lens that requires the
   cloud is a lens most users can't run.
6. **Reduce-motion pose.** Every animation has a still, information-
   preserving state. Accessibility is a launch requirement, not a patch.

### Tools creators need that don't exist yet

- **[NEW, M] Audition Mode** — the trust *and* discovery primitive in
  one: replay a candidate lens against **your own last week**, entirely
  locally (the emulator + your memory store; nothing leaves). The store
  shows: "this lens would have fired 4 times last week — here are the
  moments." No screenshot gallery can compete with *proof against your
  own life*, and only DreamLayer can offer it because only DreamLayer's
  users hold their own history.
- **[NEW, L] Figment Forge** — the visual authoring/debug surface, and
  the planned Loom revival (`RC_V2_PICKED.md` names its trigger: users
  asking to edit beats structurally). Every Figment renders as a braid;
  Forge makes the braid editable, shows the `BudgetReport` live (bytes,
  worst-case emits, flash-safety), and one-click deploys to the emulator
  stage. Ships with **Figment Golf** scoring as the leaderboard hook —
  expressiveness per byte as a competitive sport.
- **[NEW, M] The Golden Day corpus** — a recorded synthetic day (events,
  places, captions, sightings) shipped as fixtures, so a creator's CI can
  answer "when does my lens fire, and does it ever miss its deadline?"
  without hardware. Extend `object_lens/bench.py`'s deadline-runner into
  a per-plugin **latency profiler**: every extension-point call traced
  against the glance-panel budget, report rendered like a BudgetReport.
- **[NEW, S–M] Card previewer** — the 256 px circular display with safe
  inset, palette tokens, and both motion states, in the browser (rides
  the WebBLE playground pillar; the emulator's framebuffer export already
  does the rendering). Designers should see the circle before they see
  the device.
- **[NEW, S] Consent linter** — static output: what a plugin *can never
  do*, generated from declared capabilities and rendered exactly like the
  Figment safety card. Creators get the privacy copy for free; users get
  uniformity.

### Discovery and trust when privacy is the promise

- **Lead with the negative space.** Every store listing renders the
  *cannot* list first ("cannot: network, mic, filesystem"), derived from
  capabilities, enforced by the jail/WASM host — not the author's claims.
- **Trust is layered and visible:** Figment (proof — install anything) →
  WASM/jailed plugin (confined — install with a glance at capabilities)
  → signed in-process plugin (curated — reviewed code). Show the rung on
  every card; let users filter by it.
- **Audition before install** (above) — the only store where "try it"
  means *against your own week*, privately.
- **Wire receipts:** each listing shows measured bytes/day on the BLE
  link and battery cost from the Golden Day run — performance as a
  browsable, comparable number.
- **TUF/Uptane is already built** (`registry_trust.py`) — surface it:
  "this catalog cannot be rolled back, frozen, or forged, even if our
  server is owned" is a store-level differentiator no competitor states.

### Monetization that doesn't betray the architecture

- **85/15, as spec'd** (`CLOUD.md` P4), Stripe fees inside the 15. Free
  stays free to publish.
- **[NEW, M] Offline-verifiable install grants:** a purchase mints an
  Ed25519 grant binding (plugin, version-range, device key), verified by
  the same gate that checks signatures — **no phone-home DRM**, works in
  airplane mode, resellable = no (bound to device), refundable = revoke
  by CRL in the timestamped snapshot. Payment knows *what* was bought,
  never how it's used: usage telemetry is structurally absent because
  the wire has no type for it.
- **Figment packs as the low rung:** data-priced (a chef's five
  Wayfinding recipes, a coach's warm-up figments) — cheap to make,
  provable-safe, giftable across bonds (Heirloom, §2.10). This is where
  the long tail lives, and it needs no code review at all.
- **Subscriptions only where compute recurs** (Brain-side lenses that run
  nightly work on the Mac). **Never ads, never data** — not policy,
  architecture: attention isn't for sale because card slots are
  arbitrated by user benefit, and data isn't for sale because it never
  leaves.
- **Patronage hooks:** a tip line on the plugin page; the social layer
  already exists (ratings/comments Worker) and tips are one more number.

### Five killer lenses

1. **Sous** — the cook's lens. Wayfinding recipes (timed steps
   self-advance hands-free), Juno on ingredients, Label Lens allergens
   and your dietary vetoes, multiple concurrent timers as Horizon marks.
   *Only here:* hands-free timed procedures are a shipped Figment
   primitive, and your dietary rules never leave the device. *Audience:*
   everyone who cooks; the demo that sells glasses to households.
2. **Spot** — the training partner. Rehearsal-authored form sequences
   (a BJJ flow, a lifting complex), IMU rep counting, rest-timer pulses,
   Saga XP on completion. *Only here:* perform-to-program means a coach
   *demonstrates* the drill to author it — the authoring surface is the
   sport itself. *Audience:* lifters, grapplers, climbers, PTs selling
   their programs as figment packs.
3. **Docent** — cities and museums, curated. A curator ships signed
   figment tours anchored to place signatures: stand here, the story
   unfolds; walk on, it follows. Fully offline; no tracking — the places
   trigger locally. *Only here:* place `enter/exit` events without GPS,
   provable-safe third-party behavior, offline packs. *Audience:*
   museums, walking-tour authors, national parks.
4. **Lucida** — the executive-function prosthesis. Stasis tuned
   aggressive (interruption is the disability), Commitment Drift with
   gentler physics, Soft Weather defaults, body-double presence via a
   GhostMode circle of fellow Lucida users (presence, no content).
   *Only here:* interruption recovery requires the pre-interruption ring
   buffer — the one thing no reminder app possesses. *Audience:* ADHD
   adults — an underserved market that pays for tools that actually work.
5. **Aviary** — the field naturalist. Tier-0 naming tuned for birds
   (a fine-tuned int8 head is exactly what the NPU seam is for), Mac-tier
   explanation from your own field guides, life-list as cold entities,
   call recognition as Timbre-style signatures. *Only here:* offline in
   the field, and your life list is *memory* — provenance-stamped
   sightings ("first heard: Yosemite, May") — not an app's database.
   *Audience:* birders, a famously devoted and gear-buying community.

---

## Section 6 — The "Only DreamLayer" Moat

Each capability names the layer competitors are missing, what the wearer
experiences, and a defensibility rating: **Strong** (requires full-stack
replication), **Medium** (2+ years to copy), **Weak** (copyable quickly).

### 6.1 Consented human memory — the Grace Whisper class — **Strong**
Face and voice recognition of *your own people*, enrolled by spoken
introduction, stored only on your hardware, strangers structurally
invisible. **Why they can't:** Meta deliberately shipped Ray-Ban without
face recognition — as a cloud-social company it cannot touch biometrics
without existential PR/legal exposure; Apple has no ambient capture
device and no consent grammar; phone assistants have no eyes at the
moment of meeting. The missing layers: user-owned memory + closed-grammar
capture + the Veil. The wearer experiences the end of forgotten names —
the single most-wanted social superpower.

### 6.2 The archive that burns — Ember — **Strong**
Retrieval practice at the place it happened, then a consented purge, row
and vector, leaving only a cue tombstone. **Why they can't:** every
competitor's business model prices data by *accumulation*; a feature
whose success metric is deletion is organizationally unbuildable there.
Missing layer: memory the user owns outright. The wearer experiences a
product whose ambition runs opposite to dependence: it wants to make
itself unnecessary, one memory at a time.

### 6.3 Belief genealogy — Provenance + Candor — **Strong**
"You believe this because Maya told you, three weeks ago, and it's
contested." Requires *years* of structured private meaning-memory to
trace against. **Why they can't:** a cloud assistant holding a
longitudinal record of your beliefs is a subpoena magnet and a breach
catastrophe — the liability only disappears when the record never leaves
hardware you own. Missing layers: on-device meaning memory + tiered local
brain. The wearer experiences intellectual honesty as an instrument:
weighing beliefs instead of just holding them.

### 6.4 Proof-carrying behavior distribution — Figments — **Strong**
Install a stranger's behavior because the safety is a theorem
(`BudgetReport`), not a review verdict. **Why they can't:** every app
store distributes Turing-complete code; retrofitting totality proofs
means breaking their entire developer ecosystem. Vision Pro apps are
Swift; Ray-Ban has no third-party surface at all. Missing layer: the
fixed on-glass interpreter with static budgets. The wearer experiences
fearless installation — and creators experience a store with no review
queue between them and the user's eyes.

### 6.5 Wire-shape co-presence — Confluence / GhostMode — **Medium**
Entangled skies, Same Star, the Beacon: emotional bandwidth with
kilobit-shaped packets, private because the packets *can't* carry more.
**Why not Strong:** a competitor could copy the mechanic in 2+ years —
but they'd ship it through their cloud (they have no device-to-device
trust primitive), and "our server sees your togetherness scalar" is a
different product. Missing layers: bond-scoped keys + packet-shape
privacy + the Veil. The wearer experiences co-presence that no third
party mediates or mines.

### 6.6 The Veil as a platform invariant — **Medium–Strong**
One gesture, and every subsystem — capture, plugins' event bus, bonds,
the transport itself (`pause_allows_raw`) — goes silent, *including
third-party code*, because the extension surface is veil-gated by
construction. **Why they can't easily:** competitors treat privacy as an
app-level setting; making it a hardware-adjacent invariant that binds
all third-party code requires designing the extension API around it from
day one — a rewrite, not a feature. The wearer experiences a single
gesture they can trust with their livelihood: deaf, blind, provably.

### 6.7 The sovereignty ladder — phone-is-brain, Mac upgrade — **Medium**
Full function in airplane mode; a Mac mini upgrade that keeps everything
on hardware you own; cloud as a rare, flagged exception. **Why they
can't:** the tech is copyable, the *incentive* isn't — Meta, Google, and
OpenAI-class assistants monetize the cloud round-trip; Apple is closest
but ties intelligence to its services stack, not to a user-owned LAN
node. Missing layer: a business model that survives the user opting out
of the cloud. The wearer experiences graceful degradation instead of a
brick in a tunnel — and the visceral difference of "my questions stay in
my house."

### 6.8 Place-keyed time travel — Yesterlight + WeatherLedger — **Medium**
Roll your head back and the room replays its own recorded ambience;
enter a room your partner left and their weather ghosts by. **Why not
Strong:** the mechanic is inventable elsewhere, but it's only *trusted*
under this retention model (palette snapshots, veil-gated recording, no
coordinates) — the same feature from a cloud company reads as a tracking
log. Missing layers: local ambience ledger + place signatures without
location. The wearer experiences rooms with memory — the gentlest
possible version of recording everything, which is recording almost
nothing.

---

## Section 7 — The 90-Day Sprint to Jaw-Dropping

Fifteen tasks, ordered by **(impact × uniqueness) ÷ effort**. Sizes: S
(days), M (1–2 weeks), L (month), XL (quarter+). The sprint theme:
**make the felt layer instant (1–6), then ship the moments no one has
seen (7–12), then open the flywheel (13–15).**

| # | Task | Serves | Effort | The user feels | Depends on |
|---|---|---|---|---|---|
| 1 | **Shadow slot + commit protocol** — pre-position likely cards on-glass; local promote in ~10 ms | §1.1 | **M** | Taps and glances answer *instantly*; the HUD stops having a speed | — |
| 2 | **Grace Whisper dossier line** — Timbre rim glyph + one ledger line for known voices | §2.2 | **S** | Never caught blank by a familiar voice again | — |
| 3 | **Hedged escalation + quiet upgrade** — warm tier 2 in the ambiguity band; cards sharpen in place | §1.3 | **S–M** | "Tell me more" is already answered; answers visibly *refine* | — |
| 4 | **Soft Weather** — inner_storm suppresses non-urgent cards + calms Atmosphere; morning receipt | §2.7, §3 | **S** | The glasses get gentler right before you needed them to | — |
| 5 | **Don-event warm boot** — IMU don signature → cached-handle reconnect, mmap'd index, ReadyCard < 300 ms | §1.4 | **M** | Glasses feel *on* the moment they touch your face | — |
| 6 | **First-line streaming cards** — commit the primary line at first token | §1.3 | **M** | Juno answers in half a breath instead of two | 1 helps |
| 7 | **Reverie v1** — speculative answers on hardened Premonition slots + place entry, parked in shadow slots | §1.2 | **M** | The gym card is on the glass before you asked | 1 |
| 8 | **Premonition Handshake** — ghosts visibly solidify when you arrive | §2.4 | **S** | You watch the glasses' quiet bet on you come true | — |
| 9 | **Same Star** — salted gaze-hash exchange over the bond; both rims kindle on mutual attention | §4.1 | **M–L** | *We're both looking at this, and we both know* — the demo that sells the second pair | bond (shipped) |
| 10 | **Dream Gallery** — morning reel plays as world-fixed sprites on a blank wall | §2.5 | **S–M** | You watch what the glasses dreamed about your day | sprite RLE (§1.1) helps |
| 11 | **Keeper's Nod** — consent-shared promises as twin Horizon marks; both skies bloom on keep | §4.2 | **M** | A kept promise becomes a shared physical event | 9's consent card pattern |
| 12 | **Second Voice ceremony** — the anniversary Ember answer moment ("Only you remember this now") | §2.13 | **S** | The one that makes people cry | — |
| 13 | **Audition Mode** — try any lens against your own last week, locally, before install | §5 | **M** | "It would have fired here, here, and here" — trust you can watch | Golden Day corpus (S, bundled in) |
| 14 | **Almanac v1** — nightly mode inference + Glance bid modifiers + per-mode card timing | §3 | **L** | The right lens keeps winning; cards linger exactly as long as you read | 4 ships its first consumer |
| 15 | **NPU perceptor v1** — DS-CNN wake-word + person-presence/text-density on the Ethos-U55 (Vela) | §1.5–1.6 | **L** | Glance naming drops toward 60 ms; wake without streaming the mic | Vela toolchain bring-up |

Deliberately *not* in the 90 days: Figment Forge (L, the flywheel's
second quarter), Tandem Recall (L, wants the consent UX from 11 proven
first), The Vigil (M, but it should ship *after* the consent-card
pattern has earned trust in 9 and 11 — the most intimate bit in the
product deserves the most rehearsed consent flow), and the WASM host
operator story (seam-complete; needs packaging, not invention).

Day 90 demo, end to end: don the glasses (instant, #5), walk to the
gym (the card is waiting, #7, #8), a friend's voice behind you (#2),
you both look at the same absurd dog (#9), keep the promise you shared
(#11), and over morning coffee the wall plays last night's dream (#10)
while an Ember card asks about the lake — and you answer from the only
place it still exists (#12).

---

*Written against the codebase at `host-python/src/dreamlayer/` and
`halo-lua/` as of 2026-07. Every [ENHANCE] names shipped modules; every
budget and constraint cited (350 ms glance, 16 KB frames, 32-scene
figments, 90-day warm tier) is the code's own number, not an estimate.*
