import { spawn, spawnSync, execSync } from 'child_process';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import { readFileSync, existsSync, unlinkSync, writeFileSync } from 'fs';
import { homedir } from 'os';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const projectRoot = join(__dirname, '..', '..');

// ═══════════════════════════════════════════
// PID LOCKFILE HANDSHAKE — Node <-> Python
// ═══════════════════════════════════════════
// Lockfile format (JSON v2):
//   {
//     "pid": <int>,
//     "signature": "<code-location>",
//     "source": "python" | "node",
//     "instance_id": "<unique-hash>",
//     "ide": "trae" | "cursor" | "vscode" | "unknown",
//     "pid_timestamp": <unix-epoch>,
//     "version": 2
//   }
//
// Also supports legacy v1 format (plain text: PID + sig lines).
// Killed-PID cache: codecortex.killed (JSON object: {pid_str: kill_timestamp})
const LOCKFILE_DIR = join(homedir(), '.coddy', 'codecortex');
const LOCKFILE_PATH = join(LOCKFILE_DIR, 'codecortex.pid');
const KILLED_CACHE_PATH = join(LOCKFILE_DIR, 'codecortex.killed');

// ═══════════════════════════════════════════
// CLI Argument Parsing
// ═══════════════════════════════════════════
const _CLI_IDE = (() => {
  const args = process.argv.slice(2);
  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--ide' && args[i + 1] && !args[i + 1].startsWith('--')) {
      return args[i + 1];
    }
  }
  return null;
})();

function _detectIde() {
  if (_CLI_IDE) return _CLI_IDE;
  if (process.env.TRAE_ID) return 'trae';
  if (process.env.VSCODE_NLS_CONFIG) return 'vscode';
  if (process.env.TERM_PROGRAM) {
    const p = process.env.TERM_PROGRAM.toLowerCase();
    if (p.includes('cursor')) return 'cursor';
    if (p.includes('vscode')) return 'vscode';
    if (p.includes('trae')) return 'trae';
  }
  return 'unknown';
}

function _nodeInstanceId() {
  const crypto = require('crypto');
  const raw = `${process.pid}:node:${__dirname}:${Date.now()}`;
  return crypto.createHash('sha256').update(raw).digest('hex').slice(0, 12);
}

let _NODE_INSTANCE_ID = _nodeInstanceId();

function readLockfile() {
  try {
    if (!existsSync(LOCKFILE_PATH)) return null;
    const content = readFileSync(LOCKFILE_PATH, 'utf8').trim();
    if (!content) return null;

    // Try JSON v2 format first
    try {
      const data = JSON.parse(content);
      if (typeof data === 'object' && data !== null && typeof data.pid === 'number') {
        return data;
      }
    } catch { /* fall through to legacy */ }

    // Legacy v1 format: plain text lines
    const lines = content.split('\n');
    const pid = parseInt(lines[0]?.trim(), 10);
    const sig = lines[1]?.trim() || '';
    return {
      pid: isNaN(pid) ? null : pid,
      signature: sig,
      source: 'python',
      instance_id: 'legacy',
      ide: 'unknown',
      pid_timestamp: 0,
      version: 1,
    };
  } catch {
    return null;
  }
}

function writeNodeLockfile(pythonPid) {
  const identity = {
    pid: pythonPid,
    signature: `codecortex-run-server.js-${__dirname}`,
    source: 'node',
    instance_id: _NODE_INSTANCE_ID,
    ide: _detectIde(),
    pid_timestamp: Date.now() / 1000,
    version: 2,
  };
  writeFileSync(LOCKFILE_PATH, JSON.stringify(identity, null, 2), 'utf8');
  console.error(`[run_server] Lockfile written: PID=${pythonPid} instance=${identity.instance_id} IDE=${identity.ide}`);
}

function clearLockfile() {
  try {
    if (existsSync(LOCKFILE_PATH)) {
      // Only clear if it's OUR lockfile (check instance_id)
      const lock = readLockfile();
      if (lock && lock.instance_id === _NODE_INSTANCE_ID) {
        unlinkSync(LOCKFILE_PATH);
        console.error(`[run_server] Lockfile cleared: ${LOCKFILE_PATH}`);
      } else if (lock) {
        console.error(`[run_server] Not clearing lockfile — belongs to different instance (${lock.instance_id})`);
      }
    }
  } catch (err) {
    console.error(`[run_server] Cannot clear lockfile: ${err.message}`);
  }
}

function readKilledCache() {
  try {
    if (!existsSync(KILLED_CACHE_PATH)) return {};
    const content = readFileSync(KILLED_CACHE_PATH, 'utf8').trim();
    return JSON.parse(content) || {};
  } catch {
    return {};
  }
}

function writeKilledCache(data) {
  try {
    writeFileSync(KILLED_CACHE_PATH, JSON.stringify(data, null, 2), 'utf8');
  } catch (err) {
    console.error(`[run_server] Cannot write killed cache: ${err.message}`);
  }
}

function killProcessByPid(pid) {
  if (!pid || isNaN(pid)) return false;
  if (process.platform === 'win32') {
    try {
      // Check if process exists first
      const check = spawnSync('tasklist', ['/FI', `PID eq ${pid}`, '/FO', 'CSV', '/NH'], {
        shell: true,
        timeout: 5000,
      });
      if (!check.stdout || !check.stdout.toString().includes(String(pid))) {
        return false; // Process doesn't exist
      }
      // Graceful kill first
      try {
        execSync(`taskkill /PID ${pid}`, { timeout: 5000 });
        console.error(`[run_server] Sent graceful kill to PID ${pid}`);
      } catch { }
      // Wait briefly then force kill if still alive
      const wait = (ms) => new Promise(r => setTimeout(r, ms));
      // Can't use sync wait, so just do forced kill
      execSync(`taskkill /F /PID ${pid}`, { timeout: 5000, stdio: 'pipe' });
      console.error(`[run_server] Killed stale PID ${pid}`);
      return true;
    } catch (err) {
      console.error(`[run_server] Cannot kill PID ${pid}: ${err.message}`);
      return false;
    }
  } else {
    // Unix: SIGTERM, wait, SIGKILL
    try {
      process.kill(pid, 'SIGTERM');
    } catch { }
    try {
      process.kill(pid, 0); // Still alive?
      process.kill(pid, 'SIGKILL');
    } catch { }
    return true;
  }
}

function handleStaleInstance() {
  const lock = readLockfile();
  if (!lock || !lock.pid) {
    console.error('[run_server] No stale PID lockfile found');
    return;
  }

  // If lockfile has our own PID, it's a stale file from a previous session
  if (lock.pid === process.pid) {
    console.error(`[run_server] Lockfile has our own PID ${lock.pid} — cleaning stale file`);
    clearLockfile();
    return;
  }

  // If lockfile has our own instance_id (Node), it's ours — skip
  if (lock.source === 'node' && lock.instance_id === _NODE_INSTANCE_ID) {
    console.error(`[run_server] Lockfile belongs to us (instance=${lock.instance_id}) — skipping`);
    return;
  }

  // Check killed cache: if this PID was recently killed, don't kill again
  const killedCache = readKilledCache();
  const now = Date.now() / 1000;
  let foundRecentlyKilled = false;
  for (const [kpid, ktime] of Object.entries(killedCache)) {
    if (parseInt(kpid) === lock.pid && (now - ktime) < 30) {
      foundRecentlyKilled = true;
      break;
    }
  }
  if (foundRecentlyKilled) {
    console.error(`[run_server] Lockfile PID ${lock.pid} — recently killed, skipping`);
    return;
  }

  console.error(
    `[run_server] Found stale instance: PID=${lock.pid} ` +
    `source=${lock.source || 'unknown'} instance=${lock.instance_id || '?'} ` +
    `IDE=${lock.ide || '?'} sig=${lock.signature || '?'}`
  );
  killProcessByPid(lock.pid);
  clearLockfile();

  // Record in killed cache
  killedCache[String(lock.pid)] = now;
  writeKilledCache(killedCache);

  // Small delay for OS resource release
  const wait = (ms) => {
    const start = Date.now();
    while (Date.now() - start < ms) { } // blocking wait
  };
  wait(800);
}

// ═══════════════════════════════════════════
// PYTHON DISCOVERY
// ═══════════════════════════════════════════
function findPythonExecutable() {
  const pythonCommands = ['python3', 'python'];
  for (const cmd of pythonCommands) {
    try {
      const result = spawnSync(cmd, ['--version'], { shell: true });
      if (result.status === 0) return cmd;
    } catch { }
  }
  return 'python';
}

function checkUv() {
  try {
    const result = spawnSync('uv', ['--version'], { shell: true });
    return result.status === 0;
  } catch {
    return false;
  }
}

function loadEnv() {
  const envPath = join(projectRoot, '.env');
  if (existsSync(envPath)) {
    const content = readFileSync(envPath, 'utf8');
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

function runServer() {
  // PHASE 0: Kill stale Python instances BEFORE starting
  handleStaleInstance();

  loadEnv();
  const python = findPythonExecutable();
  const mainPath = join(projectRoot, 'src', 'main.py');

  const env = {
    ...process.env,
    CODECORTEX_DB_PATH: process.env.CODECORTEX_DB_PATH || join(projectRoot, 'database', 'codecortex.db'),
    CODECORTEX_GRAPH_BACKEND: process.env.CODECORTEX_GRAPH_BACKEND || 'none',
    CODECORTEX_MAX_REPOS: process.env.CODECORTEX_MAX_REPOS || '50',
    CODECORTEX_TRANSPORT: process.env.CODECORTEX_TRANSPORT || 'stdio',
    PYTHONUNBUFFERED: '1'
  };

  console.error('Starting CodeCortex MCP Server...');
  console.error(`Python: ${python}`);
  console.error(`Project root: ${projectRoot}`);
  console.error(`Lockfile: ${LOCKFILE_PATH}`);

  const child = spawn(python, ['-m', 'src.main'], {
    cwd: projectRoot,
    env: env,
    stdio: ['inherit', 'inherit', 'inherit']
  });

  console.error(`[run_server] Child PID: ${child.pid}`);

  // Write Node-specific lockfile with Python's PID
  // This lets both Python and Node know which instance they belong to
  writeNodeLockfile(child.pid);

  child.on('close', (code) => {
    console.error(`[run_server] Python child exited with code: ${code}`);

    // Clean lockfile only if it's OUR lockfile (instance-aware)
    clearLockfile();

    // Don't exit if it's just a restart — let IDE handle lifecycle
    process.exit(code || 0);
  });

  child.on('error', (err) => {
    console.error('[run_server] Failed to spawn Python child:', err.message);
    clearLockfile();
    process.exit(1);
  });

  // Handle parent process signals — forward to child, clean up
  const cleanup = () => {
    clearLockfile();
    if (child && !child.killed) {
      child.kill('SIGTERM');
    }
  };

  process.on('SIGINT', cleanup);
  process.on('SIGTERM', cleanup);
  process.on('exit', cleanup);
}

runServer();
