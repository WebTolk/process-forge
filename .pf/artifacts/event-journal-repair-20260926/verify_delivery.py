"""Audit the completed byte-range repair and run actual full-checkout validation."""
from work import *
from repair import read_snapshot,scan,digest

result=json.loads((HERE/'repair-result.json').read_text(encoding='utf-8'))
assert result['status']=='applied' and not result['after']['bad']
assert not (HERE/'delivery-verification.json').exists()
sys.path.insert(0,str(ROOT/'tools'))
import processforge as core
journal=ROOT/'.pf/runtime/events/events.ndjson'
backup=ROOT/'.pf/tmp/event-journal-repair-20260926/original-journal'
original=(backup/'events-before.bin').read_bytes()
assert digest(original)==result['sha256']
offset,end=result['changed_range']
expected=original[:offset]+b' '*(end-offset)+original[end:]
before_audit=read_snapshot(journal)
assert before_audit.startswith(expected) and not scan(before_audit)['bad']
event=core.processforge_event(ROOT,'journal.record.quarantined',severity='warn',
    event_id='evt_'+result['sha256'][:32],correlation_id='journal-repair-20260926',
    data={'repair_artifact':'.pf/artifacts/event-journal-repair-20260926/repair-result.json',
          'original_sha256':result['sha256'],'fragment_sha256':result['bad'][0]['body_sha256'],
          'line':result['bad'][0]['line'],'changed_bytes':end-offset,'original_valid_bytes_preserved':True})
core.append_process_event(ROOT,event,dispatch=False)
save('repair-audit-event.json',event)
after=read_snapshot(journal);assert after.startswith(expected)
parsed=scan(after);assert not parsed['bad'] and parsed['valid_records']>=result['valid_records']+1
command('full-checkout-schemas',[sys.executable,'-B',ROOT/'tools/validate-process-forge-schemas.py'],timeout=300)
qa=json.loads((HERE/'assurance-results.json').read_text())
assert all(sha(ROOT/n)==h for n,h in qa['source_sha256'].items())
baseline=json.loads((HERE/'baseline.json').read_text())
assert all(sha(ROOT/n)==h for n,h in baseline.items() if n not in qa['changed_files'])
previous=json.loads((ROOT/'.pf/artifacts/t10-installed-delivery-20260926/build.json').read_text())
assert all(sha(Path(n))==h for n,h in previous['protected_sha256'].items())
assert all(sha(Path(n))==h for n,h in previous['frozen_sha256'].items())
assert sha(CAP)==CAP_SHA
installed=json.loads((CORE/'processforge-core.manifest.json').read_text())
entry=next(x for x in installed['files'] if x['relative_path']=='tools/processforge.py')
assert sha(CORE/'tools/processforge.py')==entry['sha256']
assert sha(CORE/'tools/processforge.py')!=sha(ROOT/'tools/processforge.py')
out={'status':'PASS','repair':result['status'],'backup_sha256':digest(original),'changed_bytes':end-offset,
     'all_original_valid_bytes_preserved':True,'valid_records_after_audit':parsed['valid_records'],
     'invalid_records_after':0,'audit_event_id':event['event_id'],'full_checkout_schemas':'PASS',
     'unchanged_public_files':qa['unchanged_public_files'],'protected_configuration_files':len(previous['protected_sha256']),
     'prior_frozen_files':len(previous['frozen_sha256']),'capsule_unchanged':True,
     'source_fix_installed':False,'installation_boundary':'next standard combined Core update after remaining T10 work'}
save('delivery-verification.json',out);print(json.dumps(out),flush=True)
