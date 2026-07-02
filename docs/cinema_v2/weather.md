# Weather Through the Horizon

## Pitch

Dream Mode stops being a scene cut into a separate world: the same
reactors (mic weather, IMU field, place chroma) now render as weather
over the same geography — entering the dream is a change of light, not
a change of place.

## Information carried

Everything v1's dream layer carried, plus situatedness:

- **Acoustic weather**: two-band palette weather unchanged — low-band
  pressure → `sky` slot Cb, high-band energy → `energy` slot Cr, Y from
  amplitude (`dream_mode/mic_reactor.py`, wire format `{t:"palette"}`
  untouched).
- **Head motion**: Line Field 2.0 unchanged in transport
  (`{t:"line_field"}`, 12 vectors, damped curl noise) — but the host
  sampler is re-seated to a **rim-tangent band** (r ∈ [60, 90],
  tangentially biased), so the field flows *around* the day instead of
  crossing the center. Same information (motion energy, damped yaw),
  situated composition.
- **Place trust**: PlaceReactor chroma bias unchanged (known place →
  memory chroma, novel → attention chroma, 8s ramp).
- **The day itself**: the horizon stays visible in the dream — memory
  marks at their lowest luma tier, promise arc at full tier (promises
  do not sleep), notch breathing. The dream is *your* dream: the wearer
  never loses when-am-I.
- **Anchor provenance** (new): when a WorldAnchor echo ghost-wakes, its
  horizon mark (at the original event's time-angle) brightens to full
  for the duration of the echo — the echo text says *what*, the mark
  says *when it's from*.

## Sensors / state / events

- `dream_enter` / `dream_exit` messages unchanged; `host_comm_dream`
  handler set unchanged.
- Reactor cadence unchanged (2Hz host dream tick).
- New host change: `imu_reactor.py` curl-noise sample ring re-seated
  (pure host-side; wire format and device handler untouched).
- Device change: `dream_renderer.draw_frame()` composition order
  becomes horizon(dim) → line field → particles; anchor rendering gains
  the mark-brighten hook into `horizon.lua`.

## Visual & behavioral spec

- `dream_enter` transition (300ms, `MER_DREAM_ENTER_MS`): memory marks
  ramp to floor tier (`border_subtle` color swap — token swap, not
  slot animation), particle budget ramps 0→24, field fades in. No
  clear(), no scene cut — the terrain never leaves the screen. The
  *light* changes completely; the place does not.
- `dream_exit` (200ms): reverse; `palette.restore_all()` invoked as v1
  risk mitigation demanded — and the fringe-slot hazard itself is gone
  since slots 3/4 have exactly one owner now (weather), see
  `CINEMA_V2_DELTAS.md §2/§8`.
- Particles: unchanged mechanics, but wrap territory clipped to r ≤ 96
  so the rim band stays legible (particles never invade the horizon).
- Anchor echoes: Ghost Wake text treatment unchanged (per-character
  Perlin condensation, rows 192/208/222, 22-char caps — v1 got this
  right); plus the provenance brighten: `horizon.set_highlight(
  anchor_deg, duration_ms)`.
- Synesthesia v2 cards: unchanged content; they enter via the focus law
  like every card (origin = now, since a synesthesia is *of the
  present*).

```
   memory mode                      dream mode (same terrain, new light)

      ' . ┃ . ●                        · . ┃ . ●   <- marks floor-tier,
    '     ┃                          ~      ┃        promises full
   |   (idle:                      ~   ~~ ~   ~   <- field bends around
   '    horizon                     ~ o   ~ ·  ~     the rim, r 60-90
    .    only)                       ~  o~  ~
      `--seam--'                      `--seam--'
                                     MEMORY ECHO rows (ghost wake) +
                                     anchor's mark brightened at its hour
```

## reduce_motion

Weather is palette-slot color motion (allowed: it is the information),
but geometric motion honors the setting: particles render as static
constellation (positions frozen per frame update), field vectors drawn
without per-tick drift, dream_enter/exit become single-frame swaps.
Anchor text uses Ghost Wake's existing reduce variant (settled text).
Acoustic/place information survives entirely in the palette dimension.

## Failure modes

- **No line_field frames** (host quiet): v1's legacy 8-vector fallback
  dies with this doc — instead the field is simply absent and the
  horizon + particles carry the dream; an empty sky is honest weather.
- **Palette frame starvation** (BLE congestion): device interpolates
  toward the last target (v1 behavior kept); staleness beyond 10s
  freezes weather at the last state rather than snapping to defaults —
  a stuck sky is visibly stale without a jarring reset.
- **dream_enter mid-crossfade**: focus law completes as hard cut, then
  the light change runs; slots have single owners so no fringe glitch
  is possible (the v1 risk-register hole, closed structurally).
- **Anchor with no time metadata**: echo renders without a mark
  brighten (text-only) — degraded, never wrong.

## Peripheral-glance test (400ms)

Mode is readable instantly (field + particle presence = dream), weather
is readable as color temperature (storm-blue pressure vs ember energy),
and the day remains readable exactly as in memory mode (notch, promise
amber). v1's dream failed this last reading by definition — its Air
tier carried nothing.

## Daily-use test (day 30)

v1's dream risked becoming a lava lamp: pretty, meaningless, eventually
invisible. Weather-over-terrain resists this because its base layer is
the horizon (new every hour) and its color state tracks the real room's
sound — the wearer learns to *hear the room with their eyes* (quiet
library vs humming cafe are different skies). The day-30 reading is
ambient self-awareness, which does not wallpaper because the self keeps
changing.
