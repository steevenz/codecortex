
import subprocess
import json
import time
import os
import sys

def test_proxy():
    # Use the absolute path to index.js
    proxy_js = r"c:\Users\steevenz\MCP\mcp-codecortex\scripts\server\js\index.js"
    
    print(f"Starting proxy: node {proxy_js}")
    
    # Start the proxy process
    process = subprocess.Popen(
        ["node", proxy_js],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        env=os.environ.copy()
    )
    
    def send_rpc(method, params=None, rpc_id=1):
        req = {
            "jsonrpc": "2.0",
            "id": rpc_id,
            "method": method,
            "params": params or {}
        }
        print(f"\n[CLIENT] Sending: {method}")
        process.stdin.write(json.dumps(req) + "\n")
        process.stdin.flush()
        
        # Read response
        line = process.stdout.readline()
        if line:
            print(f"[CLIENT] Received: {line.strip()[:200]}...")
            return json.loads(line)
        return None

    try:
        # 1. Initialize
        res = send_rpc("initialize", {"protocolVersion": "2024-11-05"})
        if not res or "result" not in res:
            print("Failed to initialize")
            # print stderr to see what happened
            err = process.stderr.read()
            print(f"Proxy Stderr: {err}")
            return

        # 2. List Tools
        res = send_rpc("tools/list")
        if res and "result" in res:
            tools = res["result"].get("tools", [])
            print(f"Found {len(tools)} tools")
        
        # 3. Ping
        send_rpc("ping")

        print("\nTest completed successfully. Terminating proxy...")
    except Exception as e:
        print(f"Test failed: {e}")
    finally:
        process.terminate()
        # Read any remaining stderr
        stdout, stderr = process.communicate(timeout=5)
        if stderr:
            print(f"\nFinal Proxy Stderr:\n{stderr}")

if __name__ == "__main__":
    test_proxy()
