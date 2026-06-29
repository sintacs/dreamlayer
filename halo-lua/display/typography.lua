-- typography.lua : text sizing abstractions + line helpers
local utils = require("lib.utils")
local M = {}
M.SIZE_XL = "xl"
M.SIZE_LG = "lg"
M.SIZE_MD = "md"
M.SIZE_SM = "sm"
M.SIZE_XS = "xs"
local AVG_W = { xl = 18, lg = 15, md = 12, sm = 9, xs = 7 }
M.LINE_SPACING = 1.35
function M.max_chars(size, width_px)
  return math.floor(width_px / (AVG_W[size] or 12))
end
function M.truncate(text, size, width_px)
  local maxc = M.max_chars(size, width_px)
  if #text <= maxc then return text end
  if maxc <= 1 then return "…" end
  return text:sub(1, maxc - 1) .. "…"
end
function M.wrap(text, size, width_px)
  return utils.wrap(text, M.max_chars(size, width_px))
end
function M.line_height(size)
  local base = { xl = 26, lg = 22, md = 18, sm = 14, xs = 11 }
  return math.floor((base[size] or 18) * M.LINE_SPACING)
end
return M
