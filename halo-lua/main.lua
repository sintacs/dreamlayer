--- main.lua : Memoscape Halo boot entry point.
--- Ported to real Brilliant Labs frame.* API.
---
--- CardQueue is wired here as the display layer between the FSM and renderer.
--- Cards arrive via BLE → state_machine.set_card() → queue:push()
--- The tick loop calls queue:tick() every frame → renderer.show_card() on change.
---
--- Cinematic transitions: renderer.bind(time_fn) is called at boot to wire
--- the monotonic clock. renderer.dismiss() is called when the queue expires
--- a card so the EXIT animation plays before the card disappears.
---
--- Diagnostics overlay: toggled by long_press.  Single_click while open
--- cycles verbosity (MINIMAL → NORMAL → VERBOSE).  diag.tick() composites
--- the HUD on top of every frame after renderer.tick().

require("compat.frame_adapter")

local renderer      = require("display.renderer")
local diag          = require("display.diagnostics")
local cards         = require("display.cards")
local host_comm     = require("ble.host_comm")
local MT            = require("ble.message_types")
local state_machine = require("app.state_machine")
local session       = require("app.session")
local E             = require("app.events")
local CardQueue     = require("app.card_queue")

local HAS_FRAME = (type(_G.frame) == "table")

-- ---------------------------------------------------------------------------
-- Queue instance (shared, module-level)
-- ---------------------------------------------------------------------------
local queue = CardQueue.new()

-- Monotonic ms counter for environments without frame.time
local _boot_t   = os.clock()
local function now_ms()
  if HAS_FRAME and frame.time then
    return math.floor(frame.time.utc() * 1000) % (2^31)
  end
  return math.floor((os.clock() - _boot_t) * 1000)
end

-- Last card shown to renderer — used to detect changes and avoid redundant starts
local _last_shown = nil

-- ---------------------------------------------------------------------------
-- Priority mapping: which card types are URGENT vs CONTEXT vs AMBIENT
-- ---------------------------------------------------------------------------
local CARD_PRIORITY = {
  ObjectRecallCard     = CardQueue.URGENT,
  CommitmentRecallCard = CardQueue.URGENT,
  QueryListeningCard   = CardQueue.URGENT,
  LoadingCard          = CardQueue.URGENT,
  ReadyCard            = CardQueue.URGENT,
  PrivacyPausedCard    = CardQueue.URGENT,
  ProactiveMemoryCard  = CardQueue.CONTEXT,
  PersonContextCard    = CardQueue.CONTEXT,
  SavedMemoryCard      = CardQueue.CONTEXT,
  ErrorCard            = CardQueue.CONTEXT,
  LowConfidenceCard    = CardQueue.AMBIENT,
  CommitmentDriftCard  = CardQueue.CONTEXT,
  TimeScrubNodeCard    = CardQueue.CONTEXT,
  DeviationAlertCard   = CardQueue.URGENT,
}

local function card_priority(card)
  return CARD_PRIORITY[card an