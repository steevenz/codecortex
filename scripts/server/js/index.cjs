#!/usr/bin/env node

const cfg = require("./config.cjs");
cfg.loadEnv();

const _ARGS = (() => {
  const args = process.argv.slice(2);
  const p = { transport: "stdio", port: 8001, ide: "unknown" };
  for (let i = 0; i < args.length; i++) {
    switch (args[i]) {
      case "--transport": p.transport = (args[++i] || "stdio").toLowerCase(); break;
      case "--port": p.port = parseInt(args[++i], 10) || 8001; break;
      case "--ide": p.ide = args[++i] || "unknown"; break;
    }
  }
  if (!["stdio", "sse", "http"].includes(p.transport)) p.transport = "stdio";
  return p;
})();

process.stderr.write(`[${cfg.WRAPPER_NAME}] Starting (transport=${_ARGS.transport}, ide=${_ARGS.ide}, port=${_ARGS.port}) [prd_id=${cfg.PRD_ID}]\n`);

const { spawn } = require("child_process");
const { existsSync } = require("fs");
const path = require("path");

function resolveBootstrapPython() {
  const candidates = [];
  if (process.env.PYTHON) candidates.push([process.env.PYTHON.trim(), []]);
  if (cfg.IS_WINDOWS) { candidates.push(["python", []]); candidates.push(["py", ["-3"]]); }
  else { candidates.push(["python3", []]); candidates.push(["python", []]); }
  for (const [cmd, prefix] of candidates) {
    const r = require("child_process").spawnSync(cmd, [...prefix, "--version"], { cwd: cfg.PROJECT_ROOT, env: process.env, stdio: ["ignore", "pipe", "pipe"], encoding: "utf-8" });
    if (!r.error && r.status === 0) return { cmd, prefix };
  }
  throw new Error("No Python interpreter found");
}

function ensureVenv() {
  if (existsSync(cfg.VENV_DIR)) return;
  const bp = resolveBootstrapPython();
  require("child_process").spawnSync(bp.cmd, [...bp.prefix, "-m", "venv", "venv"], { cwd: cfg.PROJECT_ROOT, env: process.env, stdio: "inherit" });
}

function ensureDeps() {
  const req = path.join(cfg.PROJECT_ROOT, "requirements.txt");
  const marker = path.join(cfg.VENV_DIR, ".deps_installed");
  if (existsSync(req) && !existsSync(marker)) {
    const r = require("child_process").spawnSync(cfg.VENV_PYTHON, ["-m", "pip", "install", "-r", req, "--quiet"], { cwd: cfg.PROJECT_ROOT, env: process.env, stdio: "inherit" });
    if (r.status === 0) {
      try { require("fs").writeFileSync(marker, ""); } catch (_) {}
    }
  }
}

function main() {
  try {
    ensureVenv();
    ensureDeps();

    const transport = _ARGS.transport;
    const port = _ARGS.port;

    // Validate Python venv before dispatch
    if (!existsSync(cfg.VENV_PYTHON)) {
      process.stderr.write(`[${cfg.WRAPPER_NAME}] Python venv not found at ${cfg.VENV_PYTHON}\n`);
      process.exit(1);
    }

    switch (transport) {
      case "stdio": {
        const stdio = require("./stdio.cjs");
        stdio.run();
        break;
      }
      case "sse": {
        const sse = require("./sse.cjs");
        sse.run(port);
        break;
      }
      case "http": {
        const http = require("./http.cjs");
        http.run(port);
        break;
      }
    }
  } catch (err) {
    process.stderr.write(`[${cfg.WRAPPER_NAME}] Fatal: ${err.message}\n`);
    process.exit(1);
  }
}

main();
