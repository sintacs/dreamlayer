-- ble/protocol.lua
-- Length-prefix framing layer.
--
-- Framing format (matches real_bridge.py _send_raw):
--   Bytes 0-3  : uint32 big-endian = total frame length (including these 4 bytes)
--   Bytes 4-N  : UTF-8 JSON payload
--
-- BLE MTU fragments arrive as separate on_receive() calls; this module
-- buffers them until a complete frame has been received.

local M = {}

-- Largest frame we will ever reassemble.  The biggest legitimate frame is a
-- figment_put or sprite envelope (a few KB); anything larger is a corrupt or
-- hostile header.  Without this cap a garbage 4-byte header would leave the
-- reassembler buffering forever on a heap measured in tens of KB.
-- Keep in lockstep with real_bridge.py _MAX_FRAME_BYTES.
M.MAX_FRAME = 16384

-- Reassembly state
local _buf   = ""   -- accumulated bytes (as Lua string / byte string)
local _need  = nil  -- total expected bytes for current frame, or nil

-- Counters for telemetry/diagnostics (read via M.stats())
local _stats = { frames = 0, dropped = 0 }

local function _drop_corrupt(why)
  _buf, _need = "", nil
  _stats.dropped = _stats.dropped + 1
  if _G.halo and _G.halo.log then
    _G.halo.log("[protocol] dropped corrupt frame: " .. why)
  end
end

-- ---------------------------------------------------------------------------
-- feed(chunk)
-- Append chunk to the internal buffer and attempt to extract a complete frame.
-- Returns the JSON string when a complete frame is available, otherwise nil.
-- A corrupt header (length < 5 or > MAX_FRAME) drops the whole buffer and
-- starts clean — a wedged link is worse than a lost frame.
-- ---------------------------------------------------------------------------
function M.feed(chunk)
  _buf = _buf .. (chunk or "")

  -- Read the 4-byte length header if we don't have it yet
  if _need == nil then
    if #_buf < 4 then return nil end  -- still waiting for header
    _need = M._read_u32be(_buf, 1)
    -- Header total includes the 4 header bytes: minimum legal frame is 5.
    if _need < 5 or _need > M.MAX_FRAME then
      _drop_corrupt("length header " .. tostring(_need))
      return nil
    end
  end

  if #_buf < _need then return nil end  -- still buffering payload

  -- We have a complete frame
  local payload = _buf:sub(5, _need)   -- bytes 5.._need (1-indexed)
  _buf  = _buf:sub(_need + 1)          -- remainder for next frame
  _need = nil
  _stats.frames = _stats.frames + 1
  return payload
end

-- ---------------------------------------------------------------------------
-- pending()
-- True when the buffer may hold (the start of) another frame — callers can
-- drain queued frames by calling feed("") until it returns nil.
-- ---------------------------------------------------------------------------
function M.pending()
  return #_buf >= 4
end

-- ---------------------------------------------------------------------------
-- stats()
-- { frames = <complete frames delivered>, dropped = <corrupt drops> }
-- ---------------------------------------------------------------------------
function M.stats()
  return { frames = _stats.frames, dropped = _stats.dropped }
end

-- ---------------------------------------------------------------------------
-- frame(json_string)
-- Prepend the 4-byte big-endian length header to json_string.
-- Returns the framed binary string for transmission.
-- ---------------------------------------------------------------------------
function M.frame(json_str)
  local total = #json_str + 4
  local b4 = string.char(
    math.floor(total / 0x1000000) % 0x100,
    math.floor(total / 0x10000)   % 0x100,
    math.floor(total / 0x100)     % 0x100,
    total % 0x100
  )
  return b4 .. json_str
end

-- ---------------------------------------------------------------------------
-- reset()
-- Discard any partially-buffered frame (e.g. after a disconnect).
-- ---------------------------------------------------------------------------
function M.reset()
  _buf  = ""
  _need = nil
end

-- ---------------------------------------------------------------------------
-- Internal helper: read uint32 big-endian from string s at byte offset i (1-based)
-- ---------------------------------------------------------------------------
function M._read_u32be(s, i)
  local b1, b2, b3, b4 = s:byte(i, i+3)
  return ((b1 or 0) * 0x1000000)
       + ((b2 or 0) * 0x10000)
       + ((b3 or 0) * 0x100)
       +  (b4 or 0)
end

return M
