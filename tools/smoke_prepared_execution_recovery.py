#!/usr/bin/env python3
"""Real prepared-executor recovery and governed continuation in isolated fixtures."""
from __future__ import annotations

import argparse
import copy
import io
import json
import os
from contextlib import ExitStack, nullcontext, redirect_stdout
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import Mock, patch

import processforge as core
import processforge_core.prepared.input as prepared_input
from process_execution_smoke_support import fixture
from processforge_core.prepared.input import private_file
from processforge_core.prepared.collection import CapturedAttemptReader
from processforge_core.process_execution import ProcessExecutionService
from smoke_garage_mode_not_promoted_by_session import call_mcp
from smoke_prepared_execution_context import (
    ROOT, RUN_ID, call, create_task, event_rows, make_shell_driver,
    pf, require, setup_basic_project,
)


def terminal_worker_admission() -> None:
    failures = []
    count = 0
    real_prepare = core.prepare_worker_run

    def check(name, test):
        nonlocal count
        count += 1
        try:
            test()
        except (AssertionError, SystemExit) as exc:
            failures.append(f'{name}: {exc}')

    with tempfile.TemporaryDirectory(prefix='pf-terminal-admission-') as temporary:
        project = Path(temporary)
        run_dir = project / '.pf/runs/fixture'
        run_dir.mkdir(parents=True)

        def records(task_status='open', run_status='in_progress', marker='task'):
            task = {'id': 'fixture', 'run_id': 'fixture', 'status': task_status}
            run = {'id': 'fixture', 'status': run_status}
            if marker == 'task':
                task['process_execution'] = {}
            elif marker == 'run':
                run['process_execution'] = {}
            (run_dir / 'run.yaml').write_text(json.dumps(run), encoding='utf-8')
            return task

        def files():
            return {p.relative_to(project).as_posix(): p.read_bytes() for p in project.rglob('*') if p.is_file()}

        forbidden = ('save_task', 'existing_capsule_status', 'existing_running_worker_run',
                     'load_agent_run_state', 'runtime_driver_for_task', 'emit_process_event',
                     'emit_worker_run_skip', 'build_worker_process_command')

        def rejected(task_status, run_status, marker, operation):
            task = records(task_status, run_status, marker)
            original = copy.deepcopy(task)
            before = files()
            spies = {name: Mock(side_effect=AssertionError('unexpected ' + name)) for name in forbidden}
            prepare = Mock(side_effect=AssertionError('unexpected preparation'))
            provider = Mock(side_effect=AssertionError('unexpected prepared/provider load'))
            launch = Mock(side_effect=AssertionError('unexpected process launch'))
            stdout = io.StringIO()
            with ExitStack() as stack:
                stack.enter_context(patch.object(core, 'require_flow_root'))
                stack.enter_context(patch.object(core, 'load_task', return_value=task))
                stack.enter_context(patch.object(core, 'worker_run_lifecycle_lock', return_value=nullcontext()))
                stack.enter_context(patch.multiple(core, **spies))
                stack.enter_context(patch.object(core, 'prepare_worker_run', prepare))
                stack.enter_context(patch.object(prepared_input, 'load', provider))
                stack.enter_context(patch.object(core.subprocess, 'Popen', launch))
                with redirect_stdout(stdout):
                    if operation == 'direct':
                        try:
                            real_prepare(project, 'fixture', model_arg='fixture-model')
                        except SystemExit as exc:
                            assert 'work_is_terminal' in str(exc), exc
                        else:
                            raise AssertionError('direct prepare admitted terminal Work')
                    else:
                        code = getattr(core, 'command_worker_run_' + operation)(argparse.Namespace(project_root=str(project), task='fixture'))
                        assert code == 1 and 'work_is_terminal' in stdout.getvalue(), stdout.getvalue()
            assert all(not spy.called for spy in [*spies.values(), prepare, provider, launch])
            assert task == original and files() == before, 'terminal admission changed records/attempt/output files'

        cases = [(status, 'in_progress', marker) for status in ('done', 'completed', 'failed', 'cancelled') for marker in ('task', 'run')]
        cases += [('open', status, marker) for status in ('completed', 'failed', 'cancelled') for marker in ('task', 'run')]
        cases += [('cancelled', 'in_progress', 'legacy')]
        for task_status, run_status, marker in cases:
            for operation in ('prepare', 'start', 'direct'):
                check(f'{operation}/{marker}/{task_status}/{run_status}',
                      lambda t=task_status, r=run_status, m=marker, o=operation: rejected(t, r, m, o))

        def admitted(task_status, marker, operation):
            task = records(task_status, marker=marker)
            paths = {'status': project / 'status.json', 'command': project / 'command.json'}
            prepare = Mock(return_value=(task, {'id': 'manual', 'kind': 'manual'}, paths))
            provider = Mock(return_value={})
            launch = Mock(side_effect=AssertionError('manual fixture launched process'))
            before = files()
            with ExitStack() as stack:
                stack.enter_context(patch.object(core, 'require_flow_root'))
                stack.enter_context(patch.object(core, 'load_task', return_value=task))
                stack.enter_context(patch.object(core, 'worker_run_lifecycle_lock', return_value=nullcontext()))
                stack.enter_context(patch.object(core, 'existing_running_worker_run', return_value=None))
                stack.enter_context(patch.object(core, 'load_agent_run_state', return_value={'status': 'failed', 'attempt': 1}))
                stack.enter_context(patch.object(core, 'prepare_worker_run', prepare))
                stack.enter_context(patch.object(core, 'json_read', return_value={'status': 'ready'}))
                stack.enter_context(patch.object(prepared_input, 'load', provider))
                stack.enter_context(patch.object(core.subprocess, 'Popen', launch))
                with redirect_stdout(io.StringIO()):
                    code = getattr(core, 'command_worker_run_' + operation)(argparse.Namespace(project_root=str(project), task='fixture'))
            assert code == 0 and prepare.call_count == 1
            assert provider.call_count == (1 if operation == 'start' else 0)
            assert not launch.called and files() == before

        for status, marker in [('open', 'task'), ('open', 'run'), ('open', 'legacy'), ('failed', 'legacy'), ('done', 'legacy'), ('completed', 'legacy')]:
            for operation in ('prepare', 'start'):
                check(f'retry/{marker}/{status}/{operation}', lambda s=status, m=marker, o=operation: admitted(s, m, o))

        def cancellation_priority(operation):
            task = records('cancelled')
            intent = run_dir / 'cancellation-fixture.yaml'
            intent.write_text('pending\n', encoding='utf-8')
            try:
                stdout = io.StringIO()
                with patch.object(core, 'require_flow_root'), patch.object(core, 'load_task', return_value=task), \
                     patch.object(core, 'worker_run_lifecycle_lock', return_value=nullcontext()), \
                     patch.object(core, 'prepare_worker_run', side_effect=AssertionError('unexpected prepare')), redirect_stdout(stdout):
                    code = getattr(core, 'command_worker_run_' + operation)(argparse.Namespace(project_root=str(project), task='fixture'))
                assert code == 1 and 'cancellation_recovery_pending' in stdout.getvalue(), stdout.getvalue()
            finally:
                intent.unlink()

        for operation in ('prepare', 'start'):
            check('pending cancellation/' + operation, lambda o=operation: cancellation_priority(o))

        def failure_sync(marker, attempt_status):
            task = records(marker=marker)
            before = copy.deepcopy(task)
            saved, updated, emitted = Mock(), Mock(), Mock()
            with patch.object(core, 'save_task', saved), patch.object(core, 'update_run_task_status', updated), patch.object(core, 'emit_process_event', emitted):
                core.sync_failed_worker_lifecycle(project, task, {'status': attempt_status, 'failure_reason': 'fixture failure'})
            if marker == 'legacy':
                assert task['status'] == 'failed' and task['result']['status'] == 'failed'
                assert saved.call_count == updated.call_count == emitted.call_count == 1
            else:
                assert task == before and not any(x.called for x in (saved, updated, emitted)), 'worker failure terminalized governed Work'

        for marker in ('task', 'run', 'legacy'):
            for status in sorted(core.AGENT_RUN_FAILURE_TERMINAL_STATUSES):
                check('failure sync/' + marker + '/' + status, lambda m=marker, s=status: failure_sync(m, s))

    for failure in failures:
        print('FAIL: ' + failure, flush=True)
    print(f'Terminal admission: {count - len(failures)}/{count} cases passed', flush=True)
    assert not failures, '\n'.join(failures)


def historical_capture_checks(project: Path, task_id: str, run_id: str) -> None:
    task = core.load_task(project, task_id)
    paths = core.worker_run_paths(project, run_id, task_id)
    state = core.json_read(paths['status'])
    reader = CapturedAttemptReader(project)
    captured = reader.read(task, state, run_id=run_id)
    require(captured is not None and captured.attempt == state['attempt'], 'real capture not recognized')
    attempt = (project / state['prepared_input']['path']).parent
    receipt = attempt / 'collection-receipt.json'
    complete = attempt / 'collection-complete.json'
    prepared_path = project / state['prepared_input']['path']
    capsule = core.assignment_capsule_path(project, task_id)
    protected = [core.assignment_yaml_path(project, task_id), core.run_yaml_path(project, run_id), capsule, receipt, complete, prepared_path]
    before = [p.read_bytes() for p in protected]
    events_before = event_rows(project)

    def tick_without_collect():
        with patch.object(core, 'command_worker_run_collect', side_effect=AssertionError('historical observation collected again')):
            code, output = core.run_command_capture(core.command_supervisor_tick,
                argparse.Namespace(project_root=str(project), run=run_id, profile=None, start_allowed=False))
        require(code == 0 and 'collected=0' in output and 'observed=1' in output, output)
        report = (core.supervisor_root(project) / 'last-tick-report.md').read_text(encoding='utf-8')
        require(f'- historical_observed: `{task_id}`' in report and '- collected: `none`' in report, report)
        require(core.supervisor_pending_drain_task_ids(project, [run_id]) == [], 'historical capture still pending drain')
        require(before == [p.read_bytes() for p in protected], 'historical observation changed capture/lifecycle')
        events = event_rows(project)
        require(sum(e['event_type'] == 'worker.run.collected' for e in events) ==
                sum(e['event_type'] == 'worker.run.collected' for e in events_before), 'historical capture event duplicated')
        tick = next(e for e in reversed(events) if e['event_type'] == 'supervisor.tick.completed')
        require(tick['data']['historical_observed'] == [task_id] and tick['data']['collected'] == [], tick)

    tick_without_collect()
    state_raw = paths['status'].read_bytes()
    try:
        paths['status'].write_text(json.dumps(dict(state, status='running')), encoding='utf-8')
        def completed_now(*args):
            paths['status'].write_bytes(state_raw)
            return state
        with patch.object(core, 'observe_worker_run', side_effect=completed_now):
            tick_without_collect()
    finally:
        paths['status'].write_bytes(state_raw)
    report_path = project / '.pf/artifacts/governed-worker.md'
    report_raw = report_path.read_bytes()
    source_path = project / '.pf/artifacts/capture-input.txt'
    source_raw = source_path.read_bytes()
    for path, raw, reason in [(report_path, report_raw, 'collected_output_changed'), (source_path, source_raw, 'required_source_changed')]:
        try:
            path.write_bytes(raw + b'changed\n')
            require(reader.read(task, state, run_id=run_id) == captured, 'historical metadata asserted current material')
            tick_without_collect()
            code, output = call(project, task_id, 'collect')
            require(code != 0 and reason in output, output)
        finally:
            path.write_bytes(raw)
    code, output = call(project, task_id, 'collect')
    require(code == 0, output)

    for path in [complete, receipt, prepared_path, capsule]:
        raw = path.read_bytes()
        try:
            path.write_bytes(b'{invalid\n')
            require(reader.read(task, state, run_id=run_id) is None, f'tampered metadata accepted: {path.name}')
        finally:
            path.write_bytes(raw)
    raw = complete.read_bytes()
    try:
        complete.unlink()
        require(reader.read(task, state, run_id=run_id) is None, 'partial receipt mistaken for completed capture')
        require(core.supervisor_pending_drain_task_ids(project, [run_id]) == [task_id], 'partial capture omitted from drain')
        collect = Mock(return_value=0)
        with patch.object(core, 'command_worker_run_collect', collect):
            code, _ = core.run_command_capture(core.command_supervisor_tick,
                argparse.Namespace(project_root=str(project), run=run_id, profile=None, start_allowed=False))
        require(code == 0 and collect.call_count == 1, 'partial receipt did not enter full recovery')
    finally:
        complete.write_bytes(raw)
    for key, value in [('attempt', 2), ('attempt', True), ('task_id', 'other'), ('run_id', 'other'), ('status', 'running')]:
        changed = dict(state, **{key: value})
        require(reader.read(task, changed, run_id=run_id) is None, f'wrong state {key} accepted')
    require(reader.read(task, state, run_id='other') is None, 'foreign supervisor run accepted')
    changed_task = copy.deepcopy(task)
    changed_task['process_execution']['assignment_capsule_checksum'] = 'sha256:' + '0' * 64
    require(reader.read(changed_task, state, run_id=run_id) is None, 'wrong task capsule pin accepted')
    with patch('processforge_core.prepared.collection.bounded_read', side_effect=PermissionError('denied metadata')):
        require(reader.read(task, state, run_id=run_id) is None, 'metadata read denial accepted')
    require(reader.read(task, state, run_id=run_id) == captured, 'metadata restoration invisible')
    print('PASS: historical capture, explicit current guards, proof tamper/identity/read denial and drain recovery', flush=True)


def governed_continuation() -> None:
    with fixture() as (workplace, project, started):
        code, output = call(project, started["assignment_id"], "prepare", driver="manual")
        require(code != 0 and "worker_report_undeclared" in output, output)

        class ScopedFixtureService(ProcessExecutionService):
            def _write_capsule(self, run, assignment, pin):
                # Declare scope before immutable context creation. Do not rewrite
                # a persisted capsule or its pins to obtain a positive fixture.
                report = ".pf/artifacts/governed-worker.md"
                assignment.update(
                    allowed_files=[report], expected_report={"artifact": report},
                    required_outputs=[{"id": "worker-report", "path": report, "required": True}],
                    allowed_read_files=['.pf/artifacts/capture-input.txt'],
                    required_sources=['.pf/artifacts/capture-input.txt'],
                )
                return super()._write_capsule(run, assignment, pin)

        objective = "Governed prepared executor recovery fixture"
        source = project / '.pf/artifacts/capture-input.txt'
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_bytes(b'capture input\n')
        service = ScopedFixtureService(project, workplace, core)
        work = service.start(objective=objective, process_id="declarative-smoke")
        require(work["action"] == "created_new", work)
        task = work["assignment_id"]
        driver = make_shell_driver(project)
        code, output = call(project, task, "start", driver=str(driver))
        require(code == 0, output)
        paths = [core.assignment_yaml_path(project, task),
                 core.run_yaml_path(project, work["run_id"]),
                 core.assignment_capsule_path(project, task)]
        before = [path.read_bytes() for path in paths]
        for _ in range(2):
            code, output = call(project, task, "collect")
            require(code == 0, output)
        require(before == [path.read_bytes() for path in paths],
                "governed collection changed assignment/run/capsule")
        events = event_rows(project)
        require(sum(row["event_type"] == "worker.run.collected" for row in events) == 1, events)
        require(not any(row["event_type"] in {"task.completed", "assignment.completed"}
                        for row in events), "worker completed primary Work")
        historical_capture_checks(project, task, work['run_id'])

        # Each helper call starts and closes a new source stdio MCP process.
        # This proves durable reconnect in a fixture, not a connected host update.
        resumed = call_mcp(workplace, "pf.work.start", {
            "project_root": str(project), "objective": objective,
            "process_id": "declarative-smoke",
        })
        require(resumed.get("action") == "continue_existing"
                and resumed.get("run_id") == work["run_id"]
                and resumed.get("assignment_id") == task, resumed)
        current = call_mcp(workplace, "pf.work.state", {"project_root": str(project)})
        require(current["run"]["id"] == work["run_id"]
                and current["assignment"]["id"] == task
                and current["stage"]["id"] == "prepare", current)
        transitioned = call_mcp(workplace, "pf.work.transition", {
            "project_root": str(project), "outcome": "completed",
            "notes": "Collected executor result reviewed by fixture primary agent.",
            "evidence": [
                {"kind": "artifact", "artifact_id": "brief", "status": "ready",
                 "path": ".pf/artifacts/governed-worker.md"},
                {"kind": "gate", "gate_id": "prepare-ready", "status": "passed"},
            ],
        })
        require(transitioned.get("action") == "stage_transitioned"
                and transitioned["stage"]["id"] == "build", transitioned)
        continued = call_mcp(workplace, "pf.work.state", {"project_root": str(project)})
        require(continued["run"]["id"] == work["run_id"]
                and continued["assignment"]["id"] == task
                and continued["stage"]["id"] == "build", continued)
        require(paths[2].read_bytes() == before[2], "transition rewrote immutable capsule")
    print("PASS: offline governed execution, collection invariance, source MCP reconnect and transition", flush=True)


def abrupt_collection_recovery() -> None:
    with tempfile.TemporaryDirectory(prefix="pf-prepared-crash-") as raw:
        _, project = setup_basic_project(Path(raw), "crash-project")
        pf("run-create", "--project-root", str(project), "--id", RUN_ID,
           "--title", "Crash recovery fixture", "--process", "task-batch-execution", "--apply")
        create_task(project, "crash-task")
        code, output = call(project, "crash-task", "prepare", driver="manual")
        require(code == 0, output)
        (project / ".pf/artifacts/crash-task.md").write_text("# Crash recovery report\n", encoding="utf-8")
        child = '''import argparse,os,sys
sys.path.insert(0,sys.argv[1])
import processforge as core
import processforge_core.prepared.input as prepared_input
original=prepared_input.write_once
def interrupted(path,document):
    if path.name=='collection-complete.json': os._exit(77)
    return original(path,document)
prepared_input.write_once=interrupted
core.command_worker_run_collect(argparse.Namespace(project_root=sys.argv[2],task='crash-task'))
'''
        crashed = subprocess.run(
            [sys.executable, "-B", "-c", child, str(ROOT / "tools"), str(project)],
            capture_output=True, text=True, encoding="utf-8", timeout=90,
        )
        require(crashed.returncode == 77, (crashed.returncode, crashed.stdout, crashed.stderr))
        paths = core.worker_run_paths(project, RUN_ID, "crash-task")
        lock = paths["root"] / ".lifecycle.lock"
        state = core.json_read(paths["status"])
        attempt = (project / state["prepared_input"]["path"]).parent
        receipt = attempt / "collection-receipt.json"
        complete = attempt / "collection-complete.json"
        require(lock.is_file() and receipt.is_file() and not complete.exists(),
                "child did not leave the expected interrupted receipt/lock state")
        receipt_bytes = receipt.read_bytes()
        # Recover in another process, with no monkeypatch or in-memory state.
        for _ in range(2):
            pf("worker-run", "collect", "--project-root", str(project), "--task", "crash-task")
        require(not lock.exists() and complete.is_file() and receipt.read_bytes() == receipt_bytes,
                "dead-owner recovery lost receipt or completion")
        events = event_rows(project)
        for kind in ("task.completed", "assignment.completed", "worker.run.collected"):
            require(sum(row["event_type"] == kind for row in events) == 1,
                    {"kind": kind, "events": events})
    print("PASS: actual process death, dead-owner lock and exactly-once receipt recovery", flush=True)


def private_redirect_refused() -> None:
    with tempfile.TemporaryDirectory(prefix="pf-prepared-path-") as raw:
        project = Path(raw).resolve()
        agent = project / ".pf/runtime/agent-runs/path-run/path-task"
        target = project / ".pf/artifacts/public-fixture"
        agent.mkdir(parents=True)
        target.mkdir(parents=True)
        link = agent / "attempts"
        if os.name == "nt":
            def quote(value: Path) -> str:
                return "'" + str(value).replace("'", "''") + "'"
            command = "New-Item -ItemType Junction -Path " + quote(link) + " -Target " + quote(target) + " | Out-Null"
            created = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", command],
                                     capture_output=True, text=True, timeout=20)
            require(created.returncode == 0, created.stderr)
        else:
            link.symlink_to(target, target_is_directory=True)
        try:
            try:
                private_file(project, ".pf/runtime/agent-runs/path-run/path-task/attempts/1/prepared-input.json")
            except ValueError as exc:
                require(str(exc) == "prepared_path_redirected", str(exc))
            else:
                raise AssertionError("private manifest directory redirection accepted")
            require(not list(target.iterdir()), "private bytes were written through redirect")
        finally:
            # Verify both endpoints are inside this isolated fixture, then remove
            # only the link using one native filesystem API (never recurse).
            require(link.parent.resolve().is_relative_to(project)
                    and target.resolve().is_relative_to(project), "fixture cleanup escaped its root")
            if os.name == "nt":
                link.rmdir()
            else:
                link.unlink()
    print("PASS: real directory redirect refused without private-byte publication", flush=True)


def windows_extended_private_paths() -> None:
    if os.name != "nt":
        return
    with tempfile.TemporaryDirectory(prefix="pf-prepared-prefix-") as raw:
        project = Path(raw).resolve()
        relative = ".pf/runtime/agent-runs/path-run/path-task/.lifecycle.lock"
        lock = project / relative
        lock.parent.mkdir(parents=True)
        lock.write_text("owner", encoding="utf-8")
        original_resolve = Path.resolve

        def extended_lock(path: Path, *args, **kwargs) -> Path:
            resolved = original_resolve(path, *args, **kwargs)
            if path == lock:
                return Path("\\\\?\\" + project.drive + "\\$Extend\\$Deleted\\fixture-handle")
            if path == lock.parent:
                return Path("\\\\?\\" + str(resolved))
            return resolved

        # A disappearing regular lock must be located through its parent,
        # without treating a deleted NTFS handle name as a path redirection.
        with patch.object(Path, "resolve", extended_lock):
            require(private_file(project, relative) == lock,
                    "equivalent extended lock path refused")
        lock.unlink()
        with patch.object(Path, "resolve", extended_lock):
            require(private_file(project, relative) == lock,
                    "missing transient lock path refused")

        unc = Path("\\\\server\\share\\agent-runs\\lock")
        with patch.object(Path, "lstat", side_effect=FileNotFoundError), \
                patch.object(Path, "resolve", return_value=Path("\\\\?\\UNC\\server\\share\\agent-runs")):
            require(prepared_input._resolved_path(unc) == unc,
                    "extended UNC path changed its location")

        target = project / ".pf/artifacts/redirected-lock"
        target.parent.mkdir(parents=True)
        target.write_text("public fixture", encoding="utf-8")

        def redirected_lock(path: Path, *args, **kwargs) -> Path:
            if path == lock.parent:
                return Path("\\\\?\\" + str(target.parent))
            return original_resolve(path, *args, **kwargs)

        with patch.object(Path, "resolve", redirected_lock):
            try:
                private_file(project, relative)
            except ValueError as exc:
                require(str(exc) == "prepared_path_redirected", str(exc))
            else:
                raise AssertionError("extended redirected lock path accepted")
        require(target.read_text(encoding="utf-8") == "public fixture",
                "private bytes published to redirected target")
    print("PASS: equivalent Windows extended paths accepted; redirects refused", flush=True)


def main() -> int:
    terminal_worker_admission()
    windows_extended_private_paths()
    governed_continuation()
    abrupt_collection_recovery()
    private_redirect_refused()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
