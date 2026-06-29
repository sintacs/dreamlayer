--- main.lua : Memoscape Halo boot entry point.
--- Ported to real Brilliant Labs frame.* API.

require("compat.frame_adapter")

local renderer      = require("display.renderer")
local cards         = require("display.cards")
local host_comm     = require("ble.host_comm")
local MT            = require("ble.message_types")
local state_machine = require("app.state_machine")
local session       = require("app.session")
local E             = require("app.events")

local HAS_FRAME = (type(_G.frame) == "table")

-- ---------------------------------------------------------------------------
-- Inbound BLE dispatch
-- msg is a fully decoded table from host_comm.on_receive()
-- ---------------------------------------------------------------------------
local function process_inbound(msg)
  if not msg or not msg.t then return end
  local t = msg.t

  if t == MT.BUTTON then
    local ev_map = {
      [MT.BTN_SINGLE] = E.EVENTS.single_click,
      [MT.BTN_DOUBLE] = E.EVENTS.double_click,
      [MT.BTN_LONG]   = E.EVENTS.long_press,
    }
    local ev = ev_map[msg.ev]
    if ev then state_machine.dispatch(ev) end

  elseif t == MT.IMU_TAP then
    state_machine.dispatch(E.EVENTS.imu_tap)

  elseif t == MT.CONNECT then
    session.start(0)
    state_machine.dispatch(E.EVENTS.host_connected)

  elseif t == MT.DISCONNECT then
    session.end_session()
    state_machine.dispatch(E.EVENTS.host_disconnected)

  elseif t == MT.CARD then
    state_machine.set_card(msg.payload or msg)

  elseif t == MT.COMMAND then
    state_machine.set_command(msg)

  elseif t == MT.EVENT then
    if msg.name then
      state_machine.dispatch(msg.name, msg)
    end

  else
    host_comm.on_message(msg)
  end
end

-- Raw BLE callback: feed every chunk through host_comm framing reassembler.
-- host_comm.on_receive() returns a decoded table only when a complete
-- length-prefixed frame has been reassembled; nil while still buffering.
local function on_ble_raw(raw)
  local msg = host_comm.on_receive(raw)
  if msg then process_inbound(msg) end
end

-- ---------------------------------------------------------------------------
-- Boot
-- ---------------------------------------------------------------------------
local function boot()
  -- Bind host_comm to halo.bluetooth BEFORE registering the callback
  host_comm.bind(_G.halo.bluetooth)

  state_machine.init(renderer, nil, function(old, new_state, _)
    -- Uncomment for debug: print("[fsm] " .. old .. " -> " .. new_state)
  end)

  if HAS_FRAME then
    -- Route all inbound BLE through the framing reassembler
    frame.bluetooth.receive_callback(on_ble_raw)
    -- Physical button callbacks go directly to FSM
    frame.button.single(function() state_machine.dispatch(E.EVENTS.single_click) end)
    frame.button.double(function() state_machine.dispatch(E.EVENTS.double_click) end)
    frame.button.long(function()   state_machine.dispatch(E.EVENTS.long_press)   end)
    frame.imu.tap_callback(function() state_machine.dispatch(E.EVENTS.imu_tap)   end)
  end

  state_machine.dispatch(E.EVENTS.startup)
  print(0)  -- signal host: Lua ready
end

boot()

while true do
  local ok, err = pcall(function()
    renderer.tick()
    if HAS_FRAME then frame.sleep(0.05) end
  end)
  if not ok then
    local msg = tostring(err or "")
    if msg:find("Emulator stopped") or msg:find("stopped") then
      break
    end
    print("[memoscape] error: " .. msg)
  end
end
