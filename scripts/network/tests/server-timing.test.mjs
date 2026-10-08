import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

const source = readFileSync(new URL("../../../infra/configs/base/i319-reroute/server-timing.js", import.meta.url));
const { default: timing } = await import("data:text/javascript;base64," + source.toString("base64"));

function response(variables = {}, existing) {
    const r = { variables: { hostname: "nginx-a", ...variables }, headersOut: {} };
    if (existing !== undefined) r.headersOut["Server-Timing"] = existing;
    timing.append(r);
    return r.headersOut["Server-Timing"];
}

test("preserves opaque metrics from multiple upstream layers", () => {
    const existing = ['app;dur=10;desc="query, render"', 'other_proxy;dur=12'];
    const result = response({ request_time: "0.025", upstream_header_time: "0.020" }, existing);
    assert.deepEqual(result.slice(0, 2), existing);
    assert.match(result[2], /nginx_headers;dur=25\.000/);
    assert.match(result[2], /nginx_upstream_headers;dur=20\.000/);
    assert.deepEqual(existing, ['app;dur=10;desc="query, render"', 'other_proxy;dur=12']);
});

test("works without any upstream Server-Timing", () => {
    assert.match(response({ upstream_connect_time: "0.001" })[0], /nginx_upstream_connect;dur=1\.000/);
});

test("keeps retry and upstream-group positions while skipping unavailable values", () => {
    const result = response({ upstream_header_time: "-, 0.123 : 0.002, -" })[0];
    assert.match(result, /dur=123\.000;desc="nginx-a attempt 2"/);
    assert.match(result, /dur=2\.000;desc="nginx-a attempt 3"/);
    assert.equal(result.split("nginx_upstream_headers").length - 1, 2);
});

test("omits missing and invalid measurements without inventing zeros", () => {
    assert.equal(response({ request_time: "-", upstream_connect_time: "NaN", upstream_header_time: "-1" }), undefined);
    assert.match(response({ upstream_connect_time: "0.000" })[0], /dur=0\.000/);
});

test("escapes the local hop description", () => {
    assert.match(response({ hostname: 'a"b\\c\n', request_time: "0.001" })[0], /desc="a\\"b\\\\c"/);
});
