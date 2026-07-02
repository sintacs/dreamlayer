--- cinema_v2_prototypes/proto_promise_arc.lua
--- Phase 3 scratch: the Promise Arc state grammar
--- (docs/cinema_v2/promise_arc.md). Renders the ladder, radial stacking,
--- and a shattered promise aging into the past side.

local L = require("display.cinema_v2_prototypes.proto_lib")

local M = {}

local SCENARIOS = {
  -- all five states across the future side, one glance
  ladder = {
    marks = {
      { deg = -90 - 140, kind = "promise", pstate = "blooming"  },
      { deg = -90 - 105, kind = "promise", pstate = "healthy"   },
      { deg = -90 - 70,  kind = "promise", pstate = "drifting"  },
      { deg = -90 - 40,  kind = "promise", pstate = "cracking"  },
      { deg = -90 - 15,  kind = "promise", pstate = "shattered" },
      -- a little past-side context so the dial reads as a day
      { deg = -90 + 30, kind = "memory", luma = 1 },
      { deg = -90 + 70, kind = "memory", luma = 2 },
    },
    notch_len = 8,
  },

  -- three promises due the same hour: radial stack at r 104/100/96
  stacked = {
    marks = {
      { deg = -90 - 60, kind = "promise", pstate = "healthy", stack = 0 },
      { deg = -90 - 60, kind = "promise", pstate = "healthy", stack = 1 },
      { deg = -90 - 60, kind = "promise", pstate = "drifting", stack = 2 },
      { deg = -90 + 45, kind = "memory", luma = 1 },
    },
    notch_len = 8,
  },

  -- an unresolved promise whose due time passed 2h ago: cold tick on the
  -- past side, aging clockwise with the day
  shattered_past = {
    marks = {
      { deg = -90 + 60, kind = "promise", pstate = "shattered" },
      { deg = -90 + 20, kind = "memory", luma = 2 },
      { deg = -90 + 90, kind = "memory", luma = 1 },
      { deg = -90 - 80, kind = "promise", pstate = "blooming" },
    },
    notch_len = 8,
  },
}

function M.render(name)
  local state = assert(SCENARIOS[name], "unknown promise scenario: " .. tostring(name))
  frame.display.clear(0x000000)
  L.draw_horizon(state)
  frame.display.show()
end

M.scenarios = { "ladder", "stacked", "shattered_past" }

return M
