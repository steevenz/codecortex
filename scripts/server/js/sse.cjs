const fs = require("fs");
const path = require("path");
const { spawn } = require("child_process");
const readline = require("readline");
const cfg = require("./config.cjs");

let childProcess = null;
let sharedServerBaseUrl = null;
let apiKeyHeader = null;
let shuttingDown = false;
let heartbeatInterval = null;

function log(m) { process.stderr.write(`${m}\n`); }

function tryAcquireLock(timeoutMs = 8000) {
  fs.mkdirSync(cfg.STATE_DIR, { recursive: true });
  const start = Date.now();
  while (true) {
    try { return fs.openSync(cfg.LOCK_PATH, "wx"); } catch (err) {
      if (err.code === "EEXIST") {
        try { if (Date.now() - fs.statSync(cfg.LOCK_PATH).mtimeMs > 10000) { fs.unlinkSync(cfg.LOCK_PATH); continue; } } catch {}
      }
      if (Date.now() - start > timeoutMs) throw new Error("Lock timeout");
      Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 100);
    }
  }
}
function releaseLock(fd) { try { fs.closeSync(fd); } catch {} try { fs.unlinkSync(cfg.LOCK_PATH); } catch {} }
function readState() { try { return JSON.parse(fs.readFileSync(cfg.STATE_PATH, "utf-8")); } catch { return null; } }
function writeState(s) { fs.mkdirSync(cfg.STATE_DIR, { recursive: true }); fs.writeFileSync(cfg.STATE_PATH, JSON.stringify(s, null, 2), "utf-8"); }

async function fetchJson(url, options, timeoutMs) {
  const ctrl = new AbortController();
  const t = setTimeout(() => { try { ctrl.abort(); } catch {} }, timeoutMs);
  try {
    const res = await fetch(url, { ...options, signal: ctrl.signal });
    const ct = res.headers.get("content-type") || "";
    const text = await res.text();
    return { ok: res.ok, status: res.status, json: ct.includes("application/json") ? JSON.parse(text) : null, text };
  } catch (err) {
    if (err?.name === "AbortError") throw new Error(`Timeout ${timeoutMs}ms`);
    throw err;
  } finally { clearTimeout(t); }
}

async function probeStatus(baseUrl) {
  try {
    const probe = await fetchJson(`${baseUrl}/status`, { method: "GET" }, 2000);
    if (!probe.ok || !probe.json) return false;
    const d = probe.json.data || probe.json;
    return d.server?.name === cfg.STATUS_SERVER_NAME || (d.server && d.transport);
  } catch { return false; }
}

async function validateKey(baseUrl, key) {
  if (!key) return false;
  try {
    const probe = await fetchJson(`${baseUrl}${cfg.SYNC_PATH}`, {
      method: "POST",
      headers: { "X-API-KEY": key, "content-type": "application/json" },
      body: JSON.stringify({ jsonrpc: "2.0", id: 1, method: "ping" }),
    }, 5000);
    return probe.json?.jsonrpc === "2.0" && "result" in (probe.json || {});
  } catch { return false; }
}

async function establishAuth(baseUrl, key) {
  if (!key) throw new Error("No auth key");
  if (await validateKey(baseUrl, key)) { apiKeyHeader = { "X-API-KEY": key }; return; }
  apiKeyHeader = { "X-API-KEY": key };
}

function spawnSseServer(port) {
  const env = cfg.buildChildEnv("sse", port);
  const key = cfg.resolveApiKey();
  if (key) env[cfg.API_KEY_ENV] = key;

  return spawn(cfg.VENV_PYTHON, ["-u", "src/main.py"], {
    cwd: cfg.PROJECT_ROOT, env,
    stdio: ["ignore", "pipe", "pipe"],
  });
}

async function ensureServer(port) {
  const fd = tryAcquireLock();
  try {
    const baseUrl = `http://127.0.0.1:${port}`;
    const existing = readState();
    if (existing) {
      try {
        if (await probeStatus(existing.baseUrl) && await validateKey(existing.baseUrl, cfg.resolveApiKey())) {
          existing.refCount = (existing.refCount || 1) + 1;
          writeState(existing);
          sharedServerBaseUrl = existing.baseUrl;
          return;
        }
      } catch {}
    }
    if (await probeStatus(baseUrl) && await validateKey(baseUrl, cfg.resolveApiKey())) {
      writeState({ pid: null, baseUrl, startedAt: new Date().toISOString(), refCount: 1 });
      sharedServerBaseUrl = baseUrl;
      return;
    }
    childProcess = spawnSseServer(port);
    writeState({ pid: childProcess.pid, baseUrl, startedAt: new Date().toISOString(), refCount: 1 });
    for (let i = 0; i < 60; i++) {
      if (childProcess.exitCode !== null) break;
      if (await probeStatus(baseUrl) && await validateKey(baseUrl, cfg.resolveApiKey())) {
        sharedServerBaseUrl = baseUrl;
        return;
      }
      await new Promise(r => setTimeout(r, 250));
    }
    throw new Error("SSE server failed to become ready");
  } finally { releaseLock(fd); }
}

function forwardJsonRpc(msg) {
  if (!sharedServerBaseUrl) throw new Error("Server not available");
  return fetchJson(`${sharedServerBaseUrl}${cfg.SYNC_PATH}`, {
    method: "POST",
    headers: { ...apiKeyHeader, "content-type": "application/json" },
    body: JSON.stringify(msg),
  }, msg?.method === "tools/call" ? 120000 : 15000);
}

function writeJsonRpc(payload) { process.stdout.write(`${JSON.stringify(payload)}\n`); }

function registerStdioProxy() {
  const rl = readline.createInterface({ input: process.stdin, crlfDelay: Infinity });
  heartbeatInterval = setInterval(() => { if (!shuttingDown) log(`[${cfg.WRAPPER_NAME}] Heartbeat: Healthy`); }, 30000);
  rl.on("line", async (line) => {
    const trimmed = (line || "").trim();
    if (!trimmed) return;
    let msg;
    try { msg = JSON.parse(trimmed); } catch { return; }
    const id = msg.id;
    const notif = id === undefined || id === null;
    try {
      const fwd = await forwardJsonRpc(msg);
      if (notif) return;
      if (fwd.json?.jsonrpc === "2.0") { writeJsonRpc(fwd.json); return; }
      writeJsonRpc({ jsonrpc: "2.0", id, error: { code: -32000, message: "Upstream error" } });
    } catch (err) {
      if (!notif) writeJsonRpc({ jsonrpc: "2.0", id, error: { code: -32000, message: err.message } });
    }
  });
  rl.on("close", () => terminate(0));
}

async function terminate(exitCode) {
  if (shuttingDown) return;
  shuttingDown = true;
  let fd;
  try { fd = tryAcquireLock(2000); } catch { setImmediate(() => process.exit(exitCode)); return; }
  try {
    const s = readState();
    if (s) {
      s.refCount = Math.max(0, (s.refCount || 1) - 1);
      if (s.refCount > 0) { writeState(s); } else {
        if (childProcess && childProcess.exitCode === null) try { childProcess.kill("SIGTERM"); } catch {}
        try { fs.unlinkSync(cfg.STATE_PATH); } catch {}
      }
    }
  } finally { releaseLock(fd); }
  if (heartbeatInterval) clearInterval(heartbeatInterval);
  setImmediate(() => process.exit(exitCode));
}

async function run(port) {
  process.on("SIGINT", () => terminate(0));
  process.on("SIGTERM", () => terminate(0));
  process.on("uncaughtException", (err) => { log(`[${cfg.WRAPPER_NAME}] uncaught: ${err?.stack || err}`); terminate(1); });
  process.on("unhandledRejection", (reason) => { log(`[${cfg.WRAPPER_NAME}] unhandled: ${reason}`); terminate(1); });

  try {
    await ensureServer(port);
    const key = cfg.resolveApiKey();
    await establishAuth(sharedServerBaseUrl, key);
    registerStdioProxy();
  } catch (err) {
    log(`[${cfg.WRAPPER_NAME}] SSE startup failed: ${err.stack}`);
    process.exit(1);
  }
}

module.exports = { run };
