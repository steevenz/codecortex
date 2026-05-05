#!/usr/bin/env python
"""
CodeCortex Server Discovery and Management CLI

Standalone tool for discovering, starting, and managing CodeCortex servers
for multi-agent scenarios. Ported from CCT (Creative Critical Thinking).

Author: Steeven Andrian Salim — Senior Principal Architect
"""
from __future__ import annotations

import asyncio
import httpx
import logging
import subprocess
import time
import socket
import sys
import os
from typing import Optional, Dict, Any, List, Callable, Union
from dataclasses import dataclass, asdict
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

VERSION = "1.1.0"
TLS_CA_BUNDLE_ENV = "CODECORTEX_CA_BUNDLE"

def resolve_tls_verify(target_url: str) -> Union[bool, str]:
    parsed = urlparse(target_url)
    if parsed.scheme.lower() != "https":
        return True

    ca_bundle = os.getenv(TLS_CA_BUNDLE_ENV, "").strip()
    if not ca_bundle:
        return True

    bundle_path = Path(ca_bundle).expanduser().resolve()
    if not bundle_path.is_file():
        raise RuntimeError(
            f"{TLS_CA_BUNDLE_ENV} is set but file does not exist: {bundle_path}"
        )

    if not os.access(bundle_path, os.R_OK):
        logger.warning(
            "%s is set but unreadable due permissions (%s). Falling back to OS trust store.",
            TLS_CA_BUNDLE_ENV,
            bundle_path,
        )
        return True

    return str(bundle_path)

def build_async_http_client(target_url: str, timeout: float) -> httpx.AsyncClient:
    verify_mode = resolve_tls_verify(target_url)
    return httpx.AsyncClient(timeout=timeout, verify=verify_mode, follow_redirects=False)

def show_banner():
    print(f"\n  CODECORTEX INTELLIGENCE SERVER {VERSION}")
    print("  Crafted By Steeven Andrian Salim - https://github.com/steevenz\n")

@dataclass
class ServerInstance:
    host: str
    port: int
    url: str
    process: Optional[subprocess.Popen] = None
    is_managed: bool = False
    last_health_check: Optional[float] = None
    is_healthy: bool = False
    connection_count: int = 0
    started_at: Optional[float] = None
    uptime_seconds: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['uptime_seconds'] = self.get_uptime()
        return data
    
    def get_uptime(self) -> Optional[float]:
        if self.started_at:
            return time.time() - self.started_at
        return None

class CortexServerDiscovery:
    DEFAULT_PORTS = [8001, 8000, 8002, 8080, 3000, 5000, 3001, 5001]
    DEFAULT_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0"]
    HEALTH_ENDPOINT = "/status"
    TIMEOUT = 2.0
    
    def __init__(
        self,
        hosts: Optional[List[str]] = None,
        ports: Optional[List[int]] = None,
        timeout: float = 2.0
    ):
        self.hosts = hosts or self.DEFAULT_HOSTS
        self.ports = ports or self.DEFAULT_PORTS
        self.timeout = timeout
        self._discovered: Dict[str, ServerInstance] = {}
    
    async def scan(self, verbose: bool = False) -> List[ServerInstance]:
        discovered = []
        tasks = []
        for host in self.hosts:
            for port in self.ports:
                tasks.append(self._check_server(host, port, verbose))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, ServerInstance):
                discovered.append(result)
                self._discovered[f"{result.host}:{result.port}"] = result
        
        logger.info(f"[DISCOVERY] Found {len(discovered)} CodeCortex server(s)")
        return discovered
    
    async def _check_server(self, host: str, port: int, verbose: bool = False) -> Optional[ServerInstance]:
        if host.startswith("http://") or host.startswith("https://"):
            base_url = host.rstrip("/")
            parsed_host = urlparse(base_url).hostname or host
            effective_url = f"{base_url}:{port}" if urlparse(base_url).port is None else base_url
        else:
            base_url = f"http://{host}:{port}"
            parsed_host = host
            effective_url = base_url

        health_url = f"{effective_url}{self.HEALTH_ENDPOINT}"
        try:
            async with build_async_http_client(health_url, self.timeout) as client:
                response = await client.get(health_url)
                if response.status_code == 200:
                    payload = response.json()
                    if isinstance(payload, dict) and payload.get("server", {}).get("name") == "codecortex":
                        if verbose:
                            logger.info(f"  ✓ {parsed_host}:{port} - CodeCortex signature verified")
                        return ServerInstance(
                            host=parsed_host,
                            port=port,
                            url=effective_url,
                            is_healthy=True,
                            last_health_check=time.time()
                        )
        except Exception as e:
            if verbose:
                logger.debug(f"  - {parsed_host}:{port} - check failed: {e}")
        return None

class CortexServerPool:
    def __init__(
        self,
        auto_start: bool = True,
        preferred_port: int = 8001,
        project_root: Optional[str] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        startup_timeout: int = 30
    ):
        self.auto_start = auto_start
        self.preferred_port = preferred_port
        self.project_root = project_root
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.startup_timeout = startup_timeout
        
        self.discovery = CortexServerDiscovery(
            ports=[preferred_port] + CortexServerDiscovery.DEFAULT_PORTS,
            timeout=1.0
        )
        self._server: Optional[ServerInstance] = None
        self._lock = asyncio.Lock()
        self._health_check_task: Optional[asyncio.Task] = None
    
    async def initialize(self) -> str:
        async with self._lock:
            servers = await self.discovery.scan()
            for server in servers:
                if server.port == self.preferred_port:
                    self._server = server
                    logger.info(f"[POOL] Using existing server at {server.url}")
                    return server.url
            
            if servers:
                self._server = servers[0]
                logger.info(f"[POOL] Using discovered server at {self._server.url}")
                return self._server.url
            
            if self.auto_start:
                self._server = await self._start_server()
                return self._server.url
            
            raise RuntimeError("No CodeCortex server available")
    
    async def _start_server(self) -> ServerInstance:
        if not self.project_root:
            self.project_root = str(Path(__file__).parent.parent.parent)
        
        python_exe = os.path.join(self.project_root, ".venv", "Scripts", "python.exe")
        if not os.path.exists(python_exe):
            python_exe = "python"
        
        main_script = os.path.join(self.project_root, "src", "http_server.py")
        
        env = os.environ.copy()
        env["CODECORTEX_PORT"] = str(self.preferred_port)
        env["PYTHONPATH"] = self.project_root
        
        logger.info(f"[POOL] Starting CodeCortex HTTP server on port {self.preferred_port}...")
        
        process = subprocess.Popen(
            [python_exe, "-u", main_script],
            cwd=self.project_root,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
        )
        
        server = ServerInstance(
            host="localhost",
            port=self.preferred_port,
            url=f"http://localhost:{self.preferred_port}",
            process=process,
            is_managed=True,
            started_at=time.time()
        )
        
        for attempt in range(self.startup_timeout):
            await asyncio.sleep(1)
            check = await self.discovery._check_server("localhost", self.preferred_port)
            if check:
                server.is_healthy = True
                server.last_health_check = time.time()
                logger.info(f"[POOL] Server started successfully at {server.url}")
                return server
            if process.poll() is not None:
                raise RuntimeError("CodeCortex server failed to start")
        
        raise RuntimeError("Timeout waiting for CodeCortex server")

async def cli_start():
    show_banner()
    print("🚀 Starting CodeCortex server pool...\n")
    try:
        pool = CortexServerPool(auto_start=True)
        url = await pool.initialize()
        print(f"✅ Server started at {url}")
        print("\n⚠️  Press Ctrl+C to stop")
        while True:
            await asyncio.sleep(1)
    except Exception as e:
        print(f"❌ Failed to start server: {e}")
        return 1

def main():
    import argparse
    parser = argparse.ArgumentParser(description="CodeCortex Server Management")
    parser.add_argument("command", choices=["scan", "start", "status", "health"])
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()
    
    mapping = {
        "scan": lambda: asyncio.run(CortexServerDiscovery().scan(args.verbose)),
        "start": lambda: asyncio.run(cli_start()),
        "status": lambda: asyncio.run(cli_start()), # Placeholder for now
        "health": lambda: asyncio.run(cli_start()), # Placeholder for now
    }
    
    try:
        mapping[args.command]()
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted")

if __name__ == "__main__":
    main()
