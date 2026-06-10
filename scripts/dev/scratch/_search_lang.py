"""Search for language column usage on index_stats"""
import pathlib
for f in sorted(pathlib.Path('src').rglob('*.py')):
    try:
        content = f.read_text(encoding='utf-8', errors='ignore')
        if 'language' in content and 'index_stats' in content:
            print(f'{f}:')
            for i, line in enumerate(content.splitlines(), 1):
                if 'language' in line.lower() and 'index_stats' in line.lower():
                    print(f'  {i}: {line.strip()}')
    except Exception:
        pass
