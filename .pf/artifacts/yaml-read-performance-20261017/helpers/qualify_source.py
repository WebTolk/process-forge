"""Capture read-only public-source gates against the isolated candidate."""
import ast
import concurrent.futures
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
TASK = Path(__file__).resolve().parent
CANDIDATE = TASK / 'candidate'
OUT = ROOT / '.pf/artifacts/yaml-read-performance-20261017/source-checks'
OUT.mkdir(exist_ok=True)
paths = json.loads((TASK / 'product-paths.json').read_text())
for relative in paths:
    if relative.endswith('.py'):
        ast.parse((CANDIDATE / relative).read_text(encoding='utf-8'), filename=relative)
commands = {
    'schema': [sys.executable, '-B', str(CANDIDATE / 'tools/validate-process-forge-schemas.py'), '--root', str(CANDIDATE)],
    'public-cleanliness': [sys.executable, '-B', str(CANDIDATE / 'tools/validate-public-cleanliness.py'), '--root', str(CANDIDATE)],
    'checksums': [sys.executable, '-B', str(CANDIDATE / 'tools/validate-process-forge-checksums.py'), '--root', str(CANDIDATE), '--check'],
    'diff': ['git', 'diff', '--check'],
}
env = os.environ.copy()
env['PYTHONDONTWRITEBYTECODE'] = '1'

def run(item):
    label, command = item
    start = time.monotonic()
    result = subprocess.run(command, cwd=CANDIDATE, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=240, env=env)
    (OUT / (label + '.txt')).write_text(result.stdout + result.stderr, encoding='utf-8')
    row = {'check': label, 'command': command, 'returncode': result.returncode, 'elapsed_seconds': round(time.monotonic() - start, 3)}
    print(json.dumps(row), flush=True)
    return row

with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
    results = list(pool.map(run, commands.items()))
(OUT / 'results.json').write_text(json.dumps({'syntax': 'pass', 'checks': results}, indent=2) + '\n', encoding='utf-8')
raise SystemExit(0 if all(row['returncode'] == 0 for row in results) else 1)
