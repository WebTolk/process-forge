"""Bounded T08 acceptance helpers; never changes product source or host config."""
from __future__ import annotations
import datetime
import hashlib
import json
import subprocess
import sys
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
INSTALLED = Path('D:/.agents/processforge')
WORKPLACE = Path('D:/.agents/processforge-workplace')
FIXTURE = ROOT / '.pf/tmp/t08-host-acceptance-20260925/project'

def save(name, data):
    (OUT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def cli(base, *args):
    result = subprocess.run([sys.executable, '-B', str(base / 'bin/pf.py'), *map(str, args)], cwd=ROOT, capture_output=True, text=True, encoding='utf-8', timeout=180)
    row = {'argv': list(map(str, args)), 'exit_code': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr}
    if result.returncode:
        save('probe-command-failure.json', row)
        raise AssertionError(row)
    return row

def configs():
    paths = [WORKPLACE / 'workplace.yaml', *sorted((WORKPLACE / 'registries').rglob('*.yaml'))]
    return {str(p.relative_to(WORKPLACE)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}

def setup():
    assert not FIXTURE.exists(), 'Refuse overwriting existing acceptance fixture'
    records = {'time_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'workplace_config_before': configs()}
    for label, base in [('source', ROOT), ('installed', INSTALLED)]:
        row = cli(base, 'project-context-check', '--project-root', ROOT, '--workplace', WORKPLACE, '--json')
        records[label] = json.loads(row['stdout'])
        assert records[label]['status'] == 'fresh'
        assert records[label]['execution_readiness']['status'] == 'ready'
    assert records['source']['snapshot_id'] == records['installed']['snapshot_id'] == 'ctx-20260925-140110-0dbc7c'
    assert records['source']['snapshot_sha256'] == records['installed']['snapshot_sha256']
    save('context-cli-parity-after-restart.json', records)
    records['onboard'] = cli(INSTALLED, 'project-onboard', '--project-root', FIXTURE, '--workplace', WORKPLACE, '--type', 'generic', '--coordination-mode', 'simple', '--apply')
    process = {
        'schema_version': 1, 'id': 't08-host-acceptance', 'name': 'T08 real host acceptance', 'version': '1.0.0', 'status': 'active',
        'description': 'Isolated test of actual host MCP evidence and reconnect continuity.',
        'stages': [
            {'id': 'verify', 'title': 'Verify', 'required_role': 'agent', 'required_inputs': [], 'produced_artifacts': ['verification'], 'entry_gates': [], 'exit_gates': ['verified']},
            {'id': 'finish', 'title': 'Finish', 'required_role': 'agent', 'required_inputs': ['verification'], 'produced_artifacts': ['completion'], 'entry_gates': ['verified'], 'exit_gates': ['accepted']},
        ],
        'artifact_definitions': [
            {'id': name, 'title': name.title(), 'type': 'markdown', 'required': True, 'owner_role': 'agent'} for name in ['verification', 'completion']
        ],
        'gates': [{'id': name, 'description': name, 'type': 'checklist', 'required': True, 'blocking': True} for name in ['verified', 'accepted']],
        'stage_completion': {'handoff_note_required': True},
        'run_completion': {'summary_required': True, 'handoff_artifact_required': True},
    }
    process_path = FIXTURE / 'processes/custom/t08-host-acceptance.yaml'
    process_path.parent.mkdir(parents=True, exist_ok=True)
    process_path.write_text(yaml.safe_dump(process, sort_keys=False), encoding='utf-8')
    manifest_path = FIXTURE / '.pf/process-forge.yaml'
    manifest = yaml.safe_load(manifest_path.read_text(encoding='utf-8'))
    manifest['project']['id'] = 't08-host-acceptance-20260925'
    manifest['process'] = 't08-host-acceptance'
    manifest['context_requirements']['templates'] = [{'id': 'php.class-doc-block', 'required': True}]
    manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding='utf-8')
    records['refresh'] = cli(INSTALLED, 'project-context-refresh', '--project-root', FIXTURE, '--workplace', WORKPLACE, '--reason', 'T08 isolated real-host acceptance', '--apply')
    records['fixture_check'] = json.loads(cli(INSTALLED, 'project-context-check', '--project-root', FIXTURE, '--workplace', WORKPLACE, '--json')['stdout'])
    records['workplace_config_after'] = configs()
    assert records['workplace_config_before'] == records['workplace_config_after']
    assert records['fixture_check']['status'] == 'fresh', records['fixture_check']
    save('fixture-setup.json', records)
    print(json.dumps({'fixture': str(FIXTURE), 'status': records['fixture_check']['status'], 'workplace_config_unchanged': True}))

if __name__ == '__main__':
    setup()
