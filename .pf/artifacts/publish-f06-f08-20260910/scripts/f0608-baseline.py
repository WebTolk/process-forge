import importlib.util,json,os,sys,tempfile,time
from pathlib import Path
root=Path('.pf/tmp/pf-update-5c95391').resolve()
sys.path.insert(0,str(root/'tools'))
spec=importlib.util.spec_from_file_location('baseline',root/'tools/processforge.py');pf=importlib.util.module_from_spec(spec);sys.modules['baseline']=pf;spec.loader.exec_module(pf)
results={}
with tempfile.TemporaryDirectory(prefix='pf-f0608-baseline-') as temp:
 p=Path(temp); target=p/'registry.yaml'
 with pf.registry_file_lock(target):
  lock=target.with_name('.registry.yaml.lock');os.utime(lock,(time.time()-301,time.time()-301))
  with pf.registry_file_lock(target,timeout_seconds=.1):results['F06']='REPRODUCED: second acquisition while original owner is live'
 presence=p/'runtime/agent-presence/agent/session.json';presence.parent.mkdir(parents=True);presence.write_text('{"status":"offline"}')
 try:pf.active_organized_project_sessions(p)
 except NameError as e:results['F07']=str(e)
 try:pf.normalized_orchestrator_plan(p,{'run':{'id':'probe'},'workers':[{'id':'worker'}]})
 except NameError as e:results['F08']=str(e)
Path('.pf/artifacts/publish-f06-f08-20260910/baseline-reproduction.json').write_text(json.dumps(results,indent=2))
print(json.dumps(results));assert len(results)==3
