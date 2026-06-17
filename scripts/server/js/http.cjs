const { spawn } = require("child_process");
const cfg = require("./config.cjs");

let childProcess = null;

function log(m) { process.stderr.write(`${m}\n`); }

function run(port) {
  const env = cfg.buildChildEnv("http", port);
  const key = cfg.resolveApiKey();
  if (key) env[cfg.API_KEY_ENV] = key;

  childProcess = spawn(cfg.VENV_PYTHON, ["-u", "src/main.py"], {
    cwd: cfg.PROJECT_ROOT, env,
    stdio: ["ignore", "pipe", "pipe"],
  });
  childProcess.stdout.on("data", (chunk) => process.stderr.write(chunk));
  childProcess.stderr.on("data", (chunk) => process.stderr.write(chunk));
  childProcess.on("error", (err) => { log(`[${cfg.WRAPPER_NAME}] ${err.message}`); process.exit(1); });
  childProcess.on("exit", (code) => { log(`[${cfg.WRAPPER_NAME}] HTTP server exited (${code})`); process.exit(code || 0); });

  process.on("SIGINT", () => { if (childProcess && !childProcess.killed) childProcess.kill("SIGINT"); });
  process.on("SIGTERM", () => { if (childProcess && !childProcess.killed) childProcess.kill("SIGTERM"); });
}

module.exports = { run };
