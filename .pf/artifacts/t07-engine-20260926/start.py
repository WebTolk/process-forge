"""Standard Work start; reconcile state before retry after any timeout."""
import json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
assert not (HERE/'start.json').exists()
cmd=[sys.executable,'-B','D:/.agents/processforge/bin/pf.py','work-start','--project-root',str(ROOT),'--workplace','D:/.agents/processforge-workplace','--process-id','software-feature-development','--objective','Implement the T07 provider-neutral egress engine: qualify a bounded enforcement route, bind successor security intent, filter immutable views through policy and mandatory audit, mediate resource and tool access, preserve export provenance, test adversarial behavior and install the qualified Core through the standard updater.','--json']
p=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True,encoding='utf-8',timeout=300)
(HERE/'start.json').write_text(json.dumps(dict(argv=cmd,exit_code=p.returncode,stdout=p.stdout,stderr=p.stderr),indent=2)+'\n',encoding='utf-8')
assert p.returncode==0,(p.stdout[-5000:],p.stderr[-3000:])
s=json.loads(p.stdout)
print(json.dumps({k:s.get(k) for k in ('action','assignment_id','run_id','context','stage')},ensure_ascii=True),flush=True)
