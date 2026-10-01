import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { readFileSync } from "node:fs";

const httpsCertificate = process.env.VITE_HTTPS_CERT;
const httpsKey = process.env.VITE_HTTPS_KEY;
const apiProxyTarget = process.env.VITE_API_PROXY_TARGET ?? "http://127.0.0.1:8765";
const wsProxyTarget = process.env.VITE_WS_PROXY_TARGET ?? "ws://127.0.0.1:8765";
// A temporary tunnel hostname must be supplied by deployment environment; do
// not bake a stale public tunnel into the source or accidentally allow it.
const publicPreviewHost = process.env.VITE_PUBLIC_HOST ?? "localhost";
const https = httpsCertificate && httpsKey
  ? { cert: readFileSync(httpsCertificate), key: readFileSync(httpsKey) }
  : undefined;
const disabledApiDocs = new Set(["/docs", "/redoc", "/openapi.json"]);
const blockDisabledApiDocs = {
  name: "block-disabled-api-docs",
  enforce: "pre" as const,
  configureServer(server: { middlewares: { use: (handler: (req: { url?: string }, res: { statusCode: number; end: (body: string) => void }, next: () => void) => void) => void } }) {
    server.middlewares.use((req, res, next) => {
      if (disabledApiDocs.has((req.url ?? "").split("?", 1)[0])) {
        res.statusCode = 404;
        res.end("Not Found");
        return;
      }
      next();
    });
  },
  configurePreviewServer(server: { middlewares: { use: (handler: (req: { url?: string }, res: { statusCode: number; end: (body: string) => void }, next: () => void) => void) => void } }) {
    server.middlewares.use((req, res, next) => {
      if (disabledApiDocs.has((req.url ?? "").split("?", 1)[0])) {
        res.statusCode = 404;
        res.end("Not Found");
        return;
      }
      next();
    });
  },
};
const proxy = {
  "/api": {
    target: apiProxyTarget,
    changeOrigin: true,
    secure: false,
  },
  "/docs": {
    target: apiProxyTarget,
    changeOrigin: true,
    secure: false,
  },
  "/redoc": {
    target: apiProxyTarget,
    changeOrigin: true,
    secure: false,
  },
  "/openapi.json": {
    target: apiProxyTarget,
    changeOrigin: true,
    secure: false,
  },
  "/ws": {
    target: wsProxyTarget,
    ws: true,
    changeOrigin: true,
    secure: false,
  },
};

export default defineConfig(({ mode }) => {
  const isProduction = mode === "production";
  const corsOrigins = isProduction
    ? [`https://${publicPreviewHost}`]
    : [`https://${publicPreviewHost}`, "http://127.0.0.1:5173", "http://localhost:5173"];
  const cors = {
    origin: corsOrigins,
    credentials: true,
    methods: ["GET", "HEAD", "POST", "PATCH", "DELETE", "OPTIONS"],
    allowedHeaders: ["Authorization", "Content-Type", "If-Match", "Idempotency-Key", "X-CSRF-Token", "X-Request-ID"],
  };
  const connectSources = isProduction
    ? `'self' https://*.tile.openstreetmap.org wss://${publicPreviewHost}`
    : `'self' https://*.tile.openstreetmap.org wss://${publicPreviewHost} ws://localhost:5173 ws://127.0.0.1:5173`;
  const securityHeaders = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(self)",
    "Cross-Origin-Resource-Policy": "same-origin",
    "Cross-Origin-Opener-Policy": "same-origin",
    "X-Permitted-Cross-Domain-Policies": "none",
    "Content-Security-Policy": `default-src 'self'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'; object-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob: https://*.tile.openstreetmap.org; connect-src ${connectSources}; font-src 'self' data:`,
  };
  return {
  // The public app only uses the root document and query-string UI state.
  // Avoid SPA fallback for unknown paths such as disabled API documentation.
  appType: "spa",
  plugins: [react(), blockDisabledApiDocs],
  server: {
    host: "127.0.0.1",
    allowedHosts: [publicPreviewHost, "localhost", "127.0.0.1"],
    port: 5173,
    strictPort: false,
    https,
    cors,
    // Vite's React-refresh bootstrap is an inline module in development.
    // The production preview keeps the stricter script-src policy below.
    headers: {
      ...securityHeaders,
      "Content-Security-Policy": securityHeaders["Content-Security-Policy"].replace(
        "script-src 'self'",
        "script-src 'self' 'unsafe-inline'",
      ),
    },
    proxy,
  },
  preview: {
    host: "127.0.0.1",
    allowedHosts: [publicPreviewHost, "localhost", "127.0.0.1"],
    port: 5173,
    strictPort: true,
    cors,
    headers: securityHeaders,
    proxy,
  },
  };
});
