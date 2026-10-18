"""Build an isolated candidate from HEAD and this task's exact public paths."""
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
TASK = Path(__file__).resolve().parent
OUT = ROOT / '.pf/artifacts/yaml-read-performance-20261017'
CANDIDATE = TASK / 'candidate'
PRODUCT = [
    'CHANGELOG.md',
    'docs/concepts/document-reads.md',
    'docs/ru/concepts/document-reads.md',
    'src/processforge_core/common/request_scope.py',
    'src/processforge_core/documents/parse_cache.py',
    'src/processforge_core/documents/reader.py',
    'src/processforge_core/runtime/metrics.py',
    'tools/processforge.py',
    'tools/smoke_request_scope.py',
    'tools/smoke_yaml_parse_cache.py',
]

if CANDIDATE.exists():
    raise SystemExit('candidate_exists; inspect before replacing')
head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
subprocess.run(['git', 'worktree', 'add', '--detach', str(CANDIDATE), head], cwd=ROOT, check=True)
for relative in PRODUCT:
    target = CANDIDATE / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / relative, target)
result = subprocess.run([sys.executable, '-B', str(CANDIDATE / 'tools/validate-process-forge-checksums.py'), '--root', str(CANDIDATE), '--write'], capture_output=True, text=True, encoding='utf-8')
assert result.returncode == 0, result.stdout + result.stderr
shutil.copyfile(CANDIDATE / 'checksums/processforge.sha256', ROOT / 'checksums/processforge.sha256')
PRODUCT.append('checksums/processforge.sha256')
(TASK / 'product-paths.json').write_text(json.dumps(PRODUCT, indent=2) + '\n', encoding='utf-8')
(OUT / 'isolated-candidate.json').write_text(json.dumps({'baseline_head': head, 'candidate': str(CANDIDATE), 'product_paths': PRODUCT, 'checksum_stdout': result.stdout, 'private_project_config_copied': False}, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'baseline': head, 'product_paths': len(PRODUCT), 'candidate': str(CANDIDATE)}))
