--- cinema_v2_prototypes/proto_lib.lua
--- Shared scratch helpers for the Meridian prototypes (Phase 3).
--- Scratch code: numeric constants live here locally until integration
--- promotes them into display/animations.lua (MER_* / TESTIMONY_* bank).

local P = require("display.palette")

local M = {}

M.CX, M.CY = 128, 128

-- Dial geometry (docs/cinema_v2/horizon.md)
-- Iteration 2 (prototype review pass 1): added the rim TRACK — a 1px
-- ghost arc across the active window. Without it the marks floated in
-- void and the seam was indistinguishable from empty sky; with it the
-- dial is an instrument and the seam is a legible absence.
M.TRACK_R        = 100
M.RIM_R          = 105
M.MARK_BASE_R    = 101
M.NOW_DEG        = -90
M.DEG_PER_HOUR   = 30
M.SEAM_FROM_DEG  = 60    -- past cap edge
M.SEAM_TO_DEG    = 120   -- future cap edge (via the bottom)
M.ELDER_DEG      = 58
M.FUTURE_CAP_DEG = 122

function M.polar(r, deg)
  local rad = math.rad(deg)
  return M.CX + r * math.cos(rad), M.CY + r * math.sin(rad)
end

local function fl(n) return math.floor(n + 0.5) end
M.fl = fl

function M.radial_tick(deg, r0, r1, color, width)
  local x0, y0 = M.polar(r0, deg)
  local x1, y1 = M.polar(r1, deg)
  frame.display.line(fl(x0), fl(y0), fl(x1), fl(y1), color)
  if width and width >= 2 then
    -- 2px tick: companion line offset perpendicular by 1px
    local rad = math.rad(deg)
    local px, py = -math.sin(rad), math.cos(rad)
    frame.display.line(fl(x0 + px), fl(y0 + py), fl(x1 + px), fl(y1 + py), color)
  end
end

function M.arc(cx, cy, r, a0, a1, color, steps)
  if r <= 0 then return end
  steps = steps or 32
  local sweep = a1 - a0
  local x0, y0 = cx + r * math.cos(math.rad(a0)), cy + r * math.sin(math.rad(a0))
  for i = 1, steps do
    local a = a0 + sweep * i / steps
    local x1, y1 = cx + r * math.cos(math.rad(a)), cy + r * math.sin(math.rad(a))
    frame.display.line(fl(x0), fl(y0), fl(x1), fl(y1), color)
    x0, y0 = x1, y1
  end
end

-- ---------------------------------------------------------------------------
-- Mark grammar (docs/cinema_v2/horizon.md + promise_arc.md)
-- mark = { deg=, kind="memory"|"person"|"promise"|"elder"|"future_cap",
--          luma=0|1|2, pstate="blooming".."shattered", stack=0 }
-- ---------------------------------------------------------------------------

local MEM_STYLE = {
  [0] = { color = P.border_subtle,     len = 3 },
  [1] = { color = P.accent_memory_dim, len = 6 },
  [2] = { color = P.accent_memory,     len = 9 },
}

local PROMISE_STYLE = {
  blooming  = { r = 105, dot = 2, color = P.confidence_low,  stem = 0 },
  healthy   = { r = 105, dot = 3, color = P.confidence_low,  stem = 0 },
  drifting  = { r = 105, dot = 3, color = P.warning_amber,   stem = 3 },
  cracking  = { r = 95,  dot = 3, color = P.warning_amber,   stem = 0 },
  shattered = { r = 95,  dot = 0, color = P.status_paused,   stem = 0 }, -- tick
}

--- The rim track: 1px ghost arc across the active window (future cap,
--- through now at the top, to past cap). The seam is its absence.
function M.draw_track()
  M.arc(M.CX, M.CY, M.TRACK_R, M.SEAM_TO_DEG, 360 + M.SEAM_FROM_DEG,
        P.border_subtle, 72)
end

function M.draw_mark(mk)
  local kind = mk.kind or "memory"
  if kind == "memory" then
    local st = MEM_STYLE[mk.luma or 1]
    M.radial_tick(mk.deg, M.MARK_BASE_R, M.MARK_BASE_R + st.len + (mk.extra_len or 0), st.color)
  elseif kind == "person" then
    local color = (mk.luma or 2) >= 2 and P.accent_memory or P.accent_memory_dim
    M.radial_tick(mk.deg, M.MARK_BASE_R, M.MARK_BASE_R + 5, color)
    local dx, dy = M.polar(110, mk.deg)
    frame.display.circle(fl(dx), fl(dy), 2, color, false)
  elseif kind == "promise" then
    local st = PROMISE_STYLE[mk.pstate or "healthy"]
    -- Iteration 3: stack pitch 5->7px and stacked dots shrink one step —
    -- at 5px pitch three same-hour promises blobbed into one smear.
    local stack = mk.stack or 0
    local r = st.r - stack * 7
    if mk.pstate == "shattered" then
      -- Iteration 4: a *broken* tick — two segments with a 3px gap
      -- (r 88-93 / 96-101). Iterations 2-3 drew a solid cold tick that
      -- disappeared against the track; the fracture is both visible and
      -- the honest glyph for a broken promise.
      M.radial_tick(mk.deg, r - 7, r - 2, st.color, 2)
      M.radial_tick(mk.deg, r + 1, r + 6, st.color, 2)
    else
      local x, y = M.polar(r, mk.deg)
      local dot = stack > 0 and math.max(2, st.dot - 1) or st.dot
      frame.display.circle(fl(x), fl(y), dot, st.color, true)
      if st.stem > 0 then
        M.radial_tick(mk.deg, r - st.stem - 3, r - 3, st.color)
      end
    end
  elseif kind == "elder" then
    M.radial_tick(M.ELDER_DEG, M.MARK_BASE_R, M.MARK_BASE_R + 4, P.text_ghost)
  elseif kind == "future_cap" then
    local x, y = M.polar(105, M.FUTURE_CAP_DEG)
    frame.display.circle(fl(x), fl(y), 2, P.text_ghost, true)
  end
end

--- Now-notch: the only mark that CROSSES the track (r 96 -> 96+len).
function M.draw_notch(len, paused)
  local color = paused and P.status_paused or P.accent_memory
  M.radial_tick(M.NOW_DEG, 96, 96 + (len or 8), color, 2)
end

--- Full horizon pass.
--- state = { marks={...}, notch_len=8, paused=false, dim=false }
--- dim: every memory mark forced to floor tier (dream mode rule).
function M.draw_horizon(state)
  state = state or {}
  M.draw_track()
  for _, mk in ipairs(state.marks or {}) do
    if state.dim and mk.kind == "memory" then
      local clone = { deg = mk.deg, kind = "memory", luma = 0, extra_len = mk.extra_len }
      M.draw_mark(clone)
    else
      M.draw_mark(mk)
    end
  end
  if not state.no_notch then
    M.draw_notch(state.notch_len or 8, state.paused)
  end
end

return M
