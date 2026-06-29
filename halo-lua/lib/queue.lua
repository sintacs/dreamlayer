-- queue.lua : tiny FIFO
local Queue = {}
Queue.__index = Queue
function Queue.new() return setmetatable({first=1, last=0, items={}}, Queue) end
function Queue:push(v) self.last = self.last + 1; self.items[self.last] = v end
function Queue:pop()
  if self.first > self.last then return nil end
  local v = self.items[self.first]; self.items[self.first] = nil; self.first = self.first + 1
  return v
end
function Queue:empty() return self.first > self.last end
function Queue:size() return self.last - self.first + 1 end
return Queue
