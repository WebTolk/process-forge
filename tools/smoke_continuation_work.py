"""Pinned continuation, CLI/MCP parity and cancellation recovery regression."""
from __future__ import annotations

import copy
import hashlib
import json
import runpy
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tools")]
import processforge as core
from processforge_core.continuation import ContinuationService
from processforge_core.process_execution import ProcessExecutionService
from process_execution_smoke_support import fixture, stage_evidence
from smoke_garage_mode_not_promoted_by_session import call_mcp, cli


def records(project):
    return {str(p.relative_to(project)): p.read_bytes() for folder in ("assignments", "runs", "contexts/assignment-capsules")
            for p in (project / ".pf" / folder).rglob("*.yaml")}


def main():
    with fixture() as (workplace, project, empty):
        service = ProcessExecutionService(project, workplace, core)
        continuation = ContinuationService(project, workplace, core)
        assert service.state(assignment_id=empty['assignment_id'])['execution_readiness']['status'] == 'blocked'
        # Explicit scope is captured before creation; required source checks remain enforced.
        source = project / 'input.txt'; source.write_text('immutable input', encoding='utf-8')
        scope = {'schema_version': 1, 'assignment': {'allowed_files': ['product.txt', '.pf/artifacts/result/**'],
                 'allowed_read_files': ['input.txt', '.pf/**'], 'required_sources': ['input.txt']}}
        started = service.start(objective='Continue the exact scoped work', scope_intent=scope)
        assert started['action'] == 'created_new', started
        selectors = {'run_id': started['run_id'], 'assignment_id': started['assignment_id'], 'context_id': started['context']['id']}
        create = dict(continuation_id='resume-exact', **selectors)
        original = records(project)
        assert continuation.request('create', **create)['action'] == 'preview'
        assert not (project / '.pf/continuations/resume-exact.yaml').exists()
        assert continuation.request('create', **create, apply=True)['action'] == 'created'
        assert records(project) == original
        discovery = continuation.request('status')
        assert discovery['action'] == 'choice_required' and records(project) == original
        assert continuation.request('resume', continuation_id='missing')['reason'] == 'continuation_not_found'
        assert records(project) == original
        # A session-bound selection survives a newer queued Work, without changing old intent.
        resumed = continuation.request('resume', continuation_id='resume-exact', session_id='session-one')
        assert resumed['action'] == 'continued', resumed
        continuation_path = project / '.pf/continuations/resume-exact.yaml'
        saved_record = continuation_path.read_bytes()
        schema = json.loads((ROOT / 'schemas/continuation-capsule.schema.json').read_text(encoding='utf-8'))
        validate = runpy.run_path(str(ROOT / 'tools/validate-process-forge-schemas.py'))['validate_instance']
        assert not validate(yaml.safe_load(saved_record), schema, schema, '$')
        incomplete = yaml.safe_load(saved_record); del incomplete['work']['capsule_checksum']
        assert validate(incomplete, schema, schema, '$')
        continuation_path.write_text(yaml.safe_dump(incomplete), encoding='utf-8')
        assert continuation.request('resume', continuation_id='resume-exact')['reason'] == 'continuation_binding_invalid'
        continuation_path.write_bytes(saved_record)
        assert continuation.request('resume', continuation_id='resume-exact', session_id='session-one')['action'] == 'continued'
        assert saved_record == continuation_path.read_bytes() and records(project) == original
        assert continuation.request('create', **{**create, 'continuation_id': 'marker-failure'}, apply=True)['action'] == 'created'
        write_yaml = ProcessExecutionService._atomic_yaml
        def fail_marker(self, path, value):
            if path.name == 'marker-failure.yaml' and value.get('status') == 'resumed':
                raise OSError('injected marker interruption')
            return write_yaml(self, path, value)
        with patch.object(ProcessExecutionService, '_atomic_yaml', fail_marker):
            partial = continuation.request('resume', continuation_id='marker-failure', session_id='marker-session')
            assert partial['action'] == 'selection_committed' and partial['marker_recovery_required'], partial
        assert service.state(session_id='marker-session')['assignment']['id'] == started['assignment_id']
        assert continuation.request('resume', continuation_id='marker-failure', session_id='marker-session')['action'] == 'continued'
        later = service.start(objective='New backlog work')
        assert service.state(session_id='session-one')['assignment']['id'] == started['assignment_id']
        assert service.state(session_id='session-two')['assignment']['id'] == later['assignment_id']
        assert service.state(run_id=later['run_id'], assignment_id=started['assignment_id'])['reason'] == 'work_identity_mismatch'
        assert service.state(**{**selectors, 'context_id': 'wrong-context'})['reason'] == 'work_context_mismatch'
        # Source mutation blocks resume, does not select a fallback or change lifecycle.
        source.write_text('changed', encoding='utf-8')
        frozen = records(project)
        assert continuation.request('resume', continuation_id='resume-exact')['reason'] == 'required_source_changed'
        assert service.state(session_id='session-one')['reason'] == 'required_source_changed'
        assert records(project) == frozen
        source.write_text('immutable input', encoding='utf-8')
        # Separate wait readiness, safe paths, and legacy wait-only compatibility.
        waiting = {**create, 'continuation_id': 'wait-result', 'expected_artifacts': ['result.txt']}
        assert continuation.request('create', **waiting, apply=True)['waiting']['status'] == 'waiting'
        assert continuation.request('resume', continuation_id='wait-result')['reason'] == 'continuation_waiting'
        (project / 'result.txt').write_text('ready', encoding='utf-8')
        assert continuation.request('resume', continuation_id='wait-result')['selection'] == 'explicit_selectors_required'
        assert continuation.request('create', **{**create, 'continuation_id': 'unsafe'}, expected_artifacts=['../outside'], apply=True)['status'] == 'blocked'
        legacy = project / '.pf/continuations/legacy.yaml'
        legacy.write_text(yaml.safe_dump({'schema_version': 1, 'id': 'legacy', 'waiting_for': {}, 'resume': {}, 'status': 'waiting'}), encoding='utf-8')
        assert continuation.request('resume', continuation_id='legacy')['work_resumed'] is False
        legacy_data = yaml.safe_load(legacy.read_bytes()); legacy_data['waiting_for']['handoff_id'] = 'legacy-return'
        legacy_data['status'] = 'waiting'; legacy.write_text(yaml.safe_dump(legacy_data), encoding='utf-8')
        assert continuation.request('resume', continuation_id='legacy')['reason'] == 'continuation_waiting'
        handoff = project / '.pf/handoffs/legacy-return/handoff.yaml'
        handoff.parent.mkdir(parents=True); handoff.write_text('status: returned\n', encoding='utf-8')
        assert continuation.request('resume', continuation_id='legacy')['work_resumed'] is False
        # A forged project reference and an altered capsule fail without falling back.
        data = yaml.safe_load(saved_record); data['work']['project_id'] = 'different-project'
        continuation_path.write_text(yaml.safe_dump(data), encoding='utf-8')
        assert continuation.request('resume', continuation_id='resume-exact')['reason'] == 'work_project_mismatch'
        continuation_path.write_bytes(saved_record)
        capsule = project / '.pf/contexts/assignment-capsules' / (started['assignment_id'] + '.capsule.yaml')
        capsule_bytes = capsule.read_bytes(); capsule.write_bytes(capsule_bytes + b'\n')
        assert continuation.request('resume', continuation_id='resume-exact')['status'] == 'blocked'
        capsule.write_bytes(capsule_bytes)
        # Real CLI and fresh independent stdio use the same service.
        args = ['continuation-create','--project-root',str(project),'--workplace',str(workplace),'--id','cli-resume',
                '--run',selectors['run_id'],'--assignment',selectors['assignment_id'],'--context-id',selectors['context_id'],'--apply','--json']
        assert json.loads(cli(*args).stdout)['action'] == 'created'
        context = call_mcp(workplace, 'pf.context', {'project_root': str(project)})
        assert context['project']['id'] == core.project_id(project)
        mcp = call_mcp(workplace, 'pf.continuation.resume', {'project_root':str(project),'continuation_id':'cli-resume'})
        assert mcp['selectors'] == selectors and mcp['action'] == 'continued', mcp
        current = call_mcp(workplace, 'pf.work.state', {'project_root':str(project), **selectors})
        assert current['assignment']['id'] == started['assignment_id']
        assert current['work']['selected_resource_ids']
        allowed_resource = call_mcp(workplace, 'pf.work.resolve', {'project_root': str(project), **selectors,
                                    'resource_id': current['work']['selected_resource_ids'][0]})
        assert allowed_resource['status'] == 'ready', allowed_resource
        denied_resource = call_mcp(workplace, 'pf.work.resolve', {'project_root': str(project), **selectors,
                                   'resource_id': 'not-selected'})
        assert denied_resource['reason'] == 'resource_not_in_work', denied_resource
        moved = call_mcp(workplace, 'pf.work.transition', {'project_root':str(project), **selectors, 'outcome':'completed',
                         'evidence':stage_evidence('brief','prepare-ready'),'notes':'Verified continuation stage'})
        assert moved['action'] == 'stage_transitioned', moved
        assert capsule.read_bytes() == capsule_bytes
        # Cancellation preview has no lifecycle mutation; active workers and leases block apply.
        cancel = {**selectors,'capsule_checksum':started['context']['checksum'],'reason':'Explicit fixture cancellation'}
        before_cancel = records(project)
        assert continuation.request('cancel_work', **cancel)['action'] == 'preview'
        assert records(project) == before_cancel
        worker = core.worker_run_paths(project, selectors['run_id'], selectors['assignment_id'])['status']
        worker.parent.mkdir(parents=True,exist_ok=True); worker.write_text('{"status":"running"}',encoding='utf-8')
        assert continuation.request('resume', continuation_id='resume-exact')['reason'] == 'worker_not_quiescent'
        assert continuation.request('cancel_work', **cancel, apply=True)['reason'] == 'worker_not_quiescent'
        worker.unlink()
        lease = {'schema_version':1,'id':'fixture-lease','status':'active','scope':{'project_id':core.project_id(project),'task_id':selectors['assignment_id']}}
        core.save_lease(workplace,lease)
        assert continuation.request('cancel_work', **cancel, apply=True)['reason'] == 'active_lease'
        lease['status']='released'; core.save_lease(workplace,lease)
        # Interrupt after assignment write, then recover exact journal; no fake completed stage.
        native_write = ProcessExecutionService._atomic_yaml
        def fail_assignment(self, path, value):
            if path == service._assignment_path(selectors['assignment_id']) and value.get('status') == 'cancelled':
                raise OSError('injected interruption before first lifecycle write')
            return native_write(self, path, value)
        with patch.object(ProcessExecutionService, '_atomic_yaml', fail_assignment):
            assert continuation.request('cancel_work', **cancel, apply=True)['status'] == 'blocked'
        assert service._load_assignment(selectors['assignment_id'])['status'] == 'in_progress'
        for command in ['prepare', 'start']:
            pending = subprocess.run([sys.executable, str(ROOT/'tools/processforge.py'), 'worker-run', command,
                                      '--project-root', str(project), '--task', selectors['assignment_id']],
                                      capture_output=True, text=True, encoding='utf-8')
            assert pending.returncode != 0 and 'cancellation_recovery_pending' in pending.stdout, pending.stdout + pending.stderr
        def fail_run(self, path, value):
            if path == service._run_path(selectors['run_id']) and value.get('status') == 'cancelled':
                raise OSError('injected persistence interruption')
            return native_write(self,path,value)
        with patch.object(ProcessExecutionService,'_atomic_yaml',fail_run):
            assert continuation.request('cancel_work', **cancel, apply=True)['status'] == 'blocked'
        assert service.transition(run_id=selectors['run_id'],assignment_id=selectors['assignment_id'],outcome='completed')['reason'] == 'cancellation_recovery_pending'
        result = continuation.request('cancel_work', **cancel, apply=True)
        assert result['status'] == 'cancelled', result
        events = core.event_runtime_paths(project)[0].read_bytes()
        assert continuation.request('cancel_work', **cancel, apply=True)['already_applied']
        assert core.event_runtime_paths(project)[0].read_bytes() == events
        assert capsule.read_bytes() == capsule_bytes
        task = core.load_task(project,selectors['assignment_id'])
        assert task['stage'] == 'build' and task['stage_status'] != 'completed'
        assert continuation.request('resume',continuation_id='resume-exact')['reason'] == 'work_is_terminal'
        assert service.state(session_id='session-one')['reason'] == 'work_is_terminal'
        assert service.state(assignment_id=later['assignment_id'])['assignment']['status'] == 'in_progress'
        p=subprocess.run([sys.executable,str(ROOT/'tools/processforge.py'),'worker-run','start','--project-root',str(project),'--task',selectors['assignment_id']],capture_output=True,text=True,encoding='utf-8')
        assert p.returncode != 0 and 'work_is_terminal' in p.stdout,p.stdout+p.stderr
        # Cancellation requires intact identity but remains possible when required sources changed.
        stale = service.start(objective='Cancel work with changed source', scope_intent={**scope, 'assignment': {**scope['assignment'], 'allowed_files': ['other.txt']}})
        source.write_text('changed again', encoding='utf-8')
        stale_cancel = dict(run_id=stale['run_id'], assignment_id=stale['assignment_id'], context_id=stale['context']['id'],
                            capsule_checksum=stale['context']['checksum'], reason='Cancel stale input work')
        assert continuation.request('cancel_work', **stale_cancel, apply=True)['status'] == 'cancelled'
        # A surviving member keeps the Run active; retry must preserve its later changes.
        run_path = service._run_path(later['run_id'])
        run = service._load_run(later['run_id'])
        run['tasks'].append({'id': 'surviving-member', 'status': 'in_progress'})
        service._atomic_yaml(run_path, run)
        member_cancel = dict(run_id=later['run_id'], assignment_id=later['assignment_id'], context_id=later['context']['id'],
                             capsule_checksum=later['context']['checksum'], reason='Cancel one member')
        one = continuation.request('cancel_work', **member_cancel, apply=True)
        assert one['status'] == 'cancelled' and one['run_status'] == run['status'], one
        run = service._load_run(later['run_id']); run['tasks'][-1]['status'] = 'done'
        run['updated_at'] = '2030-01-01T00:00:00Z'; service._atomic_yaml(run_path, run)
        assert continuation.request('cancel_work', **member_cancel, apply=True)['already_applied']
        assert service._load_run(later['run_id']) == run
        readonly = service.start(objective='Explicit read only continuation', scope_intent={'schema_version': 1, 'assignment': {
            'execution_mode': 'read_only', 'allowed_actions': ['read'], 'allowed_read_files': ['input.txt', '.pf/**']}})
        ro = continuation.request('create', continuation_id='read-only', run_id=readonly['run_id'],
                                  assignment_id=readonly['assignment_id'], context_id=readonly['context']['id'], apply=True)
        assert ro['action'] == 'created', ro
        assert continuation.request('resume', continuation_id='read-only')['work_resumed']
        readonly_cancel = dict(run_id=readonly['run_id'], assignment_id=readonly['assignment_id'], context_id=readonly['context']['id'],
                               capsule_checksum=readonly['context']['checksum'], reason='Finish discovery fixture')
        assert call_mcp(workplace, 'pf.work.cancel', {'project_root': str(project), **readonly_cancel})['action'] == 'preview'
        assert call_mcp(workplace, 'pf.work.cancel', {'project_root': str(project), **readonly_cancel, 'apply': True})['status'] == 'cancelled'
        assert continuation.request('cancel_work', run_id=empty['run_id'], assignment_id=empty['assignment_id'], context_id=empty['context']['id'],
                                    capsule_checksum=empty['context']['checksum'], reason='End fixture', apply=True)['status'] == 'cancelled'
        assert continuation.request('status')['action'] == 'not_found'
    print('PASS: continuation identity, wait readiness, sessions, CLI/MCP, permissions and cancellation recovery')


if __name__ == '__main__':
    main()
