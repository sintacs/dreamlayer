--- ble/host_comm_stasis.lua
--- Stasis extensions to the host_comm BLE message handler (docs/STASIS.md).
---
--- Adds one handler:
---   t = "stasis"   {mode="freeze"|"offer"|"clear"} → shutter + ribbon
---                  (display/stasis.lua draws; replay content arrives as
---                  ordinary TimeScrubNodeCard cards through the queue)
---
--- Wire into the main host_comm dispatch table:
---   local SC = require("ble/host_comm_stasis")
---   SC.register(dispatch_table)

local Stasis = require("display.stasis")

local M = {}

function M.register(dispatch)
  dispatch["stasis"] = M.on_stasis
end

function M.on_stasis(msg)
  Stasis.on_stasis(msg)
end

return M
