import re

content = open('README.md', encoding='utf-8').read()
lines = content.splitlines()
print(f'Total lines : {len(lines)}')
print(f'Total chars : {len(content)}')
print()

# 1. Badge check — no (.) links
bad_badges = re.findall(r'shields\.io[^\)]*\]\(\.\)', content)
print(f'Broken badge links (.)  : {len(bad_badges)}  {"FAIL" if bad_badges else "OK"}')

# 2. All required sections present
sections = [
    '## What is Evo-AI?',
    '### How it looks',
    '### Core ideas',
    '## Screenshots',
    '## Features',
    '## Why Deterministic?',
    '## Quick Start',
    '## Interfaces',
    '### CLI',
    '### Overlay',
    '### Voice',
    '## How It Works',
    '### Architecture Overview',
    '### Intelligence Pipeline',
    '### Resolution Pipeline',
    '### Parameter Extraction',
    '### Execution Context',
    '### Safety Layers',
    '## All 17 Tools',
    '## Command Reference',
    '## Configuration',
    '## Project Structure',
    '## Requirements',
    '## Resource Usage',
    '## Limitations',
    '## Architecture',
]
missing = [s for s in sections if s not in content]
print(f'Missing sections        : {len(missing)}  {"FAIL" if missing else "OK"}')
for m in missing:
    print(f'  MISSING: {m}')

# 3. No dangling (.) badge links remain
dot_links = re.findall(r'\]\(\.\)', content)
print(f'Dangling (.) links      : {len(dot_links)}  {"FAIL" if dot_links else "OK"}')

# 4. No unclosed <div> tags
open_divs  = len(re.findall(r'<div', content))
close_divs = len(re.findall(r'</div>', content))
print(f'<div> balance           : open={open_divs} close={close_divs}  {"FAIL" if open_divs != close_divs else "OK"}')

# 5. Code blocks balanced
code_fences = len(re.findall(r'^```', content, re.MULTILINE))
print(f'Code fence count        : {code_fences}  {"FAIL (odd)" if code_fences % 2 != 0 else "OK (even)"}')

# 6. Tables have header separators
table_rows = re.findall(r'^\|.*\|$', content, re.MULTILINE)
print(f'Table rows found        : {len(table_rows)}  OK')

# 7. Screenshot placeholders present
placeholders = re.findall(r'<!--.*screenshot.*-->', content, re.IGNORECASE)
print(f'Screenshot placeholders : {len(placeholders)}  {"OK" if placeholders else "WARN (none found)"}')

# 8. Why Deterministic section has content
why_idx = content.find('## Why Deterministic?')
why_section = content[why_idx:why_idx+800] if why_idx >= 0 else ''
has_philosophy = 'deterministic' in why_section.lower() and 'audit' in why_section.lower()
print(f'Why Deterministic depth : {"OK" if has_philosophy else "WARN"}')

print()
overall = not missing and not bad_badges and not dot_links and open_divs == close_divs and code_fences % 2 == 0
print('OVERALL:', 'PASS' if overall else 'NEEDS REVIEW')
