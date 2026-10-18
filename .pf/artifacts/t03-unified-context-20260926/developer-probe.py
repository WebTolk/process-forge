import argparse
import copy
import json
from pathlib import Path
import shutil
import sys
import tempfile
import yaml

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src'))
import processforge as core
from processforge_core.process_execution import ProcessExecutionService
from processforge_core.work_context import validate_execution_contract
from process_execution_smoke_support import fixture, assignment, run

with tempfile.TemporaryDirectory(prefix='pf-t03-parity-') as raw:
    with fixture() as (workplace, project, started):
        task, run_doc = assignment(project, started), run(project, started)
        task['id'] = 't03-parity'
        task['process_execution'] = {k: v for k, v in task['process_execution'].items() if not k.startswith('assignment_capsule')}
        task.update(allowed_files=['.pf/artifacts/report.md'], allowed_read_files=['input.md'], required_sources=['input.md'],
                    required_outputs=[{'id': 'report', 'path': '.pf/artifacts/report.md', 'required': True}],
                    execution_mode={'kind': 'read_only', 'code_changes_allowed': False, 'artifact_changes_allowed': True})
        (project / 'input.md').write_text('fixed input', encoding='utf-8')
        task_path = project / '.pf/assignments/t03-parity.yaml'
        task_path.write_text(yaml.safe_dump(task, sort_keys=False), encoding='utf-8')
        run_doc['tasks'].append({'id': task['id'], 'status': 'in_progress', 'assignment': '.pf/assignments/t03-parity.yaml'})
        (project / '.pf/runs' / run_doc['id'] / 'run.yaml').write_text(yaml.safe_dump(run_doc, sort_keys=False), encoding='utf-8')
        clone = Path(raw) / 'clone'
        shutil.copytree(project, clone)
        service = ProcessExecutionService(project, workplace, core)
        capsule_rel, checksum = service._write_capsule(run_doc, task, run_doc['process_execution'])
        governed = core.load_yaml_document(project / capsule_rel)
        clone_task = clone / '.pf/assignments/t03-parity.yaml'
        core.command_assignment_capsule(argparse.Namespace(project_root=str(clone), assignment=str(clone_task), force=False))
        command = core.load_yaml_document(clone / capsule_rel)
        assert governed['execution_contract'] == command['execution_contract'], 'essential contracts differ'
        assert validate_execution_contract(project, task_path, task, governed, core, require_ready=True)['status'] == 'valid'
        lifecycle = copy.deepcopy(task)
        lifecycle.update(status='review', stage='build', updated_at='later', stage_history=[{'some': 'new evidence'}], agent_model='other', agent_reasoning_effort='high', diagnostics={'profile': 'trace'})
        assert validate_execution_contract(project, task_path, lifecycle, governed, core)['status'] == 'valid'
        changed = copy.deepcopy(task)
        changed['objective'] = 'different intent'
        assert validate_execution_contract(project, task_path, changed, governed, core)['reason'] == 'assignment_contract_changed'
        (project / 'input.md').write_text('changed input', encoding='utf-8')
        assert validate_execution_contract(project, task_path, task, governed, core)['reason'] == 'required_source_changed'
        try:
            core.command_assignment_capsule(argparse.Namespace(project_root=str(project), assignment=str(task_path), force=True))
        except SystemExit as exc:
            assert 'immutable_context_exists' in str(exc)
        else:
            raise AssertionError('force replaced immutable capsule')
        assert 'sha256:' + core.sha256_file(project / capsule_rel) == checksum
        result = {'status': 'PASS', 'checks': ['both actual builders exact execution-contract equality', 'ready declared source/report scope', 'lifecycle and preferences retain intent', 'objective mutation rejected', 'source byte mutation rejected', 'force rejected without capsule mutation'], 'execution_contract': governed['execution_contract']}
Path(__file__).with_name('developer-probe.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k != 'execution_contract'}))
