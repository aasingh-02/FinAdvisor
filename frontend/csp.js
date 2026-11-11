/**
 * Frontend Content Security Policy (CSP) & security header builder (FIN-SEC-02).
 *
 * Centralizes CSP generation for:
 * - Vite development server (`vite dev`)
 * - Vite preview server (`vite preview`)
 * - Built HTML fallback `<meta>` tag (`vite build`)
 * - Production static hosting / reverse proxy headers
 *
 * Security note: Setting CSP on FastAPI JSON responses does NOT govern a
 * separately hosted React SPA. The frontend HTML-serving layer MUST deliver
 * this CSP so browsers permit Axios/fetch calls from the frontend origin to
 * the exact backend API origin without resorting to broad wildcards.
 */

const DEFAULT_DEV_API_URL = 'http://localhost:8000';
const DEFAULT_DEV_FRONTEND_ORIGIN = 'http://localhost:5173';

/**
 * Strictly resolve the backend API origin for CSP `connect-src`.
 *
 * - Relative API URLs (e.g. '/api' or '/') indicate same-origin deployment
 *   behind a reverse proxy and return `null` (covered by `'self'`).
 * - Rejects broad wildcards (`*`, `https:`, `http:`) and unsafe schemes.
 * - Returns `null` when `frontendOrigin` matches the resolved API origin (same-origin).
 * - Otherwise returns the exact `scheme://host[:port]` origin string.
 *
 * @param {string | undefined} apiBaseUrl
 * @param {string | undefined} [frontendOrigin]
 * @returns {string | null}
 */
export function resolveApiOrigin(apiBaseUrl, frontendOrigin) {
  const raw = (apiBaseUrl ?? '').trim();

  // Relative path => same origin as frontend HTML
  if (raw.startsWith('/')) {
    return null;
  }

  // Match frontend/src/services/api.js fallback when VITE_API_BASE_URL is unset
  const effectiveUrl = raw || DEFAULT_DEV_API_URL;

  if (effectiveUrl === '*' || /^[a-zA-Z]+:$/.test(effectiveUrl)) {
    throw new Error(
      `Unsafe broad wildcard or scheme-only CSP connect-src value rejected: "${effectiveUrl}"`
    );
  }

  let parsedApi;
  try {
    parsedApi = new URL(effectiveUrl);
  } catch {
    throw new Error(`Invalid VITE_API_BASE_URL for CSP connect-src: "${effectiveUrl}"`);
  }

  if (parsedApi.protocol !== 'http:' && parsedApi.protocol !== 'https:') {
    throw new Error(
      `Unsupported protocol "${parsedApi.protocol}" in VITE_API_BASE_URL for CSP connect-src`
    );
  }

  if (parsedApi.hostname.includes('*')) {
    throw new Error(
      `Wildcard hostnames are disallowed in CSP connect-src: "${parsedApi.origin}"`
    );
  }

  if (frontendOrigin && frontendOrigin.trim()) {
    const parsedFrontend = new URL(frontendOrigin.trim());
    if (parsedApi.origin === parsedFrontend.origin) {
      return null;
    }
  }

  return parsedApi.origin;
}

/**
 * Build the Content-Security-Policy string for the React frontend document.
 *
 * @param {object} [options]
 * @param {string} [options.apiBaseUrl] - Configured VITE_API_BASE_URL (e.g. http://localhost:8000, https://api.example.com, or /api)
 * @param {string} [options.frontendOrigin] - Origin serving the frontend HTML (used for same-origin detection & dev HMR WS)
 * @param {boolean} [options.isDev=false] - Enable Vite dev-server HMR/Fast Refresh allowances only in development
 * @param {boolean} [options.includeFrameAncestors=true] - Include `frame-ancestors 'none'` (valid in HTTP headers; omit in `<meta>`)
 * @returns {string}
 */
export function buildFrontendCsp({
  apiBaseUrl,
  frontendOrigin,
  isDev = false,
  includeFrameAncestors = true,
} = {}) {
  const apiOrigin = resolveApiOrigin(apiBaseUrl, frontendOrigin);

  const connectSources = ["'self'"];
  if (apiOrigin) {
    connectSources.push(apiOrigin);
  }

  if (isDev) {
    const devOrigin =
      (frontendOrigin && frontendOrigin.trim()) || DEFAULT_DEV_FRONTEND_ORIGIN;
    const parsedDev = new URL(devOrigin);
    const wsProtocol = parsedDev.protocol === 'https:' ? 'wss:' : 'ws:';
    connectSources.push(`${wsProtocol}//${parsedDev.host}`);
  }

  // Production bundles contain no inline scripts or inline <style> tags
  const scriptSources = isDev ? ["'self'", "'unsafe-inline'"] : ["'self'"];
  const styleSources = isDev
    ? ["'self'", "'unsafe-inline'", 'https://fonts.googleapis.com']
    : ["'self'", 'https://fonts.googleapis.com'];

  const directives = [
    "default-src 'self'",
    `script-src ${scriptSources.join(' ')}`,
    `style-src ${styleSources.join(' ')}`,
    "font-src 'self' https://fonts.gstatic.com data:",
    "img-src 'self' data:",
    `connect-src ${connectSources.join(' ')}`,
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
  ];

  if (includeFrameAncestors) {
    directives.push("frame-ancestors 'none'");
  }

  return `${directives.join('; ')};`;
}

/**
 * Build standard HTTP security headers for the frontend HTML server (Vite dev/preview or static proxy).
 *
 * @param {object} [options]
 * @param {string} [options.apiBaseUrl]
 * @param {string} [options.frontendOrigin]
 * @param {boolean} [options.isDev=false]
 * @param {boolean} [options.isHttps=false]
 * @returns {Record<string, string>}
 */
export function buildFrontendSecurityHeaders({
  apiBaseUrl,
  frontendOrigin,
  isDev = false,
  isHttps = false,
} = {}) {
  const headers = {
    'Content-Security-Policy': buildFrontendCsp({
      apiBaseUrl,
      frontendOrigin,
      isDev,
      includeFrameAncestors: true,
    }),
    'X-Content-Type-Options': 'nosniff',
    'X-Frame-Options': 'DENY',
    'Referrer-Policy': 'strict-origin-when-cross-origin',
  };

  if (isHttps && !isDev) {
    headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains';
  }

  return headers;
}
