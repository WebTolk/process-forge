import argparse
import copy
import json
from pathlib import Path
import sys
import yaml

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src'))
import processforge as core
from processforge_core.process_execution import ProcessExecutionService
from process_execution_smoke_support import fixture, assignment, run

with fixture() as (workplace, project, started):
    task = assignment(project, started)
    run_doc = run(project, started)
    task.update(allowed_files=['.pf/artifacts/report.md'], allowed_read_files=['input.md'], required_sources=['input.md'],
                required_outputs=[{'id': 'report', 'path': '.pf/artifacts/report.md', 'required': True}],
                execution_mode={'kind': 'read_only', 'code_changes_allowed': False, 'artifact_changes_allowed': True})
    (project / 'input.md').write_text('fixed input', encoding='utf-8')
    task_path = project / '.pf/assignments' / (task['id'] + '.yaml')
    task_path.write_text(yaml.safe_dump(task, sort_keys=False), encoding='utf-8')
    service = ProcessExecutionService(project, workplace, core)
    capsule_rel, checksum = service._write_capsule(run_doc, task, run_doc['process_execution'])
    governed = core.load_yaml_document(project / capsule_rel)
    # Disposable fixture only: show the old CLI's force rewrite and different shape.
    core.command_assignment_capsule(argparse.Namespace(project_root=str(project), assignment=str(task_path), force=True))
    command = core.load_yaml_document(project / capsule_rel)
    before_status = core.existing_capsule_status(project, task['id'])[0]
    task['status'] = 'review'
    task['updated_at'] = 'later-lifecycle-time'
    task_path.write_text(yaml.safe_dump(task, sort_keys=False), encoding='utf-8')
    after_status = core.existing_capsule_status(project, task['id'])[0]
    result = {
        'governed_has_scope': 'scope' in governed, 'command_has_scope': 'scope' in command,
        'governed_required_sources': governed['context']['required_sources'],
        'command_required_sources': command['context']['required_sources'],
        'governed_has_process': 'process_execution' in governed, 'command_has_process': 'process_execution' in command,
        'before_lifecycle_status': before_status, 'after_lifecycle_status': after_status,
        'governed_capsule_was_replaced_by_force': 'sha256:' + core.sha256_file(project / capsule_rel) != checksum,
    }
    assert result['governed_has_scope'] is False and result['command_has_scope'] is True
    assert before_status == 'fresh' and after_status == 'stale'
    assert result['governed_capsule_was_replaced_by_force']
Path(__file__).with_name('before.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
print(json.dumps(result))
