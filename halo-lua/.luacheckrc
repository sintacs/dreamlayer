-- Luacheck config for the device Lua (CI: .github/workflows/lua.yml).
-- The bar: no undefined variables (except the device runtime's globals),
-- no shadowing errors, no syntax drift. Cosmetic warnings (unused args in
-- callback signatures, line length) stay out of the gate.
std = "lua53"

-- The Halo runtime injects `frame`; compat/frame_adapter.lua builds and
-- owns `_G.halo`; main.lua exposes the tick for the test harness.
read_globals = { "frame" }
globals = { "halo", "_dreamlayer_tick" }

-- 211/212/213: unused locals/args/loop-vars — common in callback signatures
-- and intentional in prototypes. 542: empty if branch (used for documented
-- no-op arms). 611/612/613/614: whitespace. 631: line length.
ignore = { "211", "212", "213", "542",
           "611", "612", "613", "614", "631" }

exclude_files = { "display/cinema_v2_prototypes/*.lua" }
