"""Assert the saved actual-host results; never substitute local calls for host evidence."""
import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path

OUT = Path(__file__).resolve().parent
REPO = OUT.parents[3]
FIXTURE = REPO / '.pf/tmp/t06-host-acceptance-20260926/project'
CORE = Path('D:/.agents/processforge')


def read(name):
    return json.loads((OUT / name).read_text(encoding='utf-8-sig'))


def payload(response):
    assert not response.get('isError'), response
    return json.loads(response['content'][0]['text'])


checks = []


def check(name, condition):
    assert condition, name
    checks.append(name)


start = payload(read('fixture-start.json')['response'])
check('complete immutable contract created by connected MCP', start['action'] == 'created_new' and start['context']['validation']['status'] == 'valid')
original_digest = start['context']['checksum'].removeprefix('sha256:')
capsule = FIXTURE / '.pf/contexts/assignment-capsules' / (start['assignment_id'] + '.capsule.yaml')
check('fixture capsule unchanged after all host operations', hashlib.sha256(capsule.read_bytes()).hexdigest() == original_digest)
search = payload(read('fixture-positive-search.json'))
check('positive fulltext coverage', search['status'] == 'ready' and search['total'] == 1 and search['coverage']['status'] == 'complete')
reads = {row['name']: json.loads(row['response']['content'][0]['text']) for row in read('resource-read-cases.json')}
check('resolve verifies declared material', reads['positive-resolve']['resource']['navigation'] == 'verified_declared_material')
check('unselected resource blocked', reads['unselected-resolve']['reason'] == 'resource_not_in_work')
check('wrong immutable context blocked', reads['wrong-context']['reason'] == 'work_context_mismatch')
check('real Ledger session required', reads['missing-session']['error']['code'] == 'missing_session')
profiles = read('profile-cases.json')
for name in ('search', 'deny'):
    results = [payload(row['response']) for row in profiles if row['name'] == name]
    check('five profiles preserve ' + name, len(results) == 5 and all(item == results[0] for item in results))
incomplete = [payload(row['response']) for row in profiles if row['name'] == 'incomplete-transition']
check('five profiles enforce required gates', len(incomplete) == 5 and all(item['action'] == 'incomplete' and item['reason'] == 'stage_requirements_incomplete' for item in incomplete))
mutations = {row['name']: payload(row['response']) for row in read('mutation-cases.json') if 'name' in row}
for name, reason in (('material-drift', 'resource_material_changed'), ('revoked-access', 'resource_access_revoked')):
    check(name, mutations[name]['status'] == 'blocked' and mutations[name]['reason'] == reason)
for name in ('restored-material', 'restored-grant'):
    check(name, mutations[name]['status'] == 'ready')
lifecycle = {row['name']: payload(row['response']) for row in read('fixture-lifecycle.json')}
check('empty stage subset enforced after governed transition', lifecycle['empty-subset-resolve']['reason'] == 'resource_not_in_stage')
check('empty stage subset gives no search documents', lifecycle['empty-subset-search']['status'] == 'ready' and lifecycle['empty-subset-search']['total'] == 0)
check('later omitted subset inherits pinned grants', lifecycle['verify-resolve']['status'] == 'ready')
check('fixture completes through actual host with diagnostics off', lifecycle['complete']['action'] == 'run_completed')
diagnostic_path = FIXTURE / '.pf/runtime/diagnostics/diagnostics.jsonl'
lines = diagnostic_path.read_text(encoding='utf-8').splitlines()
records = [json.loads(line) for line in lines]
check('bounded canonical diagnostics', len(lines) > 0 and diagnostic_path.stat().st_size <= 1048576 and all(len(line.encode()) <= 16384 and record['schema_version'] == 1 for line, record in zip(lines, records)))
entry_hash = hashlib.sha256((CORE / 'tools/pf_runtime/mcp_server.py').read_bytes()).hexdigest()
diagnostics_hash = hashlib.sha256((CORE / 'src/processforge_core/diagnostics.py').read_bytes()).hexdigest()
builds = [r['identity']['build'] for r in records if r.get('identity', {}).get('build')]
check('actual host diagnostic build matches installed entry and implementation', builds and all(b['entry_sha256'] == entry_hash and b['diagnostics_sha256'] == diagnostics_hash for b in builds))
check('diagnostics omit fixture contents and query', all('T06HostAcceptanceNeedle' not in line and 'authorized original content' not in line for line in lines))
for profile in ('quiet', 'off'):
    calls = [r for r in profiles if r['profile'] == profile]
    intervals = [(datetime.fromisoformat(r['time_utc'].replace('Z', '+00:00')) - timedelta(milliseconds=r['duration_ms']), datetime.fromisoformat(r['time_utc'].replace('Z', '+00:00'))) for r in calls]
    hits = [r for r in records if any(a <= datetime.fromisoformat(r['timestamp'].replace('Z', '+00:00')) <= b for a, b in intervals)]
    if profile == 'quiet':
        check('quiet preserves warning diagnostics while filtering lower levels', len(hits) == 1 and hits[0]['severity'] == 'warning' and hits[0]['code'] == 'work.resource_blocked')
    else:
        check('off emits no optional diagnostics', not hits)
events_path = FIXTURE / '.pf/runtime/events/events.ndjson'
events = [json.loads(line) for line in events_path.read_text(encoding='utf-8').splitlines() if line.strip()]
types = [event['event_type'] for event in events]
completed_stages = [e['data']['stage_id'] for e in events if e['event_type'] == 'process.stage.completed']
transition_targets = [e['data']['next_stage_id'] for e in events if e['event_type'] == 'process.stage.transitioned']
check('mandatory stage completions survive diagnostics off', completed_stages == ['prepare', 'build', 'verify'] and transition_targets == ['build', 'verify', ''])
check('mandatory run completion survives diagnostics off', types.count('run.completed') == 1)
boundary = read('boundary-result.json')
check('installed product frozen evidence and shared configuration preserved', not boundary['installed_mismatches'] and all(not rows for rows in boundary['changed'].values()))
(OUT / 'fixture-diagnostics.jsonl').write_bytes(diagnostic_path.read_bytes())
(OUT / 'fixture-events.ndjson').write_bytes(events_path.read_bytes())
result = {'status': 'PASS', 'checks': checks, 'count': len(checks), 'diagnostic_records': len(records), 'diagnostic_bytes': diagnostic_path.stat().st_size,
          'event_count': len(events), 'fixture_capsule_sha256': original_digest,
          'limitations': ['Raw application stdio/notification framing is not exposed by the tool API; existing delivered installed stdio proof is a separate complementary layer.', 'No real Ledger-bound session exists; session-bound cross-project negatives are covered by installed isolated tests, not claimed as live-host session acceptance.']}
(OUT / 'acceptance-result.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
print(json.dumps(result))
