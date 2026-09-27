import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools'))
import processforge as core
from process_execution_smoke_support import fixture
from processforge_core.process_execution import ProcessExecutionService
from smoke_conversation_completeness import setup_basic_project, pf

result = {}
with fixture() as (workplace,project,started):
    code, output = core.run_command_capture(core.command_worker_run_prepare,argparse.Namespace(project_root=str(project),task=started['assignment_id'],driver='manual'))
    assert code and 'worker_report_undeclared' in output,output
    result['undeclared_report_denied'] = True
    class ScopedFixtureService(ProcessExecutionService):
        def _write_capsule(self, run, assignment, pin):
            # Fixture declarations precede immutable context creation. No
            # generated capsule, digest or persisted assignment is rewritten.
            report = '.pf/artifacts/governed-worker.md'
            assignment.update(allowed_files=[report], expected_report={'artifact':report},
                              required_outputs=[{'id':'worker-report','path':report,'required':True}])
            return super()._write_capsule(run,assignment,pin)
    service = ScopedFixtureService(project,workplace,core)
    work = service.start(objective='Scoped governed prepared fixture',process_id='declarative-smoke')
    assert work['action']=='created_new',work
    task = work['assignment_id']
    code,output = core.run_command_capture(core.command_worker_run_prepare,argparse.Namespace(project_root=str(project),task=task,driver='manual'))
    assert code == 0,output
    report = project/'.pf/artifacts/governed-worker.md'
    report.write_text('# Governed worker evidence\n',encoding='utf-8')
    paths=[core.assignment_yaml_path(project,task),core.run_yaml_path(project,work['run_id']),core.assignment_capsule_path(project,task)]
    before=[p.read_bytes() for p in paths]
    for _ in range(2):
        code,output=core.run_command_capture(core.command_worker_run_collect,argparse.Namespace(project_root=str(project),task=task))
        assert code==0,output
    assert before==[p.read_bytes() for p in paths]
    state=service.state(run_id=work['run_id'],assignment_id=task)
    assert state['stage']['id']=='prepare' and state['assignment']['status']=='in_progress',state
    events=[row[1] for row in core.iter_ndjson(core.event_runtime_paths(project)[0])]
    assert sum(e['event_type']=='worker.run.collected' for e in events)==1
    assert not any(e['event_type'] in ('task.completed','assignment.completed') for e in events)
    result['governed_collection_preserves_stage_assignment_run_capsule'] = True

with tempfile.TemporaryDirectory(prefix='pf-t05-crash-') as directory:
    workplace,project=setup_basic_project(Path(directory),'crash-project')
    pf('run-create','--project-root',str(project),'--id','crash-run','--title','Crash fixture','--process','task-batch-execution','--apply')
    pf('task-create','--project-root',str(project),'--run','crash-run','--id','crash-task','--title','Crash task','--process','task-batch-execution','--allowed-file','.pf/artifacts/crash-report.md','--required-output','id=report,path=.pf/artifacts/crash-report.md','--expected-report-artifact','.pf/artifacts/crash-report.md','--apply')
    pf('worker-run','prepare','--project-root',str(project),'--task','crash-task','--driver','manual')
    (project/'.pf/artifacts/crash-report.md').write_text('# Crash recovery report\n',encoding='utf-8')
    child = '''import argparse,os,sys
from pathlib import Path
sys.path.insert(0,sys.argv[1])
import processforge as core
from processforge_core import prepared_input
original=prepared_input.write_once
def interrupted(path,document):
    if path.name=='collection-complete.json': os._exit(77)
    return original(path,document)
prepared_input.write_once=interrupted
core.command_worker_run_collect(argparse.Namespace(project_root=sys.argv[2],task='crash-task'))
'''
    crashed=subprocess.run([sys.executable,'-B','-c',child,str(ROOT/'tools'),str(project)],capture_output=True,text=True,encoding='utf-8',timeout=90)
    assert crashed.returncode==77,(crashed.stdout,crashed.stderr)
    paths=core.worker_run_paths(project,'crash-run','crash-task')
    assert (paths['root']/'.lifecycle.lock').is_file()
    pf('worker-run','collect','--project-root',str(project),'--task','crash-task')
    assert not (paths['root']/'.lifecycle.lock').exists()
    events=[row[1] for row in core.iter_ndjson(core.event_runtime_paths(project)[0])]
    for kind in ('task.completed','assignment.completed','worker.run.collected'):
        assert sum(e['event_type']==kind for e in events)==1,kind
    result['actual_process_exit_receipt_recovery_dead_owner_lock_once'] = True

Path(__file__).with_suffix('.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result))
