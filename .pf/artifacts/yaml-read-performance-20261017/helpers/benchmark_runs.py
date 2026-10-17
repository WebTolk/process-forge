import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

parser = argparse.ArgumentParser()
parser.add_argument('--core-root', type=Path, required=True)
parser.add_argument('--project-root', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--passes', type=int, default=3)
args = parser.parse_args()
sys.path.insert(0, str(args.core_root / 'src'))
sys.path.insert(0, str(args.core_root / 'tools'))
import processforge as core
from processforge_core.common import request_scope

observations = []
expected = None
for number in range(args.passes):
    start, cpu = time.perf_counter(), time.process_time()
    identifiers = core.active_run_ids(args.project_root)
    elapsed, cpu_seconds = time.perf_counter() - start, time.process_time() - cpu
    if expected is None:
        expected = identifiers
    assert expected == identifiers, 'same frozen corpus changed result'
    observation = {'pass': number + 1, 'wall_seconds': round(elapsed, 6), 'cpu_seconds': round(cpu_seconds, 6), 'active_ids': len(identifiers), 'result_sha256': hashlib.sha256(json.dumps(identifiers).encode()).hexdigest()}
    cache = getattr(request_scope, '_PARSE_CACHE', None)
    if cache is not None:
        observation['parse_cache'] = cache.info()
    observations.append(observation)
result = {'core_root': str(args.core_root), 'frozen_project': str(args.project_root), 'run_yaml_files': len(list((args.project_root / '.pf/runs').glob('*/run.yaml'))), 'observations': observations, 'identifiers': expected}
args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
print(json.dumps({key: value for key, value in result.items() if key != 'identifiers'}))
