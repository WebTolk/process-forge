import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools'))
from process_execution_smoke_support import fixture
from garage_search_smoke_support import register_fixture_resource, select_fixture_resource, empty_fixture_authorization
from smoke_garage_mode_not_promoted_by_session import call_mcp

with fixture() as (workplace, project, initial):
    a = register_fixture_resource(workplace, 'fixture.binding-a', 'root', {'a.md': 'PinnedAlphaNeedle'}, title='Alpha')
    b = register_fixture_resource(workplace, 'fixture.binding-b', 'root', {'b.md': 'CurrentBetaNeedle'}, title='Beta')
    select_fixture_resource(project, workplace, 'fixture.binding-a', 'root')
    work = call_mcp(workplace, 'pf.work.start', {'project_root': str(project), 'objective': 'Reproduce T02 Work A binding'})
    assert work['action'] == 'created_new', work
    capsule = project / '.pf/contexts/assignment-capsules' / (work['assignment_id'] + '.capsule.yaml')
    before = capsule.read_bytes()
    empty_fixture_authorization(project, workplace)
    select_fixture_resource(project, workplace, 'fixture.binding-b', 'root')
    state = call_mcp(workplace, 'pf.work.state', {'project_root': str(project)})
    resolved_a = call_mcp(workplace, 'pf.resolve', {'project_root': str(project), 'resource_id': a})
    resolved_b = call_mcp(workplace, 'pf.resolve', {'project_root': str(project), 'resource_id': b})
    search_b = call_mcp(workplace, 'pf.search', {'project_root': str(project), 'query': 'CurrentBetaNeedle'})
    report = {'work': work, 'state_after': state, 'resolve_a': resolved_a, 'resolve_b': resolved_b, 'search_b': search_b,
              'capsule_unchanged': capsule.read_bytes() == before, 'capsule_sha256': hashlib.sha256(before).hexdigest()}
    assert a in state['work']['selected_resource_ids'] and b not in state['work']['selected_resource_ids'], state
    assert resolved_a['resource']['status'] == 'denied' and resolved_b['resource']['status'] == 'available'
    assert search_b['total'] == 1 and report['capsule_unchanged']
    Path(__file__).with_name('before.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print('CONFIRMED: Work pins A; project navigation reads B; no Work resource route exists.')
