
local P = require("display.palette")
local T = require("display.typography")
local A = require("display.animations")

local M = {}

local function conf_color(c)
  if not c then return P.text_ghost end
  if c >= 0.75 then return P.accent_success
  elseif c >= 0.40 then return P.accent_memory
  else return P.status_paused end
end

function M.ready()
  local elements = {
    { kind="breathe_dot", x=128, y=128,
      r_min=A.BREATHE_R_MIN, r_max=A.BREATHE_R_MAX,
      color=P.accent_memory, color_dim=P.accent_memory_dim },
  }
  for _, s in ipairs(A.SATELLITES) do
    elements[#elements+1] = {
      kind="dot", x=s.x, y=s.y, r=A.SATELLITE_R, color=P.accent_memory_dim
    }
  end
  return {
    type       = "ReadyCard",
    dismiss_ms = A.DISMISS_MS.ReadyCard,
    elements   = elements,
  }
end

function M.saved_memory(label)
  return {
    type       = "SavedMemoryCard",
    dismiss_ms = A.DISMISS_MS.SavedMemoryCard,
    elements   = {
      { kind="text", x=128, y=98, text="SAVED",
        size=T.SIZE_SM, color=P.accent_success, align="center", tracking=2 },
      { kind="hline", x1=88, x2=168, y=110,
        stroke=1, color=P.accent_success, alpha=0.30 },
      { kind="text", x=128, y=130, text=label or "Memory saved",
        size=T.SIZE_LG, color=P.text_primary, align="center", max_width=188 },
      { kind="dot",  x=128, y=158, r=3, color=P.accent_success },
      { kind="arc",  cx=128, cy=128, r=108, stroke=1,
        color=P.accent_success, alpha=0.25,
        start_deg=200, end_deg=340 },
    },
  }
end

function M.query_listening()
  return {
    type       = "QueryListeningCard",
    dismiss_ms = A.DISMISS_MS.QueryListeningCard,
    elements   = {
      { kind="dot", x=128, y=92, r=3,
        color=P.accent_attention, alpha=0.60 },
      { kind="text", x=128, y=104, text="Listening",
        size=T.SIZE_SM, color=P.accent_attention, align="center", tracking=1 },
      { kind="waveform", cx=128, cy=138,
        bar_count=A.WAVE_BAR_COUNT, bar_width=A.WAVE_BAR_WIDTH,
        bar_h_min=A.WAVE_BAR_H_MIN, bar_h_max=A.WAVE_BAR_H_MAX,
        bar_centers=A.WAVE_BAR_CENTERS,
        color=P.accent_attention },
    },
  }
end

function M.loading()
  return {
    type       = "LoadingCard",
    dismiss_ms = A.DISMISS_MS.LoadingCard,
    elements   = {
      { kind="circle", cx=128, cy=128, r=A.SPINNER_RADIUS_PX,
        stroke=1, color=P.border_subtle, alpha=0.50 },
      { kind="spinner", cx=128, cy=128,
        r=A.SPINNER_RADIUS_PX, stroke=A.SPINNER_STROKE_PX,
        color=P.accent_memory },
    },
  }
end

function M.object_recall(o)
  local obj      = o.object or ""
  local place    = o.place  or ""
  local detail   = o.detail or ""
  local lastseen = o.last_seen or ""
  local conf     = o.confidence

  if #detail > 18 then detail = detail:sub(1,17) .. "\xE2\x80\xA6" end

  return {
    type       = "ObjectRecallCard",
    dismiss_ms = A.DISMISS_MS.ObjectRecallCard,
    stagger    = {
      primary = A.STAGGER_PRIMARY_MS,
      eyebrow = A.STAGGER_EYEBROW_MS,
      detail  = A.STAGGER_DETAIL_MS,
      footer  = A.STAGGER_FOOTER_MS,
    },
    elements   = {
      { kind="text", x=128, y=72,
        text=obj:upper(), size=T.SIZE_SM,
        color=P.accent_memory, align="center", tracking=2,
        stagger_key="eyebrow" },

      { kind="hline", x1=48, x2=208, y=86,
        stroke=1, color=P.border_subtle,
        draw_on=true, draw_start_ms=A.DRAWON_START_MS,
        draw_dur_ms=A.DRAWON_DURATION_MS },

      { kind="vbar", x=20, y1=98, y2=130,
        width=2, color=P.memory_rail,
        draw_on=true, draw_start_ms=A.DRAWON_START_MS,
        draw_dur_ms=A.DRAWON_DURATION_MS },

      { kind="text", x=128, y=114,
        text=place, size=T.SIZE_HERO,
        color=P.text_primary, align="center",
        max_width=192,
        stagger_key="primary" },

      { kind="text", x=128, y=146,
        text=detail, size=T.SIZE_MD,
        color=P.text_secondary, align="center",
        max_width=192,
        stagger_key="detail" },

      { kind="text", x=128, y=170,
        text=lastseen, size=T.SIZE_SM,
        color=P.text_ghost, align="center",
        stagger_key="footer" },

      { kind="dot", x=128, y=192, r=3,
        color=conf_color(conf),
        fade_start_ms=360, fade_dur_ms=200 },
    },
  }
end

function M.commitment_recall(c)
  local person = c.person or ""
  local task   = c.task or ""
  local due    = c.due or ""
  local conf   = c.confidence

  return {
    type       = "CommitmentRecallCard",
    dismiss_ms = A.DISMISS_MS.CommitmentRecallCard,
    elements   = {
      { kind="text", x=128, y=74,
        text="YOU PROMISED " .. person:upper(),
        size=T.SIZE_SM, color=P.accent_memory,
        align="center", tracking=2 },

      { kind="hline", x1=48, x2=208, y=88,
        stroke=1, color=P.border_subtle },

      { kind="vbar", x=20, y1=100, y2=158,
        width=2, color=P.memory_rail },

      { kind="text", x=128, y=118,
        text=task, size=T.SIZE_LG,
        color=P.text_primary, align="center",
        max_width=192, max_lines=2 },

      { kind="text", x=128, y=166,
        text=due, size=T.SIZE_SM,
        color=P.accent_memory, align="center" },

      { kind="dot", x=128, y=186, r=2, color=conf_color(conf) },
    },
  }
end

function M.proactive_memory(p)
  local summary = p.summary or ""
  local person  = p.person

  local footer_el = nil
  if person then
    footer_el = { kind="text", x=128, y=174,
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

      { kind="arc", cx=128, cy=128, r=96,
        stroke=1, color=P.accent_memory, alpha=0.30,
        start_deg=200, end_deg=340 },

      { kind="hline", x1=72, x2=184, y=82,
        stroke=1, color=P.border_subtle },

      { kind="text", x=128, y=116,
        text=summary, size=T.SIZE_LG,
        color=P.text_secondary, align="center",
        max_width=180, max_lines=2 },

      footer_el,
    },
  }
end

function M.person_context(p)
  return {
    type       = "PersonContextCard",
    dismiss_ms = A.DISMISS_MS.PersonContextCard,
    elements   = {
      { kind="arc", cx=128, cy=128, r=108,
        stroke=1, color=P.accent_memory, alpha=0.40,
        start_deg=240, end_deg=300 },

      { kind="text", x=128, y=84,
        text=p.person or "",
        size=T.SIZE_LG, color=P.accent_memory, align="center" },

      { kind="hline", x1=72, x2=184, y=98,
        stroke=1, color=P.border_subtle },

      { kind="text", x=128, y=122,
        text=p.headline or "",
        size=T.SIZE_MD, color=P.text_primary, align="center",
        max_width=192 },

      { kind="text", x=128, y=148,
        text=p.detail or "",
        size=T.SIZE_SM, color=P.text_secondary, align="center" },
    },
  }
end

function M.privacy_paused()
  return {
    type       = "PrivacyPausedCard",
    dismiss_ms = A.DISMISS_MS.PrivacyPausedCard,
    elements   = {
      { kind="circle", cx=128, cy=128, r=116,
        stroke=1, color=P.status_paused, alpha=0.35 },

      { kind="circle", cx=128, cy=100, r=20,
        stroke=2, color=P.status_paused },

      { kind="rect", x=120, y=92, w=4, h=16, color=P.status_paused },
      { kind="rect", x=130, y=92, w=4, h=16, color=P.status_paused },

      { kind="text", x=128, y=146,
        text="Memory paused",
        size=T.SIZE_LG, color=P.status_paused, align="center" },

      { kind="text", x=128, y=168,
        text="Nothing is captured",
        size=T.SIZE_SM, color=P.text_ghost, align="center" },
    },
  }
end

function M.error_card(msg)
  return {
    type       = "ErrorCard",
    dismiss_ms = A.DISMISS_MS.ErrorCard,
    elements   = {
      { kind="circle", cx=128, cy=128, r=116,
        stroke=1, color=P.accent_error, alpha=0.25 },

      { kind="triangle_outline", cx=128, cy=90, h=20,
        stroke=2, color=P.accent_error },

      { kind="text", x=128, y=122,
        text="Connection issue",
        size=T.SIZE_LG, color=P.text_primary, align="center" },

      { kind="text", x=128, y=146,
        text=msg or "Try again",
        size=T.SIZE_SM, color=P.text_ghost, align="center",
        max_width=192 },
    },
  }
end

function M.low_confidence()
  return {
    type       = "LowConfidenceCard",
    dismiss_ms = A.DISMISS_MS.LowConfidenceCard,
    elements   = {
      { kind="text", x=128, y=106,
        text="Not sure",
        size=T.SIZE_LG, color=P.text_secondary, align="center" },

      { kind="text", x=128, y=136,
        text="Try rephrasing",
        size=T.SIZE_SM, color=P.text_ghost, align="center" },

      { kind="dot", x=107, y=168, r=2, color=P.text_ghost },
      { kind="dot", x=128, y=172, r=2, color=P.text_ghost },
      { kind="dot", x=149, y=168, r=2, color=P.text_ghost },
    },
  }
end

return M
