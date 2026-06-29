-- typography.lua : text sizing abstractions + line helpers
-- Tuned for 256×256 micro-OLED at ~30cm viewing distance (1.5s glance budget).
--
-- SIZE_HERO : primary answer content (new) — largest, boldest, lands first
-- SIZE_XL   : large labels, card titles
-- SIZE_LG   : secondary content, place names, person names
-- SIZE_MD   : tertiary detail (near-text, due dates)
-- SIZE_SM   : eyebrows, footers, letter-spaced labels — minimum for waveguide
-- SIZE_XS   : REMOVED — 7px is unreadable on a waveguide; use SIZE_SM minimum
--
-- LINE_SPACING raised 1.35 → 1.55:
--   Waveguide vertical chromatic aberration makes tight lines harder to parse.
--   1.55 adds visual air that makes multi-line cards feel intentional.

local utils = require("lib.utils")
local M = {}

M.SIZE_HERO = "hero"  -- 20px avg char width, ~28-30pt equiv
M.SIZE_XL   = "xl"    -- 18px
M.SIZE_LG   = "lg"    -- 15px
M.SIZE_MD   = "md"    -- 12px
M.SIZE_SM   = "sm"    --  9px  ← absolute minimum for waveguide legibility
-- M.SIZE_XS removed; do not use

-- Average character widths in pixels at each size
local AVG_W = { hero = 20, xl = 18, lg = 15, md = 12, sm = 9 }

-- Base line heights before spacing multiplier
local BASE_H = { hero = 28, xl = 24, lg = 20, md = 16, sm = 12 }

M.LINE_SPACING = 1.55  -- was 1.35

-- Computed line heights (base × LINE_SPACING, rounded to nearest even px)
-- hero: 28 × 1.55 = 43.4 → 42
-- xl:   24 × 1.55 = 37.2 → 36
-- lg:   20 × 1.55 = 31.0 → 30
-- md:   16 × 1.55 = 24.8 → 24
-- sm:   12 × 1.55 = 18.6 → 18

function M.line_height(size)
  local base = BASE_H[size] or 16
  return math.floor(base * M.LINE_SPACING / 2 + 0.5) * 2  -- round to even
end

function M.max_chars(size, width_px)
  return math.floor(width_px / (AVG_W[size] or 12))
end

function M.truncate(text, size, width_px)
  local maxc = M.max_chars(size, width_px)
  if #text <= maxc then return text end
  if maxc <= 1 then return "\xE2\x80\xA6" end  -- UTF-8 ellipsis
  return text:sub(1, maxc - 1) .. "\xE2\x80\xA6"
end

function M.wrap(text, size, width_px)
  return utils.wrap(text, M.max_chars(size, width_px))
end

-- Letter-spacing helper: used for eyebrow labels (SIZE_SM, +2px per char)
-- Returns adjusted avg width for use in max_chars / truncate.
function M.avg_w_with_tracking(size, tracking_px)
  return (AVG_W[size] or 9) + (tracking_px or 0)
end

return M
