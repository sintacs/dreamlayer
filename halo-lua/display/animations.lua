
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
  PrivacyPausedCard    =    0,
  ErrorCard            = 4000,
  LowConfidenceCard    = 3000,
}

M.LOADING_TO_OBJECT_SPINNER_FADE_MS = 160
M.LOADING_TO_OBJECT_CARD_START_MS   = 100

return M
