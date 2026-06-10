"""
Test JSON identity between CLI, MCP, and API.
"""
import json
import asyncio
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.api.orchestration import ActionRouter
from src.modules.repository.service import get_repository_service, get_codebase_service, get_scaffolder_service
from src.modules.filesystem.service import get_filesystem_service

def ok(message, data):
    import uuid
    from datetime import datetime, timezone
    return {
        'success': True,
        'status_code': 200,
        'message': message,
        'data': data,
        'request_id': str(uuid.uuid4()),
        'meta': {'timestamp': datetime.now(timezone.utc).isoformat()}
    }

def err(message, code):
    import uuid
    from datetime import datetime, timezone
    return {
        'success': False,
        'status_code': 400,
        'message': message,
        'data': None,
        'error_code': code,
        'request_id': str(uuid.uuid4()),
        'meta': {'timestamp': datetime.now(timezone.utc).isoformat()}
    }

async def run_mcp(tool, action, args):
    router = ActionRouter(lambda: None)
    return await router.dispatch(tool, action, args)

def run_cli(tool, action, args):
    action_lower = action.lower()
    if tool == 'codecortex_filesystem':
        service = get_filesystem_service()
        if action_lower == 'list':
            result = service.list(args)
        elif action_lower == 'read':
            result = service.read(args)
        else:
            result = {"success": False, "error": f"Unknown action: {action}"}
    elif tool == 'codecortex_repository':
        service = get_repository_service()
        if action_lower == 'list':
            result = service.list(args)
        elif action_lower == 'inspect':
            result = service.inspect(args)
        else:
            result = {"success": False, "error": f"Unknown action: {action}"}
    elif tool == 'codecortex_codebase':
        service = get_codebase_service()
        if action_lower == 'search':
            result = service.search(args)
        elif action_lower == 'status':
            result = service.status(args)
        else:
            result = {"success": False, "error": f"Unknown action: {action}"}
    elif tool == 'codecortex_scaffolder':
        service = get_scaffolder_service()
        if action_lower == 'list_stacks':
            result = service.list_stacks(args)
        elif action_lower == 'validate_name':
            result = service.validate_name(args)
        else:
            result = {"success": False, "error": f"Unknown action: {action}"}
    else:
        result = {"success": False, "error": f"Unknown tool: {tool}"}
    return result

def compare(name, cli, mcp):
    def normalize(d):
        if not isinstance(d, dict):
            return d
        result = {}
        for k in sorted(d.keys()):
            v = d[k]
            if k == 'data' and isinstance(v, dict):
                result[k] = {k2: normalize(v2) for k2, v2 in sorted(v.items())}
            else:
                result[k] = normalize(v)
        return result

    cli_normalized = normalize(dict(cli))
    mcp_normalized = normalize(dict(mcp))

    for k in ['request_id', 'meta', 'status_code', 'message']:
        if k in cli_normalized:
            del cli_normalized[k]
        if k in mcp_normalized:
            del mcp_normalized[k]

    cli_str = json.dumps(cli_normalized, sort_keys=True, separators=(',', ':'))
    mcp_str = json.dumps(mcp_normalized, sort_keys=True, separators=(',', ':'))
    return {
        'name': name,
        'cli_hash': hashlib.sha256(cli_str.encode()).hexdigest()[:16],
        'mcp_hash': hashlib.sha256(mcp_str.encode()).hexdigest()[:16],
        'identical': cli_str == mcp_str
    }

async def main():
    tests = [
        ('fs_list', 'codecortex_filesystem', 'list', {'path': '.'}),
        ('repo_list', 'codecortex_repository', 'list', {}),
        ('repo_inspect', 'codecortex_repository', 'inspect', {'repo_path': '.'}),
        ('codebase_search', 'codecortex_codebase', 'search', {'query': 'test'}),
        ('codebase_status', 'codecortex_codebase', 'status', {}),
        ('scaffolder_list', 'codecortex_scaffolder', 'list_stacks', {}),
        ('scaffolder_validate', 'codecortex_scaffolder', 'validate_name', {'name': 'test'}),
    ]

    print('=' * 70)
    print('E2E TEST: CLI vs MCP JSON IDENTITY')
    print('=' * 70)

    results = []
    for name, tool, action, args in tests:
        cli_out = run_cli(tool, action, args)
        mcp_out = await run_mcp(tool, action, args)
        cmp = compare(name, cli_out, mcp_out)
        results.append(cmp)
        status = 'PASS' if cmp['identical'] else 'FAIL'
        print(f'{name}: CLI={cmp["cli_hash"]} MCP={cmp["mcp_hash"]} [{status}]')
        if not cmp['identical']:
            print(f'  CLI raw: {json.dumps(cli_out, sort_keys=True)}')
            print(f'  MCP raw: {json.dumps(mcp_out, sort_keys=True)}')

    passed = sum(1 for r in results if r['identical'])
    print('=' * 70)
    print(f'Total: {len(results)} | Passed: {passed} | Failed: {len(results) - passed}')
    return results

if __name__ == '__main__':
    results = asyncio.run(main())
