"""Authorized local acceptance: two private diagnostic events, no normalized routing."""
import json
import sys
from pathlib import Path
core=Path(r'D:\.agents\processforge');wp=Path(r'D:\.agents\processforge-workplace')
sys.path.insert(0,str(core/'tools'))
import pf_runtime.raw_ingress_kernel as m
assert Path(m.__file__).resolve().is_relative_to(core.resolve())
commit=json.loads((core/'processforge-core.manifest.json').read_text())['source']['commit']
k=m.RawIngressKernel(wp)
counts={'records':0,'bytes':0};original=m.RawIngressKernel._decode_raw_record
def counted(self,line,shard):
    counts['records']+=1;counts['bytes']+=len(line)
    return original(self,line,shard)
m.RawIngressKernel._decode_raw_record=counted
event=m.NativeAgentEvent('processforge','local-acceptance','core-verification',{'commit':commit,'check':'installed-ingress'},native_event_id='core-verification-'+commit)
try:
    first=k.ingest(event);migration=dict(counts)
    second=k.ingest(event);after_duplicate=dict(counts)
    another=k.ingest(m.NativeAgentEvent('processforge','local-acceptance','core-verification',{'commit':commit,'check':'new-event-after-migration'},native_event_id='core-verification-new-'+commit))
finally:m.RawIngressKernel._decode_raw_record=original
assert first.accepted and second.accepted and second.deduplicated
assert first.raw_location==second.raw_location and another.accepted
assert counts==migration==after_duplicate,'steady-state request decoded historical records'
data={'result':'PASS','module':str(m.__file__),'commit':commit,'legacy_migration_decodes':migration,'subsequent_historical_decodes':0,'first_deduplicated':first.deduplicated,'duplicate_confirmed':second.deduplicated,'new_event_accepted':another.accepted,'raw_locations':[first.raw_location,another.raw_location],'routing':'private raw acceptance only; no normalized event dispatch'}
Path(__file__).with_name('installed-live-ingress.json').write_text(json.dumps(data,indent=2));print(json.dumps(data,indent=2))
