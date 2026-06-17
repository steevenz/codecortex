const fs = require("fs");
const path = require("path");
const os = require("os");

const PROJECT_ROOT = path.resolve(__dirname, "..", "..", "..");
const PROJ_NAME = path.basename(PROJECT_ROOT).includes("neocortex") ? "neocortex" : "codecortex";

const PRD_ID = PROJ_NAME === "neocortex" ? "mcp-neocortex-20260506" : "mcp-codecortex-20251024";
const WRAPPER_NAME = `mcp-${PROJ_NAME}`;
const API_KEY_ENV = `${PROJ_NAME.toUpperCase()}_CLIENT_API_KEY`;
const STATUS_SERVER_NAME = PROJ_NAME === "neocortex" ? "cognitive-server" : "codecortex";
const SYNC_PATH = PROJ_NAME === "neocortex" ? "/cognitive-api/v1/sync" : "/codecortex-api/v1/sync";

const IS_WINDOWS = process.platform === "win32";
const VENV_DIR = fs.existsSync(path.join(PROJECT_ROOT, ".venv"))
  ? path.join(PROJECT_ROOT, ".venv") : path.join(PROJECT_ROOT, "venv");
const VENV_PYTHON = IS_WINDOWS
  ? path.join(VENV_DIR, "Scripts", "python.exe")
  : path.join(VENV_DIR, "bin", "python");

const BASE_DIR = path.join(os.homedir(), ".coddy", PROJ_NAME);
const STATE_DIR = path.join(BASE_DIR, "config");
const STATE_PATH = path.join(STATE_DIR, `${PROJ_NAME}_shared_server.json`);
const LOCK_PATH = path.join(STATE_DIR, `${PROJ_NAME}_shared_server.lock`);

const ENV_FILE = path.join(PROJECT_ROOT, ".env");

function loadEnv() {
  if (fs.existsSync(ENV_FILE)) {
    const content = fs.readFileSync(ENV_FILE, "utf8");
    content.split(/\r?\n/).forEach((line) => {
      const m = line.match(/^\s*([\w.-]+)\s*=\s*(.*)?\s*$/);
      if (m) {
        let v = m[2] || "";
        if (v.startsWith('"') && v.endsWith('"')) v = v.slice(1, -1);
        if (v.startsWith("'") && v.endsWith("'")) v = v.slice(1, -1);
        if (!process.env[m[1]]) process.env[m[1]] = v;
      }
    });
  }
}

function readDotenvValue(key) {
  if (!fs.existsSync(ENV_FILE)) return null;
  for (const l of fs.readFileSync(ENV_FILE, "utf-8").split(/\r?\n/)) {
    const t = l.trim();
    if (!t || t.startsWith("#")) continue;
    const n = t.startsWith("export ") ? t.slice(7).trim() : t;
    const eq = n.indexOf("=");
    if (eq <= 0) continue;
    if (n.slice(0, eq).trim() !== key) continue;
    return n.slice(eq + 1).trim().replace(/^"(.*)"$/, "$1").replace(/^'(.*)'$/, "$1");
  }
  return null;
}

function resolveApiKey() {
  return (process.env[API_KEY_ENV] || "").trim() || readDotenvValue(API_KEY_ENV) || "";
}

function buildChildEnv(transport, port) {
  return {
    ...process.env,
    [`${PROJ_NAME.toUpperCase()}_TRANSPORT`]: transport,
    [`${PROJ_NAME.toUpperCase()}_HOST`]: "127.0.0.1",
    [`${PROJ_NAME.toUpperCase()}_PORT`]: String(port || 8001),
    PYTHONPATH: PROJECT_ROOT,
    [`${PROJ_NAME.toUpperCase()}_DB_PATH`]: path.join(BASE_DIR, "data", "cognitive_memory.db"),
    [`${PROJ_NAME.toUpperCase()}_LOG_LEVEL`]: process.env[`${PROJ_NAME.toUpperCase()}_LOG_LEVEL`] || "INFO",
    PYTHONUNBUFFERED: "1",
  };
}

module.exports = {
  PROJ_NAME, PRD_ID, WRAPPER_NAME, API_KEY_ENV, STATUS_SERVER_NAME, SYNC_PATH,
  IS_WINDOWS, PROJECT_ROOT, VENV_DIR, VENV_PYTHON, BASE_DIR, STATE_DIR, STATE_PATH, LOCK_PATH, ENV_FILE,
  loadEnv, readDotenvValue, resolveApiKey, buildChildEnv,
};
