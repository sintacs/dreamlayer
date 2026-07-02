# Palette cycling — motion by recolouring, not redrawing

A reusable on-device animation primitive (`halo-lua/display/palette_cycle.lua`).

## The trick

The classic demoscene move. Paint a region **once** using a run of reserved
dynamic palette slots; then, every frame, rotate which colour each slot
holds. The pixels never move and are never redrawn — the colours flow
through them. On the 4bpp Halo panel this buys rich, continuous motion
(aurora drift, waterfalls, shimmer) for the cost of a handful of
`frame.display.assign_color_ycbcr` calls per frame and **zero geometry**.
No pixel writes, no BLE — it runs entirely on the glasses.

Dream Mode already did a hand-rolled version of this on its four sky slots.
This generalises it into a primitive any surface can use.

## Why it's cheap

The 4bpp display has 16 palette entries; slots 1–6 are the reassignable
dynamic bank (`palette.lua`). Reassigning a slot recolours **every pixel
already drawn with that slot index** in one call. So a gradient band drawn
with four slots becomes a flowing gradient by reassigning four colours —
independent of how many pixels the band covers.

## API

```lua
local PaletteCycle = require("display/palette_cycle")

-- cycle over reserved slot names, in draw order, with a colour ramp
local cy = PaletteCycle.new(
  { "sky", "energy", "drift_a", "drift_b" },   -- reserved slot names
  { 0x0E3B32, 0x2CC79A, 0x59E0D6, 0x7A6BE0 },  -- ramp (optional: defaults to
                                               -- each slot's own base colour)
  { period_ms = 4000, smooth = true })

cy:tick(now_ms)                 -- advance from the clock (one ramp per period)
cy:tick(now_ms, { reduce_motion = true })   -- hold the base arrangement
cy:advance(1.5)                 -- set an explicit ramp-step offset (float)
cy:restore()                    -- snap to the base arrangement (offset 0)
```

- **Deterministic.** `tick(now_ms)` is a pure function of the clock — the same
  now_ms always yields the same palette, so it never fights a redraw loop.
- **Smooth.** With `smooth = true` each slot interpolates between two ramp
  stops in YCbCr, so even a 4-colour ramp flows continuously instead of
  stepping. `smooth = false` snaps to the nearest stop (true retro cycling).
- **reduce_motion** freezes the cycle to its base arrangement — colour intact,
  movement gone — same accessibility contract as the notch and promise physics.
- The bank is full (slots 1–6 are all reserved), so a cycle is defined over
  existing slot **names**; it recolours them, it doesn't claim new ones.

## First use: the idle sky flow

Wired into `dream_renderer.lua`. When the mic reactor is quiet, the four sky
slots gently cycle their own colours around the ring (period 9 s), so a still
dream scene drifts like an aurora at zero redraw cost. The reactor owns the
slots the instant it speaks: any `apply_palette_shift` holds the flow off for
`IDLE_HOLD_MS`, and it resumes only in the silence the reactor leaves. The
flow paints no pixels of its own — it is pure palette motion under everything
the renderer already draws.

## Try it

```
python scripts/run_demo_palette_cycle.py
```

Drives the real Lua primitive over an aurora ramp and writes
`out/palette_cycle/flow.png` — a filmstrip (one frame per row) of a band that
scrolls without a single pixel being redrawn.

## Tests

`host-python/src/dreamlayer/tests/test_palette_cycle.py` — ramp assignment,
integer rotation and wrap, smooth YCbCr interpolation vs stepped, clock-driven
determinism and motion, period wrap, reduce_motion, the unreserved-slot guard,
the headless no-op, and the dream idle-flow integration (flows when quiet,
freezes under reduce_motion, yields to a reactor push).
