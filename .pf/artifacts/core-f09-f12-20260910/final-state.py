import hashlib
import json
import subprocess
from pathlib import Path
out=Path(__file__).resolve().parent
core=Path(r'D:\.agents\processforge');wp=Path(r'D:\.agents\processforge-workplace')
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
m=json.loads((core/'processforge-core.manifest.json').read_text())
bad=[e['relative_path'] for e in m['files'] if not (core/e['relative_path']).is_file() or digest(core/e['relative_path'])!=e['sha256']]
before=json.loads((out/'workplace-before.json').read_text())
changed=[p for p,h in before.items() if not (wp/p).is_file() or digest(wp/p)!=h]
user=json.loads((out/'core-user-files-before.json').read_text())
user_changed=[p for p,h in user.items() if not (core/p).is_file() or digest(core/p)!=h]
local=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
remote=subprocess.check_output(['git','ls-remote','origin','refs/heads/dev'],text=True).split()[0]
runtime=json.loads((out/'runtime-final.json').read_text(encoding='utf-8-sig'))
initial=json.loads((out/'runtime-before-restart.json').read_text(encoding='utf-8-sig'))
archives=list(out.glob('processforge-*.zip'));assert len(archives)==1
data={'commit':local,'remote_dev':remote,'installed_commit':m['source']['commit'],'owned_files':len(m['files']),'owned_mismatches':bad,'workplace_semantic_files':len(before),'workplace_changed':changed,'core_user_files':len(user),'core_user_files_changed':user_changed,'archive':archives[0].name,'archive_sha256':digest(archives[0]),'runtime':{k:runtime.get(k) for k in ('pid','started_at','status','health','active_workers','pending_runtime_jobs','last_scheduler_error')},'previous_runtime_pid':initial.get('pid')}
ok=local==remote==data['installed_commit'] and not bad and not changed and not user_changed and runtime.get('health')=='ready' and runtime.get('pid')!=initial.get('pid') and runtime.get('last_scheduler_error') is None
data['result']='PASS' if ok else 'FAIL'
(out/'final-state.json').write_text(json.dumps(data,indent=2))
print(json.dumps(data,indent=2));assert ok
