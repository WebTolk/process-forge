"""Audit integration probes against real temporary PF project/Workplace and MCP."""
from __future__ import annotations
import json
from pathlib import Path
import sys
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tools')]
import yaml
import processforge as core
from processforge_core.process_execution import ProcessExecutionService
from process_execution_smoke_support import fixture, stage_evidence, call_mcp, cli

RESULTS=[]
def record(name, result):
    RESULTS.append({'probe':name,'result':result})
    Path(__file__).with_name('integration-results.json').write_text(json.dumps(RESULTS,ensure_ascii=False,indent=2),encoding='utf-8')
    print(name,json.dumps(result,ensure_ascii=False),flush=True)

with fixture() as (workplace, project, started):
    service=ProcessExecutionService(project,workplace,core)
    run_id=started['run_id']
    brief=project/'brief.md'; brief.write_text('Reviewed artifact v1')
    held=service.transition(run_id=run_id,outcome='completed',evidence=[{'kind':'artifact','artifact_id':'brief','status':'ready','path':'brief.md'}])
    brief.unlink()
    advanced=service.transition(run_id=run_id,outcome='completed',evidence=[{'kind':'gate','gate_id':'prepare-ready','status':'passed'}])
    record('deleted_evidence_accepted',{'before':held['action'],'file_exists':brief.exists(),'after':advanced['action'],'stage':advanced.get('stage'),'input_state':advanced.get('required_inputs')})

    failed=service.transition(run_id=run_id,outcome='completed',evidence=stage_evidence('change','build-ready')+[
        {'kind':'gate','gate_id':'prepare-ready','status':'failed','summary':'Revalidation failed'},
        {'kind':'input','input_id':'brief','status':'failed','summary':'Input is invalid'}])
    record('new_failure_ignored',{'action':failed['action'],'stage':failed.get('stage'),
        'history':core.load_yaml_document(project/'.pf/assignments'/f"{started['assignment_id']}.yaml")['stage_history'][-1]})

    second=service.start(objective='Audit interrupted final transition')
    assert second['action']=='created_new',second
    rid=second['run_id']; aid=second['assignment_id']
    for artifact,gate in [('brief','prepare-ready'),('change','build-ready')]:
        result=service.transition(run_id=rid,outcome='completed',evidence=stage_evidence(artifact,gate))
        assert result['action']=='stage_transitioned',result
    original=ProcessExecutionService._atomic_yaml
    def fail_run_write(self,path,value):
        if path.name=='run.yaml' and value.get('status')=='completed':raise OSError('audit simulated disk failure after assignment commit')
        return original(self,path,value)
    try:
        with patch.object(ProcessExecutionService,'_atomic_yaml',fail_run_write):
            service.transition(run_id=rid,outcome='completed',evidence=stage_evidence('report','verify-ready'))
    except OSError as exc: failure=str(exc)
    else:raise AssertionError('fault was not injected')
    retried=service.transition(run_id=rid,outcome='completed',evidence=stage_evidence('report','verify-ready'))
    record('interrupted_completion_unrecoverable',{'error':failure,'run_status':core.load_yaml_document(project/'.pf/runs'/rid/'run.yaml')['status'],
        'assignment_status':core.load_yaml_document(project/'.pf/assignments'/f'{aid}.yaml')['status'],'retry':retried})

    for label,needle in [('a','AllowedAuditNeedle'),('b','ForbiddenAuditNeedle')]:
        package=workplace/f'packages/audit-{label}';package.mkdir(parents=True)
        folder=package/'guide';folder.mkdir();(folder/'guide.md').write_text(needle,encoding='utf-8')
        resources=[{'id':'guide','kind':'documentation','path':'guide','indexing':{'mode':'fulltext','sources':[{'path':'.','mode':'fulltext','include':['**/*.md']}]}}]
        (package/'package.yaml').write_text(yaml.safe_dump({'schema_version':1,'id':f'audit-{label}','version':'1.0.0','resources':resources}),encoding='utf-8')
    manifest_path=project/'.pf/process-forge.yaml'
    manifest=yaml.safe_load(manifest_path.read_text(encoding='utf-8'))
    manifest.setdefault('knowledge_stack',[]).append({'id':'audit-a','version':'1.0.0','source':'workplace'})
    manifest_path.write_text(yaml.safe_dump(manifest,allow_unicode=True,sort_keys=False),encoding='utf-8')
    cli('project-context-refresh','--project-root',str(project),'--workplace',str(workplace),'--reason','audit resource fixture registered','--apply')
    snap_path=project/'.pf/contexts/project-context.snapshot.yaml'
    snap=yaml.safe_load(snap_path.read_text(encoding='utf-8'))
    fresh=core.project_context_check_result(project,explicit_workplace=str(workplace))
    selected=[item.get('id') for item in snap.get('local_search_resources',[])]
    record('search_fixture_context',{'check':fresh,'authorized_resource_ids':selected})
    assert fresh.get('status') in {'fresh','fresh_with_updates'},fresh
    assert 'audit-b:guide' not in selected,selected
    index_snapshot=core.workplace_search_runtime_snapshot(workplace)
    from processforge_core.local_resource_search import ResourceSearchIndex
    shared_index=ResourceSearchIndex(workplace,index_snapshot,workplace)
    shared_index.maintenance_tick()
    control=shared_index.search(query='ForbiddenAuditNeedle')
    assert control.get('total')==1,control
    denied=call_mcp(workplace,'pf.resolve',{'project_root':str(project),'resource_id':'audit-b:guide'})
    leaked=call_mcp(workplace,'pf.search',{'project_root':str(project),'query':'ForbiddenAuditNeedle'})
    record('mcp_search_project_authorization_bypass',{'context_status':fresh.get('status'),'authorized_resource_ids':selected,
        'workplace_positive_control_total':control.get('total'),'resolve_b':denied,'unauthorized_search':leaked})
