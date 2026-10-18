import argparse
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools'))
from smoke_conversation_completeness import setup_basic_project, pf
import processforge as core

results = {}
with tempfile.TemporaryDirectory(prefix='pf-t05-developer-') as directory:
    workplace, project = setup_basic_project(Path(directory), 'prepared-project')
    pf('run-create','--project-root',str(project),'--id','prepared-run','--title','Prepared fixture','--process','task-batch-execution','--apply')
    for task_id in ('bad-task', 'manual-task', 'shell-task'):
        extra = ['--workspace-knowledge-resource','not-authorized-resource'] if task_id == 'bad-task' else []
        pf('task-create','--project-root',str(project),'--run','prepared-run','--id',task_id,'--title',task_id,'--process','task-batch-execution','--allowed-file',f'.pf/artifacts/{task_id}.md','--required-output',f'id=report,path=.pf/artifacts/{task_id}.md','--expected-report-artifact',f'.pf/artifacts/{task_id}.md',*extra,'--apply')
    def call(task, operation, driver='manual'):
        return core.run_command_capture(getattr(core, 'command_worker_run_' + operation), argparse.Namespace(project_root=str(project),task=task,driver=driver))
    code, text = call('bad-task', 'prepare')
    assert code and 'resource_not_in_snapshot' in text, (code,text)
    assert not core.worker_run_paths(project,'prepared-run','bad-task')['status'].exists()
    results['missing_grant_denied_before_ready'] = True
    code, text = call('manual-task','prepare')
    assert code == 0, text
    paths = core.worker_run_paths(project,'prepared-run','manual-task')
    state = core.json_read(paths['status'])
    document = core.json_read(project / state['prepared_input']['path'])
    assert not document['input']['resources']['grants']['knowledge_resources']
    (project / '.pf/artifacts/manual-task.md').write_text('# Manual report\n',encoding='utf-8')
    for _ in range(2):
        code, text = call('manual-task','collect')
        assert code == 0, text
    events = [row[1] for row in core.iter_ndjson(core.event_runtime_paths(project)[0])]
    for name in ('worker.run.collected','task.completed','assignment.completed'):
        assert sum(row['event_type']==name for row in events) == 1, name
    results['repeat_collection_one_completion'] = True
    (project / '.pf/artifacts/manual-task.md').write_text('# Changed report\n',encoding='utf-8')
    code, text = call('manual-task','collect')
    assert code and 'collected_output_changed' in text, text
    results['changed_collected_bytes_denied'] = True
    code, text = call('manual-task','prepare')
    assert code == 0, text
    code, text = call('manual-task','collect')
    assert code and 'output_not_attributable_to_attempt' in text, text
    results['retry_leftover_denied'] = True
    driver = core.default_runtime_driver_documents()['generic-shell']
    driver['id'] = 'prepared-fixture'
    driver['security']['require_explicit_executable'] = False
    driver['environment']['inherit'] = False
    driver['command'] = {'executable':'{python_executable}', 'model_args':[], 'args':['-c', "import json,os,pathlib,socket; socket.socket=lambda *a,**k: (_ for _ in ()).throw(RuntimeError('network forbidden')); p=json.loads(pathlib.Path(os.environ['PF_PREPARED_INPUT_FILE']).read_text(encoding='utf-8')); assert p['identity']['assignment_id']=='shell-task'; pathlib.Path(p['project_root'],p['input']['outputs']['expected_report']['artifact']).write_text('# Offline prepared execution\\n',encoding='utf-8')"]}
    driver_path = project/'.pf/runtime/prepared-driver.yaml'
    core.write_yaml_file(driver_path,driver)
    code,text = call('shell-task','start',str(driver_path))
    assert code == 0,text
    code,text = call('shell-task','collect')
    assert code == 0,text
    shell_paths = core.worker_run_paths(project,'prepared-run','shell-task')
    assert core.json_read(shell_paths['exit'])['exit_code']==0
    assert core.json_read(shell_paths['heartbeat'])['status']=='completed'
    results['generic_offline_lifecycle_and_collection'] = True
Path(__file__).with_suffix('.json').write_text(json.dumps(results,indent=2)+'\n',encoding='utf-8')
print(json.dumps(results))
