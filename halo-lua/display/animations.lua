-- animations.lua : timing, easing, and motion primitives
-- All durations in milliseconds unless noted.
--
-- WAVEGUIDE MOTION RULES:
--   1. Fade in / fade out — always safe; opacity transitions need no spatial tracking.
--   2. NO slide-up — spatial translation creates ghost-trail artifacts on diffractive coating.
--      Replaced with: fade + scale 0.94→1.0 (3% scale, imperceptible spatially).
--   3. Easing: cubic-bezier(0.16, 1, 0.3, 1) for entrances (fast out, gentle settle).
--              linear for exits (just dissolve — no settle needed).
--   4. Breathing dot: slow, sine, calm — not a pulse.

local M = {}

-- ---------------------------------------------------------------------------
-- Easing constants (approximated as named curves for renderer)
-- ---------------------------------------------------------------------------
M.EASE_ENTRANCE = "ease_out_expo"   -- fast out, gentle settle (replaces slide-up)
M.EASE_EXIT     = "linear"          -- dissolve only
M.EASE_BREATHE  = "ease_in_out_sine"
M.EASE_DRAW     = "ease_out"        -- separator line / accent bar draw-on

-- ---------------------------------------------------------------------------
-- Card entrance (all non-ReadyCard cards)
-- Phase 1: opacity 0→1, scale 0.94→1.0
-- ---------------------------------------------------------------------------
M.ENTER_DURATION_MS  = 180   -- total entrance
M.ENTER_SCALE_FROM   = 0.94
M.ENTER_SCALE_TO     = 1.0
M.ENTER_OPACITY_FROM = 0.0
M.ENTER_OPACITY_TO   = 1.0

-- Text stagger for ObjectRecallCard (see cards.lua OBJECT_STAGGER_MS)
M.STAGGER_PRIMARY_MS  =   0   -- primary lands first (offset from card t=0)
M.STAGGER_EYEBROW_MS  =  40
M.STAGGER_DETAIL_MS   =  60
M.STAGGER_FOOTER_MS   =  80

-- ---------------------------------------------------------------------------
-- Card exit (all non-ReadyCard cards)
-- ---------------------------------------------------------------------------
M.EXIT_DURATION_MS = 120   -- opacity 1→0, linear, no scale

-- ---------------------------------------------------------------------------
-- ReadyCard breathing dot
-- Dot radius cycles: BREATHE_R_MIN → BREATHE_R_MAX
-- Glow circle appears at peak: radius BREATHE_GLOW_R, opacity BREATHE_GLOW_ALPHA
-- ---------------------------------------------------------------------------
M.BREATHE_CYCLE_MS   = 3200   -- full inhale+exhale cycle
M.BREATHE_R_MIN      =  4     -- px, exhale
M.BREATHE_R_MAX      =  9     -- px, inhale
M.BREATHE_GLOW_R     = 14     -- px, outer glow circle at peak only
M.BREATHE_GLOW_ALPHA = 0.18   -- opacity of glow at inhale peak

-- Satellite dots (4, compass points)
M.SATELLITE_R     = 2   -- px, fixed radius
M.SATELLITE_DIST  = 20  -- px from center (center is 128,128)
-- Positions: N=(128,108) E=(148,128) S=(128,148) W=(108,128)
M.SATELLITES = {
  { x = 128, y = 108 },  -- N
  { x = 148, y = 128 },  -- E
  { x = 128, y = 148 },  -- S
  { x = 108, y = 128 },  -- W
}

-- ---------------------------------------------------------------------------
-- LoadingCard arc spinner
-- ---------------------------------------------------------------------------
M.SPINNER_RADIUS_PX  = 48
M.SPINNER_STROKE_PX  =  2
M.SPINNER_RPM_MS     = 900   -- 1 revolution per 900ms, linear
-- Arc length breathes: ARC_MIN_DEG → ARC_MAX_DEG → ARC_MIN_DEG over ARC_BREATH_MS
M.SPINNER_ARC_MIN_DEG   =  90
M.SPINNER_ARC_MAX_DEG   = 240
M.SPINNER_ARC_BREATH_MS = 1800  -- ease-in-out

-- ---------------------------------------------------------------------------
-- QueryListeningCard waveform bars (7 bars)
-- ---------------------------------------------------------------------------
M.WAVE_BAR_COUNT  = 7
M.WAVE_BAR_WIDTH  = 2    -- px
M.WAVE_BAR_GAP    = 4    -- px between bar centers → centers at 104,112,120,128,136,144,152
M.WAVE_BAR_Y      = 136  -- center y
M.WAVE_BAR_H_MIN  =  8   -- px
M.WAVE_BAR_H_MAX  = 20   -- px
M.WAVE_BAR_CENTERS = { 104, 112, 120, 128, 136, 144, 152 }

-- ---------------------------------------------------------------------------
-- ObjectRecallCard draw-on elements (Phase 3 of entrance)
-- Separator line and left accent bar draw after text fades in.
-- ---------------------------------------------------------------------------
M.DRAWON_START_MS    = 100   -- offset from card t=0 when draw-on begins
M.DRAWON_DURATION_MS = 300   -- ms to complete each drawn element
-- Separator: draws outward from center in both directions simultaneously
-- Accent bar: draws downward from top of bar

-- ---------------------------------------------------------------------------
-- Auto-dismiss durations (ms) per card type
-- 0 = never auto-dismiss
-- ---------------------------------------------------------------------------
M.DISMISS_MS = {
  ReadyCard            =    0,
  SavedMemoryCard      = 1200,
  QueryListeningCard   =    0,   -- dismissed by answer arriving
  LoadingCard          =    0,   -- dismissed by answer arriving
  ObjectRecallCard     = 3500,
  CommitmentRecallCard = 4000,
  ProactiveMemoryCard  = 3500,
  PersonContextCard    = 3500,
  PrivacyPausedCard    =    0,   -- persistent until resumed
  ErrorCard            = 4000,
  LowConfidenceCard    = 3000,
}

-- ---------------------------------------------------------------------------
-- Transition: LoadingCard → ObjectRecallCard (the wow moment)
-- Phase 1: spinner fade out (t=0 to t=160ms)
-- Phase 2: card entrance, overlapping from t=100ms
-- Phase 3: draw-on elements from t=100ms (DRAWON_START_MS)
-- Total choreography completes at ~580ms
-- ---------------------------------------------------------------------------
M.LOADING_TO_OBJECT_SPINNER_FADE_MS = 160
M.LOADING_TO_OBJECT_CARD_START_MS   = 100   -- overlap with spinner fade

return M
