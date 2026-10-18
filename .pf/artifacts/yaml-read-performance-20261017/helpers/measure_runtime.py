"""Measure the pinned actual updated service, then sample its current stacks."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[3]
TASK = Path(__file__).resolve().parent
OUT = ROOT / '.pf/artifacts/yaml-read-performance-20261017'
SERVICE = Path('D:/.agents/processforge-workplace/runtime/pf-runtime/service.json')
SPY = ROOT / '.pf/tmp/runtime-cpu-root-cause-20261017/profiler/unpacked/py_spy-0.4.2.data/scripts/py-spy.exe'

def state(label):
    result = json.loads(SERVICE.read_text(encoding='utf-8'))
    for field in ('token_hash', 'token_ref'):
        result.pop(field, None)
    assert result['pid'] == 18280 and result['instance_id'] == 'e6906e3fd2a74ffdba75b60cae8df1b7', 'owner_changed'
    assert result['status'] == 'ready', result['status']
    (OUT / (label + '.json')).write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    return result

def identity(value):
    return {field: value[field] for field in ('pid', 'instance_id', 'started_at')}

assert hashlib.sha256(SPY.read_bytes()).hexdigest() == '6e83ab095f40453742d01a2719a178f308534015da519ec0659d2584139dc995'
before = state('runtime-before-cpu')
started = datetime.fromisoformat(before['started_at'].replace('Z', '+00:00'))
remaining = 45 - (datetime.now(timezone.utc) - started).total_seconds()
if remaining > 0:
    time.sleep(remaining)
with urllib.request.urlopen(before['endpoint'] + '/readyz', timeout=10) as response:
    ready = {'status': response.status, 'body': response.read(32768).decode('utf-8')}
(OUT / 'readyz.json').write_text(json.dumps(ready, indent=2) + '\n', encoding='utf-8')
command = [sys.executable, '-B', str(TASK / 'sample_cpu.py'), '--pid', '18280', '--seconds', '60', '--interval', '2', '--output', str(OUT / 'settled-cpu.json')]
print(json.dumps({'step': 'actual-runtime-cpu-start', 'owner': identity(before), 'seconds': 60}), flush=True)
result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=90)
after = state('runtime-after-cpu')
(OUT / 'cpu-command.json').write_text(json.dumps({'command': command, 'returncode': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr, 'owner_before': identity(before), 'owner_after': identity(after)}, indent=2) + '\n', encoding='utf-8')
assert result.returncode == 0 and identity(before) == identity(after), result.stdout + result.stderr
print(result.stdout, flush=True)

before = state('runtime-before-profile')
command = [str(SPY), 'record', '--pid', '18280', '--duration', '30', '--rate', '100', '--gil', '--format', 'raw', '--output', str(OUT / 'runtime-gil-30s.txt')]
print(json.dumps({'step': 'actual-runtime-profile-start', 'owner': identity(before), 'seconds': 30}), flush=True)
start = time.monotonic()
result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=90)
after = state('runtime-after-profile')
(OUT / 'profile-command.json').write_text(json.dumps({'command': command, 'returncode': result.returncode, 'elapsed_seconds': round(time.monotonic() - start, 3), 'stdout': result.stdout, 'stderr': result.stderr, 'owner_before': identity(before), 'owner_after': identity(after)}, indent=2) + '\n', encoding='utf-8')
assert result.returncode == 0 and identity(before) == identity(after), result.stdout + result.stderr
print(result.stdout, flush=True)

buckets, owners, details = Counter(), Counter(), Counter()
total = 0
for line in (OUT / 'runtime-gil-30s.txt').read_text(encoding='utf-8').splitlines():
    stack, count = line.rsplit(' ', 1)
    count = int(count)
    total += count
    owner = 'scheduler' if 'scheduler_loop (' in stack else 'ingress' if 'process_request_thread (' in stack else 'metrics' if 'metrics_loop (' in stack else 'other'
    owners[owner] += count
    if 'pf_runtime\\host.py' in stack and 'read_json (' in stack:
        branch = 'host_json_read'
    elif 'pf_runtime\\host.py' in stack and 'write_json (' in stack:
        branch = 'host_json_write'
    elif 'active_run_ids (' in stack:
        branch = 'run_discovery'
    elif 'command_supervisor_tick (' in stack:
        branch = 'supervisor_actions'
    elif '_refresh_stage_projection (' in stack:
        branch = 'projection'
    elif 'command_agent_director_tick (' in stack:
        branch = 'director'
    else:
        branch = 'other'
    buckets[owner + '_' + branch] += count
    if '(yaml\\' in stack or '(yaml/' in stack:
        details['native_yaml_parser'] += count
    if 'active_run_ids (' in stack and ('(yaml\\' in stack or '(yaml/' in stack):
        details['run_discovery_native_yaml_parser'] += count
    if 'parse_cache.py' in stack:
        details['shared_cache_work'] += count

def share(values):
    return {key: {'samples': value, 'percent': round(value / total * 100, 2)} for key, value in values.most_common()}

summary = {'total_gil_samples': total, 'owners': share(owners), 'exclusive_buckets': share(buckets), 'inclusive_details_do_not_add_to_buckets': share(details), 'sampling_note': 'GIL stack proportions are statistical, not direct device CPU accounting; the CPU measurement is separate.'}
(OUT / 'profile-summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
print(json.dumps(summary), flush=True)
