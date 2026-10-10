#include <ngx_config.h>
#include <ngx_core.h>
#include <ngx_http.h>

typedef struct {
    ngx_str_t description;
    ngx_str_t attempt_one;
    ngx_str_t fast;
    size_t digits[3];
} ngx_http_ccsn_timing_main_conf_t;

typedef struct {
    ngx_flag_t enabled;
    ngx_http_ccsn_timing_main_conf_t *timing;
} ngx_http_ccsn_timing_conf_t;

static ngx_int_t ngx_http_ccsn_timing_init(ngx_conf_t *cf);
static void *ngx_http_ccsn_timing_create(ngx_conf_t *cf);
static void *ngx_http_ccsn_timing_create_main(ngx_conf_t *cf);
static char *ngx_http_ccsn_timing_merge(ngx_conf_t *cf, void *parent, void *child);
static ngx_http_output_header_filter_pt ngx_http_ccsn_timing_next;

static u_char *
ngx_http_ccsn_timing_number(u_char *cursor, ngx_msec_t value)
{
    u_char digits[NGX_INT64_LEN], *end = digits + sizeof(digits), *start = end;
    do {
        *--start = (u_char) ('0' + value % 10);
        value /= 10;
    } while (value != 0);
    return ngx_cpymem(cursor, start, end - start);
}

static u_char *
ngx_http_ccsn_timing_attempt(const ngx_http_ccsn_timing_main_conf_t *timing,
                            u_char *cursor, ngx_uint_t attempt)
{
    if (attempt == 1) {
        return ngx_cpymem(cursor, timing->attempt_one.data,
                          timing->attempt_one.len);
    }
    cursor = ngx_cpymem(cursor, timing->description.data,
                       timing->description.len - 1);
    cursor = ngx_cpymem(cursor, " attempt ", sizeof(" attempt ") - 1);
    cursor = ngx_http_ccsn_timing_number(cursor, attempt);
    *cursor++ = '"';
    return cursor;
}

static ngx_command_t ngx_http_ccsn_timing_commands[] = {
    { ngx_string("ccsn_server_timing"),
      NGX_HTTP_MAIN_CONF|NGX_HTTP_SRV_CONF|NGX_HTTP_LOC_CONF|NGX_CONF_FLAG,
      ngx_conf_set_flag_slot, NGX_HTTP_LOC_CONF_OFFSET,
      offsetof(ngx_http_ccsn_timing_conf_t, enabled), NULL },
    ngx_null_command
};

static ngx_http_module_t ngx_http_ccsn_timing_ctx = {
    NULL, ngx_http_ccsn_timing_init, ngx_http_ccsn_timing_create_main, NULL, NULL, NULL,
    ngx_http_ccsn_timing_create, ngx_http_ccsn_timing_merge
};

ngx_module_t ngx_http_ccsn_server_timing_module = {
    NGX_MODULE_V1, &ngx_http_ccsn_timing_ctx, ngx_http_ccsn_timing_commands,
    NGX_HTTP_MODULE, NULL, NULL, NULL, NULL, NULL, NULL, NULL,
    NGX_MODULE_V1_PADDING
};

/* Keep general integer formatting out of the common header-filter frame. */
static ngx_str_t __attribute__((noinline))
ngx_http_ccsn_timing_general(ngx_http_request_t *r,
    const ngx_http_ccsn_timing_main_conf_t *timing,
    ngx_http_upstream_state_t *states, ngx_uint_t count,
    ngx_msec_int_t elapsed)
{
    ngx_uint_t i, attempt;
    size_t capacity;
    u_char *buffer, *cursor;
    /* Each attempt emits two metrics; reserve room for integer values and labels. */
    capacity = 96 + timing->description.len
               + count * (256 + 2 * timing->description.len);
    buffer = ngx_pnalloc(r->pool, capacity);
    if (buffer == NULL) {
        return (ngx_str_t) ngx_null_string;
    }
    cursor = buffer;
    cursor = ngx_cpymem(cursor, "nginx_headers;dur=", sizeof("nginx_headers;dur=") - 1);
    cursor = ngx_http_ccsn_timing_number(cursor, (ngx_msec_t) elapsed);
    cursor = ngx_cpymem(cursor, timing->description.data,
                       timing->description.len);
    attempt = 0;
    for (i = 0; i < count; i++) {
        if (states[i].peer == NULL) {
            continue;
        }
        attempt++;
        if (states[i].connect_time != (ngx_msec_t) -1) {
            cursor = ngx_cpymem(cursor, ", nginx_upstream_connect;dur=",
                               sizeof(", nginx_upstream_connect;dur=") - 1);
            cursor = ngx_http_ccsn_timing_number(cursor, states[i].connect_time);
            if (count == 1) {
                cursor = ngx_cpymem(cursor, timing->description.data,
                                   timing->description.len);
            } else {
                cursor = ngx_http_ccsn_timing_attempt(timing, cursor, attempt);
            }
        }
        if (states[i].header_time != (ngx_msec_t) -1) {
            cursor = ngx_cpymem(cursor, ", nginx_upstream_headers;dur=",
                               sizeof(", nginx_upstream_headers;dur=") - 1);
            cursor = ngx_http_ccsn_timing_number(cursor, states[i].header_time);
            if (count == 1) {
                cursor = ngx_cpymem(cursor, timing->description.data,
                                   timing->description.len);
            } else {
                cursor = ngx_http_ccsn_timing_attempt(timing, cursor, attempt);
            }
        }
    }
    return (ngx_str_t) { (size_t) (cursor - buffer), buffer };
}

static ngx_int_t
ngx_http_ccsn_timing_filter(ngx_http_request_t *r)
{
    ngx_http_ccsn_timing_conf_t *conf;
    const ngx_http_ccsn_timing_main_conf_t *timing;
    ngx_http_upstream_state_t *states;
    ngx_table_elt_t *header;
    ngx_time_t *now;
    ngx_msec_int_t elapsed;
    ngx_uint_t count;
    u_char *buffer, *cursor;

    conf = ngx_http_get_module_loc_conf(r, ngx_http_ccsn_server_timing_module);
    if (!conf->enabled || r != r->main) {
        return ngx_http_ccsn_timing_next(r);
    }
    timing = conf->timing;
    count = r->upstream_states == NULL ? 0 : r->upstream_states->nelts;
    states = count == 0 ? NULL : r->upstream_states->elts;
    now = ngx_timeofday();
    elapsed = (ngx_msec_int_t) ((now->sec - r->start_sec) * 1000
                              + (now->msec - r->start_msec));
    elapsed = ngx_max(elapsed, 0);
    if (count == 1 && states[0].peer != NULL && elapsed < 10
        && states[0].connect_time < 10 && states[0].header_time < 10) {
        buffer = ngx_pnalloc(r->pool, timing->fast.len);
        if (buffer == NULL) {
            return NGX_ERROR;
        }
        cursor = ngx_cpymem(buffer, timing->fast.data,
                           timing->fast.len);
        buffer[timing->digits[0]] = (u_char) ('0' + elapsed);
        buffer[timing->digits[1]] = (u_char) ('0' + states[0].connect_time);
        buffer[timing->digits[2]] = (u_char) ('0' + states[0].header_time);
        goto write_header;
    }
    {
        ngx_str_t value = ngx_http_ccsn_timing_general(r, timing, states,
                                                      count, elapsed);
        if (value.data == NULL) {
            return NGX_ERROR;
        }
        buffer = value.data;
        cursor = value.data + value.len;
    }
write_header:
    /* Append a separate field; upstream fields remain byte-for-byte intact. */
    header = ngx_list_push(&r->headers_out.headers);
    if (header == NULL) {
        return NGX_ERROR;
    }
    header->hash = 1;
    ngx_str_set(&header->key, "Server-Timing");
    header->lowcase_key = NULL;
    header->next = NULL;
    header->value.data = buffer;
    header->value.len = cursor - buffer;
    return ngx_http_ccsn_timing_next(r);
}

static ngx_int_t
ngx_http_ccsn_timing_init(ngx_conf_t *cf)
{
    ngx_http_ccsn_timing_main_conf_t *timing;
    u_char *cursor, *buffer;
    size_t i;

    timing = ngx_http_conf_get_module_main_conf(cf, ngx_http_ccsn_server_timing_module);
    /* Host labels are immutable; escape and copy them once per configuration. */
    buffer = ngx_pnalloc(cf->pool, 2 * cf->cycle->hostname.len + 32);
    if (buffer == NULL) {
        return NGX_ERROR;
    }
    cursor = ngx_cpymem(buffer, ";desc=\"", sizeof(";desc=\"") - 1);
    for (i = 0; i < cf->cycle->hostname.len; i++) {
        u_char character = cf->cycle->hostname.data[i];
        if (character < 32 || character == 127) {
            continue;
        }
        if (character == '"' || character == '\\') {
            *cursor++ = '\\';
        }
        *cursor++ = character;
    }
    *cursor++ = '"';
    timing->description.data = buffer;
    timing->description.len = cursor - buffer;
    buffer = ngx_pnalloc(cf->pool, timing->description.len + 10);
    if (buffer == NULL) {
        return NGX_ERROR;
    }
    cursor = ngx_cpymem(buffer, timing->description.data,
                       timing->description.len - 1);
    cursor = ngx_cpymem(cursor, " attempt 1\"", sizeof(" attempt 1\"") - 1);
    timing->attempt_one.data = buffer;
    timing->attempt_one.len = cursor - buffer;
    buffer = ngx_pnalloc(cf->pool, 128 + 3 * timing->description.len);
    if (buffer == NULL) {
        return NGX_ERROR;
    }
    cursor = ngx_cpymem(buffer, "nginx_headers;dur=", sizeof("nginx_headers;dur=") - 1);
    timing->digits[0] = cursor - buffer;
    *cursor++ = '0';
    cursor = ngx_cpymem(cursor, timing->description.data,
                       timing->description.len);
    cursor = ngx_cpymem(cursor, ", nginx_upstream_connect;dur=",
                       sizeof(", nginx_upstream_connect;dur=") - 1);
    timing->digits[1] = cursor - buffer;
    *cursor++ = '0';
    cursor = ngx_cpymem(cursor, timing->description.data,
                       timing->description.len);
    cursor = ngx_cpymem(cursor, ", nginx_upstream_headers;dur=",
                       sizeof(", nginx_upstream_headers;dur=") - 1);
    timing->digits[2] = cursor - buffer;
    *cursor++ = '0';
    cursor = ngx_cpymem(cursor, timing->description.data,
                       timing->description.len);
    timing->fast.data = buffer;
    timing->fast.len = cursor - buffer;
    ngx_http_ccsn_timing_next = ngx_http_top_header_filter;
    ngx_http_top_header_filter = ngx_http_ccsn_timing_filter;
    return NGX_OK;
}

static void *
ngx_http_ccsn_timing_create_main(ngx_conf_t *cf)
{
    return ngx_pcalloc(cf->pool, sizeof(ngx_http_ccsn_timing_main_conf_t));
}

static void *
ngx_http_ccsn_timing_create(ngx_conf_t *cf)
{
    ngx_http_ccsn_timing_conf_t *conf;
    conf = ngx_pcalloc(cf->pool, sizeof(ngx_http_ccsn_timing_conf_t));
    if (conf == NULL) {
        return NULL;
    }
    conf->enabled = NGX_CONF_UNSET;
    return conf;
}

static char *
ngx_http_ccsn_timing_merge(ngx_conf_t *cf, void *parent, void *child)
{
    ngx_http_ccsn_timing_conf_t *previous = parent;
    ngx_http_ccsn_timing_conf_t *conf = child;
    ngx_conf_merge_value(conf->enabled, previous->enabled, 0);
    conf->timing = ngx_http_conf_get_module_main_conf(cf, ngx_http_ccsn_server_timing_module);
    return NGX_CONF_OK;
}
