import { fileURLToPath } from 'node:url'
import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import { buildFrontendCsp, buildFrontendSecurityHeaders } from './csp.js'

const FRONTEND_DIR = fileURLToPath(new URL('.', import.meta.url))

function cspMetaPlugin({ apiBaseUrl, frontendOrigin }) {
  return {
    name: 'finadvisor-csp-meta',
    apply: 'build',
    transformIndexHtml(html) {
      const csp = buildFrontendCsp({
        apiBaseUrl,
        frontendOrigin,
        isDev: false,
        includeFrameAncestors: false,
      })
      const metaTag = `<meta http-equiv="Content-Security-Policy" content="${csp}">`
      return html.replace('</head>', `    ${metaTag}\n  </head>`)
    },
  }
}

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, FRONTEND_DIR, '')
  const apiBaseUrl = env.VITE_API_BASE_URL
  const frontendOrigin = env.VITE_FRONTEND_ORIGIN

  return {
    plugins: [
      react(),
      cspMetaPlugin({ apiBaseUrl, frontendOrigin }),
    ],
    server: {
      port: 5173,
      host: true,
      headers: buildFrontendSecurityHeaders({
        apiBaseUrl,
        frontendOrigin: frontendOrigin || 'http://localhost:5173',
        isDev: true,
        isHttps: false,
      }),
    },
    preview: {
      port: 4173,
      headers: buildFrontendSecurityHeaders({
        apiBaseUrl,
        frontendOrigin,
        isDev: false,
        isHttps: Boolean(frontendOrigin && frontendOrigin.startsWith('https://')),
      }),
    },
  }
})
