import hashlib,json
from pathlib import Path
root=Path(r'D:\.agents\processforge');out=Path('.pf/artifacts/publish-f06-f08-20260910')
m=json.loads((root/'processforge-core.manifest.json').read_text())
bad=[]
for e in m['files']:
 p=root/e['relative_path']
 if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=e['sha256']:bad.append(e['relative_path'])
data={'result':'PASS' if not bad else 'FAIL','files_checked':len(m['files']),'mismatches':bad,'source':m.get('source'),'version':m.get('version')}
(out/'installed-owned-verification.json').write_text(json.dumps(data,indent=2));print(json.dumps(data));raise SystemExit(bool(bad))
