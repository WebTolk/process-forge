import hashlib
import json
from pathlib import Path
out=Path(__file__).resolve().parent
core=Path(r'D:\.agents\processforge')
wp=Path(r'D:\.agents\processforge-workplace')
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
old=json.loads((core/'processforge-core.manifest.json').read_text())
owned={e['relative_path']:e['sha256'] for e in old['files']}
bad=[p for p,h in owned.items() if not (core/p).is_file() or digest(core/p)!=h]
assert not bad,bad
# Workplace semantic configuration/resources only; Runtime and backup state intentionally evolves.
before={p.relative_to(wp).as_posix():digest(p) for p in wp.rglob('*') if p.is_file() and not any(x in {'runtime','.git','__pycache__','updates'} for x in p.relative_to(wp).parts)}
extras={p.relative_to(core).as_posix():digest(p) for directory in ('docs','examples','processes','prompts') for p in (core/directory).rglob('*') if p.is_file() and p.relative_to(core).as_posix() not in owned}
(out/'workplace-before.json').write_text(json.dumps(before,indent=2))
(out/'core-user-files-before.json').write_text(json.dumps(extras,indent=2))
(out/'installed-manifest-before.json').write_text(json.dumps(old,indent=2))
print(json.dumps({'installed_commit':old['source']['commit'],'owned_files_verified':len(owned),'workplace_semantic_files':len(before),'core_unowned_semantic_files':len(extras)}))
