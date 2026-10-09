-- Response-only LuaJIT filter; native formatters supply this proxy's timing tuple.
local ffi = require("ffi")
ffi.cdef[[
struct timespec { long tv_sec; long tv_nsec; };
int clock_gettime(int clock_id, struct timespec *value);
]]
local now = ffi.new("struct timespec[1]")
local output = ffi.new("char[4096]")
local names = {
  "envoy_headers", "envoy_upstream_tcp", "envoy_upstream_tls",
  "envoy_upstream_headers", "envoy_upstream_pool", "envoy_request_receive"
}
local cached_host, description, templates, offsets

local function initialize(host)
  cached_host = host
  description = ';desc="' .. host:gsub("[%c]", ""):gsub('[\\"]', '\\%0') .. '"'
  templates, offsets = {}, {}
  for variant = 1, 2 do
    local parts, positions, size = {}, {}, 0
    for i = 1, 6 do
      if variant == 1 or i ~= 3 then
        local prefix = (size > 0 and "," or "") .. names[i] .. ";dur="
        positions[i] = size + #prefix
        local part = prefix .. "0" .. description
        parts[#parts + 1], size = part, size + #part
      end
    end
    templates[variant], offsets[variant] = table.concat(parts), positions
  end
end

function envoy_on_response(handle)
  local headers = handle:headers()
  local raw = headers:get("x-ccsn-envoy-timing")
  if raw then
    local started, tcp, tls, upstream, pool, receive, host =
      raw:match("^([0-9]+),([^,]*),([^,]*),([^,]*),([^,]*),([^,]*),(.*)$")
    if host and #started >= 10 and ffi.C.clock_gettime(0, now) == 0 then
      local seconds = tonumber(started:sub(1, -10))
      local fraction = tonumber(started:sub(-9))
      if seconds and fraction then
        local elapsed = math.max(0, math.floor(((tonumber(now[0].tv_sec) - seconds) * 1000000000
                                               + tonumber(now[0].tv_nsec) - fraction) / 1000000))
        if host ~= cached_host then initialize(host) end
        local values = {tostring(elapsed), tcp, tls, upstream, pool, receive}
        local variant = (tls == "" or tls == "-") and 2 or 1
        local fast = #templates[variant] <= 4096
        for i = 1, 6 do
          if variant == 1 or i ~= 3 then
            local value = values[i]
            local digit = value:byte()
            if #value ~= 1 or digit < 48 or digit > 57 then fast = false; break end
          end
        end
        if fast then
          local template = templates[variant]
          ffi.copy(output, template, #template)
          for i = 1, 6 do
            if variant == 1 or i ~= 3 then output[offsets[variant][i]] = values[i]:byte() end
          end
          headers:add("server-timing", ffi.string(output, #template))
        else
          local parts = {}
          for i = 1, 6 do
            local value = values[i]
            if value:match("^[0-9]+$") then parts[#parts + 1] = names[i] .. ";dur=" .. value .. description end
          end
          headers:add("server-timing", table.concat(parts, ","))
        end
      end
    end
  end
  headers:remove("x-ccsn-envoy-timing")
end
