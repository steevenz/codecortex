import { spawn } from 'child_process';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import { existsSync } from 'fs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const projectRoot = join(__dirname, '..', '..');

function findPythonExecutable() {
  const pythonCommands = ['python3', 'python'];
  for (const cmd of pythonCommands) {
    try {
      const result = spawn.sync(cmd, ['--version'], { shell: true });
      if (result.status === 0) return cmd;
    } catch { }
  }
  return 'python';
}

function checkUv() {
  try {
    const result = spawn.sync('uv', ['--version'], { shell: true });
    return result.status === 0;
  } catch {
    return false;
  }
}

import { readFileSync, existsSync } from 'fs';

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
  console.error(`Environment:`);
  console.error(`  CODECORTEX_DB_PATH=${env.CODECORTEX_DB_PATH}`);
  console.error(`  CODECORTEX_GRAPH_BACKEND=${env.CODECORTEX_GRAPH_BACKEND}`);
  console.error(`  CODECORTEX_MAX_REPOS=${env.CODECORTEX_MAX_REPOS}`);
  console.error(`  CODECORTEX_TRANSPORT=${env.CODECORTEX_TRANSPORT}`);

  const child = spawn(python, ['-m', 'src.main'], {
    cwd: projectRoot,
    env: env,
    stdio: ['inherit', 'inherit', 'inherit']
  });

  child.on('close', (code) => {
    console.error(`Server closed with code: ${code}`);
    process.exit(code || 0);
  });

  child.on('error', (err) => {
    console.error('Failed to start CodeCortex MCP server:', err.message);
    process.exit(1);
  });
}

runServer();
