--- display/dream_renderer.lua
--- Dream Mode renderer: palette shader + particle system + ghost overlay.
---
--- Called by host_comm_dream.lua when t="palette" or t="geometry" frames arrive.
--- Also exports render_world_anchor() and render_synesthesia() for card types.
---
--- Architecture
--- -----------
--- DreamRenderer maintains:
---   _particles[]   -- 24 particle positions driven by mic energy
---   _line_field[]  -- 8 line vectors driven by IMU yaw
---   _palette_t     -- current palette animation target
---
--- All state is updated on every host_comm tick (2 Hz) and rendered
--- at the display refresh rate (up to 20fps via frame.runloop).

local P    = require("display/primitives")
local PAL  = require("display/palette")
local math = math

local HAS_FRAME = (type(_G.frame) == "table")

local M = {}

-- ---------------------------------------------------------------------------
-- Constants
-- ---------------------------------------------------------------------------
local W, H       = 256, 256          -- display dimensions
local N_PARTICLES = 24
local N_LINES     = 8
local CX, CY      = W/2, H/2

-- ---------------------------------------------------------------------------
-- State
-- ---------------------------------------------------------------------------
local _particles  = {}
local _line_angles = {}
local _scatter_t   = 0
local _scatter_dur = 0
local _palette_target = {}    -- list of {idx, y, cb, cr} from mic reactor
local _geo_intensity  = 0.0
local _geo_mode       = "rotate"

-- Seed particles
for i = 1, N_PARTICLES do
  _particles[i] = {
    x   = CX + (math.random() - 0.5) * W * 0.8,
    y   = CY + (math.random() - 0.5) * H * 0.8,
    vx  = (math.random() - 0.5) * 0.8,
    vy  = (math.random() - 0.5) * 0.8,
    r   = math.random(1, 3),
    col = PAL.accent_memory,
  }
end

-- Seed line angles
for i = 1, N_LINES do
  _line_angles[i] = (i - 1) * math.pi / N_LINES
end

-- ---------------------------------------------------------------------------
-- Palette shift
-- ---------------------------------------------------------------------------

function M.apply_palette_shift(colors)
  -- colors: list of {idx, y, cb, cr}
  if not HAS_FRAME then return end
  for _, c in ipairs(colors) do
    frame.display.assign_color_ycbcr(
      c.idx,
      c.y  or 512,
      c.cb or 512,
      c.cr or 512
    )
  end
end

-- ---------------------------------------------------------------------------
-- Particle system
-- ---------------------------------------------------------------------------

function M.update_particles(intensity, mode)
  local scatter = (mode == "scatter")
  for _, p in ipairs(_particles) do
    if scatter then
      -- Explode outward from centre
      local dx = p.x - CX
      local dy = p.y - CY
      local dist = math.sqrt(dx*dx + dy*dy) + 0.1
      p.vx = p.vx + (dx/dist) * intensity * 4
      p.vy = p.vy + (dy/dist) * intensity * 4
    else
      -- Gentle drift with damping
      p.vx = p.vx * 0.92
      p.vy = p.vy * 0.92
    end
    p.x = p.x + p.vx
    p.y = p.y + p.vy
    -- Wrap around display edges
    if p.x < 0   then p.x = W end
    if p.x > W   then p.x = 0 end
    if p.y < 0   then p.y = H end
    if p.y > H   then p.y = 0 end
  end
end

function M.draw_particles()
  if not HAS_FRAME then return end
  for _, p in ipairs(_particles) do
    P.dot(p.x, p.y, p.r, p.col)
  end
end

-- ---------------------------------------------------------------------------
-- Line field (IMU-driven)
-- ---------------------------------------------------------------------------

function M.update_line_field(yaw_rate, intensity)
  local rotate_speed = yaw_rate * 0.008 * intensity
  for i = 1, N_LINES do
    _line_angles[i] = _line_angles[i] + rotate_speed
  end
end

function M.draw_line_field()
  if not HAS_FRAME then return end
  local len = 40 + _geo_intensity * 60
  for i, angle in ipairs(_line_angles) do
    local x1 = CX + math.cos(angle) * len
    local y1 = CY + math.sin(angle) * len
    local x2 = CX - math.cos(angle) * len
    local y2 = CY - math.sin(angle) * len
    frame.display.line(
      math.floor(x1), math.floor(y1),
      math.floor(x2), math.floor(y2),
      PAL.text_ghost
    )
  end
end

-- ---------------------------------------------------------------------------
-- Geometry command handler (called from host_comm)
-- ---------------------------------------------------------------------------

function M.on_geometry(cmd)
  _geo_mode      = cmd.mode      or "rotate"
  _geo_intensity = cmd.intensity or 0.0
  local yr = cmd.yaw_rate   or 0.0
  local pr = cmd.pitch_rate or 0.0
  M.update_particles(_geo_intensity, _geo_mode)
  M.update_line_field(yr, _geo_intensity)
end

-- ---------------------------------------------------------------------------
-- Ghost anchor renderer
-- ---------------------------------------------------------------------------

function M.render_world_anchor(card)
  -- Renders at bottom of display, very dim (text_ghost color)
  if not HAS_FRAME then return end
  local summary = card.primary or ""
  local detail  = card.detail  or ""
  if #summary > 32 then summary = summary:sub(1, 31) .. "\u2026" end
  P.text_center(CX, 210, "\u2022 MEMORY ECHO \u2022", "sm", PAL.text_ghost)
  P.text_center(CX, 226, summary,                      "sm", PAL.text_ghost)
  if detail ~= "" then
    P.text_center(CX, 242, detail, "sm", PAL.text_ghost)
  end
end

-- ---------------------------------------------------------------------------
-- Synesthesia card renderer
-- ---------------------------------------------------------------------------

function M.render_synesthesia(card)
  -- 6-word VLM description in hero position, dream palette color
  if not HAS_FRAME then return end
  local desc = card.primary or ""
  P.text_center(CX, 100, "DREAM", "sm", PAL.accent_memory)
  -- Separator
  frame.display.line(64, 116, 192, 116, PAL.border_subtle)
  P.text_center(CX, 148, desc, "md", PAL.text_primary)
end

-- ---------------------------------------------------------------------------
-- Full dream frame (called from main runloop in dream mode)
-- ---------------------------------------------------------------------------

function M.draw_frame()
  if not HAS_FRAME then return end
  -- 1. Line field (background, drawn first)
  M.draw_line_field()
  -- 2. Particles (midground)
  M.draw_particles()
  -- NOTE: ghost anchor and synesthesia overlays are drawn by the card
  -- renderer when their respective cards are in the queue.
end

return M
