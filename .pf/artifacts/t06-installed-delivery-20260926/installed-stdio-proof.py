from datetime import datetime, timezone
import hashlib, json, subprocess, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
CORE=Path('D:/.agents/processforge');WP=Path('D:/.agents/processforge-workplace')
RUN='garage-t06-pf-vision-alignment-r02-integrate-acceptance-for-work-resourc'
TASK='t06-pf-vision-alignment-r02-integrate-acceptance-for-work-resources-norm'
DELIVERY='garage-t06-delivery-prerequisite-qualify-a-clean-isolated-candidate-cont'
protected=[ROOT/'.pf/assignments'/(TASK+'.yaml'),ROOT/'.pf/runs'/RUN/'run.yaml',ROOT/'.pf/contexts/assignment-capsules'/(TASK+'.capsule.yaml'),ROOT/'.pf/contexts/project-context.snapshot.yaml']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
before={str(p):sha(p) for p in protected}
result={'time_utc':datetime.now(timezone.utc).isoformat(),'layer':'separate installed stdio processes, NOT application host reconnect','before':before,'connections':[]}
argv=[sys.executable,'-B',str(CORE/'bin/pf.py'),'work-state','--project-root',str(ROOT),'--workplace',str(WP),'--run',RUN,'--assignment',TASK,'--json']
p=subprocess.run(argv,cwd=ROOT,capture_output=True,text=True,encoding='utf-8',timeout=180)
assert p.returncode==0,p.stderr
state=json.loads(p.stdout);assert state['run']['id']==RUN and state['assignment']['id']==TASK and state['stage']['id']=='code-assurance'
result['original_t06_cli']={'argv':argv,'state':state,'stderr':p.stderr}
requests=[{'jsonrpc':'2.0','id':1,'method':'initialize'}, {'jsonrpc':'2.0','method':'notifications/initialized'},
 {'jsonrpc':'2.0','id':2,'method':'tools/list'}]
calls=[('pf.context',{'project_root':str(ROOT)}),('pf.work.state',{'project_root':str(ROOT)}),
 ('pf.resolve',{'project_root':str(ROOT),'resource_id':'project.process-forge:project-artifacts'}),
 ('pf.resolve',{'project_root':str(ROOT),'resource_id':'docs.api.gitverse:root'}),
 ('pf.session_context',{'project_root':str(ROOT)}),
 ('pf.work.resolve',{'project_root':str(ROOT),'run_id':RUN,'assignment_id':TASK,'context_id':TASK+'-capsule','resource_id':'project.process-forge:project-artifacts'})]
for i,(name,args) in enumerate(calls,3):requests.append({'jsonrpc':'2.0','id':i,'method':'tools/call','params':{'name':name,'arguments':args}})
for attempt in range(2):
    argv=[sys.executable,'-B',str(CORE/'tools/pf_runtime/mcp_server.py'),'--workplace',str(WP)]
    p=subprocess.run(argv,cwd=ROOT,input='\n'.join(json.dumps(x) for x in requests)+'\n',capture_output=True,text=True,encoding='utf-8',timeout=180)
    rows=[json.loads(line) for line in p.stdout.splitlines() if line.strip()]
    result['connections'].append({'attempt':attempt+1,'argv':argv,'eof_exit':p.returncode,'stderr':p.stderr,'responses':rows})
    (HERE/'installed-stdio-proof.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    assert p.returncode==0 and not p.stderr and [x['id'] for x in rows]==list(range(1,9))
    names={x['name'] for x in rows[1]['result']['tools']};assert {'pf.work.search','pf.work.resolve'}<=names
    payloads={x['id']:json.loads(x['result']['content'][0]['text']) for x in rows[2:]}
    assert payloads[3]['context']['status']=='fresh'
    assert payloads[4]['run']['id']==DELIVERY and payloads[4]['stage']['id']=='release-delivery'
    assert not rows[4]['result'].get('isError'),payloads[5]
    assert payloads[6]['resource']['status']=='denied' and payloads[6]['resource']['reason']=='not_in_project_snapshot',payloads[6]
    assert rows[6]['result'].get('isError') and payloads[7]['error']['code']=='missing_session',payloads[7]
    print('PASS: installed stdio',attempt+1,'tools, fresh context, Work identity, positive/negative project resolve, absent-session boundary',flush=True)
result['after']={str(p):sha(p) for p in protected};assert result['after']==before
result['stdout_jsonrpc_only']=True;result['notifications_silent']=True
(HERE/'installed-stdio-proof.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
