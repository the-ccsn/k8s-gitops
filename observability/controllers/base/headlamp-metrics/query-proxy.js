// This endpoint is for existing cluster administrators. Query-only access still
// exposes every stored namespace; Kubernetes object RBAC does not filter PromQL.
const UPSTREAM = 'http://vmsingle-victoriametrics-vmks.monitoring.svc.cluster.local:8428';
const PATHS = ['/api/v1/query', '/api/v1/query_range', '/-/healthy'];
const MAX_RESPONSE_BYTES = 8 * 1024 * 1024;

async function query(r) {
  if (r.method !== 'GET') {
    r.headersOut.Allow = 'GET';
    r.return(405, '{"error":"only GET is allowed"}');
    return;
  }

  // Match the original path, before Nginx decodes escapes or resolves dot/slash
  // segments. Keep the query string unchanged, including PromQL URL encoding.
  const target = r.variables.request_uri;
  const path = target.split('?')[0];
  if (!PATHS.includes(path) || !r.variables.request.startsWith('GET /')) {
    r.return(404, '{"error":"endpoint is not allowed"}');
    return;
  }

  try {
    const response = await ngx.fetch(UPSTREAM + target, {
      method: 'GET',
      // Never forward user tokens, cookies, forwarding or method override headers.
      headers: { Accept: 'application/json' },
      max_response_body_size: MAX_RESPONSE_BYTES,
    });
    // Fetch does not follow redirects. Do not send one back through serviceproxy.
    if (response.status >= 300 && response.status < 400) {
      r.return(502, '{"error":"upstream redirect is not allowed"}');
      return;
    }
    const body = await response.arrayBuffer();
    // Check the final decoded body too: chunk framing can cross Fetch's limit
    // on the last read. Never return an oversized or partial query result.
    if (body.byteLength > MAX_RESPONSE_BYTES) {
      r.return(502, '{"error":"metrics response exceeded proxy limits"}');
      return;
    }
    r.headersOut['Content-Type'] = 'application/json';
    if (path === '/-/healthy') {
      // Plugin 0.8.2's Test Connection expects JSON even for the text health API.
      // Preserve backend status so this also remains a real readiness check.
      r.return(response.status, response.ok
        ? '{"status":"success"}' : '{"error":"metrics backend is unhealthy"}');
      return;
    }
    r.return(response.status, Buffer.from(body));
  } catch (_) {
    // Includes DNS, transport, inactivity timeout and response-size failures.
    // Do not include upstream details or the submitted query in the response/log.
    r.return(502, '{"error":"metrics query failed or exceeded proxy limits"}');
  }
}

export default { query };
