import hashlib,json,subprocess
from pathlib import Path
out=Path('.pf/artifacts/publish-f06-f08-20260910');core=Path(r'D:\.agents\processforge');wp=Path(r'D:\.agents\processforge-workplace')
m=json.loads((core/'processforge-core.manifest.json').read_text())
bad=[e['relative_path'] for e in m['files'] if not (core/e['relative_path']).is_file() or hashlib.sha256((core/e['relative_path']).read_bytes()).hexdigest()!=e['sha256']]
before=json.loads((out/'workplace-before.json').read_text())
changed=[p for p,h in before.items() if not (wp/p).is_file() or hashlib.sha256((wp/p).read_bytes()).hexdigest()!=h]
local=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
remote=subprocess.check_output(['git','ls-remote','origin','refs/heads/dev'],text=True).split()[0]
runtime=json.loads((out/'runtime-status-final.json').read_text())
initial=json.loads((out/'runtime-before-restart.json').read_text())
data={'commit':local,'remote_dev':remote,'installed_commit':m['source']['commit'],'owned_files':len(m['files']),'owned_mismatches':bad,'workplace_original_files':len(before),'workplace_changed':changed,'archive_sha256':hashlib.sha256((out/'processforge-52774e4.zip').read_bytes()).hexdigest(),'runtime':{k:runtime.get(k) for k in ('pid','started_at','status','health','active_workers','pending_runtime_jobs','last_scheduler_error')},'previous_runtime_pid':initial['pid']}
ok=local==remote==data['installed_commit'] and not bad and not changed and runtime['health']=='ready' and runtime['pid']!=initial['pid']
data['result']='PASS' if ok else 'FAIL'
(out/'final-state.json').write_text(json.dumps(data,indent=2));print(json.dumps(data));assert ok
