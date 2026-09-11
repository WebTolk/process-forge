import json
import sys
import tempfile
from pathlib import Path
sys.path[:0]=[str(Path.cwd()/'tools'),str(Path.cwd()/'src')]
import smoke_raw_ingress_incremental_recovery as s
import pf_runtime.raw_ingress_kernel as m
from smoke_core_update_missing_owned import install_old,write_archive
from processforge_core.core_update import build_plan,apply_update,CoreUpdateError
out=Path(__file__).resolve().parent
results={}
with tempfile.TemporaryDirectory(prefix='pf-f12-crlf-') as raw:
    k=m.RawIngressKernel(raw)
    events=[s.event(i,stable=True,session='legacy-crlf') for i in range(2)]
    lines=[m.canonical_json(k._raw_record(e,m.raw_event_id(e),m.raw_payload_hash(e.raw_payload),m.stable_native_identity_key(e),s.FIXED_TIME))+b'\r\n' for e in events]
    shard=k._shard(s.FIXED_TIME);shard.parent.mkdir(parents=True)
    shard.write_bytes(b''.join(lines))
    counts,original=s.with_decode_counter()
    try:
        r0=k.ingest(events[0],s.FIXED_TIME)
        first_counts=dict(counts)
        r1=k.ingest(events[1],s.FIXED_TIME)
        new=k.ingest(s.event(3,stable=False),s.FIXED_TIME)
    finally:m.RawIngressKernel._decode_raw_record=original
    assert r0.deduplicated and r1.deduplicated and not new.deduplicated
    assert r0.raw_location.endswith(':0') and r1.raw_location.endswith(':'+str(len(lines[0])))
    assert counts==first_counts=={'records':2,'bytes':sum(map(len,lines))}
    results['legacy_crlf']={'result':'PASS','records_decoded_once':counts,'second_offset':len(lines[0])}
with tempfile.TemporaryDirectory(prefix='pf-f09-link-') as raw:
    root=Path(raw);core=root/'core';core.mkdir();install_old(core)
    (core/'same.txt').unlink();(core/'target.txt').write_text('user-data')
    try:(core/'same.txt').symlink_to('target.txt')
    except OSError as exc:results['owned_symlink']={'result':'UNAVAILABLE','reason':str(exc)}
    else:
        archive=root/'new.zip';write_archive(archive,{'same.txt':'same','changed.txt':'old','removed.txt':'gone'})
        plan=build_plan(core,archive);assert plan['status']=='blocked'
        for force in (False,True):
            try:apply_update(core,archive,confirm=True,force_local_modifications=force)
            except CoreUpdateError as exc:assert exc.code=='plan_blocked'
            else:raise AssertionError('owned symlink overwritten')
        assert (core/'same.txt').is_symlink() and (core/'target.txt').read_text()=='user-data'
        results['owned_symlink']={'result':'PASS','force_cannot_bypass':True}
(out/'additional-probes.json').write_text(json.dumps(results,indent=2));print(json.dumps(results,indent=2))
