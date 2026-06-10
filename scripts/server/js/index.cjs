#!/usr/bin/env node

/**
 * CodeCortex Shared Server Proxy — Production-Grade Multi-IDE Wrapper
 *
 * Ported from CCT (Creative Critical Thinking) infrastructure.
 *
 * Features:
 *   1. Atomic file-lock based concurrency control (multi-IDE safe)
 *   2. Automatic Python venv discovery and bootstrap
 *   3. Bidirectional stdio → HTTP/SSE proxy with JSON-RPC forwarding
 *   4. Bootstrap API key auth with validation and retry
 *   5. Server state management with reference counting
 *   6. Multi-port candidate spawning with fallback
 *   7. Graceful shutdown with SIGINT/SIGTERM/uncaughtException hooks
 *
 * Author: Steeven Andrian Salim — Senior Principal Architect
 */

const fs = require("fs");
const path = require("path");
const { spawn, spawnSync } = require("child_process");
const readline = require("readline");
const os = require("os");

const PROJECT_ROOT = path.resolve(__dirname, "..", "..", "..");
const ENV_FILE = path.join(PROJECT_ROOT, ".env");

/**
 * Basic .env loader to avoid external dependencies
 */
function loadEnv() {
  if (fs.existsSync(ENV_FILE)) {
    const content = fs.readFileSync(ENV_FILE, "utf8");
    content.split(/\r?\n/).forEach((line) => {
      const match = line.match(/^\s*([\w.-]+)\s*=\s*(.*)?\s*$/);
      if (match) {
        const key = match[1];
        let value = match[2] || "";
        if (value.startsWith('"') && value.endsWith('"')) value = value.slice(1, -1);
        if (value.startsWith("'") && value.endsWith("'")) value = value.slice(1, -1);
        if (!process.env[key]) process.env[key] = value;
      }
    });
  }
}

loadEnv();

const PRD_ID = "mcp-codecortex-20251024";
const WRAPPER_NAME = "mcp-codecortex";
const VENV_DIR = fs.existsSync(path.join(PROJECT_ROOT, ".venv"))
  ? path.join(PROJECT_ROOT, ".venv")
  : path.join(PROJECT_ROOT, "venv");
const IS_WINDOWS = process.platform === "win32";
const VENV_PYTHON = IS_WINDOWS
  ? path.join(VENV_DIR, "Scripts", "python.exe")
  : path.join(VENV_DIR, "bin", "python");

const SERVER_STATE_DIR = path.join(PROJECT_ROOT, "database", "config");
const SERVER_STATE_PATH = path.join(SERVER_STATE_DIR, "codecortex_shared_server.json");
const SERVER_LOCK_PATH = path.join(SERVER_STATE_DIR, "codecortex_shared_server.lock");

let serverProcess = null;
let shuttingDown = false;
let sharedServerBaseUrl = null;
let apiKeyHeader = null;
let authConfig = null;

// ---------------------------------------------------------------------------
// Logging
// ---------------------------------------------------------------------------

function logStderr(message) {
  process.stderr.write(`${message}\n`);
}

// ---------------------------------------------------------------------------
// Sync helpers
// ---------------------------------------------------------------------------

function runSyncCommand(command, args, label) {
  logStderr(`[${WRAPPER_NAME}][${PRD_ID}] ${label}: ${command} ${args.join(" ")}`);
  const result = spawnSync(command, args, {
    cwd: PROJECT_ROOT,
    env: process.env,
    stdio: ["ignore", "pipe", "pipe"],
    encoding: "utf-8",
  });

  if (result.stdout && result.stdout.trim()) {
    logStderr(`[${label}][stdout] ${result.stdout.trim()}`);
  }
  if (result.stderr && result.stderr.trim()) {
    logStderr(`[${label}][stderr] ${result.stderr.trim()}`);
  }

  if (result.error) {
    throw result.error;
  }
  if (typeof result.status === "number" && result.status !== 0) {
    throw new Error(`${label} failed with exit code ${result.status}`);
  }
}

// ---------------------------------------------------------------------------
// Python bootstrap
// ---------------------------------------------------------------------------

function resolveBootstrapPython() {
  const candidates = [];

  if (process.env.PYTHON && process.env.PYTHON.trim()) {
    candidates.push([process.env.PYTHON.trim(), []]);
  }

  if (IS_WINDOWS) {
    candidates.push(["python", []]);
    candidates.push(["py", ["-3"]]);
  } else {
    candidates.push(["python3", []]);
    candidates.push(["python", []]);
  }

  for (const [cmd, prefix] of candidates) {
    const probe = spawnSync(cmd, [...prefix, "--version"], {
      cwd: PROJECT_ROOT,
      env: process.env,
      stdio: ["ignore", "pipe", "pipe"],
      encoding: "utf-8",
    });
    if (!probe.error && probe.status === 0) {
      return { cmd, prefix };
    }
  }

  throw new Error("No system Python interpreter found for initial bootstrap.");
}

function ensureVirtualEnvironment() {
  if (fs.existsSync(VENV_DIR)) {
    return;
  }

  const bootstrapPython = resolveBootstrapPython();

  // Check if uv.lock exists — prefer uv for venv creation
  const uvLock = path.join(PROJECT_ROOT, "uv.lock");
  if (fs.existsSync(uvLock)) {
    try {
      runSyncCommand("uv", ["sync"], "uv-sync");
      return;
    } catch {
      logStderr(`[${WRAPPER_NAME}] uv sync failed, falling back to venv + pip`);
    }
  }

  runSyncCommand(
    bootstrapPython.cmd,
    [...bootstrapPython.prefix, "-m", "venv", "venv"],
    "create-venv"
  );

  const requirementsPath = path.join(PROJECT_ROOT, "requirements.txt");
  if (fs.existsSync(requirementsPath)) {
    runSyncCommand(
      VENV_PYTHON,
      ["-m", "pip", "install", "-r", "requirements.txt"],
      "install-requirements"
    );
  }
}

// ---------------------------------------------------------------------------
// .env helpers
// ---------------------------------------------------------------------------

function readDotenvValue(key) {
  const envPath = path.join(PROJECT_ROOT, ".env");
  if (!fs.existsSync(envPath)) {
    return null;
  }
  const content = fs.readFileSync(envPath, "utf-8");
  for (const rawLine of content.split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line || line.startsWith("#")) {
      continue;
    }
    const normalized = line.startsWith("export ") ? line.slice("export ".length).trim() : line;
    const eq = normalized.indexOf("=");
    if (eq <= 0) {
      continue;
    }
    const name = normalized.slice(0, eq).trim();
    if (name !== key) {
      continue;
    }
    const value = normalized.slice(eq + 1).trim().replace(/^"(.*)"$/, "$1").replace(/^'(.*)'$/, "$1");
    return value || null;
  }
  return null;
}

function upsertDotenvValues(updates) {
  const envPath = path.join(PROJECT_ROOT, ".env");
  const existing = fs.existsSync(envPath) ? fs.readFileSync(envPath, "utf-8") : "";
  const lines = existing ? existing.split(/\r?\n/) : [];
  const remaining = new Map(Object.entries(updates).filter(([_, v]) => typeof v === "string" && v.length > 0));

  const updatedLines = lines.map((line) => {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) {
      return line;
    }
    const normalized = trimmed.startsWith("export ") ? trimmed.slice("export ".length).trim() : trimmed;
    const eq = normalized.indexOf("=");
    if (eq <= 0) {
      return line;
    }
    const name = normalized.slice(0, eq).trim();
    if (!remaining.has(name)) {
      return line;
    }
    const value = remaining.get(name);
    remaining.delete(name);
    return `${name}=${value}`;
  });

  for (const [name, value] of remaining.entries()) {
    updatedLines.push(`${name}=${value}`);
  }

  const finalContent = updatedLines.join("\n").replace(/\n*$/, "\n");
  fs.writeFileSync(envPath, finalContent, "utf-8");
}

// ---------------------------------------------------------------------------
// Auth configuration
// ---------------------------------------------------------------------------

function loadAuthConfig() {
  const envClientKey = (process.env.CODECORTEX_CLIENT_API_KEY || "").trim();
  const dotenvClientKey = (readDotenvValue("CODECORTEX_CLIENT_API_KEY") || "").trim();
  const instanceId = (
    process.env.CODECORTEX_CLIENT_INSTANCE_ID
    || readDotenvValue("CODECORTEX_CLIENT_INSTANCE_ID")
    || `codecortex-${os.hostname()}-${process.pid}`
  ).trim();

  const clientKey = envClientKey || dotenvClientKey;
  if (!clientKey) {
    throw new Error("CODECORTEX_CLIENT_API_KEY is required in environment/.env.");
  }

  return {
    clientKey: clientKey || "",
    clientInstanceId: instanceId,
  };
}

function buildApiKeyHeader(apiKey) {
  return { "X-API-KEY": apiKey };
}

// ---------------------------------------------------------------------------
// HTTP fetch helper
// ---------------------------------------------------------------------------

async function fetchJson(url, options, timeoutMs) {
  const controller = new AbortController();
  const timer = setTimeout(() => {
    try {
      controller.abort();
    } catch (e) {
      // ignore
    }
  }, timeoutMs);

  try {
    const response = await fetch(url, { ...options, signal: controller.signal });
    const contentType = response.headers.get("content-type") || "";
    const text = await response.text();
    const json = contentType.includes("application/json") ? JSON.parse(text) : null;
    return { ok: response.ok, status: response.status, json, text };
  } catch (error) {
    if (error && error.name === "AbortError") {
      throw new Error(`Request timeout after ${timeoutMs}ms`);
    }
    throw error;
  } finally {
    clearTimeout(timer);
  }
}

// ---------------------------------------------------------------------------
// Server probing
// ---------------------------------------------------------------------------

async function probeStatusSignature(baseUrl) {
  const statusUrl = `${baseUrl}/status`;
  try {
    const probe = await fetchJson(statusUrl, { method: "GET" }, 2000);
    if (!probe.ok || !probe.json || typeof probe.json !== "object") {
      return false;
    }
    // Standard response wraps data in 'data' field per src/core/errors/errors.py
    const data = probe.json.data || probe.json;
    const serverInfo = data.server;
    const transport = data.transport;

    if (!serverInfo || !transport) {
      return false;
    }
    if (typeof serverInfo === "object" && serverInfo.name === "codecortex") {
      return true;
    }
    return Boolean(serverInfo && transport);
  } catch {
    return false;
  }
}

async function detectActiveServerBaseUrl() {
  const ports = [8001, 8000, 8002, 8080, 3000, 5000, 3001, 5001];
  const hosts = ["http://localhost", "http://127.0.0.1"];

  for (const host of hosts) {
    for (const port of ports) {
      try {
        const baseUrl = `${host}:${port}`;
        const ok = await probeStatusSignature(baseUrl);
        if (ok) {
          return `${host}:${port}`;
        }
      } catch {
        continue;
      }
    }
  }

  return null;
}

// ---------------------------------------------------------------------------
// Auth validation (simplified — bootstrap key only, no handshake ceremony)
// ---------------------------------------------------------------------------

async function validateApiKeyForSync(baseUrl, apiKey) {
  if (!apiKey) {
    return false;
  }
  const mcp_secret = readDotenvValue("CODECORTEX_MCP_SECRET") || "";
  const syncPath = mcp_secret ? `/codecortex-api/v1/sync/${mcp_secret}` : "/codecortex-api/v1/sync";
  const url = `${baseUrl}${syncPath}`;
  const headers = {
    ...buildApiKeyHeader(apiKey),
    "content-type": "application/json",
  };
  try {
    const probe = await fetchJson(
      url,
      { method: "POST", headers, body: JSON.stringify({ jsonrpc: "2.0", id: 1, method: "ping" }) },
      5000
    );
    if (!probe.ok || !probe.json || typeof probe.json !== "object") {
      return false;
    }
    return probe.json.jsonrpc === "2.0" && Object.prototype.hasOwnProperty.call(probe.json, "result");
  } catch {
    return false;
  }
}

async function establishClientAuth(baseUrl, forceRefresh = false) {
  const apiKey = authConfig?.clientKey || "";
  if (!apiKey) {
    throw new Error("No usable auth key found.");
  }

  if (!forceRefresh) {
    const valid = await validateApiKeyForSync(baseUrl, apiKey);
    if (valid) {
      apiKeyHeader = buildApiKeyHeader(apiKey);
      return;
    }
    throw new Error("API key validation failed.");
  }

  // If forceRefresh, we just set the header directly and hope for the best
  apiKeyHeader = buildApiKeyHeader(apiKey);
}

async function validateServerAuth(baseUrl) {
  try {
    await establishClientAuth(baseUrl, false);
    return true;
  } catch {
    return false;
  }
}

// ---------------------------------------------------------------------------
// File-based locking (atomic)
// ---------------------------------------------------------------------------

function tryAcquireLock(timeoutMs = 8000) {
  fs.mkdirSync(SERVER_STATE_DIR, { recursive: true });
  const start = Date.now();
  while (true) {
    try {
      const fd = fs.openSync(SERVER_LOCK_PATH, "wx");
      return fd;
    } catch (error) {
      if (error.code === "EEXIST") {
        // Stale lock detection: if lock is > 10s old, try to take it
        try {
          const stats = fs.statSync(SERVER_LOCK_PATH);
          if (Date.now() - stats.mtimeMs > 10000) {
            logStderr(`[${WRAPPER_NAME}] Detected stale lock file. Removing...`);
            fs.unlinkSync(SERVER_LOCK_PATH);
            continue; // try again
          }
        } catch (e) {
          // ignore
        }
      }

      if (Date.now() - start > timeoutMs) {
        throw new Error(`Failed to acquire shared server lock after ${timeoutMs}ms.`);
      }
      Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 100);
    }
  }
}

function releaseLock(fd) {
  try {
    fs.closeSync(fd);
  } catch {
    // ignore
  }
  try {
    fs.unlinkSync(SERVER_LOCK_PATH);
  } catch {
    // ignore
  }
}

// ---------------------------------------------------------------------------
// Server state persistence
// ---------------------------------------------------------------------------

function readServerState() {
  if (!fs.existsSync(SERVER_STATE_PATH)) {
    return null;
  }
  try {
    const raw = fs.readFileSync(SERVER_STATE_PATH, "utf-8");
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object") {
      return null;
    }
    return parsed;
  } catch {
    return null;
  }
}

function writeServerState(state) {
  fs.mkdirSync(SERVER_STATE_DIR, { recursive: true });
  fs.writeFileSync(SERVER_STATE_PATH, JSON.stringify(state, null, 2), "utf-8");
}

// ---------------------------------------------------------------------------
// Server spawning
// ---------------------------------------------------------------------------

function spawnSharedHttpServer(preferredPort = 8001) {
  // Build child env — inject resolved auth keys so the Python server can
  // find them even when they only exist in .env (not in shell env).
  const resolvedClientKey =
    process.env.CODECORTEX_CLIENT_API_KEY
    || readDotenvValue("CODECORTEX_CLIENT_API_KEY")
    || "";

  const childEnv = {
    ...process.env,
    CODECORTEX_TRANSPORT: "sse",
    CODECORTEX_HOST: "127.0.0.1",
    CODECORTEX_PORT: String(preferredPort),
    PYTHONPATH: PROJECT_ROOT,
  };

  // Inject key only if it is not already in process.env
  if (resolvedClientKey && !process.env.CODECORTEX_CLIENT_API_KEY) {
    childEnv.CODECORTEX_CLIENT_API_KEY = resolvedClientKey;
  }

  const child = spawn(VENV_PYTHON, ["-u", "src/main.py"], {
    cwd: PROJECT_ROOT,
    env: childEnv,
    stdio: ["ignore", "pipe", "pipe"],
    detached: false,
  });

  child.stdout.on("data", (chunk) => process.stderr.write(chunk));
  child.stderr.on("data", (chunk) => process.stderr.write(chunk));

  return child;
}

// ---------------------------------------------------------------------------
// Shared server lifecycle
// ---------------------------------------------------------------------------

async function ensureSharedServer() {
  const lockFd = tryAcquireLock();
  try {
    const preferredPortRaw = process.env.CODECORTEX_PORT || readDotenvValue("CODECORTEX_PORT") || "8001";
    const preferredPort = /^\d+$/.test(preferredPortRaw) ? Number(preferredPortRaw) : 8001;
    const preferredBaseUrl = `http://127.0.0.1:${preferredPort}`;
    const candidatePorts = [...new Set([preferredPort, 8010, 8001, 8002, 8080])];

    // 1. Check existing server state
    const existing = readServerState();
    if (existing && typeof existing.baseUrl === "string" && typeof existing.refCount === "number") {
      if (existing.baseUrl !== preferredBaseUrl) {
        try {
          const preferredOk = await probeStatusSignature(preferredBaseUrl);
          if (preferredOk) {
            const authOk = await validateServerAuth(preferredBaseUrl);
            if (authOk) {
              writeServerState({
                prd_id: PRD_ID,
                pid: null,
                baseUrl: preferredBaseUrl,
                startedAt: new Date().toISOString(),
                refCount: existing.refCount + 1,
              });
              sharedServerBaseUrl = preferredBaseUrl;
              return;
            }
          }
        } catch {
          // continue
        }
      }

      const statusUrl = `${existing.baseUrl}/status`;
      try {
        const probe = await fetchJson(statusUrl, { method: "GET" }, 1200);
        if (probe.ok && probe.json && probe.json.server && probe.json.transport) {
          const authOk = await validateServerAuth(existing.baseUrl);
          if (authOk) {
            existing.refCount += 1;
            writeServerState(existing);
            sharedServerBaseUrl = existing.baseUrl;
            return;
          }
        }
      } catch {
        // continue
      }
    }

    // 2. Try preferred port directly
    try {
      const preferredOk = await probeStatusSignature(preferredBaseUrl);
      if (preferredOk) {
        const authOk = await validateServerAuth(preferredBaseUrl);
        if (authOk) {
          writeServerState({
            prd_id: PRD_ID,
            pid: null,
            baseUrl: preferredBaseUrl,
            startedAt: new Date().toISOString(),
            refCount: 1,
          });
          sharedServerBaseUrl = preferredBaseUrl;
          return;
        }
      }
    } catch {
      // continue
    }

    // 3. Spawn on candidate ports
    for (const port of candidatePorts) {
      const candidateBaseUrl = `http://127.0.0.1:${port}`;
      let candidateProcess = null;
      try {
        candidateProcess = spawnSharedHttpServer(port);
        writeServerState({
          prd_id: PRD_ID,
          pid: candidateProcess.pid,
          baseUrl: candidateBaseUrl,
          startedAt: new Date().toISOString(),
          refCount: 1,
        });

        for (let i = 0; i < 120; i += 1) { // Increased from 60 to 120 for slower Windows starts
          if (candidateProcess.exitCode !== null) {
            logStderr(`[${WRAPPER_NAME}] Candidate process on port ${port} exited prematurely with code ${candidateProcess.exitCode}`);
            break;
          }
          try {
            const probe = await fetchJson(`${candidateBaseUrl}/status`, { method: "GET" }, 2000);
            if (probe.ok && probe.json && probe.json.data?.server) { // Use exact data structure from src/core/errors/errors.py
              const authOk = await validateServerAuth(candidateBaseUrl);
              if (!authOk) {
                // Polling auth slightly longer because DB might be locked during init
                if (i % 4 === 0) logStderr(`[${WRAPPER_NAME}] Candidate ${candidateBaseUrl} alive, but auth still pending...`);
              } else {
                logStderr(`[${WRAPPER_NAME}] Shared server ready on ${candidateBaseUrl}`);
                serverProcess = candidateProcess;
                sharedServerBaseUrl = candidateBaseUrl;
                return;
              }
            }
          } catch (e) {
            // continue polling
          }
          await new Promise((resolve) => setTimeout(resolve, 500)); // Increased interval to reduce noise
        }
      } catch {
        // continue to next candidate port
      }

      if (candidateProcess && candidateProcess.exitCode === null) {
        try {
          candidateProcess.kill("SIGTERM");
        } catch {
          // ignore
        }
      }
    }

    // 4. Last resort: detect any running server
    const discovered = await detectActiveServerBaseUrl();
    if (discovered) {
      const authOk = await validateServerAuth(discovered);
      if (authOk) {
        writeServerState({
          prd_id: PRD_ID,
          pid: null,
          baseUrl: discovered,
          startedAt: new Date().toISOString(),
          refCount: 1,
        });
        sharedServerBaseUrl = discovered;
        return;
      }
    }

    throw new Error("Shared server failed to become ready.");
  } finally {
    releaseLock(lockFd);
  }
}

// ---------------------------------------------------------------------------
// JSON-RPC forwarding
// ---------------------------------------------------------------------------

async function forwardJsonRpcToServer(message) {
  if (!sharedServerBaseUrl) {
    throw new Error("Shared server is not available.");
  }
  if (!apiKeyHeader) {
    await establishClientAuth(sharedServerBaseUrl, false);
  }

  const mcp_secret = readDotenvValue("CODECORTEX_MCP_SECRET") || "";
  const syncPath = mcp_secret ? `/codecortex-api/v1/sync/${mcp_secret}` : "/codecortex-api/v1/sync";
  const url = `${sharedServerBaseUrl}${syncPath}`;
  const method = String(message?.method || "").trim();
  const timeoutMs = method === "tools/call" ? 120000 : 15000;
  let headers = {
    ...apiKeyHeader,
    "content-type": "application/json",
  };
  let response = await fetchJson(
    url,
    { method: "POST", headers, body: JSON.stringify(message) },
    timeoutMs
  );

  // Retry on auth failure
  if ((response.status === 401 || response.status === 403) && authConfig?.clientKey) {
    await establishClientAuth(sharedServerBaseUrl, true);
    headers = {
      ...apiKeyHeader,
      "content-type": "application/json",
    };
    response = await fetchJson(
      url,
      { method: "POST", headers, body: JSON.stringify(message) },
      timeoutMs
    );
  }
  return response;
}

function writeJsonRpcResponse(payload) {
  process.stdout.write(`${JSON.stringify(payload)}\n`);
}

// ---------------------------------------------------------------------------
// Shutdown
// ---------------------------------------------------------------------------

async function terminateWrapper(exitCode = 0) {
  if (shuttingDown) {
    return;
  }
  shuttingDown = true;

  let lockFd;
  try {
    lockFd = tryAcquireLock(2000);
  } catch {
    process.exit(exitCode);
    return;
  }

  try {
    const current = readServerState();
    if (current && typeof current.refCount === "number") {
      const nextCount = Math.max(0, current.refCount - 1);
      current.refCount = nextCount;
      if (nextCount > 0) {
        logStderr(`[${WRAPPER_NAME}] IDE disconnected. Remaining clients: ${nextCount}`);
        writeServerState(current);
      } else {
        logStderr(`[${WRAPPER_NAME}] Last client disconnected. Stopping shared server (pid: ${current.pid})...`);
        if (typeof current.pid === "number") {
          try {
            process.kill(current.pid, "SIGTERM");
          } catch {
            // ignore
          }
        }
        try {
          fs.unlinkSync(SERVER_STATE_PATH);
        } catch {
          // ignore
        }
      }
    }
  } finally {
    releaseLock(lockFd);
  }

  // Graceful exit: use setImmediate and fs.writeSync for final logs to avoid UV_HANDLE_CLOSING
  const finalMsg = `[codecortex-mcp] Proxy terminated.\n`;
  try {
    fs.writeSync(process.stderr.fd, finalMsg);
  } catch (e) { }

  // Clear heartbeat
  if (heartbeatInterval) {
    clearInterval(heartbeatInterval);
  }

  setTimeout(() => {
    process.exit(exitCode);
  }, 50);
}

// ---------------------------------------------------------------------------
// Stdio proxy
// ---------------------------------------------------------------------------

let heartbeatInterval = null;

function registerStdioProxy() {
  const rl = readline.createInterface({ input: process.stdin, crlfDelay: Infinity });

  // Prevent pipe hangs by logging periodic heartbeats to stderr
  heartbeatInterval = setInterval(() => {
    if (!shuttingDown) {
      logStderr(`[${WRAPPER_NAME}] Proxy Heartbeat: Healthy`);
    }
  }, 30000);

  rl.on("line", async (line) => {
    const trimmed = String(line || "").trim();
    if (!trimmed) {
      return;
    }

    let message;
    try {
      message = JSON.parse(trimmed);
    } catch (error) {
      logStderr(`[${WRAPPER_NAME}][${PRD_ID}] invalid JSON on stdin: ${String(error)}`);
      return;
    }

    const rpcId = Object.prototype.hasOwnProperty.call(message, "id") ? message.id : undefined;
    const isNotification = rpcId === undefined || rpcId === null;
    const startTime = Date.now();

    try {
      if (!isNotification) {
        logStderr(`[${WRAPPER_NAME}][RPC] Calling ${message.method} (id: ${rpcId})...`);
      }

      const forwarded = await forwardJsonRpcToServer(message);

      if (!isNotification) {
        const duration = Date.now() - startTime;
        logStderr(`[${WRAPPER_NAME}][RPC] ${message.method} (id: ${rpcId}) completed in ${duration}ms`);
      }

      if (isNotification) {
        return;
      }

      // Strict JSON-RPC 2.0 validation: ensure response has the required version tag
      if (forwarded.json && forwarded.json.jsonrpc === "2.0") {
        writeJsonRpcResponse(forwarded.json);
        return;
      }

      // If backend returned JSON but not valid JSON-RPC, or returned an error status
      const errorMessage = forwarded.json?.message || forwarded.json?.detail || forwarded.text || "Unknown upstream error";
      writeJsonRpcResponse({
        jsonrpc: "2.0",
        id: rpcId,
        error: {
          code: -32000,
          message: `Upstream protocol error: ${errorMessage.slice(0, 200)}`
        },
      });
    } catch (error) {
      if (isNotification) {
        return;
      }
      writeJsonRpcResponse({
        jsonrpc: "2.0",
        id: rpcId,
        error: { code: -32000, message: String(error?.message || error) },
      });
    }
  });

  rl.on("close", () => {
    terminateWrapper(0);
  });
}

// ---------------------------------------------------------------------------
// Shutdown hooks
// ---------------------------------------------------------------------------

function registerShutdownHooks() {
  process.on("SIGINT", () => terminateWrapper(0));
  process.on("SIGTERM", () => terminateWrapper(0));

  process.on("uncaughtException", (error) => {
    logStderr(
      `[${WRAPPER_NAME}][${PRD_ID}] uncaught exception: ${String(error?.stack || error)}`
    );
    terminateWrapper(1);
  });

  process.on("unhandledRejection", (reason) => {
    logStderr(`[${WRAPPER_NAME}][${PRD_ID}] unhandled rejection: ${String(reason)}`);
    terminateWrapper(1);
  });
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

function main() {
  try {
    registerShutdownHooks();
    ensureVirtualEnvironment();
    authConfig = loadAuthConfig();
    Promise.resolve()
      .then(async () => {
        await ensureSharedServer();
        await establishClientAuth(sharedServerBaseUrl, false);
        registerStdioProxy();
      })
      .catch((error) => {
        logStderr(`[${WRAPPER_NAME}][${PRD_ID}] startup failed: ${String(error?.stack || error)}`);
        process.exit(1);
      });
  } catch (error) {
    logStderr(`[${WRAPPER_NAME}][${PRD_ID}] startup failed: ${String(error?.stack || error)}`);
    process.exit(1);
  }
}

main();
