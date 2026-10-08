import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

const source = readFileSync(new URL("../../../infra/configs/base/i319-reroute/server-timing.js", import.meta.url));
const { default: timing } = await import("data:text/javascript;base64," + source.toString("base64"));

function response(variables = {}) {
    return timing.fallback({ variables: { hostname: "nginx-a", ...variables } });
}

test("keeps retry and upstream-group positions while skipping unavailable values", () => {
    const result = response({ upstream_header_time: "-, 0.123 : 0.002, -" });
    assert.match(result, /dur=123\.000;desc="nginx-a attempt 2"/);
    assert.match(result, /dur=2\.000;desc="nginx-a attempt 3"/);
    assert.equal(result.split("nginx_upstream_headers").length - 1, 2);
});

test("omits missing and invalid measurements without inventing zeros", () => {
    assert.equal(response({ request_time: "-", upstream_connect_time: "NaN", upstream_header_time: "-1" }), "");
    assert.match(response({ upstream_connect_time: "0.000" }), /dur=0\.000/);
});

test("escapes the local hop description", () => {
    assert.match(response({ hostname: 'a"b\\c\n', upstream_connect_time: "0.001" }), /desc="a\\"b\\\\c attempt 1"/);
});
