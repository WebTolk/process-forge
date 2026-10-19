#!/usr/bin/env python3
"""Scratch observer boundaries, last-report truth and scheduler fault isolation."""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import replace
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import threading
import time
from types import SimpleNamespace
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tools")]
from processforge_core.configuration import PFConfig, TemporaryFilesConfig
from processforge_core.maintenance import temporary_files as temporary
from processforge_core.garage import diagnostics_from_check
from processforge_core.agent_entry.contract import load_contract, block_span
from pf_runtime import host, service
import processforge as core
from processforge_core.project.configuration_inputs import ProjectConfigurationReader


def fixture(base, name):
    root = base / name
    (root / ".pf/tmp").mkdir(parents=True)
    return root


def old_file(path, now, age=7200):
    path.write_bytes(b"retained scratch")
    os.utime(path, (now - age, now - age))


def publish(root, report):
    temporary.write_report(root, report, atomic_writer=service.write_json_atomic)
    return root / ".pf/runtime/maintenance/temporary-files.json"


@contextmanager
def directory_link(path, target):
    if os.name == "nt":
        result = subprocess.run(["cmd", "/c", "mklink", "/J", str(path), str(target)], capture_output=True)
        assert result.returncode == 0, "native junction fixture unavailable"
    else:
        path.symlink_to(target, target_is_directory=True)
    try:
        yield
    finally:
        os.rmdir(path) if os.name == "nt" else path.unlink()


def observation_checks(base):
    root = fixture(base, "observation")
    now, config = time.time(), TemporaryFilesConfig(max_age_hours=1)
    old_file(root / ".pf/tmp/at-threshold", now, 3600)
    old_file(root / ".pf/tmp/recent", now, 3599)
    old_file(root / ".pf/tmp/future", now, -100)
    before = {path.name: (path.read_bytes(), path.stat().st_mtime_ns) for path in (root / ".pf/tmp").iterdir()}
    report = temporary.observe(root, config, now=now)
    assert report["state"] == "notify" and report["candidate_paths"] == ["at-threshold"], report
    assert report["candidate_count_lower_bound"] == 1 and report["files_count_lower_bound"] == 3
    assert report["candidate_bytes_lower_bound"] == len(b"retained scratch")
    assert {path.name: (path.read_bytes(), path.stat().st_mtime_ns) for path in (root / ".pf/tmp").iterdir()} == before
    missing = base / "absent-project"
    assert temporary.observe(missing, config)["state"] == "missing" and not missing.exists()
    with patch.object(temporary, "_directory", side_effect=AssertionError("off touched filesystem")):
        assert temporary.observe(missing, replace(config, mode="off"))["state"] == "off"
    outside = base / "outside"
    outside.mkdir()
    old_file(outside / "outside-file", now)
    outside_before = (outside / "outside-file").read_bytes()
    # Native links at both the observed root and its ancestor must be rejected.
    for target, link in ((outside, root / ".pf/tmp/redirect"), (outside, root / ".pf/tmp"), (outside, root / ".pf")):
        saved = link.with_name(link.name + "-saved")
        restore = link.exists()
        if restore:
            link.rename(saved)
        try:
            with directory_link(link, target):
                observed = temporary.observe(root, config, now=now)
                assert observed["state"] in {"partial", "error"}
                assert all("outside-file" not in path for path in observed["candidate_paths"])
        finally:
            if restore:
                saved.rename(link)
    assert (outside / "outside-file").read_bytes() == outside_before
    # Reparse-tagged regular entries must also be excluded, not just directories.
    assert temporary._linked(SimpleNamespace(st_mode=stat.S_IFREG, st_file_attributes=0x400))
    link = root / ".pf/tmp/file-link"
    try:
        link.symlink_to(outside / "outside-file")
    except OSError:
        print("SKIP: native file symlink unavailable; reparse-attribute boundary checked")
    else:
        try:
            observed = temporary.observe(root, config, now=now)
            assert observed["state"] == "partial" and "file-link" not in observed["candidate_paths"]
        finally:
            link.unlink()
    # Hold an open directory during a replacement attempt.
    directory = root / ".pf/tmp/pinned"
    directory.mkdir()
    with temporary._directory(directory) as descriptor:
        if os.name == "nt":
            try:
                directory.rename(directory.with_name("moved"))
            except PermissionError:
                pass
            else:
                raise AssertionError("Windows directory was replaceable while pinned")
        else:
            directory.rename(directory.with_name("moved"))
            with directory_link(directory, outside):
                with os.scandir(descriptor) as entries:
                    assert list(entries) == []
    with patch.object(temporary.os, "scandir", side_effect=PermissionError("private path")):
        failed = temporary.observe(root, config)
        assert failed["state"] == "error" and "private path" not in json.dumps(failed)
    bounded = fixture(base, "bounded")
    for index in range(25):
        old_file(bounded / f".pf/tmp/{index}", now)
    assert len(temporary.observe(bounded, config)["candidate_paths"]) == 20
    with patch.object(temporary, "MAX_ENTRIES", 10):
        limited = temporary.observe(bounded, config)
        assert limited["state"] == "partial" and limited["entries_observed"] == 10
    with patch.object(temporary.time, "monotonic", side_effect=[0, 1]):
        timed = temporary.observe(bounded, config)
        assert timed["state"] == "partial" and timed["reasons"] == ["time_limit"]
    deep = bounded / ".pf/tmp/deep"
    (deep / "nested").mkdir(parents=True)
    old_file(deep / "nested/hidden", now)
    with patch.object(temporary, "MAX_DEPTH", 0):
        assert "depth_limit" in temporary.observe(bounded, config)["reasons"]
    many = fixture(base, "many")
    for index in range(2001):
        (many / f".pf/tmp/{index}").touch()
    actual_limit = temporary.observe(many, config)
    assert actual_limit["state"] == "partial" and actual_limit["entries_observed"] <= 2000
    assert {"time_limit", "entry_limit"}.intersection(actual_limit["reasons"])
    assert not temporary._valid_candidate("x" * 1025)
    assert not temporary._valid_candidate("😀" * 257)
    return root, config, report


def report_checks(root, config, report):
    path = publish(root, report)
    now = temporary._read_report(root)["timestamp"]
    with patch.object(temporary.os, "scandir", side_effect=AssertionError("status scanned scratch")):
        summary = temporary.last_summary(root, config, now=now + 1)
        assert summary["status"] == "notify" and summary["notification"]
        assert "candidate_paths" not in summary
        assert temporary.last_summary(root, config, now=now + 3600)["status"] == "stale"
        assert not temporary.last_summary(root, config, now=now + 3600)["notification"]
        changed = temporary.last_summary(root, replace(config, max_age_hours=2), now=now)
        assert changed["status"] == "stale" and changed["reason"] == "configuration_changed"
        assert temporary.last_summary(root, config, now=now - 1)["status"] == "unknown"
        assert temporary.last_summary(root, replace(config, mode="off"))["status"] == "off"
    for bad in (b"{", b"x" * 65537, b"[" * 4000):
        path.write_bytes(bad)
        assert temporary.last_summary(root, config)["status"] == "unknown"
    for key, value in (("state", []), ("candidate_paths", ["../private"]), ("files_count_lower_bound", True)):
        broken = dict(report, **{key: value})
        path.write_text(json.dumps(broken), encoding="utf-8")
        assert temporary.last_summary(root, config)["status"] == "unknown"
    partial = dict(report, state="partial", reasons=["entry_limit"])
    publish(root, partial)
    assert temporary.last_summary(root, config)["status"] == "partial"
    publish(root, report)
    resolved = SimpleNamespace(config=PFConfig().with_changes({"runtime.temporary_files.max_age_hours": 1}), errors=())
    with patch.object(ProjectConfigurationReader, "project_configuration", return_value=resolved), \
         patch.object(core, "_project_context_check_result", return_value={"status": "fresh", "fresh": True}), \
         patch.object(temporary.os, "scandir", side_effect=AssertionError("context scanned scratch")):
        check = core.project_context_check_result(root)
        assert check["temporary_files"]["notification"]
        diagnostics = diagnostics_from_check(check, {"status": "ready"})
        assert diagnostics[-1]["code"] == "temporary_files_status" and diagnostics[-1]["severity"] == "warn"
        assert diagnostics[-1]["temporary_files"]["notification"]
    path.unlink()
    assert temporary.last_summary(root, config)["reason"] == "report_missing"
    # File-only context lookup reads missing reports without creating Runtime state.
    missing_root = root.parent / "file-only"
    (missing_root / ".pf").mkdir(parents=True)
    with patch.object(ProjectConfigurationReader, "project_configuration", return_value=resolved), \
         patch.object(temporary.os, "scandir", side_effect=AssertionError("file-only context scanned")):
        assert core.project_temporary_files_summary(missing_root)["reason"] == "report_missing"
    assert not (missing_root / ".pf/runtime").exists()


def runtime_fixture(roots, config):
    runtime = service.RuntimeProcess.__new__(service.RuntimeProcess)
    runtime.workplace_root = roots[0].parent
    runtime.core = SimpleNamespace(now_utc=lambda: "fixture-time", update_stale_agent_presence=lambda _: None)
    runtime._project_configuration = lambda *_: SimpleNamespace(config=config, errors=())
    runtime._temporary_files_last_run, runtime._temporary_files_results = {}, {}
    runtime.state_lock = threading.RLock()
    runtime.state = {"status": "ready"}
    runtime._project_errors = {}
    runtime.known_project_roots = lambda: roots
    runtime.save = Mock()
    runtime.interval, runtime.shutdown_check = 0.25, False
    return runtime


def posix_report_checks(base):
    if os.name == "nt":
        print("SKIP: POSIX descriptor-relative report substitution regressions require POSIX")
        return
    report = temporary._base(TemporaryFilesConfig(), time.time())
    original_directory = temporary._directory
    # Swap each ancestor after opening it, before child mkdir or publication.
    # Exercise the Runtime call so discarding its descriptor is also detected.
    for index, parts in enumerate(((".pf",), (".pf", "runtime"), (".pf", "runtime", "maintenance"))):
        root = fixture(base, f"posix-write-{index}")
        target = root.joinpath(*parts)
        moved = target.with_name(target.name + "-pinned")
        outside = base / f"posix-write-outside-{index}"
        outside.mkdir()
        (outside / "sentinel").write_bytes(b"untouched")
        runtime = runtime_fixture([root], PFConfig())
        swapped = False

        @contextmanager
        def substitute(path, parent=None):
            nonlocal swapped
            with original_directory(path, parent) as descriptor:
                if path == target:
                    target.rename(moved)
                    target.symlink_to(outside, target_is_directory=True)
                    swapped = True
                yield descriptor

        with patch.object(temporary, "_directory", substitute), \
             patch.object(temporary, "observation_age", return_value=None), \
             patch.object(temporary, "observe", return_value=report), \
             patch.object(service, "write_json_atomic", side_effect=AssertionError("POSIX absolute writer used")):
            assert runtime.observe_temporary_files([root]) == {}
        assert swapped
        destination = moved.joinpath(*(".pf", "runtime", "maintenance")[len(parts):], "temporary-files.json")
        assert json.loads(destination.read_bytes()) == report
        assert [p.name for p in destination.parent.iterdir()] == ["temporary-files.json"]
        assert {p.name: p.read_bytes() for p in outside.iterdir()} == {"sentinel": b"untouched"}
        target.unlink()
        moved.rename(target)

    root = fixture(base, "posix-read")
    path = publish(root, report)
    moved = path.parent.with_name("maintenance-pinned")
    outside = base / "posix-read-outside"
    outside.mkdir()
    # A distinct valid report makes an absolute lstat/open mismatch detectable.
    (outside / path.name).write_text(json.dumps(dict(report, state="off")), encoding="utf-8")

    @contextmanager
    def substitute_read(project_root, *, create=False):
        with destination_context(project_root, create=create) as destination:
            path.parent.rename(moved)
            path.parent.symlink_to(outside, target_is_directory=True)
            try:
                yield destination
            finally:
                path.parent.unlink()
                moved.rename(path.parent)

    destination_context = temporary.report_destination
    with patch.object(temporary, "report_destination", substitute_read):
        assert temporary._read_report(root)["state"] == "notify"

    # Failed replace cleans its own staging through the descriptor, even when
    # the absolute destination has been substituted in the meantime.
    original = path.read_bytes()

    def failed_replace(source, destination, *, src_dir_fd, dst_dir_fd):
        assert src_dir_fd == dst_dir_fd and src_dir_fd is not None
        assert "/" not in source and destination == path.name
        path.parent.rename(moved)
        path.parent.symlink_to(outside, target_is_directory=True)
        raise OSError("publication denied")

    try:
        with patch.object(temporary.os, "replace", side_effect=failed_replace):
            try:
                publish(root, dict(report, state="off"))
            except OSError as exc:
                assert str(exc) == "publication denied"
            else:
                raise AssertionError("failed replace was hidden")
        assert (moved / path.name).read_bytes() == original
        assert [p.name for p in moved.iterdir()] == [path.name], "staging leaked from pinned directory"
        assert [p.name for p in outside.iterdir()] == [path.name]
    finally:
        path.parent.unlink()
        moved.rename(path.parent)

    # Both report reads and child directory opens reject links rather than
    # falling back to absolute traversal.
    path.unlink()
    path.symlink_to(outside / path.name)
    assert temporary.last_summary(root, TemporaryFilesConfig())["reason"] == "report_invalid"
    path.unlink()
    maintenance = path.parent
    maintenance.rmdir()
    maintenance.symlink_to(outside, target_is_directory=True)
    try:
        publish(root, report)
    except OSError:
        pass
    else:
        raise AssertionError("linked maintenance directory accepted")


def scheduler_checks(base):
    roots = [fixture(base, "bad-project"), fixture(base, "good-project")]
    config = PFConfig()
    runtime = runtime_fixture(roots, config)
    actual_observe = temporary.observe
    calls = []

    def isolated(root, selected):
        calls.append(root)
        if root == roots[0]:
            raise RuntimeError("private scanner exception")
        return actual_observe(root, selected)

    class SinglePass:
        def __init__(self):
            self.calls = 0

        def wait(self, _):
            self.calls += 1
            return self.calls > 1

    runtime.stop_event = SinglePass()
    with patch.object(temporary, "observe", side_effect=isolated), \
         patch.object(host, "tick_payload", side_effect=[({"projects": []}, 7), ({"projects": []}, 0)]) as tick:
        runtime.scheduler_loop()
        assert tick.call_count == 2 and len(calls) == 2
        assert "status 7" in runtime.state["project_errors"][str(roots[0])]
        assert runtime.state["project_errors"][f"temporary_files:{roots[0]}"] == "temporary_files_observation_failed"
        assert runtime.state["health"] == "degraded"
        runtime.observe_temporary_files(roots)
        assert len(calls) == 2, "observation repeated within an hour"
    assert temporary._read_report(roots[0])["state"] == "error"
    assert "private scanner exception" not in json.dumps(temporary._read_report(roots[0]))
    restarted = runtime_fixture(roots, config)
    with patch.object(temporary, "observe", side_effect=AssertionError("restart repeated recent scan")):
        assert restarted.observe_temporary_files(roots) == {}
        assert all(row["last_result"] == "deferred" for row in restarted._temporary_files_results.values())
    failing = runtime_fixture([fixture(base, "write-error")], config)
    with patch.object(temporary, "write_report", side_effect=OSError("private writer exception")):
        errors = failing.observe_temporary_files(list(failing.known_project_roots()))
    assert list(errors.values()) == ["temporary_files_report_write_failed"]
    invalid = runtime_fixture([fixture(base, "invalid-config")], config)
    invalid._project_configuration = lambda *_: SimpleNamespace(errors=("invalid",))
    with patch.object(temporary, "observe", side_effect=AssertionError("invalid config scanned")):
        assert list(invalid.observe_temporary_files(invalid.known_project_roots()).values()) == ["temporary_files_configuration_invalid"]
    # Expired per-project cadence uses the current effective configuration.
    for project in roots:
        runtime._temporary_files_last_run[project] -= temporary.PERIOD_SECONDS
    runtime._project_configuration = lambda *_: SimpleNamespace(config=config.with_changes({"runtime.temporary_files.mode": "off"}), errors=())
    assert runtime.observe_temporary_files(roots) == {}
    assert all(temporary._read_report(project)["state"] == "off" for project in roots)


def main():
    with tempfile.TemporaryDirectory(dir=os.environ.get("PF_TEST_SCRATCH_ROOT", ROOT / ".pf/tmp")) as raw:
        base = Path(raw).resolve()
        root, config, report = observation_checks(base)
        report_checks(root, config, report)
        posix_report_checks(base)
        scheduler_checks(base)
        contract = load_contract()
        assert block_span(contract.raw, contract) == (0, len(contract.raw))
        assert b"arbitrary agent scratch only" in contract.raw
        assert b"atomic replacement staging" in contract.raw
        for text in (core.GLOBAL_AGENT_SECTION, (ROOT / "templates/global-agents-processforge-section.md").read_text(encoding="utf-8")):
            assert ".pf/tmp/" in text and "atomic replacement staging" in text
    print("PASS: threshold/no deletion, off/missing, native link/junction boundaries and handle pinning, limits, report freshness/config, cheap context, hourly scheduler/restart and fault isolation")


if __name__ == "__main__":
    main()
