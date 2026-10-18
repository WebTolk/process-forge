"""Primary validation of worker hypotheses with real filesystem/Core/ingress."""
from pathlib import Path
import json
import os
import sys
import tempfile
import threading

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'tools'))
import processforge as core
from pf_runtime import host, service
from pf_runtime.codex_hooks import native_envelope
from smoke_conversation_completeness import setup_basic_project, events


def main():
    result = {}
    with tempfile.TemporaryDirectory(prefix='pf-primary-hooks-') as raw:
        root = Path(raw)
        wp = root / 'orphan-workplace'
        service.runtime_root(wp).mkdir(parents=True)
        state = service.base_state(wp, core, status='ready', pid=os.getpid(), instance_id='old-owner')
        service.save_service_state(wp, core, state)
        # A genuine live OS PID and durable ownership state, no PID/lock mocks.
        service.write_json_atomic(service.lock_path(wp), {'pid': os.getpid(), 'instance_id': 'mismatched-lock'})
        before = service.inspect_lifecycle(wp, core)
        acquired = service.acquire_singleton(wp, core, 'new-owner')
        after = service.read_json(service.lock_path(wp))
        result['orphan_takeover'] = {'lifecycle_before': before['kind'], 'old_pid_alive': core.process_pid_running(state['pid']), 'acquire_returned': acquired, 'lock_owner_after': after['instance_id'], 'limitation': 'Real live PID and files; fixture represents damaged ownership metadata, no second daemon started.'}
        broken = root / 'broken-cache'
        runtime = service.RuntimeProcess(broken, core, interval=0.01)
        host.state_path(broken).parent.mkdir(parents=True, exist_ok=True)
        host.state_path(broken).write_text('{broken', encoding='utf-8')
        escaped = []
        def run_scheduler():
            try:
                runtime.scheduler_loop()
            except BaseException as exc:
                escaped.append({'type': type(exc).__name__, 'error': str(exc)})
        thread = threading.Thread(target=run_scheduler, daemon=True)
        thread.start()
        thread.join(timeout=2)
        result['cache_read_failure'] = {'scheduler_alive': thread.is_alive(), 'escaped': escaped, 'last_scheduler_error': runtime.state.get('last_scheduler_error')}
        runtime.stop_event.set()
        thread.join(timeout=2)
        workplace, project = setup_basic_project(root, 'hook-project')
        captures = []
        for source in ('startup', 'resume'):
            envelope = native_envelope({'hook_event_name': 'SessionStart', 'source': source, 'cwd': str(project), 'session_id': 'fixture-session'})
            captured = host.ingest_event(envelope, workplace, core)
            captures.append({'source': source, 'derived_event_type': envelope['derived_event']['event_type'], 'derived_event_id': envelope['derived_event']['event_id'], 'raw_event_id': captured.get('raw_event_id'), 'duplicate': captured.get('duplicate'), 'normalized_event_ids': captured.get('normalized_event_ids')})
        lifecycle = [e for e in events(project) if e.get('event_type') in ('agent.session.started', 'agent.session.resumed')]
        result['session_start_resume'] = {'captures': captures, 'stored_lifecycle_types': [e['event_type'] for e in lifecycle]}
    assert result['orphan_takeover']['lifecycle_before'] == 'orphaned'
    assert result['orphan_takeover']['lock_owner_after'] == 'new-owner'
    assert not result['cache_read_failure']['scheduler_alive']
    assert result['cache_read_failure']['escaped'][0]['type'] == 'JSONDecodeError'
    assert result['session_start_resume']['stored_lifecycle_types'] == ['agent.session.started']
    (OUT / 'hooks-primary-results.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
