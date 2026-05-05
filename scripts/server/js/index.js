#!/usr/bin/env node

/**
 * CodeCortex Shared Server Proxy
 * 
 * This Node.js wrapper provides:
 * 1. Port locking to prevent multiple instance collisions.
 * 2. Automatic Python venv discovery and management.
 * 3. Bidirectional Proxying: stdio -> HTTP/SSE.
 * 4. Multi-client support: Allows multiple IDEs to share the same CodeCortex backend.
 */

const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const http = require('http');
const net = require('net');
const os = require('os');

// --- Configuration ---
const PROJECT_ROOT = path.resolve(__dirname, '../../..');
const LOCK_FILE = path.join(PROJECT_ROOT, 'database/codecortex_shared_server.lock');
const STATE_FILE = path.join(PROJECT_ROOT, 'database/codecortex_server_state.json');
const DEFAULT_PORT = parseInt(process.env.CODECORTEX_PORT || '8001');
const API_KEY = process.env.CODECORTEX_DASHBOARD_API_KEY || 'cc-dev-key-2026';
const MCP_SECRET = process.env.CODECORTEX_MCP_SECRET || '';

// --- Logging ---
const log = (msg) => console.error(`[CodeCortex-Proxy] ${msg}`);

/**
 * Ensures database directory exists
 */
function ensureDirs() {
    const dbDir = path.join(PROJECT_ROOT, 'database');
    if (!fs.existsSync(dbDir)) {
        fs.mkdirSync(dbDir, { recursive: true });
    }
}

/**
 * Port Locking Logic
 */
async function acquireLock(port) {
    if (fs.existsSync(LOCK_FILE)) {
        const pid = parseInt(fs.readFileSync(LOCK_FILE, 'utf8'));
        try {
            process.kill(pid, 0); // Check if process exists
            return false; // Already running
        } catch (e) {
            log(`Stale lock found (PID ${pid}). Cleaning up.`);
            fs.unlinkSync(LOCK_FILE);
        }
    }
    fs.writeFileSync(LOCK_FILE, process.pid.toString());
    return true;
}

/**
 * State Management
 */
function updateState(data) {
    const state = {
        pid: process.pid,
        port: data.port,
        startTime: new Date().toISOString(),
        transport: 'sse',
        endpoint: `http://127.0.0.1:${data.port}/codecortex-api/v1/sync${MCP_SECRET ? '/' + MCP_SECRET : ''}`
    };
    fs.writeFileSync(STATE_FILE, JSON.stringify(state, null, 2));
}

/**
 * Python Environment Discovery
 */
function findPython() {
    const venvPaths = [
        path.join(PROJECT_ROOT, '.venv/Scripts/python.exe'),
        path.join(PROJECT_ROOT, 'venv/Scripts/python.exe'),
        'python'
    ];
    for (const p of venvPaths) {
        if (p === 'python' || fs.existsSync(p)) return p;
    }
    return 'python';
}

/**
 * Proxy: stdio -> HTTP
 */
async function forwardRequest(payload) {
    return new Promise((resolve, reject) => {
        const endpoint = MCP_SECRET ? `/codecortex-api/v1/sync/${MCP_SECRET}` : '/codecortex-api/v1/sync';
        const options = {
            hostname: '127.0.0.1',
            port: DEFAULT_PORT,
            path: endpoint,
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-API-KEY': API_KEY
            }
        };

        const req = http.request(options, (res) => {
            let data = '';
            res.on('data', (chunk) => data += chunk);
            res.on('end', () => {
                try {
                    resolve(JSON.parse(data));
                } catch (e) {
                    reject(new Error(`Failed to parse response: ${data}`));
                }
            });
        });

        req.on('error', reject);
        req.write(JSON.stringify(payload));
        req.end();
    });
}

/**
 * Main Execution
 */
async function main() {
    ensureDirs();
    const isPrimary = await acquireLock(DEFAULT_PORT);

    if (isPrimary) {
        log(`Starting Primary Instance on port ${DEFAULT_PORT}...`);
        const python = findPython();
        const serverEnv = { ...process.env, CODECORTEX_TRANSPORT: 'sse', CODECORTEX_PORT: DEFAULT_PORT.toString() };

        const server = spawn(python, ['-m', 'src.main'], {
            cwd: PROJECT_ROOT,
            env: serverEnv,
            stdio: ['inherit', 'pipe', 'inherit']
        });

        server.stdout.on('data', (data) => {
            const line = data.toString();
            // Silence Uvicorn logs but keep application output if needed
            if (!line.includes('INFO:')) {
                process.stdout.write(data);
            }
        });

        server.on('close', (code) => {
            log(`Python server exited with code ${code}`);
            if (fs.existsSync(LOCK_FILE)) fs.unlinkSync(LOCK_FILE);
            process.exit(code);
        });

        updateState({ port: DEFAULT_PORT });

        // Handle process termination
        const cleanup = () => {
            log('Shutting down proxy...');
            server.kill();
            if (fs.existsSync(LOCK_FILE)) fs.unlinkSync(LOCK_FILE);
            process.exit();
        };
        process.on('SIGINT', cleanup);
        process.on('SIGTERM', cleanup);

    } else {
        log(`Connecting to existing server on port ${DEFAULT_PORT}...`);
    }

    // Standard MCP Stdio listener for IDE integration
    process.stdin.on('data', async (data) => {
        try {
            const lines = data.toString().split('\n').filter(l => l.trim());
            for (const line of lines) {
                const rpc = JSON.parse(line);
                const result = await forwardRequest(rpc);
                process.stdout.write(JSON.stringify(result) + '\n');
            }
        } catch (e) {
            log(`Stdio Proxy Error: ${e.message}`);
        }
    });
}

main().catch(err => {
    log(`Fatal error: ${err.message}`);
    process.exit(1);
});
