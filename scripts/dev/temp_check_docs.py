import sys
files = [
    'docs/features/codegraph/sub-features/knowledge-graph/concept.md',
    'docs/features/codegraph/sub-features/community-detection/concept.md',
    'docs/features/codegraph/sub-features/execution-flow/concept.md',
    'docs/features/codegraph/sub-features/heritage-extraction/concept.md',
    'docs/features/codegraph/sub-features/architecture-audit/concept.md',
    'docs/features/codegraph/sub-features/graph-backends/concept.md',
    'docs/features/codegraph/sub-features/route-extraction/concept.md',
    'docs/features/codegraph/sub-features/orm-dataflow/concept.md',
    'docs/features/codegraph/sub-features/entry-point-scoring/concept.md',
]
for f in files:
    with open(f, 'r', encoding='utf-8') as content:
        text = content.read()
    has_ec = '## Error Codes' in text
    has_perf = '## Performance' in text
    print(f'{f}: EC={has_ec} Perf={has_perf}')
