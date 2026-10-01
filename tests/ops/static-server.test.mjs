import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { createServer, request as httpRequest } from "node:http";
import { once } from "node:events";
import { setTimeout as delay } from "node:timers/promises";
import { fileURLToPath } from "node:url";
import path from "node:path";
import test from "node:test";

const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");
const staticServerScript = path.join(projectRoot, "ops", "pc", "static-server.mjs");
const distIndex = path.join(projectRoot, "frontend", "dist", "index.html");

async function freePort() {
  const server = createServer();
  server.listen(0, "127.0.0.1");
  await once(server, "listening");
  const { port } = server.address();
  await new Promise((resolve, reject) => server.close((error) => error ? reject(error) : resolve()));
  return port;
}

async function waitForServer(url, child) {
  for (let attempt = 0; attempt < 40; attempt += 1) {
    if (child.exitCode !== null) throw new Error(`Static server exited early with ${child.exitCode}`);
    try {
      const response = await fetch(url);
      if (response.ok) return;
    } catch { /* wait until listener is ready */ }
    await delay(100);
  }
  throw new Error("Static server did not become ready within four seconds");
}

function requestWithHost(url, host) {
  return new Promise((resolve, reject) => {
    const request = httpRequest(url, { headers: { Host: host } }, (response) => {
      const chunks = [];
      response.on("data", (chunk) => chunks.push(chunk));
      response.on("end", () => resolve({
        status: response.statusCode,
        headers: response.headers,
        text: Buffer.concat(chunks).toString("utf8"),
      }));
    });
    request.on("error", reject);
    request.end();
  });
}

test("production static server enforces host/CSP, hides docs, serves SPA, and proxies API", async (t) => {
  await assert.doesNotReject(() => import("node:fs/promises").then(({ access }) => access(distIndex)), "build frontend before running this test");

  const apiPort = await freePort();
  const webPort = await freePort();
  const seenRequests = [];
  const apiServer = createServer((request, response) => {
    const chunks = [];
    request.on("data", (chunk) => chunks.push(chunk));
    request.on("end", () => {
      seenRequests.push({ method: request.method, url: request.url, body: Buffer.concat(chunks).toString("utf8") });
      response.writeHead(201, { "Content-Type": "application/json", "Cache-Control": "no-store" });
      response.end(JSON.stringify(seenRequests.at(-1)));
    });
  });
  apiServer.listen(apiPort, "127.0.0.1");
  await once(apiServer, "listening");
  t.after(() => new Promise((resolve) => apiServer.close(() => resolve())));

  const child = spawn(process.execPath, [staticServerScript], {
    cwd: projectRoot,
    env: {
      PATH: process.env.PATH,
      SystemRoot: process.env.SystemRoot,
      TEMP: process.env.TEMP,
      TMP: process.env.TMP,
      VITE_PUBLIC_HOST: "portal.example.test",
      FRONTEND_PORT: String(webPort),
      PORT: String(apiPort),
    },
    stdio: "ignore",
  });
  t.after(async () => {
    if (child.exitCode !== null) return;
    child.kill();
    await new Promise((resolve) => child.once("exit", resolve));
  });

  const origin = `http://127.0.0.1:${webPort}`;
  await waitForServer(`${origin}/`, child);

  const rootResponse = await requestWithHost(`${origin}/`, "portal.example.test");
  assert.equal(rootResponse.status, 200);
  assert.match(rootResponse.headers["content-security-policy"] ?? "", /frame-ancestors 'none'/);
  assert.equal(rootResponse.headers["strict-transport-security"], "max-age=31536000; includeSubDomains");
  assert.equal(rootResponse.headers["cache-control"], "no-cache");

  const localResponse = await fetch(`${origin}/`, { headers: { Host: `127.0.0.1:${webPort}` } });
  assert.equal(localResponse.status, 200);
  assert.equal(localResponse.headers.get("strict-transport-security"), null);

  const spaResponse = await fetch(`${origin}/login`, { headers: { Host: `127.0.0.1:${webPort}`, Accept: "text/html" } });
  assert.equal(spaResponse.status, 200);
  assert.match(await spaResponse.text(), /id="root"/);

  const docsResponse = await fetch(`${origin}/openapi.json`, { headers: { Host: `127.0.0.1:${webPort}` } });
  assert.equal(docsResponse.status, 404);
  const docsNestedResponse = await fetch(`${origin}/docs/extra`, { headers: { Host: `127.0.0.1:${webPort}` } });
  assert.equal(docsNestedResponse.status, 404);

  const unknownHostResponse = await requestWithHost(`${origin}/`, `evil.example:${webPort}`);
  assert.equal(unknownHostResponse.status, 421);

  const apiResponse = await fetch(`${origin}/api/v1/test?check=1`, {
    method: "POST",
    headers: { Host: `127.0.0.1:${webPort}`, "Content-Type": "application/json" },
    body: JSON.stringify({ probe: "static-proxy" }),
  });
  assert.equal(apiResponse.status, 201);
  assert.deepEqual(await apiResponse.json(), {
    method: "POST",
    url: "/api/v1/test?check=1",
    body: JSON.stringify({ probe: "static-proxy" }),
  });
  assert.equal(seenRequests.length, 1);
});
