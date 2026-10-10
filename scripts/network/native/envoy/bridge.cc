#include "source/extensions/filters/http/dynamic_modules/filter.h"
#include <cstdint>

namespace Native = Envoy::Extensions::DynamicModules::HttpFilters;

extern "C" int ccsn_native_timings(void *state, int64_t values[6], unsigned *mask) {
  if (!state || !values || !mask) return 0;
  auto *processor = static_cast<Native::DynamicModuleHttpFilter *>(state);
  const Envoy::StreamInfo::StreamInfo &info = *processor->streamInfo();
  *mask = 0;
  const auto set = [&](unsigned index, std::chrono::nanoseconds duration) {
    if (duration.count() < 0) return;
    values[index] = std::chrono::duration_cast<std::chrono::milliseconds>(duration).count();
    *mask |= 1u << index;
  };
  const auto interval = [&](unsigned index, const auto &begin, const auto &end) {
    if (begin.has_value() && end.has_value()) set(index, *end - *begin);
  };
  const auto completed = info.requestComplete();
  if (completed.has_value()) set(0, *completed);
  else set(0, processor->dispatcher()->timeSource().monotonicTime() - info.startTimeMonotonic());
  const auto upstream = info.upstreamInfo();
  if (upstream.has_value()) {
    const auto &timing = upstream->upstreamTiming();
    interval(1, timing.upstream_connect_start_, timing.upstream_connect_complete_);
    interval(2, timing.upstream_connect_complete_, timing.upstream_handshake_complete_);
    interval(3, timing.first_upstream_tx_byte_sent_, timing.first_upstream_rx_byte_received_);
    const auto pool = timing.connectionPoolCallbackLatency();
    if (pool.has_value()) set(4, *pool);
  }
  const auto downstream = info.downstreamTiming();
  if (downstream.has_value()) {
    const auto received = downstream->lastDownstreamRxByteReceived();
    if (received.has_value()) set(5, *received - info.startTimeMonotonic());
  }
  return 1;
}
