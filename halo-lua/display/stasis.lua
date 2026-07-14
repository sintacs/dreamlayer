--- display/stasis.lua
--- Stasis affordances: the shutter and the ribbon (docs/STASIS.md).
---
--- Three visual states, all deliberately sub-card — nothing to read,
--- nothing to dismiss, nothing that competes for the queue:
---
---   freeze  the edge of vision dims for ~400ms, like a camera shutter
---           closing slowly, and a small ribbon glyph settles into the
---           periphery and fades. The whole affordance is an
---           acknowledgment: *kept*. Total cost 400ms, zero words.
---   offer   the ribbon reappears and glows softly — the wearer returned
---           to a frozen context. It offers; it never plays unbidden.
---           Unaccepted, it fades on its own.
---   clear   everything off (a resume just played, or the host says so).
---
--- Driven by {t="stasis", mode=...} messages (ble/host_comm_stasis.lua);
--- drawn from main.lua's render loop after the card layer, so the glyph
--- rides over whatever else is showing without owning the display.

local P = require("display.palette")

local M = {}

-- timings (ms)
local SHUTTER_MS     = 400     -- the slow blink
local RIBBON_SETTLE_MS = 2200  -- freeze: ribbon settles, then fades
local OFFER_GLOW_MS  = 10000   -- offer: soft glow, then gives up quietly

-- where the ribbon lives: lower periphery, off the text axes
local RIBBON_X, RIBBON_Y = 206, 206

-- state: mode + t0 latched on the first draw after a message (handlers
-- have no clock; the render loop does — same convention as dream_renderer)
local _mode  = nil    -- "freeze" | "offer" | nil
local _t0    = nil

-- ---------------------------------------------------------------------------
-- Message handling
-- ---------------------------------------------------------------------------

function M.on_stasis(msg)
  local mode = msg and msg.mode
  if mode == "freeze" or mode == "offer" then
    _mode, _t0 = mode, nil          -- t0 latches on next draw
  elseif mode == "clear" then
    _mode, _t0 = nil, nil
  end
end

function M.is_active()
  return _mode ~= nil
end

-- test/introspection seam
function M.state()
  return _mode
end

-- ---------------------------------------------------------------------------
-- Drawing
-- ---------------------------------------------------------------------------

local function clamp(v, lo, hi) return math.max(lo, math.min(hi, v)) end

--- The ribbon: a small bookmark glyph — two verticals, a notch, a tail dot.
--- `lum` 0..1 picks the color family: settled (ghost) vs glowing (memory).
local function draw_ribbon(lum)
  local col = (lum > 0.5) and P.accent_memory or P.text_ghost
  local x, y = RIBBON_X, RIBBON_Y
  frame.display.line(x - 3, y - 8, x - 3, y + 6, col)
  frame.display.line(x + 3, y - 8, x + 3, y + 6, col)
  frame.display.line(x - 3, y - 8, x + 3, y - 8, col)
  -- the notch: the two rails fold to a point, like a ribbon's cut tail
  frame.display.line(x - 3, y + 6, x, y + 2, col)
  frame.display.line(x + 3, y + 6, x, y + 2, col)
end

--- The shutter: concentric dark rings at the rim, closing inward then
--- releasing. No alpha on this display — "dim" is drawn darkness.
local function draw_shutter(t)
  -- t 0..1 over SHUTTER_MS: rings sweep in to ~radius 116 and let go
  local reach = math.floor(12 * (1.0 - math.abs(2 * t - 1)))  -- 0→12→0
  for i = 0, reach do
    frame.display.circle(128, 128, 127 - i, P.surface, false)
  end
end

function M.draw(now_ms)
  if _mode == nil then return end
  if _t0 == nil then _t0 = now_ms end
  local dt = now_ms - _t0

  if _mode == "freeze" then
    if dt <= SHUTTER_MS then
      draw_shutter(clamp(dt / SHUTTER_MS, 0, 1))
    end
    if dt <= SHUTTER_MS + RIBBON_SETTLE_MS then
      -- settle bright, fade to ghost over the settle window
      local ft = clamp((dt - SHUTTER_MS) / RIBBON_SETTLE_MS, 0, 1)
      draw_ribbon(1.0 - ft)
    else
      _mode, _t0 = nil, nil          -- fully faded; dormant = invisible
    end

  elseif _mode == "offer" then
    if dt <= OFFER_GLOW_MS then
      -- a slow breath (~2.4s cycle) between ghost and glow — an
      -- invitation in the periphery, never a notification LED
      local pulse = (math.sin(dt / 1200 * math.pi) + 1) / 2
      draw_ribbon(pulse)
    else
      _mode, _t0 = nil, nil          -- unaccepted offers give up quietly
    end
  end
end

return M
