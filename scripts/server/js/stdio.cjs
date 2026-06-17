const { spawn } = require("child_process");
const cfg = require("./config.cjs");

function run() {
  const env = cfg.buildChildEnv("stdio", 8001);
  const key = cfg.resolveApiKey();
  if (key) env[cfg.API_KEY_ENV] = key;

  const child = spawn(cfg.VENV_PYTHON, ["-u", "src/main.py"], {
    cwd: cfg.PROJECT_ROOT, env,
    stdio: ["inherit", "inherit", "inherit"], windowsHide: true,
  });

  child.on("error", (err) => { console.error(`[${cfg.WRAPPER_NAME}] ${err.message}`); process.exit(1); });
  child.on("exit", (code) => process.exit(code || 0));

  process.on("SIGINT", () => { if (!child.killed) child.kill("SIGINT"); });
  process.on("SIGTERM", () => { if (!child.killed) child.kill("SIGTERM"); });
}

module.exports = { run };
