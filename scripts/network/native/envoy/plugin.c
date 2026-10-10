#include "source/extensions/dynamic_modules/abi/abi.h"
#include <stdint.h>
#include <string.h>
#include <unistd.h>

extern int ccsn_compatible_host(void);
extern int ccsn_native_timings(void *filter, int64_t values[6], unsigned *mask);

typedef struct {
    size_t description_len;
    char description[530];
    char templates[2][3400];
    size_t template_lengths[2];
    size_t offsets[2][6];
} TimingConfig;

/* Initialized once before the module is published to workers. */
static TimingConfig config;

typedef struct { const char *data; size_t length; } Span;

static const char *const names[] = {
    "e_hdr;dur=", "e_tcp;dur=",
    "e_tls;dur=", "e_ttfb;dur=",
    "e_pool;dur=", "e_rx;dur="
};

static int digits(Span span) {
    if (span.length == 0 || span.length > 20) return 0;
    for (size_t i = 0; i < span.length; i++)
        if (span.data[i] < '0' || span.data[i] > '9') return 0;
    return 1;
}

static size_t decimal(char *out, uint64_t value) {
    char reversed[20];
    size_t size = 0;
    do { reversed[size++] = (char)('0' + value % 10); value /= 10; } while (value);
    for (size_t i = 0; i < size; i++) out[i] = reversed[size - i - 1];
    return size;
}

static int append(char *out, size_t *used, size_t capacity, const char *data, size_t size) {
    if (size > capacity - *used) return 0;
    memcpy(out + *used, data, size);
    *used += size;
    return 1;
}

static int format_slow(char *out, size_t capacity, const TimingConfig *config, const Span values[6]) {
    size_t used = 0;
    for (size_t i = 0; i < 6; i++) {
        if (!digits(values[i])) continue;
        if ((used && !append(out, &used, capacity, ",", 1)) ||
            !append(out, &used, capacity, names[i], strlen(names[i])) ||
            !append(out, &used, capacity, values[i].data, values[i].length) ||
            !append(out, &used, capacity, config->description, config->description_len)) return -1;
    }
    return (int)used;
}

/* Both immutable templates contain every available metric and real zeros.
 * Larger durations or other missing intervals use the complete general path. */
static void initialize_templates(TimingConfig *settings) {
    const Span zero = {"0", 1};
    for (size_t variant = 0; variant < 2; variant++) {
        Span values[6];
        size_t used = 0;
        for (size_t i = 0; i < 6; i++) {
            values[i] = variant && i == 2 ? (Span){0} : zero;
            if (!values[i].length) continue;
            if (used) used++;
            settings->offsets[variant][i] = used + strlen(names[i]);
            used += strlen(names[i]) + 1 + settings->description_len;
        }
        int size = format_slow(settings->templates[variant], sizeof(settings->templates[variant]), settings, values);
        settings->template_lengths[variant] = size > 0 ? (size_t)size : 0;
    }
}

static int format(char *out, size_t capacity, const TimingConfig *settings, const Span values[6]) {
    size_t variant = values[2].length == 0 ||
                     (values[2].length == 1 && values[2].data[0] == '-');
    for (size_t i = 0; i < 6; i++) {
        if (variant && i == 2) continue;
        if (values[i].length != 1 || values[i].data[0] < '0' || values[i].data[0] > '9')
            return format_slow(out, capacity, settings, values);
    }
    size_t size = settings->template_lengths[variant];
    if (!size || size > capacity) return format_slow(out, capacity, settings, values);
    memcpy(out, settings->templates[variant], size);
    for (size_t i = 0; i < 6; i++)
        if (!variant || i != 2) out[settings->offsets[variant][i]] = values[i].data[0];
    return (int)size;
}

envoy_dynamic_module_type_abi_version_module_ptr envoy_dynamic_module_on_program_init(void) {
    if (!ccsn_compatible_host()) return NULL;
    char hostname[257] = {0};
    if (gethostname(hostname, sizeof(hostname) - 1) != 0) memcpy(hostname, "envoy", 6);
    int token = 1;
    for (size_t i = 0; hostname[i]; i++) {
        unsigned char ch = (unsigned char)hostname[i];
        if (!((ch >= 'a' && ch <= 'z') || (ch >= 'A' && ch <= 'Z') ||
              (ch >= '0' && ch <= '9') || ch == '-' || ch == '.' || ch == '_')) token = 0;
    }
    size_t at = token ? 6 : 7;
    memcpy(config.description, token ? ";desc=" : ";desc=\"", at);
    for (size_t i = 0; hostname[i]; i++) {
        unsigned char ch = (unsigned char)hostname[i];
        if (ch < 32 || ch == 127) continue;
        if (!token && (ch == '\"' || ch == '\\')) config.description[at++] = '\\';
        config.description[at++] = (char)ch;
    }
    if (!token) config.description[at++] = '\"';
    config.description_len = at;
    initialize_templates(&config);
    return ENVOY_DYNAMIC_MODULES_ABI_VERSION;
}

envoy_dynamic_module_type_http_filter_config_module_ptr envoy_dynamic_module_on_http_filter_config_new(
    envoy_dynamic_module_type_http_filter_config_envoy_ptr host,
    envoy_dynamic_module_type_envoy_buffer name, envoy_dynamic_module_type_envoy_buffer data) {
    (void)host; (void)data;
    if (name.length != 13 || memcmp(name.ptr, "server-timing", 13)) return NULL;
    return &config;
}

envoy_dynamic_module_type_http_filter_module_ptr envoy_dynamic_module_on_http_filter_new(
    envoy_dynamic_module_type_http_filter_config_module_ptr settings,
    envoy_dynamic_module_type_http_filter_envoy_ptr host) {
    (void)host;
    return (void *)settings;
}

envoy_dynamic_module_type_on_http_filter_response_headers_status
    envoy_dynamic_module_on_http_filter_response_headers(
        envoy_dynamic_module_type_http_filter_envoy_ptr host,
        envoy_dynamic_module_type_http_filter_module_ptr settings, bool end) {
    (void)end;
    int64_t native[6];
    unsigned available = 0;
    Span values[6] = {{0}};
    char decimals[6][20];
    char output[4096];
    if (ccsn_native_timings(host, native, &available)) {
        for (size_t i = 0; i < 6; i++)
            if (available & (1u << i))
                values[i] = (Span){decimals[i], decimal(decimals[i], (uint64_t)native[i])};
        int size = format(output, sizeof(output), settings, values);
        if (size > 0)
            envoy_dynamic_module_callback_http_add_header(host,
                envoy_dynamic_module_type_http_header_type_ResponseHeader,
                (envoy_dynamic_module_type_module_buffer){"server-timing", 13},
                (envoy_dynamic_module_type_module_buffer){output, (size_t)size});
    }
    return envoy_dynamic_module_type_on_http_filter_response_headers_status_Continue;
}

/* Required ABI hooks: no buffering, request state, or callouts. */
void envoy_dynamic_module_on_http_filter_config_destroy(
    envoy_dynamic_module_type_http_filter_config_module_ptr filter_config_ptr) {
    (void)filter_config_ptr;
}

envoy_dynamic_module_type_on_http_filter_request_headers_status envoy_dynamic_module_on_http_filter_request_headers(
    envoy_dynamic_module_type_http_filter_envoy_ptr filter_envoy_ptr,
    envoy_dynamic_module_type_http_filter_module_ptr filter_module_ptr, bool end_of_stream) {
    (void)filter_envoy_ptr;
    (void)filter_module_ptr;
    (void)end_of_stream;
    return envoy_dynamic_module_type_on_http_filter_request_headers_status_Continue;
}

envoy_dynamic_module_type_on_http_filter_request_body_status envoy_dynamic_module_on_http_filter_request_body(
    envoy_dynamic_module_type_http_filter_envoy_ptr filter_envoy_ptr,
    envoy_dynamic_module_type_http_filter_module_ptr filter_module_ptr, bool end_of_stream) {
    (void)filter_envoy_ptr;
    (void)filter_module_ptr;
    (void)end_of_stream;
    return envoy_dynamic_module_type_on_http_filter_request_body_status_Continue;
}

envoy_dynamic_module_type_on_http_filter_request_trailers_status envoy_dynamic_module_on_http_filter_request_trailers(
    envoy_dynamic_module_type_http_filter_envoy_ptr filter_envoy_ptr,
    envoy_dynamic_module_type_http_filter_module_ptr filter_module_ptr) {
    (void)filter_envoy_ptr;
    (void)filter_module_ptr;
    return envoy_dynamic_module_type_on_http_filter_request_trailers_status_Continue;
}

envoy_dynamic_module_type_on_http_filter_response_body_status envoy_dynamic_module_on_http_filter_response_body(
    envoy_dynamic_module_type_http_filter_envoy_ptr filter_envoy_ptr,
    envoy_dynamic_module_type_http_filter_module_ptr filter_module_ptr, bool end_of_stream) {
    (void)filter_envoy_ptr;
    (void)filter_module_ptr;
    (void)end_of_stream;
    return envoy_dynamic_module_type_on_http_filter_response_body_status_Continue;
}

envoy_dynamic_module_type_on_http_filter_response_trailers_status envoy_dynamic_module_on_http_filter_response_trailers(
    envoy_dynamic_module_type_http_filter_envoy_ptr filter_envoy_ptr,
    envoy_dynamic_module_type_http_filter_module_ptr filter_module_ptr) {
    (void)filter_envoy_ptr;
    (void)filter_module_ptr;
    return envoy_dynamic_module_type_on_http_filter_response_trailers_status_Continue;
}

void envoy_dynamic_module_on_http_filter_stream_complete(
    envoy_dynamic_module_type_http_filter_envoy_ptr filter_envoy_ptr,
    envoy_dynamic_module_type_http_filter_module_ptr filter_module_ptr) {
    (void)filter_envoy_ptr;
    (void)filter_module_ptr;
}

void envoy_dynamic_module_on_http_filter_destroy(
    envoy_dynamic_module_type_http_filter_module_ptr filter_module_ptr) {
    (void)filter_module_ptr;
}

void envoy_dynamic_module_on_http_filter_http_callout_done(
    envoy_dynamic_module_type_http_filter_envoy_ptr filter_envoy_ptr,
    envoy_dynamic_module_type_http_filter_module_ptr filter_module_ptr, uint64_t callout_id,
    envoy_dynamic_module_type_http_callout_result result,
    envoy_dynamic_module_type_envoy_http_header* headers, size_t headers_size,
    envoy_dynamic_module_type_envoy_buffer* body_chunks, size_t body_chunks_size) {
    (void)filter_envoy_ptr;
    (void)filter_module_ptr;
    (void)callout_id;
    (void)result;
    (void)headers;
    (void)headers_size;
    (void)body_chunks;
    (void)body_chunks_size;
}

void envoy_dynamic_module_on_http_filter_http_stream_headers(
    envoy_dynamic_module_type_http_filter_envoy_ptr filter_envoy_ptr,
    envoy_dynamic_module_type_http_filter_module_ptr filter_module_ptr, uint64_t stream_id,
    envoy_dynamic_module_type_envoy_http_header* headers, size_t headers_size, bool end_stream) {
    (void)filter_envoy_ptr;
    (void)filter_module_ptr;
    (void)stream_id;
    (void)headers;
    (void)headers_size;
    (void)end_stream;
}

void envoy_dynamic_module_on_http_filter_http_stream_data(
    envoy_dynamic_module_type_http_filter_envoy_ptr filter_envoy_ptr,
    envoy_dynamic_module_type_http_filter_module_ptr filter_module_ptr, uint64_t stream_id,
    const envoy_dynamic_module_type_envoy_buffer* data, size_t data_count, bool end_stream) {
    (void)filter_envoy_ptr;
    (void)filter_module_ptr;
    (void)stream_id;
    (void)data;
    (void)data_count;
    (void)end_stream;
}

void envoy_dynamic_module_on_http_filter_http_stream_trailers(
    envoy_dynamic_module_type_http_filter_envoy_ptr filter_envoy_ptr,
    envoy_dynamic_module_type_http_filter_module_ptr filter_module_ptr, uint64_t stream_id,
    envoy_dynamic_module_type_envoy_http_header* trailers, size_t trailers_size) {
    (void)filter_envoy_ptr;
    (void)filter_module_ptr;
    (void)stream_id;
    (void)trailers;
    (void)trailers_size;
}

void envoy_dynamic_module_on_http_filter_http_stream_complete(
    envoy_dynamic_module_type_http_filter_envoy_ptr filter_envoy_ptr,
    envoy_dynamic_module_type_http_filter_module_ptr filter_module_ptr, uint64_t stream_id) {
    (void)filter_envoy_ptr;
    (void)filter_module_ptr;
    (void)stream_id;
}

void envoy_dynamic_module_on_http_filter_http_stream_reset(
    envoy_dynamic_module_type_http_filter_envoy_ptr filter_envoy_ptr,
    envoy_dynamic_module_type_http_filter_module_ptr filter_module_ptr, uint64_t stream_id,
    envoy_dynamic_module_type_http_stream_reset_reason reason) {
    (void)filter_envoy_ptr;
    (void)filter_module_ptr;
    (void)stream_id;
    (void)reason;
}

void envoy_dynamic_module_on_http_filter_scheduled(
    envoy_dynamic_module_type_http_filter_envoy_ptr filter_envoy_ptr,
    envoy_dynamic_module_type_http_filter_module_ptr filter_module_ptr, uint64_t event_id) {
    (void)filter_envoy_ptr;
    (void)filter_module_ptr;
    (void)event_id;
}

void envoy_dynamic_module_on_http_filter_downstream_above_write_buffer_high_watermark(
    envoy_dynamic_module_type_http_filter_envoy_ptr filter_envoy_ptr,
    envoy_dynamic_module_type_http_filter_module_ptr filter_module_ptr) {
    (void)filter_envoy_ptr;
    (void)filter_module_ptr;
}

void envoy_dynamic_module_on_http_filter_downstream_below_write_buffer_low_watermark(
    envoy_dynamic_module_type_http_filter_envoy_ptr filter_envoy_ptr,
    envoy_dynamic_module_type_http_filter_module_ptr filter_module_ptr) {
    (void)filter_envoy_ptr;
    (void)filter_module_ptr;
}
