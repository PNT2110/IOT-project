import http from "node:http";
import { createReadStream } from "node:fs";
import { access, stat } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");
const webRoot = path.join(projectRoot, "frontend", "dist");
const publicHost = (process.env.VITE_PUBLIC_HOST ?? "").trim().toLowerCase();
const port = Number(process.env.FRONTEND_PORT ?? "5173");
const apiPort = Number(process.env.PORT ?? "8765");

if (!publicHost || !/^(?=.{1,253}$)([a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$/.test(publicHost)) {
  throw new Error("VITE_PUBLIC_HOST must be the approved public DNS hostname (without scheme or path).");
}
if (!Number.isInteger(port) || port < 1 || port > 65535 || !Number.isInteger(apiPort) || apiPort < 1 || apiPort > 65535) {
  throw new Error("FRONTEND_PORT and PORT must be valid TCP ports.");
}
await access(path.join(webRoot, "index.html"));

const allowedHosts = new Set([publicHost, "localhost", "127.0.0.1"]);
const contentTypes = new Map([
  [".html", "text/html; charset=utf-8"],
  [".js", "text/javascript; charset=utf-8"],
  [".mjs", "text/javascript; charset=utf-8"],
  [".css", "text/css; charset=utf-8"],
  [".json", "application/json; charset=utf-8"],
  [".svg", "image/svg+xml"],
  [".png", "image/png"],
  [".jpg", "image/jpeg"],
  [".jpeg", "image/jpeg"],
  [".webp", "image/webp"],
  [".ico", "image/x-icon"],
  [".woff", "font/woff"],
  [".woff2", "font/woff2"],
]);

function applyWebSecurityHeaders(response, isPublicHost = false) {
  response.setHeader("X-Content-Type-Options", "nosniff");
  response.setHeader("X-Frame-Options", "DENY");
  if (isPublicHost) response.setHeader("Strict-Transport-Security", "max-age=31536000; includeSubDomains");
  response.setHeader("Referrer-Policy", "strict-origin-when-cross-origin");
  response.setHeader("Permissions-Policy", "camera=(), microphone=(), geolocation=(self)");
  response.setHeader("Cross-Origin-Resource-Policy", "same-origin");
  response.setHeader("Cross-Origin-Opener-Policy", "same-origin");
  response.setHeader("X-Permitted-Cross-Domain-Policies", "none");
  response.setHeader(
    "Content-Security-Policy",
    `default-src 'self'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'; object-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob: https://*.tile.openstreetmap.org; connect-src 'self' https://*.tile.openstreetmap.org wss://${publicHost}; font-src 'self' data:`,
  );
}

function sendText(response, statusCode, text, contentType = "text/plain; charset=utf-8") {
  response.writeHead(statusCode, { "Content-Type": contentType, "Cache-Control": "no-store" });
  response.end(text);
}

function proxyApi(request, response) {
  const upstream = http.request({
    hostname: "127.0.0.1",
    port: apiPort,
    path: request.url,
    method: request.method,
    headers: { ...request.headers, host: `127.0.0.1:${apiPort}` },
  }, (upstreamResponse) => {
    response.writeHead(upstreamResponse.statusCode ?? 502, upstreamResponse.headers);
    upstreamResponse.pipe(response);
  });
  upstream.on("error", () => {
    if (!response.headersSent) sendText(response, 502, "PC API is unavailable.");
    else response.destroy();
  });
  request.pipe(upstream);
}

async function serveStatic(request, response, pathname) {
  let decodedPath;
  try { decodedPath = decodeURIComponent(pathname); }
  catch { sendText(response, 400, "Bad request"); return; }
  if (decodedPath.includes("\0") || decodedPath.split("/").some((part) => part.startsWith("."))) {
    sendText(response, 404, "Not found");
    return;
  }

  const isRoot = decodedPath === "/";
  const requestedPath = path.resolve(webRoot, `.${decodedPath}`);
  const rootPrefix = `${webRoot}${path.sep}`;
  if (!isRoot && requestedPath !== webRoot && !requestedPath.startsWith(rootPrefix)) {
    sendText(response, 404, "Not found");
    return;
  }

  let filePath = isRoot ? path.join(webRoot, "index.html") : requestedPath;
  let fileInfo;
  try {
    fileInfo = await stat(filePath);
    if (!fileInfo.isFile()) throw new Error("not a file");
  } catch {
    // The public site currently uses a single root route plus hash navigation.
    // Keep extensionless browser paths compatible, but never turn missing
    // assets or hidden API documentation routes into HTML responses.
    if (!path.extname(decodedPath) && request.headers.accept?.includes("text/html")) {
      filePath = path.join(webRoot, "index.html");
      try { fileInfo = await stat(filePath); }
      catch { sendText(response, 404, "Not found"); return; }
    } else {
      sendText(response, 404, "Not found");
      return;
    }
  }

  applyWebSecurityHeaders(response);
  response.setHeader("Content-Type", contentTypes.get(path.extname(filePath).toLowerCase()) ?? "application/octet-stream");
  response.setHeader("Content-Length", fileInfo.size);
  response.setHeader("Cache-Control", filePath.endsWith("index.html") ? "no-cache" : "public, max-age=3600");
  if (request.method === "HEAD") { response.end(); return; }
  createReadStream(filePath).on("error", () => {
    if (!response.headersSent) sendText(response, 500, "Internal server error");
    else response.destroy();
  }).pipe(response);
}

const server = http.createServer((request, response) => {
  const incomingHost = (request.headers.host ?? "").split(":", 1)[0].toLowerCase();
  applyWebSecurityHeaders(response, incomingHost === publicHost);
  if (!allowedHosts.has(incomingHost)) { sendText(response, 421, "Misdirected request"); return; }

  let pathname;
  try { pathname = new URL(request.url ?? "/", "http://localhost").pathname; }
  catch { sendText(response, 400, "Bad request"); return; }

  if (["/docs", "/redoc", "/openapi.json"].includes(pathname) || pathname.startsWith("/docs/") || pathname.startsWith("/redoc/")) { sendText(response, 404, "Not found"); return; }
  if (pathname === "/api" || pathname.startsWith("/api/")) { proxyApi(request, response); return; }
  if (request.method !== "GET" && request.method !== "HEAD") { sendText(response, 405, "Method not allowed"); return; }
  void serveStatic(request, response, pathname);
});

server.listen(port, "127.0.0.1", () => {
  console.log(`PC static frontend listening on 127.0.0.1:${port}; API proxy target 127.0.0.1:${apiPort}`);
});

for (const signal of ["SIGINT", "SIGTERM"]) {
  process.once(signal, () => server.close(() => process.exit(0)));
}
