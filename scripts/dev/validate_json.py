#!/usr/bin/env python
"""JSON Validation Script for all output files."""

import json
import sys
from pathlib import Path

JSON_FILES = [
    'package.json',
    '.config/mcp_client_stdio.json',
    '.config/mcp_client_sse.json',
    'docs/features/scaffolder/examples/create-project.json',
    'docs/features/scaffolder/examples/generate-class.json',
    'docs/features/scaffolder/examples/validate-name.json',
    'docs/features/scaffolder/examples/list-stacks.json',
    'docs/features/scaffolder/examples/generate-content.json',
    'docs/features/scaffolder/examples/get-stack.json',
    'docs/features/codegraph/examples/graph-build-incremental.json',
    'docs/features/codeindex/examples/semantic-search-results.json',
    'docs/features/codegraph/examples/graph-query-callers.json',
]

def main():
    results = []
    for f in JSON_FILES:
        path = Path(f)
        if path.exists():
            try:
                data = json.loads(path.read_text())
                results.append({'file': f, 'valid': True, 'error': None, 'size': len(json.dumps(data))})
            except json.JSONDecodeError as e:
                results.append({'file': f, 'valid': False, 'error': str(e), 'size': 0})
        else:
            results.append({'file': f, 'valid': False, 'error': 'File not found', 'size': 0})

    print('JSON VALIDATION RESULTS')
    print('=' * 60)
    for r in results:
        status = 'VALID' if r['valid'] else 'INVALID'
        print(f'{status}: {r["file"]} ({r["size"]} bytes)')
        if r['error']:
            print(f'   Error: {r["error"]}')
    
    print()
    print(f'Total: {len(results)} files')
    print(f'Valid: {sum(1 for r in results if r["valid"])}')
    print(f'Invalid: {sum(1 for r in results if not r["valid"])}')
    
    return 0 if all(r['valid'] for r in results) else 1

if __name__ == '__main__':
    sys.exit(main())