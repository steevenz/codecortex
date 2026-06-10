"""
Codebase mapping script using MCP tools.
"""
import sys
import asyncio
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.api.orchestration import ActionRouter

async def map_codebase():
    router = ActionRouter(lambda: None)

    # Map repository structure
    result = await router.dispatch('codecortex_repository', 'list', {})
    print('=== REPOSITORY STRUCTURE ===')
    print(json.dumps(result, indent=2))

    # Map filesystem structure
    result = await router.dispatch('codecortex_filesystem', 'list', {'path': '.'})
    print('\n=== FILESYSTEM STRUCTURE ===')
    data = result.get('data', {})
    if 'entries' in data:
        for entry in data['entries'][:20]:
            entry_type = '(dir)' if entry['is_dir'] else '(file)'
            print(f'  {entry["name"]} {entry_type}')

    # Codebase status
    result = await router.dispatch('codecortex_codebase', 'status', {})
    print('\n=== CODEBASE STATUS ===')
    print(json.dumps(result, indent=2))

if __name__ == '__main__':
    asyncio.run(map_codebase())
