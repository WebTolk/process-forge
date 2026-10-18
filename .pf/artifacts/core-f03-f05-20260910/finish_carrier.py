from pathlib import Path
import json, subprocess, sys, time
BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[2]
RUN='garage-remediate-python-core-audit-f03-f04-f05-evidence-freshness-and-re'
for phase in ['execution','result','review','summary']:
    cmd=[sys.executable,'bin/pf.py','work-transition','--project-root','.', '--run',RUN,'--outcome','completed','--evidence-file',str(BASE/(phase+'-evidence.json')),'--notes',f'F03-F05 {phase} obligations satisfied with durable scoped evidence; F06-F12 and full release qualification remain separate.','--json']
    start=time.monotonic()
    result=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True,encoding='utf-8',timeout=180)
    (BASE/(phase+'-transition.stdout.txt')).write_text(result.stdout,encoding='utf-8')
    (BASE/(phase+'-transition.stderr.txt')).write_text(result.stderr,encoding='utf-8')
    metadata={'command':cmd,'exit_code':result.returncode,'seconds':round(time.monotonic()-start,3)}
    (BASE/(phase+'-transition-meta.json')).write_text(json.dumps(metadata,indent=2),encoding='utf-8')
    assert result.returncode==0,(phase,result.stdout,result.stderr)
    payload=json.loads(result.stdout)
    (BASE/(phase+'-transition.json')).write_text(json.dumps(payload,indent=2),encoding='utf-8')
    expected='run_completed' if phase=='summary' else 'stage_transitioned'
    assert payload.get('action')==expected,(phase,payload)
    print(phase,payload['action'],flush=True)
