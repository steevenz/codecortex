
import subprocess
import json
import os
import time
from pathlib import Path

def test_all_tools():
    proxy_js = r"c:\Users\steevenz\MCP\mcp-codecortex\scripts\server\js\index.js"
    
    print("--- CODECORTEX PRODUCTION TOOL AUDIT (v2: 27 TOOLS) ---")
    
    # Target tools list
    TARGET_TOOLS = {
        "repo_init", "repo_inspect", "git_status", "git_commit", "repo_analyze", "repo_codemap",
        "fs_tree", "fs_read", "fs_write", "fs_manage", "fs_glob",
        "search_code", "search_replace", "refactor_symbol", "refactor_impact", "refactor_apply",
        "graph_find_symbols", "graph_query", "graph_find_related", "graph_build", "graph_trace_flow",
        "arch_analyze", "arch_audit",
        "qa_run", "qa_status",
        "index_repo", "index_file"
    }
    
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
        req = {"jsonrpc": "2.0", "id": rpc_id, "method": method, "params": params or {}}
        process.stdin.write(json.dumps(req) + "\n")
        process.stdin.flush()
        line = process.stdout.readline()
        if not line: return None
        return json.loads(line)

    try:
        # 1. Initialize
        print("[1/4] Initializing connection...")
        init_res = send_rpc("initialize", {"protocolVersion": "2024-11-05"})
        if not init_res:
            print("ERROR: No response from proxy during initialization.")
            return

        # 2. List Tools
        print("[2/4] Fetching tool registry...")
        list_res = send_rpc("tools/list")
        tools = list_res.get("result", {}).get("tools", [])
        tool_names = {t["name"] for t in tools}
        
        print(f"Total Tools Registered: {len(tool_names)}")
        
        # Verify Tool Count
        if len(tool_names) == 27:
            print("✅ SUCCESS: Exactly 27 tools registered.")
        else:
            print(f"❌ FAILURE: Expected 27 tools, found {len(tool_names)}.")
            missing = TARGET_TOOLS - tool_names
            extra = tool_names - TARGET_TOOLS
            if missing: print(f"   Missing: {missing}")
            if extra: print(f"   Extra: {extra}")

        # 3. Smoke Test: repo_init
        test_dir = Path(r"c:\Users\steevenz\MCP\mcp-codecortex\scratch\test_repo")
        test_dir.mkdir(exist_ok=True, parents=True)
        (test_dir / "hello.py").write_text("def hello(): print('world')")
        
        print(f"\n[3/4] Testing repo_init on {test_dir}...")
        idx_res = send_rpc("tools/call", {"name": "repo_init", "arguments": {"path": str(test_dir)}})
        
        if not idx_res or "result" not in idx_res:
            print(f"ERROR: repo_init failed with NO response.")
            return
            
        content = idx_res["result"].get("content", [])
        if not content:
            print(f"ERROR: repo_init returned empty content. Result: {idx_res}")
            return
            
        try:
            data_str = content[0].get("text", "")
            data = json.loads(data_str)
            if data.get("success"):
                repo_id = data["data"]["repository_id"]
                print(f"✅ SUCCESS: Initialized repository (ID: {repo_id})")
                
                # 4. Test fs_tree
                print("\n[4/4] Testing fs_tree...")
                tree_res = send_rpc("tools/call", {"name": "fs_tree", "arguments": {"repo_id": repo_id}})
                tree_content = tree_res["result"].get("content", [])
                if tree_content:
                    tree_data = json.loads(tree_content[0].get("text", "{}"))
                    if tree_data.get("success"):
                        print("✅ SUCCESS: Retrieved filesystem tree.")
                    else:
                        print(f"❌ FAILURE: fs_tree logic error: {tree_data}")
                else:
                    print(f"❌ FAILURE: fs_tree returned no content. {tree_res}")
            else:
                print(f"❌ FAILURE: repo_init logic error: {data}")
        except Exception as e:
            print(f"ERROR parsing result: {e}. Content: {content}")

    except Exception as e:
        print(f"Audit failed with exception: {e}")
    finally:
        print("\nAudit finished. Cleaning up...")
        process.terminate()

if __name__ == "__main__":
    test_all_tools()
