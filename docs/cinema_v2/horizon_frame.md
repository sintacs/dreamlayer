# The Horizon Frame

## Pitch

One semantic BLE message streams the composed day to the glasses, and
one phone component mirrors it — the horizon is a product surface, not
an emulator screenshot.

## Information carried

The frame is pure transport for `horizon.md`'s content: mark angles,
kinds, drift states, luma tiers. The phone mirror carries the same
reading to the companion app so the two screens agree about the day
(triple-mirror doctrine: phone preview is QA truth,
`CardPreview.tsx:4-8`).

## Wire format

New message type in `halo-lua/ble/message_types.lua`:

```lua
M.HORIZON = "horizon"   -- host->halo: composed day-ring state
```

Payload (JSON over the existing 4-byte framed transport,
`ble/protocol.lua` — reassembly already handles multi-MTU):

```json
{ "t": "horizon",
  "seq": 1234,
  "v": [ dd1, code1, dd2, code2, ... ] }
```

- `v` is a flat int array (line_field precedent), 2 ints per mark, ≤48
  marks (`MER_MARKS_MAX`) → ≤96 ints ≈ 500–600 bytes ≈ 3 MTU chunks at
  ambient cadence — no head-of-line pressure on palette frames.
- `dd`: angle in **deci-degrees** screen space (−2700 = 12 o'clock),
  precomputed by the host. The device does zero time math (no clock
  skew shear).
- `code`: packed `kind*100 + state*10 + luma`:
  - kind: 1 memory, 2 promise, 3 person, 4 elder-tick, 5 future-cap
  - state (promises): 0 n/a, 1 blooming, 2 healthy, 3 drifting,
    4 cracking, 5 shattered
  - luma tier: 0 floor, 1 dim, 2 full
- `seq` monotonic; the device drops frames with stale seq (out-of-order
  BLE delivery is harmless).

Composer: `host-python/src/dreamlayer/orchestrator/horizon_composer.py`
(new). Inputs: `SemanticRingBuffer.since(now − 5h)`,
`CommitmentDriftEngine.all_records()`, privacy gate. Emits on the
orchestrator tick, rate-limited to one frame per 5s
(`HORIZON_CADENCE_S = 5`) or immediately on buffer/drift change.
Local-first: every input is on-host; there is no cloud dependency in
the path. While privacy-paused the composer emits a single empty frame
(`v: []`) and goes silent — the device shows the paused notch
(`horizon.md` failure modes).

Device handler: `horizon.lua:on_frame(msg)` registered via
`HostComm.register(MT.HORIZON, ...)` at boot in `main.lua`.

## Phone mirror

`phone-app/src/ui/components/HorizonPreview.tsx` (react-native-svg,
same dependency as CardPreview): renders the identical dial — notch,
seam, mark grammar, promise states — from a `HorizonState` object, with
the same mock-source pattern as `DreamCanvas.tsx` (`mockTick`) for
offline dev, and a `source` prop for the live feed. Colors from
`theme/colors.ts haloPalette` only; geometry constants mirrored from
`animations.lua MER_*` into `theme/motion.ts` (`meridian` export) — the
same parity discipline as `signatures`.

## Sensors / state / events

None of its own — pure plumbing. It exists as an element (with a design
doc and tests) because v1's Wrong #1 proves plumbing dies silently when
it isn't owned: a renderer dispatch gap shipped black goldens. The
frame's tests assert end-to-end: composer output → framed bytes →
`protocol.lua` reassembly → `horizon.lua` state → drawn primitives.

## reduce_motion

N/A (no visual behavior of its own); cadence unchanged by the setting.

## Failure modes

- **Frame larger than budget** (>48 marks): composer truncates by
  documented priority (drop lowest-confidence memories first, never
  promises) and sets no flag — the cap is a composition rule, not an
  error.
- **Device misses frames** (congestion): last frame persists; staleness
  rule (30s → luma drop) communicates it. Composer always sends full
  state, never diffs — any single frame fully heals.
- **Malformed frame**: `horizon.lua` validates arity (even-length `v`,
  codes in range) and keeps the previous frame on violation; a parse
  error never blanks the day.
- **Privacy Veil mid-flight**: `PAUSE_ALLOWED_RAW` gating on the
  bridges (`bridge/base.py:19`) is extended to allow the empty pause
  frame through — the *absence* of marks must be deliverable while
  paused, or the rim would keep showing pre-pause state.

## Peripheral-glance / daily-use tests

Inherited from `horizon.md` — this element's job is to make those tests
pass on real hardware and on the phone, not just in the emulator.
