-- utils.lua : small pure helpers
local M = {}
function M.clamp(v, lo, hi) if v < lo then return lo elseif v > hi then return hi end return v end
function M.round(v) return math.floor(v + 0.5) end
function M.lerp(a, b, t) return a + (b - a) * t end
function M.map(t) local n = 0 for _ in pairs(t) do n = n + 1 end return n end
function M.shallow_copy(t) local r = {} for k,v in pairs(t) do r[k]=v end return r end
function M.wrap(text, max_len)
  local lines, line = {}, ""
  for word in tostring(text):gmatch("%S+") do
    if #line == 0 then line = word
    elseif #line + 1 + #word <= max_len then line = line .. " " .. word
    else lines[#lines+1] = line; line = word end
  end
  if #line > 0 then lines[#lines+1] = line end
  return lines
end
return M
