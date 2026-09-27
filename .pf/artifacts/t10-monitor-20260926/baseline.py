import hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
target=HERE/'baseline.json'
assert not target.exists()
paths={ROOT/p for p in subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','-z'],cwd=ROOT).decode().split('\0') if p and not p.startswith('.pf/') and (ROOT/p).is_file()}
for parent in ['.pf/artifacts','.pf/contexts/assignment-capsules','.pf/contexts/project-context.snapshots']:
 paths.update(p for p in (ROOT/parent).rglob('*') if p.is_file() and HERE not in p.parents and 'projections' not in p.parts and p.parent!=ROOT/'.pf/artifacts')
paths.update([ROOT/'.pf/contexts/project-context.snapshot.yaml',ROOT/'.pf/process-forge.yaml'])
data={str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}
target.write_text(json.dumps({'files':data},indent=2)+'\n',encoding='utf-8')
for name in ['tools/pf_runtime/service.py','tools/processforge.py','docs/concepts/runtime-mcp.md','docs/ru/concepts/runtime-mcp.md','checksums/processforge.sha256']:
 out=HERE/'originals'/name;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes((ROOT/name).read_bytes())
print(len(data),'protected baseline files; originals retained')
