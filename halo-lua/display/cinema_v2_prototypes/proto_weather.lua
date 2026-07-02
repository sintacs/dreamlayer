--- cinema_v2_prototypes/proto_weather.lua
--- Phase 3 scratch: Weather Through the Horizon (docs/cinema_v2/weather.md).
--- Dream mode as light-change over the shared terrain: floor-tier memory
--- marks, full promise arc, rim-tangent line field (r 60-90), particles
--- clipped to r<=96, anchor echo with provenance brighten.

local L = require("display.cinema_v2_prototypes.proto_lib")
local P = require("display.palette")
local E = require("lib.easing")

local M = {}

local CX, CY = L.CX, L.CY
local fl = L.fl

local DAY = {
  marks = {
    { deg = -90 + 135, kind = "memory", luma = 1, extra_len = 2 },
    { deg = -90 + 100, kind = "memory", luma = 1 },
    { deg = -90 + 60,  kind = "memory", luma = 2 },
    { deg = -90 + 20,  kind = "memory", luma = 2 },
    { deg = -90 + 84,  kind = "person", luma = 2 },
    { deg = -90 - 45,  kind = "promise", pstate = "healthy" },
    { deg = -90 - 120, kind = "promise", pstate = "drifting" },
  },
  notch_len = 8,
}

-- Deterministic rim-tangent field: 12 vectors sampled on a ring band
-- r in [60,90], tangentially biased with value-noise wobble. On the real
-- system these arrive precomputed via {t="line_field"}; the prototype
-- reproduces the *composition* the host sampler will aim for.
local function field_vectors(seed)
  -- Iteration 2 (review pass 1): even 30-degree spacing + mild wobble read
  -- as a broken decagon, not weather. Spacing/radius/length variance all
  -- widened so the band reads as flow, not geometry.
  local vecs = {}
  for i = 1, 12 do
    local base = (i - 1) * 30 + E.perlin1d(seed + i * 7.13) * 26
    local r    = 74 + E.perlin1d(seed + i * 13.7) * 18
    local rad  = math.rad(base)
    local cxp, cyp = CX + r * math.cos(rad), CY + r * math.sin(rad)
    -- tangent direction, wobbled +-34 deg
    local tang = base + 90 + E.perlin1d(seed + i * 3.31) * 34
    local trad = math.rad(tang)
    local len  = 15 + E.perlin1d(seed + i * 5.77) * 9
    vecs[i] = {
      fl(cxp - len * math.cos(trad)), fl(cyp - len * math.sin(trad)),
      fl(cxp + len * math.cos(trad)), fl(cyp + len * math.sin(trad)),
    }
  end
  return vecs
end

-- Deterministic particles, wrap territory clipped to r<=96.
local function particles(seed, n)
  local pts = {}
  local i = 0
  local k = 0
  while i < n and k < n * 8 do
    k = k + 1
    local x = 128 + E.perlin1d(seed + k * 2.09) * 120
    local y = 128 + E.perlin1d(seed + k * 4.73 + 31) * 120
    local dx, dy = x - CX, y - CY
    if dx * dx + dy * dy <= 96 * 96 then
      i = i + 1
      pts[i] = { fl(x), fl(y), (k % 3 == 0) and 2 or 1 }
    end
  end
  return pts
end

--- Memory-mode idle for comparison: horizon only.
function M.render_memory_idle()
  frame.display.clear(0x000000)
  L.draw_horizon(DAY)
  frame.display.show()
end

--- Dream frame. mood = "quiet" | "storm" (palette weather proxied by
--- token choice here; live YCbCr slot motion is exercised in integration).
function M.render_dream(mood)
  frame.display.clear(0x000000)

  -- terrain: floor-tier memory marks, promises full, notch breathing
  L.draw_horizon({ marks = DAY.marks, notch_len = 9, dim = true })

  -- weather: line field bends around the rim
  local sky = (mood == "storm") and P.accent_attention or P.accent_memory_dim
  for _, v in ipairs(field_vectors((mood == "storm") and 40 or 7)) do
    frame.display.line(v[1], v[2], v[3], v[4], sky)
  end

  -- particles (Air tier), clipped inside r=96
  for _, pt in ipairs(particles(11, 24)) do
    frame.display.circle(pt[1], pt[2], pt[3], P.border_subtle, true)
  end
  frame.display.show()
end

--- Dream frame + world-anchor echo with provenance brighten: the ghost
--- rows keep v1's treatment (settled state shown); the anchor's horizon
--- mark at its original hour is lit to full while the echo is visible.
function M.render_anchor_echo()
  frame.display.clear(0x000000)

  local marks = {}
  for _, mk in ipairs(DAY.marks) do
    local c = {}
    for k, v in pairs(mk) do c[k] = v end
    marks[#marks + 1] = c
  end
  -- the echo is about the lunch memory at +60deg past -> lit full + longer
  for _, mk in ipairs(marks) do
    if mk.deg == -90 + 60 then mk.luma = 2; mk.extra_len = 3 end
  end
  L.draw_horizon({ marks = marks, notch_len = 8, dim = true })
  -- keep the lit mark on top of the dim pass
  L.draw_mark({ deg = -90 + 60, kind = "memory", luma = 2, extra_len = 3 })

  for _, v in ipairs(field_vectors(7)) do
    frame.display.line(v[1], v[2], v[3], v[4], P.accent_memory_dim)
  end
  for _, pt in ipairs(particles(11, 18)) do
    frame.display.circle(pt[1], pt[2], pt[3], P.border_subtle, true)
  end

  -- ghost rows (settled Ghost Wake state), v1 geometry: 192/208/222
  frame.display.text("\xE2\x80\xA2 MEMORY ECHO \xE2\x80\xA2", CX, 192, P.text_ghost)
  frame.display.text("Keys at kitchen count\xE2\x80\xA6", CX, 208, P.text_ghost)
  frame.display.text("Kitchen \xE2\x80\xA2 12:30", CX, 222, P.text_ghost)
  frame.display.show()
end

return M
