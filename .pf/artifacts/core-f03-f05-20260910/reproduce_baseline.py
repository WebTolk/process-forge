from pathlib import Path
import json,sys
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tools')]
import processforge as core
from processforge_core.process_execution import ProcessExecutionService
from process_execution_smoke_support import fixture,stage_evidence
results={}
with fixture() as (wp,project,started):
    service=ProcessExecutionService(project,wp,core)
    rid=started['run_id']
    service.transition(run_id=rid,outcome='completed',evidence=stage_evidence('brief','prepare-ready'))
    value=service.transition(run_id=rid,outcome='completed',evidence=stage_evidence('change','build-ready')+[{'kind':'input','input_id':'brief','status':'failed'},{'kind':'gate','gate_id':'prepare-ready','status':'failed'}])
    results['F03']={'action':value['action'],'stage':value['stage']['id']}
    started=service.start(objective='Baseline saved file deletion');rid=started['run_id']
    proof=project/'proof.md';proof.write_text('proof',encoding='utf-8')
    service.transition(run_id=rid,outcome='completed',evidence=[{'kind':'artifact','artifact_id':'brief','path':'proof.md','status':'ready'}])
    proof.unlink()
    value=service.transition(run_id=rid,outcome='completed',evidence=[{'kind':'gate','gate_id':'prepare-ready','status':'passed'}])
    results['F04']={'action':value['action'],'stage':value['stage']['id'],'exists':proof.exists()}
    started=service.start(objective='Baseline interrupted completion');rid=started['run_id']
    for a,g in [('brief','prepare-ready'),('change','build-ready')]:service.transition(run_id=rid,outcome='completed',evidence=stage_evidence(a,g))
    original=ProcessExecutionService._atomic_yaml
    def fail(self,path,value):
        if path.name=='run.yaml' and value.get('status')=='completed':raise OSError('one-shot run completion write failure')
        return original(self,path,value)
    try:
        with patch.object(ProcessExecutionService,'_atomic_yaml',fail):service.transition(run_id=rid,outcome='completed',evidence=stage_evidence('report','verify-ready'))
    except OSError:pass
    else:raise AssertionError('fault not triggered')
    value=ProcessExecutionService(project,wp,core).transition(run_id=rid,outcome='completed')
    results['F05']={'action':value['action'],'reason':value.get('reason'),'assignment':core.load_yaml_document(project/'.pf/assignments'/f"{started['assignment_id']}.yaml")['status'],'run':core.load_yaml_document(project/'.pf/runs'/rid/'run.yaml')['status']}
Path(__file__).with_name('baseline-reproduction.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
print(json.dumps(results,indent=2))
