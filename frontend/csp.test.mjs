import test from 'node:test';
import assert from 'node:assert/strict';
import {
  buildFrontendCsp,
  buildFrontendSecurityHeaders,
  resolveApiOrigin,
} from './csp.js';
import viteConfig from './vite.config.js';

test('resolveApiOrigin extracts exact origin for cross-origin API URLs', () => {
  assert.equal(
    resolveApiOrigin('http://localhost:8000', 'http://localhost:5173'),
    'http://localhost:8000'
  );
  assert.equal(
    resolveApiOrigin('https://api.finadvisor.com/api/v1', 'https://app.finadvisor.com'),
    'https://api.finadvisor.com'
  );
  // Matches frontend/src/services/api.js fallback when empty
  assert.equal(resolveApiOrigin('', 'http://localhost:5173'), 'http://localhost:8000');
});

test('resolveApiOrigin returns null for same-origin configurations', () => {
  assert.equal(resolveApiOrigin('/api', 'https://finadvisor.com'), null);
  assert.equal(resolveApiOrigin('/', 'https://finadvisor.com'), null);
  assert.equal(
    resolveApiOrigin('https://finadvisor.com/api', 'https://finadvisor.com'),
    null
  );
});

test('resolveApiOrigin rejects broad wildcards and unsafe schemes', () => {
  assert.throws(() => resolveApiOrigin('*'), /wildcard|scheme-only/i);
  assert.throws(() => resolveApiOrigin('https:'), /wildcard|scheme-only/i);
  assert.throws(() => resolveApiOrigin('https://*.finadvisor.com'), /wildcard/i);
  assert.throws(() => resolveApiOrigin('javascript:alert(1)'), /unsupported protocol/i);
});

test('development cross-origin CSP explicitly allows localhost:8000 and HMR ws without broad wildcards', () => {
  const csp = buildFrontendCsp({
    apiBaseUrl: 'http://localhost:8000',
    frontendOrigin: 'http://localhost:5173',
    isDev: true,
    includeFrameAncestors: true,
  });

  assert.match(csp, /connect-src 'self' http:\/\/localhost:8000 ws:\/\/localhost:5173;/);
  assert.match(csp, /script-src 'self' 'unsafe-inline';/);
  assert.match(csp, /style-src 'self' 'unsafe-inline' https:\/\/fonts\.googleapis\.com;/);
  assert.match(csp, /font-src 'self' https:\/\/fonts\.gstatic\.com data:;/);
  assert.match(csp, /object-src 'none';/);
  assert.match(csp, /frame-ancestors 'none';/);
  assert.doesNotMatch(csp, /connect-src[^;]*\*/);
  assert.doesNotMatch(csp, /connect-src[^;]*\bhttps:\b/);
});

test('production cross-origin CSP allows exact API origin without unsafe-inline or wildcards', () => {
  const headers = buildFrontendSecurityHeaders({
    apiBaseUrl: 'https://api.finadvisor.com',
    frontendOrigin: 'https://app.finadvisor.com',
    isDev: false,
    isHttps: true,
  });

  const csp = headers['Content-Security-Policy'];
  assert.match(csp, /default-src 'self';/);
  assert.match(csp, /script-src 'self';/);
  assert.match(csp, /style-src 'self' https:\/\/fonts\.googleapis\.com;/);
  assert.match(csp, /connect-src 'self' https:\/\/api\.finadvisor\.com;/);
  assert.match(csp, /object-src 'none';/);
  assert.match(csp, /base-uri 'self';/);
  assert.match(csp, /frame-ancestors 'none';/);

  // Must not weaken production script-src/style-src or use wildcards
  assert.doesNotMatch(csp, /'unsafe-inline'/);
  assert.doesNotMatch(csp, /cdn\.jsdelivr\.net/);
  assert.doesNotMatch(csp, /connect-src[^;]*\*/);

  // Preserves security headers and HSTS over HTTPS
  assert.equal(headers['X-Content-Type-Options'], 'nosniff');
  assert.equal(headers['X-Frame-Options'], 'DENY');
  assert.equal(headers['Referrer-Policy'], 'strict-origin-when-cross-origin');
  assert.equal(
    headers['Strict-Transport-Security'],
    'max-age=31536000; includeSubDomains'
  );
});

test('production same-origin CSP restricts connect-src strictly to self', () => {
  const relativeCsp = buildFrontendCsp({
    apiBaseUrl: '/api',
    frontendOrigin: 'https://finadvisor.com',
    isDev: false,
  });
  assert.match(relativeCsp, /connect-src 'self';/);
  assert.match(relativeCsp, /frame-ancestors 'none';/);

  const matchingOriginCsp = buildFrontendCsp({
    apiBaseUrl: 'https://finadvisor.com',
    frontendOrigin: 'https://finadvisor.com',
    isDev: false,
  });
  assert.match(matchingOriginCsp, /connect-src 'self';/);
});

test('meta fallback CSP omits frame-ancestors while preserving connect-src and object-src', () => {
  const metaCsp = buildFrontendCsp({
    apiBaseUrl: 'https://api.finadvisor.com',
    frontendOrigin: 'https://app.finadvisor.com',
    isDev: false,
    includeFrameAncestors: false,
  });

  assert.doesNotMatch(metaCsp, /frame-ancestors/);
  assert.match(metaCsp, /connect-src 'self' https:\/\/api\.finadvisor\.com;/);
  assert.match(metaCsp, /object-src 'none';/);
  assert.match(metaCsp, /script-src 'self';/);
});

test('vite.config.js attaches strict CSP headers on dev and preview servers', () => {
  const config = viteConfig({ mode: 'development', command: 'serve' });
  const devCsp = config.server.headers['Content-Security-Policy'];
  const previewCsp = config.preview.headers['Content-Security-Policy'];

  assert.match(devCsp, /connect-src 'self' http:\/\/localhost:8000 ws:\/\/localhost:5173;/);
  assert.match(devCsp, /frame-ancestors 'none';/);
  assert.match(previewCsp, /script-src 'self';/);
  assert.match(previewCsp, /connect-src 'self' http:\/\/localhost:8000;/);
  assert.equal(config.server.headers['X-Frame-Options'], 'DENY');
  assert.equal(config.server.headers['X-Content-Type-Options'], 'nosniff');
});
