import hashlib
import json
from pathlib import Path

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[2]
baseline=json.loads((OUT/'baseline.json').read_text(encoding='utf-8'))
allowed={'src/processforge_core/garage.py','src/processforge_core/core_update.py','tools/smoke_garage_cross_project_security.py','tools/smoke_garage_no_hooks_sessionless.py','tools/smoke_core_update_manifest.py','checksums/processforge.sha256'}
changed=[]
unexpected=[]
for name,digest in baseline['sha256'].items():
    if name.startswith('.pf/'):
        continue
    path=ROOT/name
    actual=hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
    if digest!=actual:
        changed.append(name)
        if name not in allowed:
            unexpected.append(name)
result={'status':'PASS' if not unexpected else 'FAIL','changed_public_tracked':changed,'unexpected':unexpected,'basis':'Byte hashes of every tracked public file before worker launch; existing dirty baseline preserved outside this bounded scope.'}
(OUT/'source-preservation.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result))
raise SystemExit(bool(unexpected))
