-- cards.lua : card layout descriptors for all 11 Memoscape card types.
-- Each card returns a table consumed by renderer.lua.
-- All coordinates are absolute pixels on the 256×256 circular display.
-- Safe text area: x = 20..236 (216px wide), y = 32..224.
-- Center: (128, 128).
--
-- Typography sizes: hero(20px), xl(18px), lg(15px), md(12px), sm(9px)
-- Color tokens: see palette.lua

local P = require("display.palette")
local T = require("display.typography")
local A = require("display.animations")

local M = {}

-- Confidence dot color helper
local function conf_color(c)
  if not c then return P.text_ghost end
  if c >= 0.75 then return P.accent_success
  elseif c >= 0.40 then return P.accent_memory
  else return P.status_paused end
end

-- ---------------------------------------------------------------------------
-- 1. ReadyCard — idle breathing state
-- ---------------------------------------------------------------------------
function M.ready()
  return {
    type       = "ReadyCard",
    dismiss_ms = A.DISMISS_MS.ReadyCard,
    elements   = {
      -- Breathing dot (animated; radius/glow driven by animations.lua)
      { kind="breathe_dot", x=128, y=128,
        color=P.accent_memory, color_dim=P.accent_memory_dim },
      -- 4 satellite dots
      { kind="dot", x=128, y=108, r=A.SATELLITE_R, color=P.accent_memory_dim },
      { kind="dot", x=148, y=128, r=A.SATELLITE_R, color=P.accent_memory_dim },
      { kind="dot", x=128, y=148, r=A.SATELLITE_R, color=P.accent_memory_dim },
      { kind="dot", x=108, y=128, r=A.SATELLITE_R, color=P.accent_memory_dim },
    },
  }
end

-- ---------------------------------------------------------------------------
-- 2. SavedMemoryCard — transient confirmation
-- ---------------------------------------------------------------------------
function M.saved_memory(label)
  return {
    type       = "SavedMemoryCard",
    dismiss_ms = A.DISMISS_MS.SavedMemoryCard,
    elements   = {
      { kind="text", x=128, y=102, text="SAVED",
        size=T.SIZE_SM, color=P.accent_success, align="center",
        tracking=2 },
      { kind="text", x=128, y=126, text=label or "Memory saved",
        size=T.SIZE_LG, color=P.text_primary, align="center" },
      { kind="dot",  x=128, y=158, r=3, color=P.accent_success },
      -- 210° arc (gap at top): radius=110, 1px, accent_success 30% alpha
      { kind="arc",  cx=128, cy=128, r=110, stroke=1,
        color=P.accent_success, alpha=0.30,
        start_deg=210, end_deg=330 },   -- gap is top 150°→30°
    },
  }
end

-- ---------------------------------------------------------------------------
-- 3. QueryListeningCard — mic active
-- ---------------------------------------------------------------------------
function M.query_listening()
  return {
    type       = "QueryListeningCard",
    dismiss_ms = A.DISMISS_MS.QueryListeningCard,
    elements   = {
      { kind="text", x=128, y=110, text="Listening\xE2\x80\xA6",
        size=T.SIZE_SM, color=P.accent_attention, align="center" },
      { kind="waveform", cx=128, cy=136,
        bar_count=A.WAVE_BAR_COUNT, bar_width=A.WAVE_BAR_WIDTH,
        bar_h_min=A.WAVE_BAR_H_MIN, bar_h_max=A.WAVE_BAR_H_MAX,
        bar_centers=A.WAVE_BAR_CENTERS,
        color=P.accent_attention },
    },
  }
end

-- ---------------------------------------------------------------------------
-- 4. LoadingCard — arc spinner, no text
-- ---------------------------------------------------------------------------
function M.loading()
  return {
    type       = "LoadingCard",
    dismiss_ms = A.DISMISS_MS.LoadingCard,
    elements   = {
      { kind="spinner", cx=128, cy=128,
        r=A.SPINNER_RADIUS_PX, stroke=A.SPINNER_STROKE_PX,
        color=P.accent_memory },
    },
  }
end

-- ---------------------------------------------------------------------------
-- 5. ObjectRecallCard — THE HERO CARD
-- Stagger sequence (all offsets from card t=0):
--   t+0ms  : place name (primary) — lands FIRST, largest
--   t+40ms : object name (eyebrow)
--   t+60ms : near-text (detail)
--   t+80ms : last-seen (footer)
--   t+100ms: separator line draws outward from center
--   t+100ms: left accent bar draws downward
--   t+360ms: confidence dot fades in
-- ---------------------------------------------------------------------------
function M.object_recall(o)
  local obj      = o.object or ""
  local place    = o.place  or ""
  local detail   = o.detail or ""
  local lastseen = o.last_seen or ""
  local conf     = o.confidence

  -- Truncate detail to 18 chars
  if #detail > 18 then detail = detail:sub(1,17) .. "\xE2\x80\xA6" end

  return {
    type       = "ObjectRecallCard",
    dismiss_ms = A.DISMISS_MS.ObjectRecallCard,
    -- Stagger offsets (ms from card entrance t=0)
    stagger    = {
      primary  = A.STAGGER_PRIMARY_MS,
      eyebrow  = A.STAGGER_EYEBROW_MS,
      detail   = A.STAGGER_DETAIL_MS,
      footer   = A.STAGGER_FOOTER_MS,
    },
    elements   = {
      -- Eyebrow: object name, ALL-CAPS, +2px tracking
      { kind="text", x=128, y=76,
        text=obj:upper(), size=T.SIZE_SM,
        color=P.accent_memory, align="center", tracking=2,
        stagger_key="eyebrow" },

      -- Separator line at y=92, x=54→202 (draws outward from center)
      { kind="hline", x1=54, x2=202, y=92,
        stroke=1, color=P.border_subtle,
        draw_on=true, draw_start_ms=A.DRAWON_START_MS,
        draw_dur_ms=A.DRAWON_DURATION_MS },

      -- Left accent mark: x=22, y=104→128 (draws downward)
      { kind="vbar", x=22, y1=104, y2=128,
        width=2, color=P.accent_memory,
        draw_on=true, draw_start_ms=A.DRAWON_START_MS,
        draw_dur_ms=A.DRAWON_DURATION_MS },

      -- Primary: place name (largest, lands first)
      { kind="text", x=128, y=116,
        text=place, size=T.SIZE_HERO,
        color=P.text_primary, align="center",
        max_width=196,   -- L=42 (after accent bar) R=214
        stagger_key="primary" },

      -- Detail: near-text
      { kind="text", x=128, y=148,
        text=detail, size=T.SIZE_MD,
        color=P.text_secondary, align="center",
        stagger_key="detail" },

      -- Footer: last seen
      { kind="text", x=128, y=173,
        text=lastseen, size=T.SIZE_SM,
        color=P.text_ghost, align="center",
        stagger_key="footer" },

      -- Confidence dot (fades in last)
      { kind="dot", x=128, y=196, r=3,
        color=conf_color(conf),
        fade_start_ms=360, fade_dur_ms=200 },
    },
  }
end

-- ---------------------------------------------------------------------------
-- 6. CommitmentRecallCard
-- ---------------------------------------------------------------------------
function M.commitment_recall(c)
  local person = c.person or ""
  local task   = c.task or ""
  local due    = c.due or ""
  local conf   = c.confidence

  return {
    type       = "CommitmentRecallCard",
    dismiss_ms = A.DISMISS_MS.CommitmentRecallCard,
    elements   = {
      { kind="text", x=128, y=82,
        text="YOU PROMISED " .. person:upper(),
        size=T.SIZE_SM, color=P.accent_memory,
        align="center", tracking=2 },

      -- Left accent bar: x=22, y=96→168
      { kind="vbar", x=22, y1=96, y2=168, width=2, color=P.accent_memory },

      -- Primary task (up to 2 lines), safe width 196px (left of accent bar)
      { kind="text", x=128, y=108,
        text=task, size=T.SIZE_LG,
        color=P.text_primary, align="center",
        max_width=196, max_lines=2 },

      -- Due line
      { kind="text", x=128, y=174,
        text=due, size=T.SIZE_SM,
        color=P.text_secondary, align="center" },

      { kind="dot", x=128, y=195, r=2, color=conf_color(conf) },
    },
  }
end

-- ---------------------------------------------------------------------------
-- 7. ProactiveMemoryCard — ambient, the quietest card
-- ---------------------------------------------------------------------------
function M.proactive_memory(p)
  local summary = p.summary or ""
  local person  = p.person
  local conf    = p.confidence

  local footer_el = nil
  if person then
    footer_el = { kind="text", x=128, y=178,
      text="With " .. person, size=T.SIZE_SM,
      color=P.accent_memory, align="center" }
  end

  return {
    type       = "ProactiveMemoryCard",
    dismiss_ms = A.DISMISS_MS.ProactiveMemoryCard,
    elements   = {
      { kind="text", x=128, y=68,
        text="LAST TIME HERE",
        size=T.SIZE_SM, color=P.text_ghost,
        align="center", tracking=2 },

      { kind="hline", x1=68, x2=188, y=82,
        stroke=1, color=P.border_subtle },

      { kind="text", x=128, y=96,
        text=summary, size=T.SIZE_MD,
        color=P.text_secondary, align="center",
        max_width=196, max_lines=2 },

      footer_el,  -- nil if no person (renderer must skip nils)
    },
  }
end

-- ---------------------------------------------------------------------------
-- 8. PersonContextCard
-- ---------------------------------------------------------------------------
function M.person_context(p)
  return {
    type       = "PersonContextCard",
    dismiss_ms = A.DISMISS_MS.PersonContextCard,
    elements   = {
      -- Outer framing arc (full circle)
      { kind="circle", cx=128, cy=128, r=112, stroke=1, color=P.border_subtle },

      { kind="text", x=128, y=88,
        text=p.person or "",
        size=T.SIZE_LG, color=P.accent_memory, align="center" },

      { kind="text", x=128, y=122,
        text=p.headline or "",
        size=T.SIZE_MD, color=P.text_primary, align="center",
        max_width=196 },

      { kind="text", x=128, y=150,
        text=p.detail or "",
        size=T.SIZE_SM, color=P.text_secondary, align="center" },
    },
  }
end

-- ---------------------------------------------------------------------------
-- 9. PrivacyPausedCard — safety-critical, teal MUST be absent
-- ---------------------------------------------------------------------------
function M.privacy_paused()
  return {
    type       = "PrivacyPausedCard",
    dismiss_ms = A.DISMISS_MS.PrivacyPausedCard,
    elements   = {
      -- Outer ring (only card with a ring in status_paused color)
      { kind="circle", cx=128, cy=128, r=118, stroke=1,
        color=P.status_paused, alpha=0.40 },

      -- Filled circle behind pause icon (only fill element in the system)
      { kind="filled_circle", cx=128, cy=100, r=28,
        color=P.status_paused, alpha=0.20 },

      -- Pause icon: two vertical bars, each 4×14px, gap 5px, centered at (128,100)
      { kind="rect", x=119, y=93, w=4, h=14, color=P.status_paused },  -- left bar
      { kind="rect", x=128, y=93, w=4, h=14, color=P.status_paused },  -- right bar (gap=5)

      { kind="text", x=128, y=142,
        text="Memory paused",
        size=T.SIZE_LG, color=P.status_paused, align="center" },

      { kind="text", x=128, y=166,
        text="Nothing is captured",
        size=T.SIZE_SM, color=P.text_ghost, align="center" },
    },
  }
end

-- ---------------------------------------------------------------------------
-- 10. ErrorCard
-- ---------------------------------------------------------------------------
function M.error_card(msg)
  return {
    type       = "ErrorCard",
    dismiss_ms = A.DISMISS_MS.ErrorCard,
    elements   = {
      -- Outer ring
      { kind="circle", cx=128, cy=128, r=118, stroke=1,
        color=P.accent_error, alpha=0.30 },

      -- Triangle outline (24px high, centered at 128,88)
      { kind="triangle_outline", cx=128, cy=88, h=24,
        stroke=2, color=P.accent_error },

      { kind="text", x=128, y=108,
        text="Something went wrong",
        size=T.SIZE_SM, color=P.text_secondary, align="center" },

      { kind="text", x=128, y=128,
        text=msg or "Try again",
        size=T.SIZE_MD, color=P.accent_error, align="center",
        max_width=196 },
    },
  }
end

-- ---------------------------------------------------------------------------
-- 11. LowConfidenceCard — no teal; no confidence
-- ---------------------------------------------------------------------------
function M.low_confidence()
  return {
    type       = "LowConfidenceCard",
    dismiss_ms = A.DISMISS_MS.LowConfidenceCard,
    elements   = {
      { kind="text", x=128, y=110,
        text="Not sure",
        size=T.SIZE_LG, color=P.text_secondary, align="center" },

      { kind="text", x=128, y=142,
        text="Try rephrasing",
        size=T.SIZE_SM, color=P.text_ghost, align="center" },

      -- Three dots
      { kind="dot", x=108, y=170, r=3, color=P.text_ghost },
      { kind="dot", x=128, y=170, r=3, color=P.text_ghost },
      { kind="dot", x=148, y=170, r=3, color=P.text_ghost },
    },
  }
end

return M
