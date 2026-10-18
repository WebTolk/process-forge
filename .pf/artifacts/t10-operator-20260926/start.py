"""Standard Work CLI fallback after repeated MCP post-mutation timeouts."""
import json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
assert not (HERE/'start.json').exists(), 'Reconcile actual Work before retrying'
cmd=[sys.executable,'-B','D:/.agents/processforge/bin/pf.py','work-start','--project-root',str(ROOT),'--workplace','D:/.agents/processforge-workplace','--process-id','software-feature-development','--objective','T10 local operator completion: publish bounded authoritative activity snapshots, add compatible server controls and diagnostic profile configuration, then install the qualified changes with the journal fix through the standard Core updater.','--json']
p=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True,encoding='utf-8',timeout=240)
(HERE/'start.json').write_text(json.dumps({'argv':cmd,'exit_code':p.returncode,'stdout':p.stdout,'stderr':p.stderr},indent=2)+'\n',encoding='utf-8')
assert p.returncode==0,(p.stdout,p.stderr)
data=json.loads(p.stdout)
print(json.dumps(data,ensure_ascii=True),flush=True)
