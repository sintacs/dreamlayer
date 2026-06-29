--- main.lua : Memoscape Halo boot entry point.
--- Ported to real Brilliant Labs frame.* API.
--- Loads frame_adapter first so all downstream modules can use either
--- frame.* directly or the _G.halo compatibility shim.

require("compat.frame_adapter")   -- builds _G.halo; safe if frame absent

local renderer      = require("display.renderer")
local cards         = require("display.cards")
local host_comm     = require("ble.host_comm")
local state_machine = require("app.state_machine")
local session       = require("app.session")
local E             = require("app.events")

local HAS_FRAME = (type(_G.frame) == "table")

local BUTTON_MAP = {
  single = E.EVENTS.single_click,
  double = E.EVENTS.double_click,
  long   = E.EVENTS.long_press,
}

local function on_ble_data(raw)
  if not raw or raw == "" then return end
  local msg = host_comm.on_receive(raw)
  if not msg then return end
  local t = msg.t
  if t == "button" then
    local ev = BUTTON_MAP[msg.ev]
    if ev then state_machine.dispatch(ev) end
  elseif t == "imu_tap" then
    state_machine.dispatch(E.EVENTS.imu_tap)
  elseif t == "connect" then
    session.start(0)
    state_machine.dispatch(E.EVENTS.host_connected)
  elseif t == "disconnect" then
    session.end_session()
    state_machine.dispatch(E.EVENTS.host_disconnected)
  else
    host_comm.on_message(msg)
  end
end

local function boot()
  if HAS_FRAME then
    frame.bluetooth.receive_callback(on_ble_data)
    frame.button.single(function() state_machine.dispatch(E.EVENTS.single_click) end)
    frame.button.double(function() state_machine.dispatch(E.EVENTS.double_click) end)
    frame.button.long(function()   state_machine.dispatch(E.EVENTS.long_press)   end)
    frame.imu.tap_callback(function() state_machine.dispatch(E.EVENTS.imu_tap)   end)
  end
  state_machine.init(renderer, nil, function(old, new, ev) end)
  state_machine.dispatch(E.EVENTS.startup)
  renderer.show_card(cards.ready())
  print(0)  -- signal host: Lua ready
end

boot()

-- Main loop: break cleanly when emulator stops rather than spamming console.
while true do
  local ok, err = pcall(function()
    renderer.tick()
    if HAS_FRAME then
      frame.sleep(0.05)
    end
  end)
  if not ok then
    -- "Emulator stopped" is a normal shutdown signal, not a real error.
    local msg = tostring(err or "")
    if msg:find("Emulator stopped") or msg:find("stopped") then
      break  -- exit cleanly, no spam
    end
    print("[memoscape] error: " .. msg)
  end
end
