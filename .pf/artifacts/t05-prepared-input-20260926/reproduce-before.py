import json
from pathlib import Path
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools'))
from smoke_conversation_completeness import setup_basic_project,pf
import processforge as core

with tempfile.TemporaryDirectory(prefix='pf-t05-before-') as directory:
    workplace,project=setup_basic_project(Path(directory),'before-project')
    pf('run-create','--project-root',str(project),'--id','prepared-run','--title','Prepared fixture','--process','task-batch-execution','--apply')
    pf('task-create','--project-root',str(project),'--run','prepared-run','--id','prepared-task','--title','Prepared fixture task','--process','task-batch-execution','--allowed-file','.pf/artifacts/report.md','--required-output','id=report,path=.pf/artifacts/report.md','--expected-report-artifact','.pf/artifacts/report.md','--workspace-knowledge-resource','not-authorized-resource','--apply')
    output=pf('worker-run','prepare','--project-root',str(project),'--task','prepared-task','--driver','manual')
    paths=core.worker_run_paths(project,'prepared-run','prepared-task')
    workspace=json.loads(paths['workspace_access'].read_text(encoding='utf-8'))
    prompt=core.render_worker_launch_prompt(project,'prepared-task')
    result={'missing_resource_prepare_succeeded':True,'requested':workspace['requested']['knowledge_resources'],'granted':workspace['grants']['knowledge_resources'],'prompt_requires_new_work': '`pf.work.start`' in prompt,'prompt_requires_mcp': 'MCP tools are unavailable' in prompt,'prepared_input_manifest_present':(paths['root']/'prepared-input.json').exists()}
    assert result['requested'] and not result['granted'] and result['prompt_requires_new_work'] and not result['prepared_input_manifest_present']
    (project/'.pf/artifacts/report.md').write_text('# Fixture report\n',encoding='utf-8')
    for _ in range(2):
        pf('worker-run','collect','--project-root',str(project),'--task','prepared-task')
    event_path=project/'.pf/runtime/events/events.ndjson'
    rows=[json.loads(line) for line in event_path.read_text(encoding='utf-8').splitlines() if line]
    result['repeated_collection_events']=sum(row.get('event_type')=='worker.run.collected' for row in rows)
    result['repeated_task_completed_events']=sum(row.get('event_type')=='task.completed' for row in rows)
    assert result['repeated_collection_events']==2 and result['repeated_task_completed_events']==2
    Path(__file__).with_suffix('.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result))
