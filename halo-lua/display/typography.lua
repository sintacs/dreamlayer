
local utils = require("lib.utils")
local M = {}

M.SIZE_HERO = "hero"
M.SIZE_XL   = "xl"
M.SIZE_LG   = "lg"
M.SIZE_MD   = "md"
M.SIZE_SM   = "sm"

local AVG_W  = { hero = 22, xl = 19, lg = 17, md = 13, sm = 10 }
local BASE_H = { hero = 30, xl = 26, lg = 22, md = 17, sm = 13 }

M.LINE_SPACING = 1.55

function M.line_height(size)
  local base = BASE_H[size] or 17
  return math.floor(base * M.LINE_SPACING / 2 + 0.5) * 2
end

function M.max_chars(size, width_px)
  return math.floor(width_px / (AVG_W[size] or 13))
end

function M.truncate(text, size, width_px)
  local maxc = M.max_chars(size, width_px)
  if #text <= maxc then return text end
  if maxc <= 1 then return "\xE2\x80\xA6" end
  return text:sub(1, maxc - 1) .. "\xE2\x80\xA6"
end

function M.wrap(text, size, width_px)
  return utils.wrap(text, M.max_chars(size, width_px))
end

function M.avg_w_with_tracking(size, tracking_px)
  return (AVG_W[size] or 10) + (tracking_px or 0)
end

return M
