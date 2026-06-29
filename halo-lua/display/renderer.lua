--- display/renderer.lua
--- Ported to real Brilliant Labs frame.* API.
--- All draw calls use frame.display.* directly.
--- Every render path: frame.display.clear(0x000000) → draw → frame.display.show()
---
--- New primitives (quadratic_bezier, elliptical_arc, etc.) implemented
--- as line-segment polylines using math.cos/sin.
---
--- FIXES applied over commit 99ece13:
---   - HAS_FRAME guard added to all internal primitives (CI safety)
---   - radial_rays signature unified: (cx,cy,r_min,r_max,n_rays,color,bloom_r)
---   - renderer.tick() guarded so Python CI does not crash
---   - tick throttle fixed: was %1 (always true), now %3 (~3fps on 0.1s sleep)

local math = math
local P    = require("display.palette")
local T    = require("display.typography")

local HAS_FRAME = (type(_G.frame) == "table")

local renderer = {}

-- Current displayed card (set by show_card)
local _current_card = nil
local _tick_count   = 0

-- ---------------------------------------------------------------------------
-- Layer constants (kept for API compatibility with callers)
-- ---------------------------------------------------------------------------
renderer.LAYER_BG      = 0
renderer.LAYER_CONTENT = 10
renderer.LAYER_OVERLAY = 20
renderer.LAYER_HUD     = 30

-- ---------------------------------------------------------------------------
-- Utility helpers
-- ---------------------------------------------------------------------------

local function floor(n) return math.floor(n + 0.5) end

--- Color passthrough: frame API takes 0xRRGGBB integer directly.
local function col(c) return c end

-- ---------------------------------------------------------------------------
-- Primitive approximations
-- (No frame.display.bezier / arc / polyline exist in the real API)
-- All helpers guard HAS_FRAME so require() in Python CI is safe.
-- ---------------------------------------------------------------------------

--- APPROX: quadratic_bezier via polyline of line segments
local function bezier(p0x, p0y, p1x, p1y, p2x, p2y, color, steps)
  if not HAS_FRAME then return end
  steps = steps or 24
  local px, py = p0x, p0y
  for i = 1, steps do
    local t  = i / steps
    local mt = 1 - t
    local x  = mt*mt*p0x + 2*mt*t*p1x + t*t*p2x
    local y  = mt*mt*p0y + 2*mt*t*p1y + t*t*p2y
    -- Dash: skip every other segment group
    local seg_idx = math.floor(i * 12 / steps) % 12
    if seg_idx < 7 then
      frame.display.line(floor(px), floor(py), floor(x), floor(y), color)
    end
    px, py = x, y
  end
end

--- APPROX: elliptical_arc as polyline
local function elliptical_arc(cx, cy, rx, ry, start_deg, end_deg, color, steps)
  if not HAS_FRAME then return end
  steps = steps or 32
  local sweep = end_deg - start_deg
  local function rad_pt(deg)
    local r = math.rad(deg)
    return cx + rx * math.cos(r), cy + ry * math.sin(r)
  end
  local x0, y0 = rad_pt(start_deg)
  for i = 1, steps do
    local x1, y1 = rad_pt(start_deg + sweep * i / steps)
    frame.display.line(floor(x0), floor(y0), floor(x1), floor(y1), color)
    x0, y0 = x1, y1
  end
end

--- APPROX: polyline
local function polyline(pts, color)
  if not HAS_FRAME then return end
  for i = 1, #pts - 1 do
    local a, b = pts[i], pts[i+1]
    frame.display.line(floor(a[1]), floor(a[2]), floor(b[1]), floor(b[2]), color)
  end
end

--- APPROX: polar_segments ring
local function polar_segments(cx, cy, r_inner, r_outer, n_segs, lit_indices, color, ghost_color)
  if not HAS_FRAME then return end
  ghost_color = ghost_color or 0x2A3C44  -- P.border_subtle
  local lit_set = {}
  for _, v in ipairs(lit_indices) do lit_set[v] = true end
  local step = (2 * math.pi) / n_segs
  for i = 0, n_segs - 1 do
    local angle = step * i - math.pi / 2
    local xi = cx + r_inner * math.cos(angle)
    local yi = cy + r_inner * math.sin(angle)
    local xo = cx + r_outer * math.cos(angle)
    local yo = cy + r_outer * math.sin(angle)
    local c = lit_set[i] and color or ghost_color
    frame.display.line(floor(xi), floor(yi), floor(xo), floor(yo), c)
  end
end

--- APPROX: radial_rays + tip bloom circles
--- Signature: (cx, cy, r_min, r_max, n_rays, color, bloom_r)
--- FIXED: was (cx,cy,count,lengths_table,color,bloom_r) — unified with frame_adapter.
local function radial_rays(cx, cy, r_min, r_max, n_rays, color, bloom_r)
  if not HAS_FRAME then return end
  bloom_r = bloom_r or 2
  local step = (2 * math.pi) / n_rays
  for i = 0, n_rays - 1 do
    local angle = step * i - math.pi / 2
    local x1 = cx + r_min * math.cos(angle)
    local y1 = cy + r_min * math.sin(angle)
    local x2 = cx + r_max * math.cos(angle)
    local y2 = cy + r_max * math.sin(angle)
    frame.display.line(floor(x1), floor(y1), floor(x2), floor(y2), color)
    -- tip bloom dot
    frame.display.circle(floor(x2), floor(y2), bloom_r, color, false)
  end
end

--- APPROX: check_glyph (2-segment polyline)
local function check_glyph(cx, cy, size, color, progressive)
  if not HAS_FRAME then return end
  progressive = progressive or 1.0
  local s   = size / 60.0
  local ax  = cx - floor(21*s);  local ay  = cy
  local bx  = cx - floor(3*s);   local by  = cy + floor(18*s)
  local ccx = cx + floor(21*s);  local ccy = cy - floor(22*s)
  frame.display.line(ax, ay, bx, by, color)
  if progressive > 0.5 then
    local frac = math.min(1.0, (progressive - 0.5) * 2)
    local ex = bx + floor((ccx - bx) * frac)
    local ey = by + floor((ccy - by) * frac)
    frame.display.line(bx, by, ex, ey, color)
  end
end

--- APPROX: shield_glyph (hexagon polyline + filled rect pause bars)
local function shield_glyph(cx, cy, size, color, pause_bars)
  if not HAS_FRAME then return end
  if pause_bars == nil then pause_bars = true end
  local hw = size / 2
  local pts = {}
  for i = 0, 5 do
    local angle = math.rad(60 * i - 30)
    pts[#pts+1] = { floor(cx + hw * math.cos(angle)),
                    floor(cy + hw * math.sin(angle)) }
  end
  pts[#pts+1] = pts[1]  -- close
  polyline(pts, color)
  if pause_bars then
    local bar_h = math.max(3, floor(size * 0.24))
    local bar_w = math.max(2, floor(size * 0.08))
    local gap   = math.max(2, floor(size * 0.07))
    frame.display.rect(cx - gap - bar_w, cy - bar_h, bar_w, bar_h * 2, color, true)
    frame.display.rect(cx + gap,          cy - bar_h, bar_w, bar_h * 2, color, true)
  end
end

--- APPROX: point_cloud_text → ghost text fallback
--- True particle rendering not feasible in Lua/frame API.
local function point_cloud_text(text, cx, cy, color)
  if not HAS_FRAME then return end
  frame.display.text(text, cx, cy, color)  -- APPROX: point_cloud_text
end

-- ---------------------------------------------------------------------------
-- Card draw functions  (clear → draw → show per card)
-- ---------------------------------------------------------------------------

local CX, CY = 128, 128

local function draw_ready()
  -- Hexagon core
  local hex_pts = {}
  for i = 0, 5 do
    local angle = math.rad(60 * i - 30)
    hex_pts[#hex_pts+1] = { floor(CX + 8 * math.cos(angle)),
                             floor(CY + 8 * math.sin(angle)) }
  end
  frame.display.polygon(hex_pts, P.memory_trace)
  -- Asymmetric partial-arc rings
  elliptical_arc(CX, CY, 24, 24, 180, 360, P.accent_memory)       -- Ring 1: 180°
  elliptical_arc(CX, CY, 36, 36, 0,   270, P.accent_memory_dim)   -- Ring 2: 270°
  elliptical_arc(CX, CY, 48, 48, 270, 360, P.border_subtle)        -- Ring 3: 90°
  -- 4 satellite dots at ring-1 endpoints
  for _, deg in ipairs({0, 90, 180, 270}) do
    local r  = math.rad(deg)
    local sx = floor(CX + 24 * math.cos(r))
    local sy = floor(CY + 24 * math.sin(r))
    frame.display.circle(sx, sy, 2, P.memory_trace, true)
  end
end

local function draw_saved_memory(card)
  -- Seal arc (near-full ring, bright 90° at top)
  elliptical_arc(CX, CY, 48, 48,   0, 360, P.accent_success, 48)
  elliptical_arc(CX, CY, 48, 48, -90,   0, P.accent_success, 12)  -- bright top
  -- Mid-draw checkmark (progressive=0.6)
  check_glyph(CX, CY - 8, 56, P.accent_success, 0.6)
  -- "SAVED" inside arc segment
  frame.display.text("SAVED", CX, CY - 42, P.accent_success)
  -- Primary label
  local label = (card and card.primary) or "Memory saved"
  frame.display.text(label, CX, CY + 22, P.text_primary)
end

local function draw_query_listening()
  -- Cardioid mic glyph
  frame.display.line(84, CY-6, 94, CY, P.memory_trace)
  frame.display.line(84, CY+6, 94, CY, P.memory_trace)
  frame.display.line(80, CY,   94, CY, P.memory_trace)
  frame.display.circle(94, CY, 2, P.memory_trace, true)
  -- Sine-envelope waveform: 32 bars as vertical lines
  local bar_count = 32
  local bar_w     = 2
  local gap       = 1
  local total_w   = bar_count * (bar_w + gap) - gap
  local start_x   = CX - math.floor(total_w / 2) + 12
  for i = 0, bar_count - 1 do
    local envelope = math.sin(math.pi * i / (bar_count - 1))
    local phase    = math.abs(math.sin(math.pi * 2 * i / bar_count * 3 + 1.2))
    local bh       = math.max(2, floor(22 * envelope * phase))
    local bx       = start_x + i * (bar_w + gap)
    frame.display.line(bx, CY - math.floor(bh/2), bx, CY + math.floor(bh/2),
                       P.accent_attention)
  end
end

local function draw_loading()
  -- Ghost rings (4 concentric, dim)
  for _, gr in ipairs({16, 28, 40, 52}) do
    elliptical_arc(CX, CY, gr, gr, 0, 360, P.border_subtle, 24)
  end
  -- Active arc on ring 3 (40px), bright 120°
  elliptical_arc(CX, CY, 40, 40,  -70,  50, P.memory_trace, 16)
  -- Fading echoes
  elliptical_arc(CX, CY, 40, 40, -100, -70, P.accent_memory,     4)
  elliptical_arc(CX, CY, 40, 40, -130,-100, P.accent_memory_dim, 2)
  -- Center pulsing dot
  frame.display.circle(CX, CY, 3, P.memory_trace,     true)
  frame.display.circle(CX, CY, 6, P.accent_memory_dim, false)
end

local function draw_object_recall(card)
  local obj    = ((card.object or card.primary or ""):upper())
  local place  = card.place    or ""
  local detail = card.detail   or ""
  local footer = card.last_seen or card.footer or ""
  local conf   = card.confidence
  -- Confidence jewel color
  local jcol = P.confidence_med
  if conf then
    if conf >= 0.75 then jcol = P.confidence_high
    elseif conf < 0.40 then jcol = P.confidence_low end
  end
  -- Eyebrow
  frame.display.text(obj, CX, 68, P.memory_trace)
  -- Memory trace: quadratic Bezier from 3-o'clock → place baseline
  bezier(228, 128, 180, 92, 128, 148, P.memory_trace)
  -- Confidence jewel (diamond via 4 lines)
  local jx, jy = 174, 112
  local jd = 4
  frame.display.line(jx,    jy-jd, jx+jd, jy,    jcol)
  frame.display.line(jx+jd, jy,    jx,    jy+jd, jcol)
  frame.display.line(jx,    jy+jd, jx-jd, jy,    jcol)
  frame.display.line(jx-jd, jy,    jx,    jy-jd, jcol)
  -- Orbit arcs around jewel
  elliptical_arc(jx, jy, 8, 8,   0, 100, jcol, 8)
  elliptical_arc(jx, jy, 8, 8, 120, 220, jcol, 8)
  elliptical_arc(jx, jy, 8, 8, 240, 340, jcol, 8)
  -- Place hero text
  frame.display.text(place, 112, 150, P.text_primary)
  -- Detail bracket
  frame.display.text("[ " .. detail .. " ]", CX, 180, P.text_secondary)
  -- Footer
  frame.display.text(footer, CX, 200, P.text_ghost)
  -- Confidence dot
  frame.display.circle(CX, 218, 3, jcol, true)
end

local function draw_commitment_recall(card)
  local person = card.person  or ""
  local task   = card.primary or card.task or ""
  local due    = card.due     or ""
  local conf   = card.confidence
  -- Header
  frame.display.text("YOU PROMISED " .. person:upper(), CX, 68, P.memory_trace)
  -- Chain links: 3 rounded rects via polyline outlines
  local link_w, link_h = 128, 18
  local lx     = CX - math.floor(link_w / 2)
  local link_ys = {84, 108, 132}
  for li, ly in ipairs(link_ys) do
    local c = (li == 3) and P.memory_trace or P.border_subtle
    polyline({
      {lx,         ly},          {lx+link_w, ly},
      {lx+link_w,  ly+link_h},   {lx,        ly+link_h}, {lx, ly}
    }, c)
  end
  -- Connector lines between links
  frame.display.line(CX, 84+link_h,  CX, 108, P.border_subtle)
  frame.display.line(CX, 108+link_h, CX, 132, P.border_subtle)
  -- Task inside second link
  frame.display.text(task, CX, 108 + math.floor(link_h/2), P.text_primary)
  -- Due inside last (bright) link
  frame.display.text(due,  CX, 132 + math.floor(link_h/2), P.memory_trace)
  -- Conf dot
  local jcol = conf and (conf >= 0.75 and P.confidence_high or
                         conf >= 0.40 and P.confidence_med  or P.confidence_low)
               or P.text_ghost
  frame.display.circle(CX, 168, 2, jcol, true)
end

local function draw_proactive_memory(card)
  local summary = card.primary or card.summary or ""
  local person  = card.person
  frame.display.text("LAST TIME HERE", CX, 62, P.text_ghost)
  -- Radial ray field: 5 rays, r_min=5, r_max=52 (unified signature)
  radial_rays(CX, CY - 10, 5, 52, 5, P.memory_trace, 2)
  frame.display.circle(CX, CY - 10, 3, P.memory_trace, true)
  frame.display.text(summary, CX, CY + 50, P.text_secondary)
  if person then
    frame.display.text("With " .. person, CX, CY + 78, P.memory_trace)
  end
end

local function draw_person_context(card)
  local name     = card.primary  or ""
  local headline = card.headline or ""
  local detail   = card.detail   or ""
  -- Polar segment ring (12 segs, 3 lit)
  polar_segments(CX, 100, 38, 56, 12, {0, 1, 2}, P.memory_trace, P.border_subtle)
  frame.display.text(name, CX, 100, P.memory_trace)
  frame.display.line(72, 116, 184, 116, P.border_subtle)
  frame.display.text(headline, CX, 140, P.text_primary)
  frame.display.text(detail,   CX, 164, P.text_secondary)
end

local function draw_privacy_paused()
  -- Breach halo (340° arc, 20° gap at top)
  elliptical_arc(CX, CY, 108, 108,  10, 350, P.privacy_danger, 48)
  elliptical_arc(CX, CY,  88,  88,   0, 360, P.privacy_danger, 32)
  -- Shield glyph (52px) with pause bars
  shield_glyph(CX, CY - 14, 52, P.privacy_danger, true)
  frame.display.text("PAUSED",             CX, CY + 32, P.privacy_caution)
  frame.display.text("Nothing is captured", CX, CY + 48, P.text_ghost)
end

local function draw_error(card)
  -- Outer amber ring
  elliptical_arc(CX, CY, 116, 116, 0, 360, P.warning_amber, 48)
  -- Equilateral triangle outline
  local tri_cy = CY - 8
  local ts = 56
  polyline({
    {CX,                        tri_cy - math.floor(ts/2)},
    {CX + floor(ts*0.577),      tri_cy + math.floor(ts/2)},
    {CX - floor(ts*0.577),      tri_cy + math.floor(ts/2)},
    {CX,                        tri_cy - math.floor(ts/2)},
  }, P.warning_amber)
  -- Exclamation: dot + line
  frame.display.circle(CX, tri_cy - 6,  2, P.warning_amber, true)
  frame.display.line(  CX, tri_cy + 2, CX, tri_cy + 14, P.warning_amber)
  -- Telemetry text
  local msg = (card and card.primary) or "Try again"
  frame.display.text(msg, CX, CY + 52, P.text_ghost)
end

local function draw_low_confidence()
  -- APPROX: point_cloud_text → ghost text
  point_cloud_text("Not sure",        CX, CY - 14, P.text_secondary)
  point_cloud_text("Try rephrasing",  CX, CY + 16, P.text_ghost)
  frame.display.circle(107, 180, 2, P.text_ghost, true)
  frame.display.circle(128, 184, 2, P.text_ghost, true)
  frame.display.circle(149, 180, 2, P.text_ghost, true)
end

-- ---------------------------------------------------------------------------
-- Dispatch table
-- ---------------------------------------------------------------------------
local CARD_DRAW = {
  ReadyCard            = function(_) draw_ready()              end,
  SavedMemoryCard      = function(c) draw_saved_memory(c)      end,
  QueryListeningCard   = function(_) draw_query_listening()    end,
  LoadingCard          = function(_) draw_loading()            end,
  ObjectRecallCard     = function(c) draw_object_recall(c)     end,
  CommitmentRecallCard = function(c) draw_commitment_recall(c) end,
  ProactiveMemoryCard  = function(c) draw_proactive_memory(c)  end,
  PersonContextCard    = function(c) draw_person_context(c)    end,
  PrivacyPausedCard    = function(_) draw_privacy_paused()     end,
  ErrorCard            = function(c) draw_error(c)             end,
  LowConfidenceCard    = function(_) draw_low_confidence()     end,
}

-- ---------------------------------------------------------------------------
-- Public API
-- ---------------------------------------------------------------------------

--- Show a card payload on the display.
--- @param card table  Card payload table (type field required)
function renderer.show_card(card)
  if not card then return end
  if not HAS_FRAME then return end
  local draw_fn = CARD_DRAW[card.type]
  if not draw_fn then return end
  -- Every render: clear → draw → show
  frame.display.clear(0x000000)
  draw_fn(card)
  frame.display.show()
  _current_card = card
end

--- Tick: called each loop iteration.
--- Redraws current card for animation (spinner, waveform, etc.)
--- FIXED: was %1 (always true / every tick). Now %3 → ~3fps on 0.1s sleep.
--- Static cards get instant display via show_card(); tick only drives animation.
function renderer.tick()
  if not HAS_FRAME then return end   -- safe no-op in Python CI
  _tick_count = _tick_count + 1
  -- Animate at ~3fps (every 3rd tick at frame.sleep(0.1) cadence)
  if _current_card and (_tick_count % 3 == 0) then
    local draw_fn = CARD_DRAW[_current_card.type]
    if draw_fn then
      frame.display.clear(0x000000)
      draw_fn(_current_card)
      frame.display.show()
    end
  end
end

--- Legacy push/flush/clear API stubs (kept for callers that use them)
function renderer.push(layer, fn) if fn then fn() end end
function renderer.flush() end
function renderer.clear() end
function renderer.bind(disp, time_fn) end  -- no-op; frame.* is global

return renderer
