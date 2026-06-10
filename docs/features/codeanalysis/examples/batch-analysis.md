# Batch Analysis Example

Demonstrates parallel processing of multiple targets with the `code_analyze` tool.

## Basic Batch Analysis

```python
from src.modules.codeanalysis.api.tools import code_analyze

# Analyze multiple modules in parallel
result = code_analyze(
    target="src/",  # Fallback target
    targets=[
        "src/auth/",
        "src/payment/",
        "src/user/",
        "src/notification/",
    ],
    mode="batch_detailed",
    parallel=True,
    max_workers=4,
)

print(f"Analyzed {result['count']} symbols across {len(result['targets'])} targets")
print(f"Found {len(result['edges'])} relationships")
```

## Cross-Target Call Graph

Batch analysis automatically builds call graphs across all analyzed targets, showing inter-module dependencies.

```python
# The result includes edges showing cross-target calls
for edge in result['edges']:
    print(f"{edge['from_symbol']} -> {edge['to_symbol']} ({edge['relation']})")
```

## Error Handling

Batch analysis continues even if one target fails:

```python
# If one target fails, others continue
# Errors are reported in the result
for target in targets:
    target_path, symbols, error = analyze_single(target)
    if error:
        errors.append({"target": target_path, "error": error})
    elif symbols:
        all_symbols.extend(symbols)
```

## Performance Tips

- Use `parallel=True` for large codebases
- Adjust `max_workers` based on CPU cores
- Use `follow_depth` to limit call graph complexity
