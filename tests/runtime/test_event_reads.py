"""Runtime event summaries retain the allowlist and isolate failed project reads."""

from __future__ import annotations

import json
import math
import os
import sqlite3
from contextlib import closing
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pf_native_control as native
import pytest
from pf_runtime import service
from smoke_runtime_scheduler_failure_isolation import pf

from processforge_core.common.yaml_io import write_yaml_file
from processforge_core.process_event_journal import ProcessEventJournal


def _native_capability_notes(log: Path) -> list[str]:
    """Export bounded typed facts from private stderr, never marked raw text."""
    marker = "PF_NATIVE_CAPABILITY "
    fields: dict[str, dict[str, type]] = {
        "entry_or_platform": {
            "supported_platform": bool,
            "entry_present": bool,
            "publication_present": bool,
        },
        "child_exit": {"returncode": int},
        "job_active_after_wait": {"active": int},
        "job_retired_after_wait": {"active": int},
        "job_retirement_timeout": {},
        "probe_exception": {},
    }
    failure_types = {
        "OSError",
        "FileNotFoundError",
        "PermissionError",
        "NativeControlError",
        "TimeoutExpired",
        "ValueError",
        "AttributeError",
        "SubprocessError",
    }
    try:
        with log.open("rb") as stream:
            stream.seek(0, 2)
            stream.seek(max(0, stream.tell() - 65536))
            raw = stream.read(65536)
    except (OSError, ValueError):
        return []
    notes = []
    for line in raw.decode("utf-8", errors="replace").splitlines():
        if marker not in line or len(line) > 4096:
            continue
        try:
            value = json.loads(line.split(marker, 1)[1])
        except (ValueError, RecursionError):
            continue
        if not isinstance(value, dict):
            continue
        reason = value.get("reason")
        if not isinstance(reason, str) or reason not in fields:
            continue
        if any(
            type(value.get(key)) is not kind
            or (kind is int and not -(2**31) <= value[key] < 2**32)
            for key, kind in fields[reason].items()
        ):
            continue
        if "active" in fields[reason] and value["active"] < 0:
            continue
        clean: dict[str, object] = {
            "reason": reason,
            **{key: value[key] for key in fields[reason]},
        }
        for key in (
            "active",
            "first_active",
            "observations",
            "root_wait_ms",
            "elapsed_ms",
        ):
            number = value.get(key)
            kinds = (int, float) if key.endswith("_ms") else (int,)
            if (
                isinstance(number, (int, float))
                and type(number) in kinds
                and 0 <= number < 2**32
                and math.isfinite(number)
            ):
                clean[key] = number
        failures = value.get("failures")
        if not isinstance(failures, list) or len(failures) > 4:
            continue
        safe_failures = []
        for failure in failures:
            if not isinstance(failure, dict):
                continue
            name = failure.get("type")
            safe: dict[str, object] = {
                "type": name
                if isinstance(name, str) and name in failure_types
                else "other"
            }
            for key in ("errno", "winerror", "native_line"):
                number = failure.get(key)
                if type(number) is int and -(2**31) <= number < 2**32:
                    safe[key] = number
            safe_failures.append(safe)
        clean["failures"] = safe_failures
        notes.append(marker + json.dumps(clean, sort_keys=True))
        if len(notes) == 8:
            break
    return notes


def test_private_stderr_export_filters_forged_records_and_bounds_notes(
    tmp_path: Path,
) -> None:
    log = tmp_path / "stderr"
    marker = "PF_NATIVE_CAPABILITY "
    valid = {
        "reason": "job_active_after_wait",
        "active": 1,
        "private": "private-path-and-token",
        "failures": [
            {
                "type": "PermissionError",
                "errno": 13,
                "native_function": "private-path-and-token",
                "message": "private-path-and-token",
            }
        ],
    }
    invalid = [
        "private-path-and-token",
        json.dumps({"reason": "private-path-and-token", "failures": []}),
        json.dumps({"reason": "job_active_after_wait", "active": True, "failures": []}),
        json.dumps({"reason": "job_active_after_wait", "active": -1, "failures": []}),
        json.dumps({"reason": "job_retired_after_wait", "active": -1, "failures": []}),
        json.dumps({"reason": ["private-path-and-token"], "failures": []}),
        "[" * 1000,
    ]
    log.write_text("\n".join(marker + value for value in invalid), encoding="utf-8")
    assert _native_capability_notes(log) == []
    log.write_text((marker + json.dumps(valid) + "\n") * 1001, encoding="utf-8")
    notes = _native_capability_notes(log)
    assert len(notes) == 8
    assert all("private-path-and-token" not in note for note in notes)
    assert json.loads(notes[0].removeprefix(marker)) == {
        "reason": "job_active_after_wait",
        "active": 1,
        "failures": [{"type": "PermissionError", "errno": 13}],
    }
    log.write_bytes(b"x" * 100000 + b"\n" + (marker + json.dumps(valid)).encode())
    assert len(_native_capability_notes(log)) == 1
    assert _native_capability_notes(tmp_path / "missing") == []
    retired = {
        "reason": "job_retired_after_wait",
        "active": 0,
        "first_active": 1,
        "observations": 3,
        "root_wait_ms": 10.125,
        "elapsed_ms": 30.25,
        "failures": [],
        "private": "private-path-and-token",
    }
    log.write_text(marker + json.dumps(retired), encoding="utf-8")
    exported = json.loads(_native_capability_notes(log)[0].removeprefix(marker))
    assert exported == {
        key: value for key, value in retired.items() if key != "private"
    }


@pytest.mark.parametrize("failure", [ValueError, OSError, RuntimeError])
def test_diagnostic_output_failure_preserves_capability_refusal(
    monkeypatch: pytest.MonkeyPatch, failure: type[Exception]
) -> None:
    def refuse_output(*args: object, **kwargs: object) -> None:
        raise failure("private diagnostic output failure")

    monkeypatch.setattr(native.logging.Logger, "warning", refuse_output)
    # An ordinary import has no executable entry; no authority is fabricated.
    assert native._ENTRY is None
    assert native.supports_owned_execution() is False


@pytest.mark.parametrize("signal", [KeyboardInterrupt, SystemExit])
def test_diagnostic_output_does_not_swallow_process_signals(
    monkeypatch: pytest.MonkeyPatch, signal: type[BaseException]
) -> None:
    def interrupt_output(*args: object, **kwargs: object) -> None:
        raise signal()

    monkeypatch.setattr(native.logging.Logger, "warning", interrupt_output)
    with pytest.raises(signal):
        native._log_owned_execution_refusal("probe_exception")


def test_last_event_isolates_corrupt_project_and_keeps_public_allowlist(
    tmp_path: Path,
) -> None:
    roots = [tmp_path / name for name in ("bad", "good", "absent")]
    for project in roots:
        write_yaml_file(
            project / ".pf/process-forge.yaml", {"project": {"id": project.name}}
        )
    bad = roots[0] / ".pf/runtime/events/events.sqlite3"
    bad.parent.mkdir(parents=True)
    bad.write_bytes(b"corrupt store")
    good = roots[1] / ".pf/runtime/events/events.sqlite3"
    ProcessEventJournal().append(
        good,
        {
            "event_id": "intended",
            "event_type": "fixture.observed",
            "time": "2026-11-16T00:00:00Z",
            "payload": {"private": "must not escape summary"},
        },
    )
    with closing(sqlite3.connect(good)) as connection:
        assert (
            connection.execute("PRAGMA journal_mode=DELETE").fetchone()[0] == "delete"
        )
    before = {
        p: p.read_bytes() for root in roots for p in root.rglob("*") if p.is_file()
    }
    runtime = SimpleNamespace(
        core=SimpleNamespace(project_id=lambda root: root.name),
        workplace_root=None,
        _project_errors={},
    )
    assert service.RuntimeProcess.last_event(
        cast(service.RuntimeProcess, runtime), roots
    ) == {
        "project_id": "good",
        "event_id": "intended",
        "event_type": "fixture.observed",
        "time": "2026-11-16T00:00:00Z",
    }
    assert list(runtime._project_errors) == [str(roots[0])]
    assert "journal_database_error" in runtime._project_errors[str(roots[0])]
    assert {
        p: p.read_bytes() for root in roots for p in root.rglob("*") if p.is_file()
    } == before


def test_fresh_cli_to_runtime_public_status_and_bound_refusal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Use real onboarding and IPC; no native, migration or identity guard patches."""
    # Configure only the native logger in these fixture subprocesses, including
    # the real Runtime child. Normal CLI invocations retain silent successes.
    diagnostic_entry = tmp_path / "diagnostic-entry"
    diagnostic_entry.mkdir()
    (diagnostic_entry / "sitecustomize.py").write_text(
        "import logging\n"
        'logger = logging.getLogger("pf_native_control")\n'
        "logger.setLevel(logging.DEBUG)\n"
        "logger.addHandler(logging.StreamHandler())\n"
        "logger.propagate = False\n",
        encoding="utf-8",
    )
    monkeypatch.setenv(
        "PYTHONPATH",
        os.pathsep.join([str(diagnostic_entry), os.environ.get("PYTHONPATH", "")]),
    )
    workplace = tmp_path / "workplace"
    pf("workplace-init", "--workplace", str(workplace), "--apply")
    projects = [tmp_path / name for name in ("bad-project", "good-project")]
    for project in projects:
        project.mkdir()
        pf(
            "project-onboard",
            "--project-root",
            str(project),
            "--workplace",
            str(workplace),
            "--type",
            "generic-software-project",
            "--apply",
        )
        pf(
            "project-mode",
            "set",
            "--project-root",
            str(project),
            "--workplace",
            str(workplace),
            "--mode",
            "simple",
        )
    pf(
        "runtime-host",
        "init",
        "--workplace",
        str(workplace),
        "--project-root",
        str(projects[0]),
        "--project-root",
        str(projects[1]),
    )
    started = False
    try:
        pf(
            "runtime",
            "start",
            "--workplace",
            str(workplace),
            "--interval",
            "60",
            "--json",
        )
        started = True
        admitted = []
        for project in projects:
            request = tmp_path / (project.name + ".json")
            request.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "event_id": project.name + "-event",
                        "event_type": "fixture.observed",
                        "project_root": str(project),
                        "source": {"adapter": "generic", "agent": "event-read-fixture"},
                        "payload": {"private": "must not escape the event summary"},
                    }
                ),
                encoding="utf-8",
            )
            admitted.append(
                json.loads(
                    pf(
                        "runtime",
                        "event",
                        "--workplace",
                        str(workplace),
                        "--input",
                        str(request),
                        "--json",
                    )
                )
            )
        status = json.loads(
            pf("runtime", "status", "--workplace", str(workplace), "--json")
        )
        assert status["health"] == "ready", status
        log = service.runtime_root(workplace) / "logs/runtime.stderr.log"
        assert any(
            json.loads(note.split("PF_NATIVE_CAPABILITY ", 1)[1])["reason"]
            == "job_retired_after_wait"
            for note in _native_capability_notes(log)
        ), "fixture logger must retain native success observations"
        summary = status["last_event"]
        assert summary["event_id"] == admitted[1]["event_id"]
        assert summary["project_id"] == admitted[1]["project_id"]
        assert set(summary) == {"project_id", "event_id", "event_type", "time"}
        bad = projects[0]
        pin = bad / ".pf/data/storage-identities.json"
        pins = json.loads(pin.read_text(encoding="utf-8"))
        event_slot = next(slot for slot in pins["slots"] if slot["kind"] == "events")
        event_slot["store_id"] = "f" * 32
        pin.write_text(json.dumps(pins), encoding="utf-8")
        journal = bad / ".pf/runtime/events/events.sqlite3"
        before = (journal.read_bytes(), pin.read_bytes())
        refused = json.loads(
            pf("runtime", "status", "--workplace", str(workplace), "--json")
        )
        assert refused["health"] == "degraded", refused
        assert refused["last_event"] == summary
        assert "storage_identity_conflict" in str(refused["project_errors"])
        assert (journal.read_bytes(), pin.read_bytes()) == before
    except AssertionError as error:
        # Runtime stderr is private. Retain only the native probe allowlist in
        # pytest/JUnit, which the existing CI job uploads even after failure.
        log = service.runtime_root(workplace) / "logs/runtime.stderr.log"
        for note in _native_capability_notes(log):
            error.add_note(note)
        raise
    finally:
        if started:
            pf("runtime", "stop", "--workplace", str(workplace), "--timeout", "30")
