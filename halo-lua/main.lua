-- main.lua : Halo boot entry point. Autoruns on device.
-- Wires modules, registers callbacks, runs the event loop.
local time      = require("system.time")
local logging   = require("system.logging")
local settings  = require("system.settings")
local power     = require("system.power")
local renderer  = require("display.renderer")
local anim      = require("display.animations")
local scheduler = require("capture.scheduler")
local camera    = require("capture.camera")
local microphone= require("capture.microphone")
local activity  = require("capture.activity")
local host_comm = require("ble.host_comm")
local state_machine = require("app.state_machine")
local session   = require("app.session")
local E         = require("app.events")

-- `halo` is the global injected by the Halo runtime (display, bluetooth, button,
-- imu, microphone, speaker, camera, file, time, power). On emulator it is mocked.
local halo = _G.halo or {}

local function boot()
  time.bind(halo.time and halo.time.now or function() return 0 end)
  logging.bind and logging.info("Memoscape boot")
  settings.bind(halo.file); settings.load()
  power.bind(halo.power)
  camera.bind(halo.camera); microphone.bind(halo.microphone)
  scheduler.bind(camera, microphone, activity)
  host_comm.bind(halo.bluetooth)
  renderer.bind(halo.display, time.now)
  anim.enabled = not settings.get("reduce_motion")

  state_machine.init(renderer, scheduler, function(old,new,ev)
    logging.info("state "..old.." -> "..new.." ("..tostring(ev)..")") 
  end)

  -- input callbacks -> state machine events
  if halo.button then
    halo.button.on_single = function() state_machine.dispatch(E.EVENTS.single_click) end
    halo.button.on_double = function() state_machine.dispatch(E.EVENTS.double_click) end
    halo.button.on_long   = function() state_machine.dispatch(E.EVENTS.long_press) end
  end
  if halo.imu then halo.imu.on_tap = function() state_machine.dispatch(E.EVENTS.imu_tap) end end
  if halo.bluetooth then
    halo.bluetooth.on_message = function(m) host_comm.on_message(m) end
    halo.bluetooth.on_connect = function() session.start(time.now()); state_machine.dispatch(E.EVENTS.host_connected) end
    halo.bluetooth.on_disconnect = function() session.end_session(); state_machine.dispatch(E.EVENTS.host_disconnected) end
  end

  state_machine.dispatch(E.EVENTS.startup)
end

-- cooperative event loop tick
local function tick()
  renderer.tick()
  local pe = power.poll(); if pe then state_machine.dispatch(pe) end
end

boot()
if halo.on_tick then halo.on_tick(tick) end
_G.memoscape = { tick = tick, state = state_machine.state }
return _G.memoscape
