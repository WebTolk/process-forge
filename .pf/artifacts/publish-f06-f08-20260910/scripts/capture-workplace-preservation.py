import hashlib,json
from pathlib import Path
r=Path(r'D:\.agents\processforge-workplace')
paths=[p for p in r.rglob('*') if p.is_file() and p.relative_to(r).parts[0] not in {'runtime','cache','logs','.git'}]
data={str(p.relative_to(r)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
Path('.pf/artifacts/publish-f06-f08-20260910/workplace-before.json').write_text(json.dumps(data,indent=2))
print('Recorded',len(data),'semantic Workplace files')
