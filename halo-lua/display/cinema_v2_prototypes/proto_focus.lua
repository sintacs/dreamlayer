--- cinema_v2_prototypes/proto_focus.lua
--- Phase 3 scratch: the Focus law (docs/cinema_v2/focus.md).
--- Condensation (travel 140ms + landing 100ms), hold ring (sweep = conf),
--- recession (160ms + arrival pulse). Rendered over a dimmed horizon.

local L = require("display.cinema_v2_prototypes.proto_lib")
local P = require("display.palette")
local E = require("lib.easing")

local M = {}

local CX, CY = L.CX, L.CY
local fl = L.fl

-- scratch constants (integration home: display/animations.lua)
local TRAVEL_MS   = 140
local LAND_MS     = 100
local RECEDE_MS   = 160
local RING_HOLD_R = 92
local LAND_R_FROM, LAND_R_TO = 56, 36
local ORIGIN_DEG  = 0        -- the answer lives at 3 o'clock (3h ago)

-- Backdrop: the day this answer comes from (dimmed one tier during focus)
local BACKDROP = {
  marks = {
    { deg = -90 + 135, kind = "memory", luma = 0, extra_len = 2 },
    { deg = -90 + 100, kind = "memory", luma = 0 },
    { deg = ORIGIN_DEG, kind = "memory", luma = 2 },  -- the origin mark, lit
    { deg = -90 + 20,  kind = "memory", luma = 0 },
    { deg = -90 - 45,  kind = "promise", pstate = "healthy" },
  },
  notch_len = 7,
}

-- Content: an ObjectRecall-shaped answer, drawn fully-held; the focus law
-- decides what is revealed (stagger) — card draw fns stay pure in v2.
local function draw_content(stagger_gate)
  -- stagger_gate: 0..1 fraction of ENTER elapsed (1 = everything visible)
  local function ok(ms) return stagger_gate * 240 >= ms end
  if ok(40) then
    frame.display.text("KEYS", CX, 78, P.memory_trace)
  end
  if ok(0) then
    frame.display.text("Kitchen table", CX, 118, P.text_primary)
  end
  if ok(60) then
    frame.display.text("beside blue notebook", CX, 146, P.text_secondary)
  end
  if ok(80) then
    frame.display.text("7:42 PM", CX, 172, P.text_ghost)
  end
end

local function bezier_point(t, x0, y0, x1, y1)
  -- control point perpendicular-offset, matching comet mechanics
  local mx, my = (x0 + x1) / 2, (y0 + y1) / 2
  local px, py = -(y1 - y0), (x1 - x0)
  local plen = math.sqrt(px * px + py * py) + 0.001
  local cx = mx + px / plen * 24
  local cy = my + py / plen * 24
  local u = E.in_out_cubic(math.max(0, math.min(1, t)))
  local mt = 1 - u
  return mt * mt * x0 + 2 * mt * u * cx + u * u * x1,
         mt * mt * y0 + 2 * mt * u * cy + u * u * y1
end

local function draw_head(t, x0, y0, x1, y1, color)
  -- Iteration 2: head 2px->3px, tail 2->3 samples; at 2px the travel was
  -- sub-visible against the dial (prototype review pass 1).
  local hx, hy = bezier_point(t, x0, y0, x1, y1)
  frame.display.circle(fl(hx), fl(hy), 3, color, true)
  local shades = { P.accent_memory, P.accent_memory_dim, P.text_ghost }
  for i = 1, 3 do
    local tt = t - i * 0.07
    if tt > 0 then
      local x, y = bezier_point(tt, x0, y0, x1, y1)
      frame.display.circle(fl(x), fl(y), i == 1 and 2 or 1, shades[i], true)
    end
  end
end

--- Condensation frame at t_ms in [0, 240].
function M.render_condense(t_ms, conf)
  frame.display.clear(0x000000)
  L.draw_horizon(BACKDROP)
  local ox, oy = L.polar(L.RIM_R, ORIGIN_DEG)

  if t_ms <= TRAVEL_MS then
    draw_head(t_ms / TRAVEL_MS, ox, oy, CX, CY, P.accent_memory)
  else
    local lt = (t_ms - TRAVEL_MS) / LAND_MS
    lt = math.max(0, math.min(1, lt))
    local r = LAND_R_FROM + (LAND_R_TO - LAND_R_FROM) * E.out_expo(lt)
    L.arc(CX, CY, fl(r), 0, 360, P.accent_memory, 40)
    draw_content(lt)
  end
  frame.display.show()
end

--- Hold frame: full content + static focus ring, sweep = conf.
function M.render_hold(conf)
  frame.display.clear(0x000000)
  L.draw_horizon(BACKDROP)
  draw_content(1)
  local sweep = math.max(0, math.min(1, conf or 0.5)) * 360
  local col = (conf or 0.5) >= 0.75 and P.accent_memory
           or (conf or 0.5) >= 0.40 and P.confidence_med
           or P.confidence_low
  L.arc(CX, CY, RING_HOLD_R, -90, -90 + sweep, col, 48)
  frame.display.show()
end

--- Recession frame at t_ms in [0, RECEDE_MS + 300 pulse].
function M.render_recede(t_ms)
  frame.display.clear(0x000000)
  local t = t_ms / RECEDE_MS
  local ox, oy = L.polar(L.RIM_R, ORIGIN_DEG)

  -- origin mark pulses +1 tier for 300ms on arrival
  local pulsing = t >= 1 and (t_ms - RECEDE_MS) <= 300
  local backdrop = { marks = {}, notch_len = 7 }
  for _, mk in ipairs(BACKDROP.marks) do
    local c = {}
    for k, v in pairs(mk) do c[k] = v end
    if c.deg == ORIGIN_DEG and c.kind == "memory" then
      c.extra_len = pulsing and 3 or 0
      c.luma = 2
    end
    backdrop.marks[#backdrop.marks + 1] = c
  end
  L.draw_horizon(backdrop)

  if t < 1 then
    -- text cuts at t=0.4 (kill-list #2 rule); geometry contracts
    if t < 0.4 then draw_content(1) end
    draw_head(t, CX, CY, ox, oy, P.accent_memory_dim)
    local ring_r = fl(LAND_R_TO * (1 - t))
    if ring_r > 2 and t < 0.5 then
      L.arc(CX, CY, ring_r, 0, 360, P.accent_memory_dim, 24)
    end
  end
  frame.display.show()
end

--- reduce_motion condense: complete frame + origin tick, single frame.
function M.render_reduced(conf)
  frame.display.clear(0x000000)
  L.draw_horizon(BACKDROP)
  draw_content(1)
  local sweep = math.max(0, math.min(1, conf or 0.5)) * 360
  L.arc(CX, CY, RING_HOLD_R, -90, -90 + sweep, P.accent_memory, 48)
  -- 8px static origin tick on the rim (comet reduce-variant precedent)
  L.radial_tick(ORIGIN_DEG, 100, 108, P.accent_memory, 2)
  frame.display.show()
end

return M
