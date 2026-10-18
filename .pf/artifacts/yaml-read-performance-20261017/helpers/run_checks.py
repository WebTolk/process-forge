import concurrent.futures
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / '.pf/artifacts/yaml-read-performance-20261017/checks'
OUT.mkdir(parents=True, exist_ok=True)
TMP = ROOT / '.pf/tmp/yaml-read-performance-20261017/test-tmp'
TMP.mkdir(exist_ok=True)
environment = os.environ.copy()
environment['TEMP'] = environment['TMP'] = str(TMP)
environment['PYTHONDONTWRITEBYTECODE'] = '1'


def run(name):
    start = time.monotonic()
    command = [sys.executable, '-B', str(ROOT / 'tools' / name)]
    if name == 'smoke_process_catalog_real_core.py':
        command += ['--scratch-root', str(TMP / 'catalog')]
    try:
        result = subprocess.run(command, cwd=ROOT, env=environment, capture_output=True,
                                text=True, encoding='utf-8', errors='replace', timeout=240)
        receipt = {'check': name, 'returncode': result.returncode,
                   'elapsed_seconds': round(time.monotonic() - start, 3)}
        (OUT / (name + '.txt')).write_text(result.stdout + result.stderr, encoding='utf-8')
    except subprocess.TimeoutExpired as error:
        receipt = {'check': name, 'returncode': None, 'timeout': True,
                   'elapsed_seconds': round(time.monotonic() - start, 3)}
        raw = (error.stdout or b'') + (error.stderr or b'')
        (OUT / (name + '.txt')).write_bytes(raw)
    print(json.dumps(receipt), flush=True)
    return receipt


with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
    results = list(pool.map(run, sys.argv[1:]))
(OUT / ('results-' + str(time.time_ns()) + '.json')).write_text(json.dumps(results, indent=2) + '\n', encoding='utf-8')
raise SystemExit(0 if all(row['returncode'] == 0 for row in results) else 1)
