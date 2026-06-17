#!/usr/bin/env node

const { spawnSync } = require("child_process");
const { resolve } = require("path");

const indexJs = resolve(__dirname, "js", "index.cjs");
const transport = process.argv.includes("--transport")
  ? process.argv[process.argv.indexOf("--transport") + 1]
  : "stdio";

const result = spawnSync("node", [indexJs, "--transport", transport], {
  stdio: "inherit",
  env: process.env,
});

process.exit(result.status || 0);
