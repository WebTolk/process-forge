"""Imported native metadata writers: byte fidelity and handled fault ownership."""

from __future__ import annotations

import hashlib
import json
import os
import sys
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import Any

import codex_exec_worker as worker
import pf_native_control as native
import prepared_executor as executor
import pytest

from processforge_core.maintenance import temporary_disposal as disposal

KINDS = ("input", "exit", "usage", "prepared")
PAYLOAD = {"z": "Строка λ\n", "a": [0, False, None, "é"]}
OBSERVATIONS: list[dict[str, Any]] = []


@dataclass
class Writer:
    kind: str
    target: Path
    invoke: Callable[[], Any]
    expected: bytes
    calls: list[dict[str, Any]]


def physical(text: str) -> bytes:
    """Path.write_text/open('w') use the platform default newline conversion."""
    return text.replace("\n", os.linesep).encode("utf-8")


def state(path: Path) -> tuple[bytes, int, int]:
    info = path.stat()
    return path.read_bytes(), info.st_dev, info.st_ino


@pytest.fixture(params=KINDS)
def writer(
    request: pytest.FixtureRequest, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Writer:
    kind = request.param
    invoke: Callable[[], Any]
    calls: list[dict[str, Any]] = []
    target = tmp_path / "metadata.json"
    if kind == "input":
        # Real imports and real serializer; only private fixture callbacks replace
        # environment discovery/ingestion. No actual PF operation is invoked.
        import processforge as core
        from pf_runtime import host, provider_adapters

        root = tmp_path / "project"
        run_dir = root / ".pf/runtime/agent-runs/run/task"
        run_dir.mkdir(parents=True)
        target = run_dir / "worker-input-contract.json"
        output = root / "report.md"
        for key, value in {
            "PF_PROJECT_ROOT": str(root),
            "PF_RUN_ID": "run",
            "PF_TASK_ID": "task",
            "PF_WORKER_ATTEMPT": "1",
            "PF_AGENT_RUN_DIR": str(run_dir),
        }.items():
            monkeypatch.setenv(key, value)
        monkeypatch.setattr(
            core, "resolve_workplace_root", lambda *a, **k: root / "workplace"
        )

        def ingest(envelope: dict[str, Any], *args: Any) -> dict[str, Any]:
            calls.append(envelope)
            return {"accepted": True, "chat_message_ids": ["fixture-message"]}

        monkeypatch.setattr(host, "ingest_event", ingest)
        text = "private fixture payload λ"
        summary = provider_adapters.worker_input_summary(
            "run",
            "task",
            "1",
            "sha256:" + hashlib.sha256(text.encode()).hexdigest(),
            "report.md",
        )
        data = {
            "schema_version": 1,
            "run_id": "run",
            "task_id": "task",
            "attempt": "1",
            "stdin_payload_hash": "sha256:" + hashlib.sha256(text.encode()).hexdigest(),
            "expected_report": "report.md",
            "summary": summary,
        }
        invoke = partial(worker.capture_worker_input, text, output)
        expected = physical(json.dumps(data, ensure_ascii=False, sort_keys=True) + "\n")
    elif kind == "exit":
        invoke = partial(worker.write_exit_contract, target, 7)
        expected = physical(
            json.dumps(
                {"schema_version": 1, "exit_code": 7, "status": "failed"},
                indent=2,
                ensure_ascii=False,
            )
            + "\n"
        )
    elif kind == "usage":
        capture = worker.ManagedUsageCapture(tmp_path, target, "fixture-model")
        capture.directory = tmp_path
        invoke = partial(capture._write_json, target.name, PAYLOAD)
        expected = physical(json.dumps(PAYLOAD, sort_keys=True) + "\n")
    else:
        invoke = partial(executor._write_json_atomic, target, PAYLOAD)
        expected = physical(
            json.dumps(PAYLOAD, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
        )
    target.write_bytes(b"accepted prior state\r\n")
    return Writer(kind, target, invoke, expected, calls)


class StopPublication(BaseException):
    """Exercise cleanup beyond Exception, without stopping the test process."""


class FaultStream:
    def __init__(self, stream: Any, mode: str, error: BaseException, events: list[str]):
        self.stream, self.mode, self.error, self.events = stream, mode, error, events

    def __enter__(self) -> FaultStream:
        return self

    def __exit__(self, *args: Any) -> None:
        self.stream.close()
        self.events.append("close")
        if self.mode == "close":
            raise self.error

    def write(self, text: str) -> Any:
        self.events.append("write")
        if self.mode in {"write", "base", "short"}:
            count = self.stream.write(text[: min(3, len(text))])
            if self.mode == "short":
                return count if len(text) > 3 else 0
            raise self.error
        count = self.stream.write(text)
        if self.mode == "zero":
            return 0
        return True if self.mode == "bool" else None if self.mode == "none" else count

    def flush(self) -> None:
        self.events.append("flush")
        if self.mode == "flush":
            raise self.error
        self.stream.flush()

    def fileno(self) -> int:
        return self.stream.fileno()


def faults(
    monkeypatch: pytest.MonkeyPatch,
    writer: Writer,
    mode: str,
    error: BaseException,
    events: list[str],
) -> None:
    original_open, original_replace, original_fsync = Path.open, os.replace, os.fsync

    def opened(path: Path, *args: Any, **kwargs: Any) -> Any:
        stream = original_open(path, *args, **kwargs)
        if path.parent == writer.target.parent and path.suffix == ".tmp":
            return FaultStream(stream, mode, error, events)
        return stream

    def replaced(source: Any, destination: Any, *args: Any, **kwargs: Any) -> Any:
        if Path(destination) == writer.target:
            events.append("replace")
            if mode == "replace":
                raise error
        return original_replace(source, destination, *args, **kwargs)

    def synced(fd: int) -> None:
        events.append("fsync")
        if mode == "fsync":
            raise error
        original_fsync(fd)

    monkeypatch.setattr(Path, "open", opened)
    monkeypatch.setattr(os, "replace", replaced)
    monkeypatch.setattr(os, "fsync", synced)


def staging(writer: Writer) -> list[Path]:
    return sorted(writer.target.parent.glob("*.tmp"))


def test_success_bytes_and_order(
    writer: Writer, monkeypatch: pytest.MonkeyPatch
) -> None:
    prior = state(writer.target)
    events: list[str] = []
    faults(monkeypatch, writer, "success", OSError("unused"), events)
    writer.invoke()
    assert writer.target.read_bytes() == writer.expected
    assert state(writer.target)[1:] != prior[1:]
    assert staging(writer) == []
    if writer.kind == "usage":
        assert events == ["write", "flush", "fsync", "close", "replace"]
    else:
        assert events == ["write", "close", "replace"]
    if writer.kind == "input":
        assert len(writer.calls) == 1


@pytest.mark.parametrize(
    "mode",
    [
        "write",
        "base",
        "replace",
        "close",
        "short",
        "bool",
        "none",
        "zero",
        "flush",
        "fsync",
    ],
)
def test_handled_failure(
    writer: Writer, monkeypatch: pytest.MonkeyPatch, mode: str
) -> None:
    if mode in {"flush", "fsync"} and writer.kind != "usage":
        pytest.skip("writer has no explicit flush/fsync operation")
    prior = state(writer.target)
    error = (
        StopPublication("primary base exception")
        if mode == "base"
        else OSError("primary " + mode)
    )
    events: list[str] = []
    faults(monkeypatch, writer, mode, error, events)
    with pytest.raises(BaseException) as caught:
        writer.invoke()
    if mode not in {"short", "bool", "none", "zero"}:
        assert caught.value is error
    else:
        assert str(caught.value) == "short_write"
        assert "replace" not in events
        assert "fsync" not in events
    assert state(writer.target) == prior
    assert staging(writer) == []
    assert not writer.calls


def test_serialization_failure(writer: Writer, monkeypatch: pytest.MonkeyPatch) -> None:
    prior = state(writer.target)
    error = TypeError("serialization fixture failure")

    def fail(*args: Any, **kwargs: Any) -> Any:
        raise error

    monkeypatch.setattr(json, "dumps", fail)
    monkeypatch.setattr(json, "dump", fail)
    with pytest.raises(TypeError) as caught:
        writer.invoke()
    assert caught.value is error
    assert state(writer.target) == prior
    assert staging(writer) == []
    assert not writer.calls


@pytest.mark.parametrize("base", [False, True])
def test_primary_and_cleanup_denial(
    writer: Writer, monkeypatch: pytest.MonkeyPatch, base: bool
) -> None:
    prior = state(writer.target)
    error = StopPublication("primary survives") if base else OSError("primary survives")
    events: list[str] = []
    faults(monkeypatch, writer, "base" if base else "write", error, events)

    def denied(resource: disposal.OwnedTemporary) -> int:
        raise PermissionError(13, "fixture cleanup denied")

    if writer.kind in {"exit", "prepared"}:
        original = native._receipt_handle

        def denied_stage(path: Path, access: int, flags: int) -> Any:
            if path.suffix == ".tmp":
                raise PermissionError(13, "fixture cleanup denied")
            return original(path, access, flags)

        monkeypatch.setattr(native, "_receipt_handle", denied_stage)
    else:
        monkeypatch.setattr(disposal, "_windows_delete", denied)
    with pytest.raises(BaseException) as caught:
        writer.invoke()
    assert caught.value is error
    assert any("cleanup_pending:13" in note for note in getattr(error, "__notes__", ()))
    assert state(writer.target) == prior
    remnants = staging(writer)
    assert len(remnants) == 1
    OBSERVATIONS.append(
        {
            "kind": writer.kind,
            "case": "cleanup_denial",
            "base_exception": base,
            "files": 1,
            "bytes": remnants[0].stat().st_size,
            "primary_identity": True,
            "diagnostic": getattr(error, "__notes__", ()),
        }
    )


def test_cleanup_only_reports_failure(
    writer: Writer, monkeypatch: pytest.MonkeyPatch
) -> None:
    error = PermissionError(13, "fixture cleanup denied")

    def denied(resource: disposal.OwnedTemporary) -> disposal.CleanupReceipt:
        # The real filesystem deletion refusal is tested above. This callback
        # exercises the helper's otherwise unreachable post-replace failure.
        return disposal.CleanupReceipt(
            resource.resource_id, "cleanup_pending", error_code=error.errno
        )

    if writer.kind in {"exit", "prepared"}:
        monkeypatch.setattr(
            native, "_receipt_dispose", lambda *args: "cleanup_pending:13"
        )
    else:
        monkeypatch.setattr(disposal, "dispose_owned", denied)
    cleanup_error = (
        OSError if writer.kind in {"exit", "prepared"} else disposal.CleanupError
    )
    with pytest.raises(cleanup_error, match="cleanup_pending:13"):
        writer.invoke()
    assert writer.target.read_bytes() == writer.expected
    assert staging(writer) == []


def test_foreign_and_nested_publishers(
    writer: Writer, monkeypatch: pytest.MonkeyPatch
) -> None:
    foreign = [
        writer.target.with_name("." + writer.target.name + ".tmp"),
        writer.target.with_suffix(writer.target.suffix + ".tmp"),
        writer.target.with_name("." + writer.target.name + "." + "f" * 32 + ".tmp"),
    ]
    snapshots = {}
    for path in foreign:
        path.write_bytes(b"foreign preserve\x00\xff")
        snapshots[path] = state(path)
    original = os.replace
    paths: list[Path] = []
    nested = False

    def interleaved(source: Any, target: Any, *args: Any, **kwargs: Any) -> Any:
        nonlocal nested
        if Path(target) == writer.target:
            paths.append(Path(source))
            if not nested:
                nested = True
                writer.invoke()
                assert Path(source).exists()
        return original(source, target, *args, **kwargs)

    monkeypatch.setattr(os, "replace", interleaved)
    writer.invoke()
    assert len(paths) == 2 and paths[0] != paths[1]
    assert writer.target.read_bytes() == writer.expected
    assert all(state(path) == snapshot for path, snapshot in snapshots.items())
    assert set(staging(writer)) == set(foreign)


def test_repeat100(writer: Writer, monkeypatch: pytest.MonkeyPatch) -> None:
    rows = []
    for index in range(100):
        prior = state(writer.target)
        mode = ("success", "replace", "write", "base", "short")[index % 5]
        error = (
            StopPublication("bounded base")
            if mode == "base"
            else OSError("bounded " + mode)
        )
        with monkeypatch.context() as local:
            faults(local, writer, mode, error, [])
            if mode == "success":
                writer.invoke()
                assert writer.target.read_bytes() == writer.expected
            else:
                with pytest.raises(BaseException) as caught:
                    writer.invoke()
                assert mode == "short" or caught.value is error
                assert state(writer.target) == prior
        remains = staging(writer)
        rows.append(
            {
                "attempt": index + 1,
                "mode": mode,
                "staging_files": len(remains),
                "staging_bytes": sum(p.stat().st_size for p in remains),
                "destination_sha256": hashlib.sha256(
                    writer.target.read_bytes()
                ).hexdigest(),
                "destination_identity_preserved_on_failure": mode == "success"
                or state(writer.target)[1:] == prior[1:],
            }
        )
        assert remains == []
    OBSERVATIONS.append({"kind": writer.kind, "case": "repeat100", "attempts": rows})


def test_exclusive_uuid_collision(
    writer: Writer, monkeypatch: pytest.MonkeyPatch
) -> None:
    from types import SimpleNamespace

    foreign = writer.target.with_name(
        "." + writer.target.name + "." + "e" * 32 + ".tmp"
    )
    foreign.write_bytes(b"foreign collision must not be opened")
    prior, foreign_prior = state(writer.target), state(foreign)
    monkeypatch.setattr(disposal.uuid, "uuid4", lambda: SimpleNamespace(hex="e" * 32))
    monkeypatch.setattr(native, "uuid4", lambda: SimpleNamespace(hex="e" * 32))
    with pytest.raises(FileExistsError):
        writer.invoke()
    assert state(writer.target) == prior
    assert state(foreign) == foreign_prior
    assert not writer.calls


def test_changed_staging_identity_is_not_deleted(
    writer: Writer, monkeypatch: pytest.MonkeyPatch
) -> None:
    prior = state(writer.target)
    error = OSError("replacement failed after fixture identity change")
    original = os.replace
    moved = writer.target.parent / "owned-stage-retained.bin"
    substituted: list[Path] = []

    def replace_then_fail(source: Any, target: Any, *args: Any, **kwargs: Any) -> Any:
        if Path(target) == writer.target:
            original(source, moved)
            Path(source).write_bytes(b"foreign substituted object")
            substituted.append(Path(source))
            raise error
        return original(source, target, *args, **kwargs)

    monkeypatch.setattr(os, "replace", replace_then_fail)
    with pytest.raises(OSError) as caught:
        writer.invoke()
    assert caught.value is error
    assert any("identity_changed" in note for note in getattr(error, "__notes__", ()))
    assert state(writer.target) == prior
    assert moved.read_bytes() == writer.expected
    assert substituted[0].read_bytes() == b"foreign substituted object"


def test_relative_destination(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    target = Path("relative.json")
    executor._write_json_atomic(target, PAYLOAD)
    assert target.read_bytes() == physical(
        json.dumps(PAYLOAD, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    )
    worker.write_exit_contract(target, 0)
    assert json.loads(target.read_text()) == {
        "schema_version": 1,
        "exit_code": 0,
        "status": "completed",
    }
    capture = worker.ManagedUsageCapture(tmp_path, target, "fixture-model")
    capture.directory = Path(".")
    capture._write_json(target.name, PAYLOAD)
    assert target.read_bytes() == physical(json.dumps(PAYLOAD, sort_keys=True) + "\n")
    assert list(tmp_path.glob("*.tmp")) == []


def test_capture_identity_rejection_is_unchanged(
    writer: Writer, monkeypatch: pytest.MonkeyPatch
) -> None:
    if writer.kind != "input":
        pytest.skip("capture admission applies only to worker input")
    monkeypatch.setenv("PF_AGENT_RUN_DIR", str(writer.target.parent / "foreign"))
    prior = state(writer.target)
    with pytest.raises(SystemExit, match="does not match run/task identity"):
        writer.invoke()
    assert state(writer.target) == prior
    assert staging(writer) == [] and not writer.calls


def test_optional_exit_path_and_empty_serialization(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    worker.write_exit_contract(None, 0)
    target = tmp_path / "empty.json"
    monkeypatch.setattr(json, "dumps", lambda *a, **k: "")
    executor._write_json_atomic(target, {})
    assert target.read_bytes() == physical("\n")


@pytest.fixture(scope="session", autouse=True)
def save_observations() -> Iterator[None]:
    OBSERVATIONS.append(
        {
            "case": "runtime",
            "executable": sys.executable,
            "version": sys.version,
            "platform": sys.platform,
            "pytest_version": pytest.__version__,
            "writer_modules": [worker.__file__, executor.__file__, disposal.__file__],
            "MYPYPATH": os.environ.get("MYPYPATH"),
        }
    )
    yield
    output = os.environ.get("W55_OBSERVATIONS")
    if output:
        Path(output).write_text(
            json.dumps(OBSERVATIONS, indent=2) + "\n", encoding="utf-8"
        )
