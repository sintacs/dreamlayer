--- display/focus.lua
--- The Focus law: condensation / recession (docs/cinema_v2/focus.md).
--- One motion law replaces four v1 signatures (Iris Bloom, Prism Slide,
--- Confidence Halo orbit, Memory Comet — docs/CINEMA_V2_DELTAS.md §1-§4):
--- content is drawn inward into focus FROM its horizon angle, holds with
--- a static ring whose sweep is its confidence, and goes home when
--- released. Nothing materializes; nothing dies.
---
--- Public API (renderer.lua composes these):
---   focus.enter_ms() / focus.recede_ms()
---   focus.travel(t, origin_deg, color)          -- head+tail, rim -> core
---   focus.landing_ring(t, accent)               -- r 56->36 collapse + ghost ramp
---   focus.hold_ring(confidence, color)          -- static arc, sweep = conf
---   focus.recede(t, origin_deg)                 -- reverse flight home
---   focus.origin_or_now(card) -> deg            -- card.origin_deg | -90

local A   = require("display.animations")
local P   = require("display.palette")
local E   = require("lib.easing")
local TR  = require("display.transitions")

local HAS_FRAME = (type(_G.frame) == "table")

local M = {}

local CX, CY = 128, 128

local function fl(n) return math.floor(n + 0.5) end
local function clamp(v, lo, hi) return math.max(lo, math.min(hi, v)) end
local function lerp(a, b, t) return a + (b - a) * t end

local function polar(r, deg)
  local rad = math.rad(deg)
  return CX + r * math.cos(rad), CY + r * math.sin(rad)
end

local function arc(r, a0, a1, color, steps)
  if not HAS_FRAME or r <= 0 then return end
  steps = steps or 40
  local sweep = a1 - a0
  local x0, y0 = polar(r, a0)
  for i = 1, steps do
    local x1, y1 = polar(r, a0 + sweep * i / steps)
    frame.display.line(fl(x0), fl(y0), fl(x1), fl(y1), color)
    x0, y0 = x1, y1
  end
end

function M.enter_ms()
  if TR.reduce_motion() then return 0 end
  return A.SIG_FOCUS_TRAVEL_MS + A.SIG_FOCUS_LAND_MS
end

function M.recede_ms()
  if TR.reduce_motion() then return 0 end
  return A.SIG_RECEDE_MS
end

--- Cards without a temporal origin condense from "now" (12 o'clock).
function M.origin_or_now(card)
  local deg = card and tonumber(card.origin_deg)
  return deg or A.MER_NOW_DEG
end

-- ---------------------------------------------------------------------------
-- Travel: 3px head + 3-sample fading tail along a perpendicular-offset
-- bezier from (MER_RIM_R, origin_deg) to the content core.
-- ---------------------------------------------------------------------------
local function bezier_point(t, x0, y0, x1, y1)
  local mx, my = (x0 + x1) / 2, (y0 + y1) / 2
  local px, py = -(y1 - y0), (x1 - x0)
  local plen = math.sqrt(px * px + py * py) + 0.001
  local cx = mx + px / plen * 24
  local cy = my + py / plen * 24
  local u = E.in_out_cubic(clamp(t, 0, 1))
  local mt = 1 - u
  return mt * mt * x0 + 2 * mt * u * cx + u * u * x1,
         mt * mt * y0 + 2 * mt * u * cy + u * u * y1
end

local function head_and_tail(t, x0, y0, x1, y1, head_color)
  if not HAS_FRAME then return end
  local hx, hy = bezier_point(t, x0, y0, x1, y1)
  frame.display.circle(fl(hx), fl(hy), 3, head_color, true)
  local shades = { P.accent_memory, P.accent_memory_dim, P.text_ghost }
  for i = 1, 3 do
    local tt = t - i * 0.07
    if tt > 0 then
      local x, y = bezier_point(tt, x0, y0, x1, y1)
      frame.display.circle(fl(x), fl(y), i == 1 and 2 or 1, shades[i], true)
    end
  end
end

--- Condensation travel phase. t in [0,1].
function M.travel(t, origin_deg, color)
  if TR.reduce_motion() then return end
  local ox, oy = polar(A.MER_RIM_R, origin_deg or A.MER_NOW_DEG)
  head_and_tail(clamp(t, 0, 1), ox, oy, CX, CY, color or P.accent_memory)
end

--- Landing phase: ring collapses r 56->36 (out_expo) while content draws
--- inside; the ghost slot Y-ramps over the trailing SIG_FOCUS_TRAIL_MS.
--- t in [0,1] of SIG_FOCUS_LAND_MS.
function M.landing_ring(t, accent)
  local MAT = require("display.materials")
  MAT.init()
  if TR.reduce_motion() or t >= 1 then
    P.restore("ghost_text")
    return
  end
  t = clamp(t, 0, 1)
  local r = lerp(A.SIG_FOCUS_LAND_R_FROM, A.SIG_FOCUS_LAND_R_TO, E.out_expo(t))
  arc(fl(r), 0, 360, accent or P.accent_memory, 40)
  local trail_frac = A.SIG_FOCUS_TRAIL_MS / A.SIG_FOCUS_LAND_MS
  local trail_t = clamp((t - (1 - trail_frac)) / trail_frac, 0, 1)
  P.set_dynamic_y("ghost_text", lerp(160, 400, trail_t))
end

--- The landed focus ring: static, sweep = confidence. This is the card's
--- certainty gauge during HOLD; reduce_motion variant is identical (the
--- first signature whose reduce path is a no-op — the v2 standard).
function M.hold_ring(confidence, color)
  local conf = clamp(confidence or 0.5, 0, 1)
  local sweep = conf * 360
  if sweep < 4 then return end
  -- segment count follows the sweep: a sliver costs a sliver's draw calls
  local steps = math.max(6, fl(sweep / 7.5))
  arc(A.SIG_FOCUS_RING_R, -90, -90 + sweep, color or P.accent_memory, steps)
end

--- Recession flight home. t in [0,1] of SIG_RECEDE_MS. The caller
--- (renderer) handles content contraction + text cut via exit_contract
--- and fires horizon.pulse_mark on completion.
function M.recede(t, origin_deg)
  if TR.reduce_motion() then return end
  t = clamp(t, 0, 1)
  local ox, oy = polar(A.MER_RIM_R, origin_deg or A.MER_NOW_DEG)
  head_and_tail(t, CX, CY, ox, oy, P.accent_memory_dim)
  local ring_r = fl(A.SIG_FOCUS_LAND_R_TO * (1 - t))
  if ring_r > 2 and t < 0.5 then
    arc(ring_r, 0, 360, P.accent_memory_dim, 24)
  end
end

--- reduce_motion condensation: an 8px static tick at the origin angle
--- carries the temporal-origin reading (the comet's reduce variant,
--- generalized). Drawn once during HOLD alongside the full-sweep ring.
function M.origin_tick(origin_deg, color)
  if not HAS_FRAME then return end
  local rad = math.rad(origin_deg or A.MER_NOW_DEG)
  local x1 = CX + 100 * math.cos(rad)
  local y1 = CY + 100 * math.sin(rad)
  local x2 = CX + 108 * math.cos(rad)
  local y2 = CY + 108 * math.sin(rad)
  frame.display.line(fl(x1), fl(y1), fl(x2), fl(y2), color or P.accent_memory)
end

return M
