"""Primary acceptance inventory; no product or baseline writes."""
from pathlib import Path
import hashlib
import json
import subprocess

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
baseline = json.loads((OUT / 'baseline.json').read_text())
expected_changed = {
    'checksums/processforge.sha256',
    'src/processforge_core/core_update.py',
    'src/processforge_core/local_resource_search.py',
    'tools/processforge.py',
    'tools/pf_runtime/codex_hooks.py',
    'tools/pf_runtime/host.py',
    'tools/pf_runtime/mcp_server.py',
    'tools/pf_runtime/service.py',
    'tools/smoke_long_lived_runtime.py',
    'tools/smoke_single_agent_session_flow.py',
    'tools/smoke_project_init_local_search_mcp.py',
    'tools/smoke_garage_session_enhanced.py',
    'tools/smoke_garage_mode_not_promoted_by_session.py',
    'tools/smoke_governed_work_stage_resolution.py',
    *{f'docs/{language}concepts/{name}.md' for language in ('', 'ru/')
      for name in ('agent-session-model', 'runtime-mcp', 'runtime-model')},
}
regressions = [
    'smoke_search_file_root_containment', 'smoke_search_multiple_roots',
    'smoke_classifier_distribution_parity',
    'smoke_runtime_scheduler_failure_isolation', 'smoke_runtime_singleton_orphan',
    'smoke_core_update_migration_sources', 'smoke_expected_report_containment',
    'smoke_authenticated_report_content', 'smoke_mcp_jsonrpc_validation',
    'smoke_session_identity_roundtrip', 'smoke_codex_lifecycle_identity',
]
def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None

changed = {path: digest(ROOT / path) for path, previous in baseline['hashes'].items()
           if digest(ROOT / path) != previous}
assert set(changed) == expected_changed, sorted(set(changed) ^ expected_changed)
new_public = set(subprocess.check_output(
    ['git', 'ls-files', '--others', '--exclude-standard', '--', 'src', 'tools', 'docs', 'checksums'],
    cwd=ROOT, text=True).splitlines())
assert new_public == {f'tools/{name}.py' for name in regressions}, sorted(new_public)
assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip() == baseline['head']

counterexamples = []
for name in regressions:
    current = json.loads((OUT / 'validation/current' / (name + '.json')).read_text())
    old = json.loads((OUT / 'validation/baseline' / (name + '.json')).read_text())
    assert current['returncode'] == 0, current
    assert old['returncode'] != 0, old
    counterexamples.append({'test': name, 'current': current['returncode'], 'baseline': old['returncode']})

scoped = subprocess.run(['git', 'diff', '--check', '--', 'src', 'tools', 'docs', 'checksums'],
                        cwd=ROOT, capture_output=True, text=True)
(OUT / 'source-diff-check.txt').write_text(scoped.stdout + scoped.stderr, encoding='utf-8')
assert scoped.returncode == 0, scoped.stdout + scoped.stderr
inventory = {
    'baseline_head': baseline['head'], 'baseline_public_file_count': len(baseline['hashes']),
    'changed_tracked_public_files': changed,
    'new_public_files': {path: digest(ROOT / path) for path in sorted(new_public)},
    'regression_counterexamples': counterexamples, 'scoped_diff_check': 'PASS',
    'boundary': 'Source-only uncommitted working tree; unrelated PF artifacts preserved.',
}
(OUT / 'accepted-source-inventory.json').write_text(json.dumps(inventory, indent=2) + '\n', encoding='utf-8')
print(f'PASS: {len(changed)} tracked changes, {len(new_public)} new regressions; '
      f'{len(counterexamples)} baseline/current counterexamples; scoped diff clean; HEAD unchanged')
