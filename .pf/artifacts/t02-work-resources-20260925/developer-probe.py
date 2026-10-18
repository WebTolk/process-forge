import json
from pathlib import Path
import sys
import yaml
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools'))
from process_execution_smoke_support import fixture
from garage_search_smoke_support import register_fixture_resource, select_fixture_resource, run_cli
from smoke_garage_mode_not_promoted_by_session import call_mcp

with fixture() as (workplace, project, initial):
    identifier = register_fixture_resource(workplace, 'fixture.t02-probe', 'guide', {'guide.md': 'PinnedMaterialNeedle'}, title='Guide')
    declaration = workplace / 'packages/fixture.t02-probe/package.yaml'
    package = yaml.safe_load(declaration.read_text(encoding='utf-8'))
    package['resources'][0]['indexing'] = {'enabled': True, 'mode': 'fulltext', 'sources': [{'path': '.', 'mode': 'fulltext', 'include': ['**/*.md']}]}
    declaration.write_text(yaml.safe_dump(package), encoding='utf-8')
    select_fixture_resource(project, workplace, 'fixture.t02-probe', 'guide')
    work = call_mcp(workplace, 'pf.work.start', {'project_root': str(project), 'objective': 'Probe exact Work resource reads'})
    selectors = {'project_root': str(project), 'run_id': work['run_id'], 'assignment_id': work['assignment_id'], 'context_id': work['context']['id']}
    resolved = call_mcp(workplace, 'pf.work.resolve', {**selectors, 'resource_id': identifier})
    searched = call_mcp(workplace, 'pf.work.search', {**selectors, 'query': 'PinnedMaterialNeedle'})
    cli = run_cli('work-search', '--project-root', str(project), '--workplace', str(workplace), '--run', work['run_id'],
                  '--assignment', work['assignment_id'], '--context-id', work['context']['id'], '--query', 'PinnedMaterialNeedle', '--json')
    report = {'work': work, 'resolve': resolved, 'search': searched, 'cli': json.loads(cli.stdout)}
    Path(__file__).with_name('developer-probe.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    assert resolved['status'] == searched['status'] == 'ready', report
    assert searched['total'] == 1 and searched == report['cli'], report
    print('PASS: real source Work resolve/search and CLI parity')
