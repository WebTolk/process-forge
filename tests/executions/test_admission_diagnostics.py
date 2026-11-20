"""Failure facts survive normalization without changing admission semantics."""

import errno
import json
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from contextvars import copy_context

import pytest

from processforge_core import diagnostics as diag
from processforge_core.executions.model import ExecutionError
from processforge_core.runtime import execution_admission as module


@pytest.fixture
def capture():
    records = []
    logger = diag.Logger(sinks=[records.append])
    token = diag._CURRENT.set(logger)
    identity = diag._IDENTITY.set({"request_id": "request", "run_id": "run"})
    try:
        yield records
    finally:
        diag._CURRENT.reset(token)
        diag._IDENTITY.reset(identity)


@pytest.mark.parametrize("phase", ["acquire", "release"])
@pytest.mark.parametrize("kind", ["io", "timeout", "exit"])
def test_normalized_failure_is_correlated_and_sanitized(tmp_path, capture, phase, kind):
    failure = {
        "io": OSError(errno.EBADF, "PRIVATE_LOCK_MESSAGE"),
        "timeout": TimeoutError("PRIVATE_LOCK_MESSAGE"),
        "exit": SystemExit("PRIVATE_LOCK_MESSAGE"),
    }[kind]
    if kind == "exit":
        failure.registry_lock_reason = "contention_timeout"
        failure.registry_lock_phase = "owner"
    calls = []

    @contextmanager
    def lock(path, **options):
        calls.append(options)
        if phase == "acquire":
            raise failure
        yield
        raise failure

    with pytest.raises(ExecutionError) as caught:
        with module.ExecutionAdmission(lock).project(tmp_path):
            assert phase == "release"
    error = caught.value
    assert str(error) == "execution_activity_unknown"
    assert error.__context__ is failure and error.__suppress_context__
    assert len(calls) == 1 and calls[0]["stale_after_seconds"] == 0
    assert 0 < calls[0]["timeout_seconds"] <= 30
    assert len(capture) == 1
    record = capture[0]
    assert record["code"] == "runtime.admission.failed"
    assert record["identity"]["request_id"] == "request"
    clean = record["context"]["exception"]
    assert clean["admission_phase"] == phase
    expected = {
        "io": "lock_io_error",
        "timeout": "timeout",
        "exit": "contention_timeout",
    }
    assert clean["admission_reason"] == expected[kind]
    assert clean["frames"]
    if kind == "exit":
        assert clean["registry_lock_phase"] == "owner"
    if kind == "io":
        assert clean["admission_errno"] == errno.EBADF
    assert "PRIVATE_LOCK_MESSAGE" not in json.dumps(record)
    assert not module._HELD_GATES.get()


@pytest.mark.parametrize(
    "failure",
    [
        OSError("business"),
        TimeoutError("business"),
        SystemExit("business"),
        RuntimeError("business"),
    ],
)
def test_inner_business_error_is_same_object_and_not_lock_failure(
    tmp_path, capture, failure
):
    calls = []

    @contextmanager
    def lock(path, **options):
        calls.append("acquire")
        try:
            yield
        finally:
            calls.append("release")

    with pytest.raises(type(failure)) as caught:
        with module.ExecutionAdmission(lock).project(tmp_path):
            raise failure
    assert caught.value is failure
    assert capture == [] and calls == ["acquire", "release"]


def test_nested_failure_logs_only_after_all_gates_release(tmp_path, monkeypatch):
    events = []

    @contextmanager
    def lock(path, **options):
        if events:
            raise OSError(errno.EPERM, "private inner failure")
        events.append("workplace-acquired")
        try:
            yield
        finally:
            events.append("workplace-released")

    def emit(*args, **kwargs):
        assert not module._HELD_GATES.get()
        events.append("emitted")

    monkeypatch.setattr(diag, "emit", emit)
    with pytest.raises(ExecutionError):
        with module.ExecutionAdmission(lock).maintenance(
            tmp_path, tmp_path / "workplace"
        ):
            pytest.fail("must stay fail-closed")
    assert events == ["workplace-acquired", "workplace-released", "emitted"]


@pytest.mark.parametrize("hostile", [False, True])
def test_optional_sink_cannot_change_failure_or_success(tmp_path, monkeypatch, hostile):
    calls = []

    def unavailable(*args, **kwargs):
        calls.append("emit")
        if hostile:
            raise SystemExit("hostile optional logger")

    @contextmanager
    def lock(path, **options):
        calls.append("acquire")
        if len(calls) == 1:
            raise OSError(errno.EPERM, "private")
        yield

    monkeypatch.setattr(diag, "emit", unavailable)
    admission = module.ExecutionAdmission(lock)
    with pytest.raises(ExecutionError, match="execution_activity_unknown"):
        with admission.project(tmp_path):
            pytest.fail("must stay fail-closed")
    with admission.project(tmp_path):
        result = "original success"
    assert result == "original success"
    assert calls == ["acquire", "emit", "acquire"]


def test_malformed_lock_metadata_does_not_escape_or_change_error(tmp_path, capture):
    class Hostile(OSError):
        @property
        def registry_lock_phase(self):
            raise KeyboardInterrupt()

    failure = Hostile(errno.EBADF, "private")
    failure.registry_lock_reason = {"private": "payload"}

    @contextmanager
    def lock(path, **options):
        raise failure
        yield

    with pytest.raises(ExecutionError, match="execution_activity_unknown"):
        with module.ExecutionAdmission(lock).project(tmp_path):
            pytest.fail("must stay fail-closed")
    clean = capture[0]["context"]["exception"]
    assert clean["admission_reason"] == "lock_io_error"
    assert "registry_lock_phase" not in clean
    assert "payload" not in json.dumps(capture)


def test_real_logger_contains_hostile_sink_failure(tmp_path):
    calls = []

    def sink(record):
        calls.append(record["code"])
        raise KeyboardInterrupt("optional sink")

    @contextmanager
    def lock(path, **options):
        raise OSError(errno.EBADF, "private")
        yield

    logger = diag.Logger(sinks=[sink])
    token = diag._CURRENT.set(logger)
    try:
        with pytest.raises(ExecutionError, match="execution_activity_unknown"):
            with module.ExecutionAdmission(lock).project(tmp_path):
                pytest.fail("must stay fail-closed")
    finally:
        diag._CURRENT.reset(token)
    assert calls == ["runtime.admission.failed"]
    assert logger.health["sink_failures"] == 1


@contextmanager
def failing_lock(*args, **kwargs):
    raise OSError(13, "synthetic private failure")
    yield


def test_sink_reentry_sequential_and_copied_context(tmp_path, monkeypatch):
    calls = []
    contexts = []
    errors = []
    gate = module.ExecutionAdmission(failing_lock)

    def refuse():
        with pytest.raises(ExecutionError) as caught:
            with gate.project(tmp_path):
                pytest.fail("must refuse")
        assert module._PENDING_FAILURE.get() is None
        return caught.value

    def emit(*args, **kwargs):
        assert module._HELD_GATES.get() == ()
        assert module._PENDING_FAILURE.get() is None
        calls.append(kwargs)
        contexts.append(copy_context())
        original = args[2]["exception"]
        errors.append(original)
        nested = refuse()
        assert nested is not original

    monkeypatch.setattr(diag, "emit", emit)
    assert refuse() is errors[0]
    assert len(calls) == 1
    assert refuse() is errors[1]
    assert contexts[0].run(refuse) is errors[2]
    with ThreadPoolExecutor(max_workers=1) as executor:
        assert executor.submit(contexts[1].run, refuse).result(timeout=5) is errors[3]
    assert len(calls) == 4


@pytest.mark.parametrize("failure", [KeyboardInterrupt("sink"), SystemExit("sink")])
def test_emit_baseexception_restores_guard(tmp_path, monkeypatch, failure):
    calls = []

    def emit(*args, **kwargs):
        calls.append(args[2]["exception"])
        raise failure

    monkeypatch.setattr(diag, "emit", emit)
    gate = module.ExecutionAdmission(failing_lock)
    for _ in range(2):
        with pytest.raises(ExecutionError) as caught:
            with gate.project(tmp_path):
                pytest.fail("must refuse")
        assert caught.value is calls[-1]
        assert module._PENDING_FAILURE.get() is None
        assert not module._EMITTING_FAILURE.active
    assert len(calls) == 2


def test_other_thread_emits_while_sink_active(tmp_path, monkeypatch):
    from threading import local

    state = local()
    calls = []
    gate = module.ExecutionAdmission(failing_lock)

    def refuse():
        with pytest.raises(ExecutionError):
            with gate.project(tmp_path):
                pytest.fail("must refuse")

    def emit(*args, **kwargs):
        calls.append(1)
        if not getattr(state, "child", False):
            context = copy_context()

            def child():
                state.child = True
                context.run(refuse)

            with ThreadPoolExecutor(max_workers=1) as executor:
                executor.submit(child).result(timeout=5)

    monkeypatch.setattr(diag, "emit", emit)
    refuse()
    assert len(calls) == 2
