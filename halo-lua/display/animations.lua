
local M = {}

M.EASE_ENTRANCE = "ease_out_expo"
M.EASE_EXIT     = "linear"
M.EASE_BREATHE  = "ease_in_out_sine"
M.EASE_DRAW     = "ease_out"

M.ENTER_DURATION_MS  = 180
M.ENTER_SCALE_FROM   = 0.94
M.ENTER_SCALE_TO     = 1.0
M.ENTER_OPACITY_FROM = 0.0
M.ENTER_OPACITY_TO   = 1.0

M.STAGGER_PRIMARY_MS  =   0
M.STAGGER_EYEBROW_MS  =  40
M.STAGGER_DETAIL_MS   =  60
M.STAGGER_FOOTER_MS   =  80

M.EXIT_DURATION_MS = 120

M.BREATHE_CYCLE_MS   = 3200
M.BREATHE_R_MIN      =  5
M.BREATHE_R_MAX      = 10
M.BREATHE_GLOW_R     = 16
M.BREATHE_GLOW_ALPHA = 0.18

M.SATELLITE_R    = 2
M.SATELLITE_DIST = 22
M.SATELLITES = {
  { x = 128, y = 106 },
  { x = 144, y = 112 },
  { x = 150, y = 128 },
  { x = 144, y = 144 },
  { x = 128, y = 150 },
  { x = 112, y = 144 },
  { x = 106, y = 128 },
  { x = 112, y = 112 },
}

M.SPINNER_RADIUS_PX  = 52
M.SPINNER_STROKE_PX  =  2
M.SPINNER_RPM_MS     = 900
M.SPINNER_ARC_MIN_DEG   =  80
M.SPINNER_ARC_MAX_DEG   = 260
M.SPINNER_ARC_BREATH_MS = 1800

M.WAVE_BAR_COUNT  = 7
M.WAVE_BAR_WIDTH  = 2
M.WAVE_BAR_GAP    = 6
M.WAVE_BAR_Y      = 138
M.WAVE_BAR_H_MIN  =  6
M.WAVE_BAR_H_MAX  = 22
M.WAVE_BAR_CENTERS = { 101, 109, 117, 128, 139, 147, 155 }

M.DRAWON_START_MS    = 100
M.DRAWON_DURATION_MS = 300

M.DISMISS_MS = {
  ReadyCard            =    0,
  SavedMemoryCard      = 1200,
  QueryListeningCard   =    0,
  LoadingCard          =    0,
  ObjectRecallCard     = 3500,
  CommitmentRecallCard = 4000,
  ProactiveMemoryCard  = 3500,
  PersonContextCard    = 3500,
  PrivacyVeilCard    =    0,
  ErrorCard            = 4000,
  LowConfidenceCard    = 3000,
  TruthLensCard        = 5000,
}

M.LOADING_TO_OBJECT_SPINNER_FADE_MS = 160
M.LOADING_TO_OBJECT_CARD_START_MS   = 100

-- ---------------------------------------------------------------------------
-- Meridian (Cinema v2) — every duration/geometry constant lives here;
-- display modules read these and NEVER hardcode milliseconds.
-- Survivors from Halo Cinema v1 (Ghost Wake, Truth Ripple, acoustics)
-- keep their SIG_* names. The killed v1 signatures (Iris Bloom, Prism
-- Slide, Confidence Halo orbit, Memory Comet) are removed with their
-- replacements shipping in the same PR — see docs/CINEMA_V2_DELTAS.md.
-- ---------------------------------------------------------------------------

-- S2 Ghost Wake (WorldAnchorCard ENTER: per-char Perlin condensation)
M.SIG_GHOSTWAKE_MS        = 320
M.SIG_GHOSTWAKE_JITTER_PX = 2
M.SIG_GHOSTWAKE_Y_FROM    = 0      -- ghost slot luma ramp (0-1023 scale)
M.SIG_GHOSTWAKE_Y_TO      = 400

-- S5 Truth Ripple (Truth Lens verdict ENTER: ripple from eye landmark)
M.SIG_RIPPLE_MS      = 400
M.SIG_RIPPLE_R_MAX   = 120
M.SIG_RIPPLE_CR      = 80     -- warm shift peak on the ripple slot
M.SIG_RIPPLE_COLD_MS = 240    -- cold recovery on false-positive dismiss
M.SIG_RIPPLE_CB      = 60     -- cold shift on recovery

-- HUD acoustics analogs (docs/HALO_CINEMA_V1.md §1.3, kept)
M.SIG_CHIME_MS       = 220    -- memory saved: single expanding ring
M.SIG_CHIME_R_FROM   = 8
M.SIG_CHIME_R_TO     = 28
M.SIG_CHORD_STEP_MS  = 40     -- person recognized: 3-arc arpeggio step
M.SIG_RUMBLE_MS      = 100    -- privacy veil: full-field dim pre-slam
M.SIG_RUMBLE_Y_DROP  = 160    -- dynamic slot luma drop during rumble

-- ---------------------------------------------------------------------------
-- Focus law (docs/cinema_v2/focus.md): condensation / recession
-- ---------------------------------------------------------------------------
M.SIG_FOCUS_TRAVEL_MS   = 140   -- head flight rim -> core
M.SIG_FOCUS_LAND_MS     = 100   -- landing ring collapse + content bloom
M.SIG_FOCUS_TRAIL_MS    = 60    -- ghost-slot Y ramp trailing edge (from v1 iris)
M.SIG_FOCUS_LAND_R_FROM = 56
M.SIG_FOCUS_LAND_R_TO   = 36
M.SIG_FOCUS_RING_R      = 92    -- landed hold ring radius (sweep = confidence)
M.SIG_RECEDE_MS         = 160   -- content contracts, head flies home
M.SIG_RECEDE_TEXT_CUT   = 0.4   -- text cuts at this fraction (kill-list #2)
M.SIG_FOCUS_XFADE_LAG_MS = 40   -- condense start lag during crossfade

-- ---------------------------------------------------------------------------
-- The Horizon (docs/cinema_v2/horizon.md): the persistent rim instrument
-- ---------------------------------------------------------------------------
M.MER_TRACK_R          = 100   -- rim track radius (1px ghost arc)
M.MER_MARK_BASE_R      = 101   -- marks radiate outward from here
M.MER_RIM_R            = 105   -- nominal mark anchor (travel origin)
M.MER_NOW_DEG          = -90   -- 12 o'clock, screen coords
M.MER_DEG_PER_HOUR     = 30    -- full dial = 12h
M.MER_WINDOW_HOURS     = 5     -- lookback/lookahead cap (150 deg each)
M.MER_SEAM_FROM_DEG    = 60    -- past cap edge (seam start)
M.MER_SEAM_TO_DEG      = 120   -- future cap edge (seam end, via bottom)
M.MER_ELDER_DEG        = 58    -- older-than-window compression tick
M.MER_FUTURE_CAP_DEG   = 122   -- further-than-window promise dot
M.MER_MARKS_MAX        = 48
M.MER_MARK_MERGE_DEG   = 3     -- memory marks within this merge (+len)
M.MER_MARK_LEN         = { [0] = 3, [1] = 6, [2] = 9 }  -- by luma tier
M.MER_NOW_LEN_MIN      = 6     -- notch breathe (geometric, no slot)
M.MER_NOW_LEN_MAX      = 9
M.MER_STALE_MS         = 30000 -- no horizon frame for this long -> tier drop
M.MER_ARRIVAL_PULSE_MS = 300   -- mark pulse after recession lands
M.MER_HIGHLIGHT_MS     = 2400  -- anchor-echo provenance brighten
M.MER_DREAM_ENTER_MS   = 300   -- light change into dream (no scene cut)
M.MER_DREAM_EXIT_MS    = 200
M.MER_PROMISE_R        = 105   -- on-rim promise dot anchor
M.MER_PROMISE_SLIP_R   = 95    -- cracking/shattered inward position
M.MER_PROMISE_STACK_PX = 7     -- radial pitch for same-hour promises

-- ---------------------------------------------------------------------------
-- Testimony Thread (docs/cinema_v2/testimony.md): Truth Lens verdict
-- ---------------------------------------------------------------------------
M.TESTIMONY_R        = 64    -- thread radius (clears the verdict capsule)
M.TESTIMONY_SLOT_DEG = 40    -- 9 stages x 40 deg
M.TESTIMONY_STAGE_MS = 80    -- accumulation per stage after the ripple
M.TESTIMONY_TEAR_PX  = 3     -- radial jitter on torn (deceptive) stages

return M
