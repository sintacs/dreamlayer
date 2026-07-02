--- cinema_v2_prototypes/proto_horizon.lua
--- Phase 3 scratch: the Horizon's resting states (docs/cinema_v2/horizon.md).
--- Each scenario renders one full frame; the Python driver exports PNGs.

local L = require("display.cinema_v2_prototypes.proto_lib")

local M = {}

-- A believable Tuesday, 14:30. Past (clockwise from top): standup cluster
-- ~4.5h ago, lunch ~2h ago, recent person moment. Future: two promises.
local TYPICAL_DAY = {
  marks = {
    -- standup cluster (merged: extra length), ~4.5h ago -> +45deg past
    { deg = -90 + 135, kind = "memory", luma = 1, extra_len = 2 },
    { deg = -90 + 128, kind = "memory", luma = 1 },
    -- misc morning
    { deg = -90 + 100, kind = "memory", luma = 1 },
    { deg = -90 + 84,  kind = "person", luma = 2 },
    -- lunch, 2h ago
    { deg = -90 + 60,  kind = "memory", luma = 2 },
    { deg = -90 + 55,  kind = "memory", luma = 1 },
    -- 40 min ago, high confidence
    { deg = -90 + 20,  kind = "memory", luma = 2 },
    -- just now
    { deg = -90 + 4,   kind = "memory", luma = 2 },
    -- promises: invoice due in ~1.5h (healthy), review due in 4h (blooming)
    { deg = -90 - 45,  kind = "promise", pstate = "healthy" },
    { deg = -90 - 120, kind = "promise", pstate = "blooming" },
    -- older-than-window compression
    { kind = "elder" },
  },
  notch_len = 8,
}

local SCENARIOS = {
  typical_day = TYPICAL_DAY,

  quiet_morning = {
    marks = {
      { deg = -90 + 30, kind = "memory", luma = 1 },
      { deg = -90 + 8,  kind = "memory", luma = 2 },
    },
    notch_len = 9,
  },

  empty_boot = { marks = {}, notch_len = 7 },

  stale_link = (function()
    -- staleness rule: every mark one luma tier down, notch unaffected
    local s = { marks = {}, notch_len = 8 }
    for _, mk in ipairs(TYPICAL_DAY.marks) do
      local clone = {}
      for k, v in pairs(mk) do clone[k] = v end
      if clone.luma and clone.luma > 0 then clone.luma = clone.luma - 1 end
      s.marks[#s.marks + 1] = clone
    end
    return s
  end)(),

  paused = { marks = {}, notch_len = 8, paused = true },

  dream_dim = (function()
    local s = { marks = TYPICAL_DAY.marks, notch_len = 8, dim = true }
    return s
  end)(),
}

function M.render(name)
  local state = assert(SCENARIOS[name], "unknown horizon scenario: " .. tostring(name))
  frame.display.clear(0x000000)
  L.draw_horizon(state)
  frame.display.show()
end

M.scenarios = {}
for k in pairs(SCENARIOS) do M.scenarios[#M.scenarios + 1] = k end
table.sort(M.scenarios)

return M
