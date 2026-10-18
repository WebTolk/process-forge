import json
from pathlib import Path
root=Path(r'D:\.agents\processforge-workplace\runtime\agent-events\raw\v1')
records=0;bad=[];size=0;changed=[]
for p in root.rglob('*.ndjson'):
    before=p.stat().st_size
    with p.open('rb') as f:
        for number,line in enumerate(f,1):
            records+=1;size+=len(line)
            try:
                r=json.loads(line)
                valid=isinstance(r,dict) and r.get('schema_version')==1 and all(isinstance(r.get(k),str) and r[k] for k in ('raw_event_id','raw_payload_hash')) and line.endswith(b'\n')
            except (ValueError,UnicodeError):valid=False
            if not valid:bad.append({'shard':p.relative_to(root).as_posix(),'line':number})
    if p.stat().st_size!=before:changed.append(p.relative_to(root).as_posix())
result={'records':records,'bytes':size,'invalid_records':bad,'shards_changed_during_read':changed,'result':'PASS' if not bad else 'FAIL'}
Path(__file__).with_name('installed-raw-preflight.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result));assert not bad
