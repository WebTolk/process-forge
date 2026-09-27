"""Private T06 acceptance setup; constructors come only from delivered installed Core."""
import copy
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
CORE = Path('D:/.agents/processforge')
WORKPLACE = Path('D:/.agents/processforge-workplace')
FIXTURE = REPO / '.pf/tmp/t06-host-acceptance-20260926/project'
sys.path[:0] = [str(CORE / 'tools'), str(CORE / 'src')]
import processforge as core
from process_execution_smoke_support import PROCESS


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def boundary():
    manifest = json.loads((CORE / 'processforge-core.manifest.json').read_text(encoding='utf-8'))
    installed = {row['relative_path']: digest(CORE / row['relative_path']) for row in manifest['files']}
    mismatches = [row['relative_path'] for row in manifest['files'] if installed[row['relative_path']] != row['sha256']]
    product = {p: digest(REPO / p) for p in installed if not p.startswith('.pf/') and (REPO / p).is_file()}
    frozen = {}
    for parent in (REPO / '.pf/artifacts', REPO / '.pf/contexts/assignment-capsules', REPO / '.pf/contexts/project-context.snapshots'):
        for path in parent.rglob('*'):
            if path.is_file() and OUT not in path.parents and path.suffix.lower() in {'.md', '.yaml', '.json', '.py', '.jsonl'}:
                if 'projections' not in path.parts and path.parent != REPO / '.pf/artifacts':
                    frozen[str(path.relative_to(REPO))] = digest(path)
    configs = [WORKPLACE / 'workplace.yaml', *sorted((WORKPLACE / 'registries').glob('*.yaml')),
               REPO / '.pf/process-forge.yaml', REPO / '.pf/contexts/project-context.snapshot.yaml',
               Path('C:/Users/musst/.codex/config.toml')]
    return {'time_utc': datetime.now(timezone.utc).isoformat(), 'installed': installed,
            'installed_mismatches': mismatches, 'product': product, 'frozen': frozen,
            'configs': {str(p): digest(p) for p in configs if p.is_file()}}


def refresh():
    # Public constructor writes only this fixture's snapshot/cache/report. Avoid
    # CLI index-maintenance side effects on the application's global Workplace.
    result = core.write_project_context_snapshot_outputs(FIXTURE, explicit_workplace=str(WORKPLACE))
    save('fixture-refresh-latest.json', {'status': result[0], 'snapshot': result[2]})
    check = core.project_context_check_result(FIXTURE, explicit_workplace=str(WORKPLACE))
    save('fixture-context-check.json', check)
    assert check['status'] in ('fresh', 'fresh_with_updates'), check


def init():
    assert not FIXTURE.exists(), 'Refuse to overwrite prior fixture'
    baseline = boundary()
    save('boundary-before.json', baseline)
    assert not baseline['installed_mismatches'], baseline['installed_mismatches']
    flow = FIXTURE / '.pf'
    for name in ('packages', 'resources/guide', 'resources/unselected', 'artifacts', 'assignments', 'contexts', 'runs', 'handoffs', 'logs'):
        (flow / name).mkdir(parents=True, exist_ok=True)
    process = copy.deepcopy(PROCESS)
    process['id'] = 't06-host-fixture'
    process['stages'][1]['resource_subset'] = []
    path = FIXTURE / 'processes/custom/t06-host-fixture.yaml'
    path.parent.mkdir(parents=True)
    path.write_text(yaml.safe_dump(process, sort_keys=False), encoding='utf-8')
    package_id = 'project.t06-host-fixture'
    manifest = {'schema_version': 1, 'project': {'id': 't06-host-fixture', 'type': 'generic'},
                'process_forge': {'version': '1.1.0', 'mode': 'file_only'},
                'workplace': {'reference': 'auto'}, 'process': 't06-host-fixture',
                'processes': [{'id': process['id'], 'path': '../processes/custom/t06-host-fixture.yaml'}],
                'packages': [{'id': package_id, 'path': 'packages/' + package_id + '.yaml'}],
                'knowledge_stack': [{'id': package_id, 'version': '1.0.0', 'source': 'project'}],
                'context_requirements': {'knowledge_packages': [{'id': package_id, 'constraint': '*', 'required': True}],
                                         'knowledge_resources': [{'id': 'guide', 'constraint': '*', 'required': True}]}}
    (flow / 'process-forge.yaml').write_text(yaml.safe_dump(manifest, sort_keys=False), encoding='utf-8')
    package = {'schema_version': 1, 'id': package_id, 'name': 'T06 host fixture', 'version': '1.0.0',
               'kind': 'project', 'scope': 'project', 'status': 'draft', 'resources': []}
    for rid in ('guide', 'unselected'):
        package['resources'].append({'id': rid, 'kind': 'reference', 'title': 'T06 ' + rid,
            'path_ref': {'package': package_id, 'relative_path': 'resources/' + rid},
            'indexing': {'enabled': True, 'mode': 'fulltext', 'sources': [{'path': '.', 'mode': 'fulltext', 'include': ['**/*.md']}]}})
    (flow / 'packages' / (package_id + '.yaml')).write_text(yaml.safe_dump(package, sort_keys=False), encoding='utf-8')
    (flow / 'resources/guide/guide.md').write_text('T06HostAcceptanceNeedle authorized original content.\n', encoding='utf-8')
    (flow / 'resources/unselected/private.md').write_text('T06UnselectedNeedle must remain outside this Work.\n', encoding='utf-8')
    (flow / 'artifacts/proof.md').write_text('Fixture stage evidence for actual connected MCP acceptance.\n', encoding='utf-8')
    save('fixture-manifest-original.json', manifest)
    refresh()
    save('fixture-identity.json', {'project_root': str(FIXTURE), 'core_constructor': core.__file__,
         'resource_id': package_id + ':guide', 'unselected_resource_id': package_id + ':unselected',
         'objective': 'T06 actual connected host isolated current contract acceptance'})
    print(json.dumps({'fixture': str(FIXTURE), 'installed_files_verified': len(baseline['installed']), 'frozen_files': len(baseline['frozen'])}))


command = sys.argv[1]
if command == 'init':
    init()
elif command == 'profile':
    profile = sys.argv[2]
    config = {'schema_version': 1, 'profile': profile, 'sink': 'jsonl'}
    if profile in ('diagnostic', 'trace'):
        config['expires_at'] = (datetime.now(timezone.utc) + timedelta(minutes=12)).isoformat()
    (FIXTURE / '.pf/diagnostics.json').write_text(json.dumps(config), encoding='utf-8')
    print(json.dumps(config))
elif command in ('drift', 'restore-material'):
    text = 'T06HostAcceptanceNeedle authorized original content.\n' if command == 'restore-material' else 'T06HostDriftChanged.\n'
    (FIXTURE / '.pf/resources/guide/guide.md').write_text(text, encoding='utf-8')
    print(command)
elif command in ('revoke', 'restore-grant'):
    manifest = json.loads((OUT / 'fixture-manifest-original.json').read_text(encoding='utf-8'))
    if command == 'revoke':
        manifest['knowledge_stack'] = []
        manifest['context_requirements'] = {'knowledge_packages': [], 'knowledge_resources': []}
        manifest['packages'] = []
    (FIXTURE / '.pf/process-forge.yaml').write_text(yaml.safe_dump(manifest, sort_keys=False), encoding='utf-8')
    refresh()
    print(command)
elif command == 'boundary':
    before = json.loads((OUT / 'boundary-before.json').read_text(encoding='utf-8'))
    after = boundary()
    changed = {group: [p for p, v in before[group].items() if after[group].get(p) != v] for group in ('installed', 'product', 'frozen', 'configs')}
    save('boundary-after.json', after)
    save('boundary-result.json', {'changed': changed, 'installed_mismatches': after['installed_mismatches']})
    print(json.dumps(changed))
