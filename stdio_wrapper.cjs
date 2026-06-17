#!/usr/bin/env node

const { spawn } = require("child_process");
const path = require("path");

const PROJECT_ROOT = "C:\\Users\\steevenz\\MCP\\mcp-codecortex";
const UV_EXE = "uv";
const ARGS = ["run", "python", "-m", "src.main"];

const env = {
  ...process.env,
  CODECORTEX_TRANSPORT: "stdio"
};

const child = spawn(UV_EXE, ARGS, {
  cwd: PROJECT_ROOT,
  stdio: ["inherit", "inherit", "inherit"],
  env: env,
  windowsHide: true
});

child.on("error", (err) => {
  console.error("Failed to start:", err);
  process.exit(1);
});

child.on("exit", (code) => {
  process.exit(code || 0);
});

process.on("SIGINT", () => child.kill("SIGINT"));
process.on("SIGTERM", () => child.kill("SIGTERM"));