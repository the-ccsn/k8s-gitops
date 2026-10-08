function milliseconds(raw) {
    if (!/^\d+(?:\.\d+)?$/.test(raw || "")) {
        return null;
    }
    const value = Number(raw) * 1000;
    return Number.isFinite(value) ? value.toFixed(3) : null;
}

function append(r) {
    const metrics = [];
    const hop = (r.variables.hostname || "nginx")
        .replace(/["\\]/g, "\\$&").replace(/[\x00-\x1f\x7f]/g, "");
    const elapsed = milliseconds(r.variables.request_time);
    if (elapsed !== null) {
        // Snapshot at response headers, not total response/download duration.
        metrics.push('nginx_headers;dur=' + elapsed + ';desc="' + hop + '"');
    }

    // Commas separate retries; colons separate upstream groups after redirects.
    // Keep attempt positions even when a failed attempt has no measurement.
    const fields = ["connect", "headers"];
    for (let fieldIndex = 0; fieldIndex < fields.length; fieldIndex++) {
        const field = fields[fieldIndex];
        const variable = field === "connect" ? "upstream_connect_time" : "upstream_header_time";
        const attempts = (r.variables[variable] || "").trim().split(/\s*[,:]\s*/);
        for (let i = 0; i < attempts.length; i++) {
            const duration = milliseconds(attempts[i]);
            if (duration !== null) {
                metrics.push('nginx_upstream_' + field + ';dur=' + duration +
                    ';desc="' + hop + ' attempt ' + (i + 1) + '"');
            }
        }
    }

    if (metrics.length > 0) {
        // Treat upstream Server-Timing as opaque, regardless of its producer.
        const existing = r.headersOut["Server-Timing"];
        const values = existing === undefined ? [] :
            (Array.isArray(existing) ? existing : [existing]);
        r.headersOut["Server-Timing"] = values.concat([metrics.join(", ")]);
    }
}

export default { append };
