--- cinema_v2_prototypes/proto_testimony.lua
--- Phase 3 scratch: the Testimony Thread (docs/cinema_v2/testimony.md).
--- One arc at r=48, nine 40-degree slots clockwise from 12; truthful =
--- continuous, deceptive = torn (3 dashes, ±2px radial jitter),
--- insufficient = empty slot. Verdict word + capsule + confidence dot.

local L = require("display.cinema_v2_prototypes.proto_lib")
local P = require("display.palette")

local M = {}

local CX, CY = L.CX, L.CY
local fl = L.fl

-- Iteration 2 (prototype review pass 1): r=48 put the thread under the
-- verdict capsule — the armor erased slots 3 and 7, v1's gauge disease
-- reborn. r=64 clears the widest verdict word with margin.
local THREAD_R  = 64
local SLOT_DEG  = 40
local STAGE_MS  = 80
local TEAR_PX   = 3

local DIR_COLOR = {
  truthful  = P.accent_success,
  deceptive = P.accent_attention,
}

local SCENARIOS = {
  elevated_mixed = {
    verdict = "ELEVATED", confidence = 0.72,
    stages = {
      { confidence = 0.85, direction = "truthful" },     -- face
      { confidence = 0.60, direction = "deceptive" },    -- AU
      { confidence = 0.75, direction = "truthful" },     -- voice
      { confidence = 0.80, direction = "deceptive" },    -- prosody
      { confidence = 0.55, direction = "truthful" },     -- linguistic
      { confidence = 0.00, direction = "insufficient" }, -- narrative
      { confidence = 0.70, direction = "deceptive" },    -- fusion
      { confidence = 0.65, direction = "truthful" },     -- aggregate
      { confidence = 0.72, direction = "truthful" },     -- verdict
    },
  },
  clean_truthful = {
    verdict = "CONSISTENT", confidence = 0.88,
    stages = {
      { confidence = 0.90, direction = "truthful" },
      { confidence = 0.85, direction = "truthful" },
      { confidence = 0.80, direction = "truthful" },
      { confidence = 0.88, direction = "truthful" },
      { confidence = 0.75, direction = "truthful" },
      { confidence = 0.70, direction = "truthful" },
      { confidence = 0.92, direction = "truthful" },
      { confidence = 0.86, direction = "truthful" },
      { confidence = 0.88, direction = "truthful" },
    },
  },
  stranger_insufficient = {
    verdict = "UNKNOWN", confidence = 0.20,
    stages = {
      { confidence = 0.30, direction = "truthful" },
      { confidence = 0.00, direction = "insufficient" },
      { confidence = 0.00, direction = "insufficient" },
      { confidence = 0.00, direction = "insufficient" },
      { confidence = 0.25, direction = "insufficient" },
      { confidence = 0.00, direction = "insufficient" },
      { confidence = 0.00, direction = "insufficient" },
      { confidence = 0.00, direction = "insufficient" },
      { confidence = 0.20, direction = "insufficient" },
    },
  },
}

local function draw_slot_ticks()
  for i = 0, 8 do
    local deg = -90 + i * SLOT_DEG
    L.radial_tick(deg, THREAD_R - 2, THREAD_R + 2, P.border_subtle)
  end
end

local function draw_stage(i, stage, fraction)
  -- fraction in [0,1]: how much of this stage's stroke has accumulated
  local dir = stage.direction or "insufficient"
  if dir == "insufficient" then return end
  local conf = math.max(0, math.min(1, stage.confidence or 0))
  local a0 = -90 + (i - 1) * SLOT_DEG + 2           -- 2 deg inset from tick
  local full = conf * (SLOT_DEG - 4)
  local span = full * math.max(0, math.min(1, fraction))
  if span <= 1 then return end
  local color = DIR_COLOR[dir]
  if dir == "truthful" then
    L.arc(CX, CY, THREAD_R, a0, a0 + span, color, 12)
  else
    -- torn: 3 dashes, alternating radial offset -TEAR/+TEAR/-TEAR
    local dash = span / 4
    local offsets = { -TEAR_PX, TEAR_PX, -TEAR_PX }
    for d = 1, 3 do
      local da0 = a0 + (d - 1) * (dash + dash / 2)
      local da1 = math.min(da0 + dash, a0 + span)
      if da1 > da0 then
        L.arc(CX, CY, THREAD_R + offsets[d], da0, da1, color, 4)
      end
    end
  end
end

--- Render at t_ms since ENTER. Ripple (0-400ms) is the surviving S5 and
--- not re-prototyped here; the thread accumulates 400..1120ms.
--- t_ms = nil renders the settled hold state.
function M.render(name, t_ms)
  local sc = assert(SCENARIOS[name], "unknown testimony scenario: " .. tostring(name))
  frame.display.clear(0x000000)

  draw_slot_ticks()
  for i, stage in ipairs(sc.stages) do
    local fraction = 1
    if t_ms then
      local begun = (t_ms - 400) - (i - 1) * STAGE_MS
      fraction = math.max(0, math.min(1, begun / STAGE_MS))
    end
    draw_stage(i, stage, fraction)
  end

  -- verdict word appears with the ripple landing (before the thread)
  if not t_ms or t_ms >= 400 then
    local half_w = fl(#sc.verdict * 8 / 2) + 5
    frame.display.rect(CX - half_w, CY - 15, half_w * 2, 19, P.background, true)
    frame.display.text(sc.verdict, CX, CY - 6, P.text_primary)
    local conf = sc.confidence
    local jcol = (conf >= 0.75 and P.confidence_high)
              or (conf >= 0.40 and P.confidence_med)
              or  P.confidence_low
    frame.display.circle(CX, CY + 16, 3, jcol, true)
  end
  frame.display.show()
end

M.scenarios = { "clean_truthful", "elevated_mixed", "stranger_insufficient" }

return M
