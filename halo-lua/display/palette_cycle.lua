--- display/palette_cycle.lua
--- Palette cycling: motion by recolouring, not redrawing.
---
--- The demoscene trick. Paint a region once using a run of reserved
--- dynamic slots (a "ramp"); then, every frame, rotate which colour each
--- slot holds. The pixels never move and are never redrawn — the colours
--- flow through them. On the 4bpp Halo panel this buys rich, continuous
--- motion (aurora drift, waterfalls, shimmer) at the cost of a handful of
--- frame.display.assign_color_ycbcr calls per frame and zero geometry.
--- No pixel writes, no BLE — it runs entirely on-device.
---
--- This generalises what Dream Mode already does by hand to the four sky
--- slots. It cycles colours among *existing* reserved slots (the 1-6 bank
--- is full), so a cycle is defined over slot *names*, in draw order.
---
--- Smooth mode interpolates each slot between two ramp stops in YCbCr, so
--- even a 4-colour ramp flows continuously rather than stepping. Motion is
--- a pure function of now_ms (deterministic); reduce_motion freezes the
--- cycle to its base arrangement, colours intact.
---
--- Public API:
---   PaletteCycle.new(names, ramp, opts) -> cycle
---       names : list of reserved dynamic-slot names, in draw order
---       ramp  : list of 0xRRGGBB stops (defaults to each name's base)
---       opts  : { period_ms = 4000, smooth = true }
---   cycle:tick(now_ms [, opts])   advance from the clock (opts.reduce_motion)
---   cycle:advance(offset)         set the cycle to a ramp-step offset (float)
---   cycle:restore()               snap to the base arrangement (offset 0)
---   cycle:slots() / cycle:names() introspection (tests)

-- Match dream_renderer's require string exactly: Lua keys package.loaded by
-- the literal module name, so "display/palette" and "display.palette" would
-- be two separate palette instances with separate slot reservations. The
-- sky slots live on the slash instance, so we take that one.
local PAL = require("display/palette")

local HAS_FRAME = (type(_G.frame) == "table")

local M = {}
M.__index = M

local DEFAULT_PERIOD_MS = 4000

local function clamp1023(v)
  if v < 0 then return 0 elseif v > 1023 then return 1023 end
  return math.floor(v + 0.5)
end

--- Build a cycle over reserved slot `names`. Colours come from `ramp`
--- (0xRRGGBB stops) or, when omitted, each slot's own base colour.
function M.new(names, ramp, opts)
  assert(type(names) == "table" and #names >= 2,
         "palette_cycle needs at least two slot names")
  opts = opts or {}
  local self = setmetatable({}, M)
  self._names = names
  self._slots = {}
  for i, name in ipairs(names) do
    self._slots[i] = PAL.dynamic_slot(name)
    assert(self._slots[i], "palette_cycle: slot '" .. tostring(name) ..
           "' is not reserved")
  end

  -- The ramp defaults to the slots' own base colours, so a bare cycle over
  -- the sky slots simply drifts their existing palette around the ring.
  ramp = ramp or {}
  if #ramp == 0 then
    for _, name in ipairs(names) do ramp[#ramp + 1] = PAL.dynamic_color(name) end
  end
  assert(#ramp >= 2, "palette_cycle ramp needs at least two stops")

  -- Pre-convert the ramp to YCbCr once; cycling only ever interpolates.
  self._ycbcr = {}
  for i, hex in ipairs(ramp) do
    local y, cb, cr = PAL.hex_to_ycbcr(hex)
    self._ycbcr[i] = { y, cb, cr }
  end
  self._m = #self._ycbcr
  self._period = opts.period_ms or DEFAULT_PERIOD_MS
  self._smooth = opts.smooth ~= false
  return self
end

--- Sample the ramp at fractional position `pos` (wraps over the ramp).
--- Smooth: interpolate between adjacent stops in YCbCr. Stepped: nearest.
function M:_sample(pos)
  local m = self._m
  pos = pos % m
  if pos < 0 then pos = pos + m end
  local i0 = math.floor(pos)
  local a = self._ycbcr[i0 + 1]
  if not self._smooth then
    return a[1], a[2], a[3]
  end
  local frac = pos - i0
  local b = self._ycbcr[((i0 + 1) % m) + 1]
  return a[1] + (b[1] - a[1]) * frac,
         a[2] + (b[2] - a[2]) * frac,
         a[3] + (b[3] - a[3]) * frac
end

--- Set the cycle to ramp-step `offset` (a float). Slot i shows the ramp
--- sampled at offset + (i-1): the ramp laid across the slots, slid by
--- offset. offset 0 is the base arrangement (slot i -> ramp[i]).
function M:advance(offset)
  if not HAS_FRAME then return end
  for i = 1, #self._slots do
    local y, cb, cr = self:_sample(offset + (i - 1))
    frame.display.assign_color_ycbcr(self._slots[i],
      clamp1023(y), clamp1023(cb), clamp1023(cr))
  end
end

--- Advance from the wall clock. One full ramp traversal per period_ms.
--- reduce_motion holds the base arrangement — colour without movement.
function M:tick(now_ms, opts)
  if opts and opts.reduce_motion then
    self:advance(0)
    return
  end
  local offset = ((now_ms or 0) / self._period) * self._m
  self:advance(offset)
end

--- Snap back to the base arrangement (slot i -> ramp[i]).
function M:restore()
  self:advance(0)
end

function M:slots() return self._slots end
function M:names() return self._names end
function M:period_ms() return self._period end

return M
