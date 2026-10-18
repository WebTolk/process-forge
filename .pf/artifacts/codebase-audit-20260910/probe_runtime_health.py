"""Isolated real-core probes for scheduler failure visibility; no installed state."""
from pathlib import Path
import json
import sys
import tempfile
import threading
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools'))
import processforge as core
from pf_runtime import host, service

def probe(kind):
    with tempfile.TemporaryDirectory(prefix='pf-audit-runtime-') as tmp:
        root = Path(tmp)
        workplace = root / 'workplace'
        project = root / 'project'
        flow = project / '.pf'
        flow.mkdir(parents=True)
        core.write_yaml_file(flow / 'process-forge.yaml', {
            'schema_version': 1, 'project': {'id': 'audit-runtime'},
            'coordination': {'mode': 'simple'},
            'paths': {'runtime': 'runtime', 'assignments': 'assignments'},
        })
        core.write_yaml_file(workplace / 'workplace.yaml', {
            'schema_version': 1, 'id': 'audit-workplace',
            'coordination': {'default_project_mode': 'simple', 'director_enabled': False},
        })
        state = host.load_state(workplace)
        host.remember_project(state, host.route_project(str(project), workplace, core))
        host.save_state(workplace, state, core)
        runtime = service.RuntimeProcess(workplace, core, interval=0.25)
        runtime.state.update(status='ready', health='ready')
        if kind == 'malformed_assignment':
            target = flow / 'assignments' / 'broken.yaml'
            target.parent.mkdir(parents=True)
            target.write_text('schema_version: [', encoding='utf-8')
        elif kind == 'invalid_task_order':
            core.write_yaml_file(flow / 'runs' / 'broken' / 'run.yaml', {
                'id': 'broken', 'status': 'in_progress',
                'tasks': [{'id': 'missing', 'order': 'invalid'}]
            })
        else:
            core.write_yaml_file(flow / 'runs' / 'broken' / 'run.yaml', {
                'id': 'broken', 'status': 'in_progress', 'tasks': [{'id': 'missing'}]
            })
        escapes = []
        def run():
            try:
                runtime.scheduler_loop()
            except BaseException as exc:
                escapes.append({'type': type(exc).__name__, 'error': str(exc)})
        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline and not escapes and not runtime.state.get('last_scheduler_error'):
            time.sleep(0.05)
        was_alive = thread.is_alive()
        runtime.stop_event.set()
        thread.join(timeout=3)
        payload = runtime.status_payload()
        return {'case': kind, 'scheduler_alive': was_alive, 'escaped': escapes,
                'internal_health': runtime.state.get('health'),
                'reported_health': payload.get('health'), 'reported_status': payload.get('status'),
                'last_scheduler_error': payload.get('last_scheduler_error')}

if __name__ == '__main__':
    print(json.dumps([probe('invalid_task_order'), probe('missing_assignment')], indent=2))
