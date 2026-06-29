-- palette.lua : semantic color tokens ONLY. No raw hex elsewhere.
-- Tuned for micro-OLED waveguide physics:
--   - Pure black = true off (battery & contrast)
--   - Outlines over fills (reduces halation)
--   - No mid-tone fills (wash out against ambient light)
--   - text_primary pulled off pure white (kills white-fringe artifact)
--   - accent_memory shifted 8° warm / -12% lum (kills blue fringe on glass)
--   - status_paused raised to be safety-readable in daylight
local M = {}

-- Foundations
M.background        = 0x000000  -- true off; never used as fill on cards
M.surface           = 0x0E1416  -- outline / 1px border only; never fill

-- Text hierarchy
M.text_primary      = 0xF0F4F5  -- warm off-white; kills white-fringe halation
M.text_secondary    = 0xA8B8C0  -- raised from 0x8A9BA3; survives daylight
M.text_ghost        = 0x5A6E76  -- lowest hierarchy: eyebrows, footers, proactive

-- Accent: memory / trust (teal family)
M.accent_memory     = 0x39D6A8  -- was 0x2FD4C4; +8° warm, -12% lum; no blue fringe
M.accent_memory_dim = 0x1E7A6A  -- idle breathing dot low-intensity glow

-- Accent: attention / call-to-action (coral)
M.accent_attention  = 0xE8624E  -- was 0xFF6B5E; -6% red peak; prevents channel clip

-- Accent: success / confirmation (green)
M.accent_success    = 0x56D364  -- unchanged; reads cleanly on glass

-- Accent: error (red)
M.accent_error      = 0xFF5C5C  -- unchanged; error must alarm

-- Structural
M.border_subtle     = 0x2E4048  -- was 0x1F2A2E; 1px outlines now perceptible
M.status_paused     = 0x9AADB5  -- was 0x6B7A82; safety-critical: must read in any light

return M
