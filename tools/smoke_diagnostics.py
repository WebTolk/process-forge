#!/usr/bin/env python3
"""Behavioral privacy/failure/protocol/storage/performance diagnostics regressions."""
from __future__ import annotations

import contextlib
import errno
import io
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock, patch

import processforge as core
from processforge_core import diagnostics as d
from processforge_core.process_execution import ProcessExecutionService

ROOT = Path(__file__).resolve().parents[1]


def config(**kwargs):
    if kwargs.get("profile") in {"diagnostic", "trace"} or kwargs.get("threshold") == "debug":
        kwargs.setdefault("expires_at", datetime.fromtimestamp(time.time() + 600, timezone.utc).isoformat())
    return d.resolve_config(("invocation", kwargs))


def rejected(fn):
    try:
        fn()
    except (ValueError, OSError):
        return
    raise AssertionError("expected rejection")


def levels_config_privacy(root):
    for threshold, number in d.LEVELS.items():
        records = []
        logger = d.Logger(config(threshold=threshold), sinks=[records.append])
        for level, value in d.LEVELS.items():
            logger.log(level, "Hello {name}", {"name": "reader"})
            getattr(logger, level)("Hello {name}", {"name": "reader"})
            expected = 2 * sum(n >= number for n in list(d.LEVELS.values())[:list(d.LEVELS).index(level)+1])
            assert len(records) == expected
            if value >= number:
                assert records[-1]["severity"] == level and records[-1]["python_level"] == value
                assert records[-1]["message"] == "Hello reader"
    rejected(lambda: d.NullLogger().log("unknown", "bad"))
    with patch.object(d, "build_identity", side_effect=AssertionError("unused source identity computed")):
        assert d.identity_for(d.NullLogger(), __file__) is None
    base = {"profile": "quiet", "quota_bytes": 32768, "file_bytes": 16384, "locked": ["sink"], "sink": "none"}
    effective = d.resolve_config(("project", base), ("work", {"profile": "normal"}), ("session", {"threshold": "error"}))
    assert effective["sources"]["threshold"] == "session"
    assert effective["values"]["quota_bytes"] == 32768
    rejected(lambda: d.resolve_config(("project", base), ("invocation", {"sink": "stderr"})))
    rejected(lambda: d.resolve_config(("project", base), ("invocation", {"quota_bytes": 65536})))
    rejected(lambda: d.resolve_config(("project", {"profile": "trace"})))
    for invalid in ({"schema_version": 2}, {"surprise": True}, {"record_bytes": True}, {"components": [3]}):
        rejected(lambda: d.resolve_config(("project", invalid)))
    records = []
    logger = d.Logger(config(profile="trace", detail_records=2), sinks=[records.append])
    logger.debug("a"); logger.debug("b"); logger.debug("c"); logger.error("serious")
    assert [r["message"] for r in records] == ["a", "b", "serious"]
    assert logger.effective()["detail_expired"]
    logger = d.Logger(config(profile="trace", expires_at="2020-01-01T00:00:00Z"), sinks=[records.append])
    assert not logger.enabled("debug") and logger.enabled("error")
    records.clear()
    logger = d.Logger(config(components=["search"]), sinks=[records.append])
    logger.error("excluded", component="mcp"); logger.warning("included", component="search")
    assert len(records) == 1

    class Hostile:
        def __str__(self):
            raise AssertionError("unsafe str invoked")
        __repr__ = __str__
    secrets = ["synthetic-password-98", "synthetic-token-76", "synthetic-cookie-54"]
    records, stderr = [], io.StringIO()
    sink = d.JsonlSink(root / "privacy", d.DEFAULTS)
    logger = d.Logger(config(profile="trace"), sinks=[records.append, d.stderr_sink, sink])
    cycle = {}; cycle["self"] = cycle
    with contextlib.redirect_stderr(stderr):
        with d.operation(logger, "mcp", "privacy", request_id="req-secret", session_id=None):
            logger.error("{password} failed {message}", {"password": secrets[0], "token": secrets[1], "cookie": secrets[2],
                         "message": "=".join(("password", secrets[0])), "exception": ValueError("Bearer " + secrets[1]),
                         "prompt": "private prompt", "raw_payload": "private payload", "cycle": cycle, "object": Hostile()})
            logger.info("alias privacy", {"prompt_text": "private prompt alias", "environment_variables": "private environment alias",
                                          "rawPayloadBody": "private payload alias", "envVars": "private camel environment"})
            with d.span("branch", {"headers": {"Authorization": secrets[1]}}):
                pass
    rendered = json.dumps(records) + stderr.getvalue() + (root / "privacy/diagnostics.jsonl").read_text(encoding="utf-8")
    assert all(secret not in rendered for secret in secrets), rendered
    assert "private prompt" not in rendered and "private payload" not in rendered
    assert "private environment alias" not in rendered and "private camel environment" not in rendered
    assert "<Hostile>" in rendered and "<truncated>" in rendered
    assert all(r["identity"]["session_id"] is None for r in records)
    assert all(len(d.encode(r)) <= 16384 for r in records)
    with contextlib.redirect_stderr(stderr):
        logger.info("large", {str(i): "x" * 10000 for i in range(100)})
    assert len(d.encode(records[-1])) <= 16384 and records[-1]["truncated"]
    # A failing lazy context and failed serializer cannot change the operation.
    with contextlib.redirect_stderr(io.StringIO()):
        logger.error("bad-context", lambda: 1/0)
        with patch.object(d, "encode", side_effect=ValueError("broken serializer")):
            logger.error("bad-serializer")
    assert logger.health["serialization_failures"] == 2
    with patch.dict(os.environ, {"PF_DIAGNOSTICS": "{invalid"}):
        with contextlib.redirect_stderr(io.StringIO()):
            fallback = d.for_project(root)
        assert fallback.config["errors"] and fallback.values["profile"] == "off"
    with patch.object(Path, "is_dir", side_effect=PermissionError("diagnostic setup denied")), contextlib.redirect_stderr(io.StringIO()):
        assert d.for_project(root) is d.NULL


def failure_correlation_journal(root):
    for error in (OSError(errno.ENOSPC, "full"), PermissionError("read-only")):
        def broken(record):
            raise error
        logger = d.Logger(config(), sinks=[broken])
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            with d.operation(logger, "test", "preserve"):
                logger.error("one"); logger.error("two")
            try:
                with d.operation(logger, "test", "original"):
                    raise LookupError("original business error")
            except LookupError as caught:
                assert str(caught) == "original business error"
        assert logger.health["sink_failures"] >= 3
        assert stderr.getvalue().count("diagnostic_delivery_failed") == 1
    # Same process event/evidence across every profile, using the actual durable writer.
    events, detail_counts = [], []
    service = ProcessExecutionService(root, root, core)
    for profile in d.PROFILES:
        records = []
        logger = d.Logger(config(profile=profile), sinks=[records.append])
        with d.operation(logger, "work", "scenario", request_id=profile):
            service._emit("stage.completed", {"id": "fixed-run", "process": "fixture"}, {"id": "fixed-assignment"}, "verify", outcome="completed", event_id="profile-" + profile)
            logger.debug("details")
            with d.span("evidence-check"):
                pass
        detail_counts.append(len(records))
    path, _ = core.event_runtime_paths(root)
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    for row in rows:
        events.append({key: row[key] for key in ("event_type", "data", "process", "assignment")})
    assert len(events) == 5 and all(item == events[0] for item in events)
    assert detail_counts[0] == detail_counts[-1] == 0 and detail_counts[3] > detail_counts[2] > detail_counts[1]
    # Required journal failures still propagate under off.
    with patch.object(core, "emit_process_event", side_effect=OSError("required journal unavailable")):
        with d.operation(d.NullLogger(), "work", "required"):
            rejected(lambda: service._emit("stage.completed", {}, {}, "verify", outcome="completed"))
    records, barrier = [], threading.Barrier(2)
    logger = d.Logger(config(), sinks=[records.append])
    def one(identity):
        with d.operation(logger, "mcp", "parallel", request_id="req-"+identity, session_id=identity, run_id="run-"+identity):
            barrier.wait(timeout=5)
            for _ in range(20):
                logger.info("concurrent", {"expected": identity})
    with ThreadPoolExecutor(2) as pool:
        list(pool.map(one, ["A", "B"]))
    for record in records:
        if record["message"] == "concurrent":
            expected = record["context"]["expected"]
            assert record["identity"]["session_id"] == expected
            assert record["identity"]["run_id"] == "run-"+expected
    assert d.current() is d.NULL
    # Exact Work/session preferences are applied only after application selection.
    settings_path = root / ".pf/diagnostics.json"
    settings_path.write_text(json.dumps({"schema_version": 1, "profile": "off", "work": {"chosen": {"profile": "quiet"}},
                                         "sessions": {"bound": {"threshold": "error"}}}), encoding="utf-8")
    scoped = d.for_project(root, session_id="bound")
    with d.operation(scoped, "work", "selection", session_id="bound"):
        d.select_work(root, "chosen", "assignment")
        assert d.current().values["profile"] == "quiet" and d.current().values["threshold"] == "error"
        assert d.current().config["sources"]["profile"] == "work"
        assert d.current().config["sources"]["threshold"] == "session"
    settings_path.unlink()


def protocol(root):
    script = f'''import sys;sys.path.insert(0,{str(ROOT / "tools")!r});from pf_runtime import codex_hooks as h
def fail(payload): raise OSError("token=synthetic-hook-token")
h.dispatch=fail
raise SystemExit(h.main())
'''
    for debug in ("0", "1"):
        for hook in ("Stop", "SubagentStop", "SessionStart"):
            result = subprocess.run([sys.executable, "-B", "-c", script], cwd=root, input=json.dumps({"hook_event_name": hook}),
                                    env={**os.environ, "PF_CODEX_HOOK_DEBUG": debug}, text=True, capture_output=True, timeout=20)
            assert result.returncode == 0
            assert result.stdout.strip() == ("{}" if hook in {"Stop", "SubagentStop"} else ""), result
            assert "synthetic-hook-token" not in result.stderr
        result = subprocess.run([sys.executable, "-B", str(ROOT / "tools/pf_runtime/codex_hooks.py")], cwd=root, input="{bad-json",
                                env={**os.environ, "PF_CODEX_HOOK_DEBUG": debug}, text=True, capture_output=True, timeout=20)
        assert result.stdout == "" and result.returncode == 0
    policy = root / ".pf/diagnostics.json"
    policy.write_text(json.dumps({"schema_version": 1, "sink": "jsonl", "locked": ["sink"]}), encoding="utf-8")
    locked = subprocess.run([sys.executable, "-B", "-c", script], cwd=root,
                            input=json.dumps({"hook_event_name": "Stop", "cwd": str(root)}),
                            env={**os.environ, "PF_CODEX_HOOK_DEBUG": "1"}, text=True, capture_output=True, timeout=20)
    assert locked.stdout.strip() == "{}" and "hook.dispatch" not in locked.stderr
    assert "diagnostics_config_invalid" in locked.stderr and "synthetic-hook-token" not in locked.stderr
    policy.unlink()
    # Real source CLI and MCP failure paths share concrete freshness reasons.
    workplace = root / "workplace"
    workplace.mkdir()
    (workplace / "workplace.yaml").write_text("schema_version: 1\nid: fixture\n", encoding="utf-8")
    checks, counts = [], {}
    for profile in d.PROFILES:
        settings = {"profile": profile, "sink": "stderr"}
        if profile in {"diagnostic", "trace"}:
            settings["expires_at"] = datetime.fromtimestamp(time.time() + 600, timezone.utc).isoformat()
        env = {**os.environ, "PF_DIAGNOSTICS": json.dumps(settings)}
        cli = subprocess.run([sys.executable, "-B", "tools/processforge.py", "project-context-check", "--project-root", str(root), "--json"],
                             cwd=ROOT, env=env, text=True, capture_output=True, timeout=30)
        checks.append(json.loads(cli.stdout))
        cli_rows = [json.loads(line) for line in cli.stderr.splitlines()]
        request = {"jsonrpc": "2.0", "id": "wire-"+profile, "method": "tools/call", "params": {"name": "pf.search", "arguments": {"project_root": str(root), "query": "needle"}}}
        wire = subprocess.run([sys.executable, "-B", "tools/pf_runtime/mcp_server.py", "--workplace", str(workplace)],
                              input=json.dumps(request)+"\n", cwd=ROOT, env=env, text=True, capture_output=True, timeout=30)
        response = json.loads(wire.stdout)
        assert response["id"] == "wire-"+profile and response["result"]["isError"], response
        assert "snapshot_not_fresh" in response["result"]["content"][0]["text"]
        rows = [json.loads(line) for line in wire.stderr.splitlines()]
        counts[profile] = len(rows)
        if profile != "off":
            freshness = next(row for row in rows if row["code"] == "context.freshness")
            assert freshness["identity"]["request_id"] == "wire-"+profile
            assert freshness["identity"]["session_id"] is None
            assert freshness["context"]["status"] == "broken"
            assert freshness["context"]["broken_refs"] == [{"reason": "project context snapshot missing"}]
            assert any(row["code"] == "context.freshness" for row in cli_rows)
        else:
            assert not rows and not cli_rows
    assert all(check == checks[0] for check in checks)
    assert counts["trace"] > counts["diagnostic"] > counts["normal"] > counts["quiet"] > counts["off"], counts


def storage_export_performance(root):
    limits = config(record_bytes=2048, file_bytes=8192, quota_bytes=16384, files=2)
    logger = d.Logger(limits, root=root / ".pf/runtime/diagnostics")
    start = time.perf_counter()
    for i in range(10000):
        logger.info("load", {"index": i, "safe": "x" * 200})
    elapsed = time.perf_counter() - start
    files = [p for p in d.log_files(root / ".pf/runtime/diagnostics") if p.exists()]
    assert len(files) <= 2 and sum(p.stat().st_size for p in files) <= 16384
    assert logger.health["sink_failures"] == 0, logger.health
    assert elapsed <= 20, ("jsonl budget", elapsed)
    for path in files:
        for line in path.read_text(encoding="utf-8").splitlines():
            assert json.loads(line)["severity"] == "info" and len(line.encode()) < 2048
    with d.operation(logger, "context", "read", request_id="export-request", run_id="export-work"):
        logger.warning("context.freshness", {"status": "stale", "reason": "source changed", "path": str(root / "private"), "password": "synthetic-export-secret"})
    output = root / "bundle.json"
    original = {p: p.read_bytes() for p in files}
    result = d.export_bundle(root, output, request_id="export-request", run_id="export-work", metadata={"snapshot_id": "fixture", "path": str(root)})
    bundle = json.loads(output.read_text(encoding="utf-8"))
    assert result["records"] >= 1 and bundle["manifest"] and bundle["read_only"]
    assert str(root) not in output.read_text(encoding="utf-8") and "synthetic-export-secret" not in output.read_text(encoding="utf-8")
    assert all(record["identity"]["request_id"] == "export-request" for record in bundle["records"])
    assert all(path.read_bytes() == data for path, data in original.items())
    rejected(lambda: d.export_bundle(root, output))
    # Numeric wire request IDs can be selected through a string CLI argument.
    with d.operation(logger, "mcp", "numeric", request_id=42):
        logger.info("numeric event", {"path": str(root / "private directory" / "file.txt")})
    numeric_output = root / "numeric.json"
    assert d.export_bundle(root, numeric_output, request_id="42")["records"] >= 1
    assert "private directory" not in numeric_output.read_text(encoding="utf-8")
    # Retention is enforced during idle export, without deleting or touching inputs.
    log_root = root / ".pf/runtime/diagnostics"
    old_path = log_root / "diagnostics.7.jsonl"
    old_record = {"timestamp": "2020-01-01T00:00:00Z", "identity": {"request_id": "expired"}, "context": {"value": "expired-record-private"}}
    old_path.write_bytes(d.encode(old_record))
    old_bytes = old_path.read_bytes()
    expired_output = root / "expired.json"
    d.export_bundle(root, expired_output)
    assert "expired-record-private" not in expired_output.read_text(encoding="utf-8")
    assert json.loads(expired_output.read_text(encoding="utf-8"))["expired_records"] == 1
    assert old_path.read_bytes() == old_bytes
    # Expired retention and lock/sink failure remain bounded.
    for path in files:
        if path.exists(): os.utime(path, (1, 1))
    logger.info("after-retention")
    assert sum(p.stat().st_size for p in d.log_files(root / ".pf/runtime/diagnostics") if p.exists()) < 2048
    with patch.object(d, "_file_lock", side_effect=OSError("lock unavailable")), contextlib.redirect_stderr(io.StringIO()):
        logger.error("lock-failure")
    assert logger.health["sink_failures"] == 1
    no_op = d.NullLogger()
    calls = []
    def expensive(): calls.append(1); return {}
    trials = []
    for _ in range(3):
        start = time.perf_counter()
        for _ in range(100000): no_op.debug("disabled", expensive)
        trials.append(time.perf_counter() - start)
    disabled = statistics.median(trials)
    assert not calls and disabled <= 0.5, ("disabled budget", trials)
    memory_logger = d.Logger(config(), sinks=[lambda record: None])
    start = time.perf_counter()
    for _ in range(10000): memory_logger.info("enabled", {"status": "ok"})
    memory_seconds = time.perf_counter() - start
    assert memory_seconds <= 5, memory_seconds
    return {"disabled_100000_seconds_median": disabled, "memory_10000_seconds": memory_seconds, "jsonl_10000_seconds": elapsed,
            "max_storage_bytes": 16384, "rotated_files": len(files), "bundle_records": result["records"]}


def multiprocess_storage(root):
    target = root / "concurrent-storage"
    script = f'''import sys,json;sys.path.insert(0,{str(ROOT / "src")!r})
from pathlib import Path
from processforge_core import diagnostics as d
logger=d.Logger(d.resolve_config(("test",dict(record_bytes=2048,file_bytes=8192,quota_bytes=16384,files=2))),root=Path(sys.argv[1]))
with d.operation(logger,"mcp","writer",request_id=sys.argv[2],session_id=sys.argv[2]):
    for i in range(100): logger.info("parallel",{{"index":i}})
print(json.dumps(logger.health))
'''
    workers = [subprocess.Popen([sys.executable, "-B", "-c", script, str(target), name], cwd=root,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for name in ("A", "B")]
    for worker in workers:
        stdout, stderr = worker.communicate(timeout=30)
        assert worker.returncode == 0 and not stderr, (stdout, stderr)
        assert json.loads(stdout)["sink_failures"] == 0
    files = [p for p in d.log_files(target) if p.exists()]
    assert len(files) <= 2 and sum(p.stat().st_size for p in files) <= 16384
    for path in files:
        for line in path.read_text(encoding="utf-8").splitlines():
            record = json.loads(line)
            assert record["identity"]["request_id"] == record["identity"]["session_id"]


def lock_admission_controls(root):
    """Deterministic budgets/unwind plus real same-root thread serialization."""
    root.mkdir(parents=True, exist_ok=True)
    if os.name != "nt":
        with patch.object(d, "_windows_mutex_api", side_effect=AssertionError("Windows API on POSIX")):
            with d._file_lock(root):
                pass
        return {"posix_file_lock": "passed", "windows": "not_applicable"}

    import ctypes
    from ctypes import wintypes
    import msvcrt

    native = d._windows_mutex_api()
    assert native.CreateMutexW.restype is wintypes.HANDLE
    assert native.CreateMutexW.argtypes == [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
    assert native.WaitForSingleObject.argtypes == [wintypes.HANDLE, wintypes.DWORD]
    assert native.WaitForSingleObject.restype is wintypes.DWORD
    for fn in (native.ReleaseMutex, native.CloseHandle):
        assert fn.argtypes == [wintypes.HANDLE] and fn.restype is wintypes.BOOL

    cases = ("success", "abandoned", "create-null", "create-error", "create-late",
             "wait-timeout", "wait-failed", "wait-unexpected", "wait-error", "wait-late",
             "abandoned-late", "release-failed", "release-error", "close-failed", "close-error",
             "body-error", "thread-timeout", "thread-late", "setup-late", "open-error",
             "byte-late", "byte-timeout", "unlock-error", "shared-budget", "sleep-cap", "sleep-late",
             "file-close-error", "gate-release-error", "combined-errors", "lock-link-after-wait")
    receipts = []
    for case in cases:
        clock, sleeps, entered = [0.0], [], []
        api = SimpleNamespace(CreateMutexW=Mock(return_value=0x123456789AB),
            WaitForSingleObject=Mock(return_value=0), ReleaseMutex=Mock(return_value=True),
            CloseHandle=Mock(return_value=True))
        gate = SimpleNamespace(acquire=Mock(return_value=True), release=Mock())
        byte = Mock()
        original_open = Path.open

        def advance(seconds):
            clock[0] += seconds

        def acquire(**kwargs):
            assert 0 < kwargs["timeout"] <= 0.05
            advance(0.051 if case == "thread-late" else 0.02 if case == "shared-budget" else 0.047 if case == "sleep-cap" else 0)
            return case != "thread-timeout"

        def create(*args):
            assert args[:2] == (None, False)
            if case == "create-error": raise OSError("create failure")
            if case == "create-late": advance(0.051)
            return None if case == "create-null" else 0x123456789AB

        def wait(handle, milliseconds):
            assert handle == 0x123456789AB and 0 <= milliseconds <= (0.05 - clock[0]) * 1000
            if case == "wait-error": raise OSError("wait failure")
            if case in {"wait-late", "abandoned-late"}: advance(0.051)
            if case == "shared-budget": advance(0.02)
            return {"abandoned": 0x80, "abandoned-late": 0x80, "wait-timeout": 0x102,
                    "wait-failed": 0xFFFFFFFF, "wait-unexpected": 0x81}.get(case, 0)

        def locking(fd, mode, size):
            assert size == 1
            if mode == msvcrt.LK_NBLCK:
                if case == "byte-late": advance(0.051)
                if case in {"byte-timeout", "sleep-cap", "sleep-late"} or (case == "shared-budget" and byte.call_count == 1):
                    raise PermissionError(errno.EACCES, "legacy byte busy")
            elif case == "unlock-error":
                raise OSError("byte unlock failure")

        def sleep(seconds):
            assert 0 < seconds <= min(0.005, 0.05 - clock[0])
            sleeps.append(seconds)
            advance(0.06 if case == "sleep-late" else seconds)

        def opening(path, *args, **kwargs):
            if case == "open-error": raise PermissionError("lock open denied")
            handle = original_open(path, *args, **kwargs)
            if case == "setup-late": advance(0.051)
            if case == "file-close-error":
                class ClosingFile:
                    def __enter__(self): return handle
                    def __exit__(self, *exc):
                        handle.close()
                        raise OSError("file close failure")
                return ClosingFile()
            return handle

        gate.acquire.side_effect = acquire
        api.CreateMutexW.side_effect, api.WaitForSingleObject.side_effect = create, wait
        byte.side_effect = locking
        for label, fn in (("release", api.ReleaseMutex), ("close", api.CloseHandle)):
            if case == label + "-failed": fn.return_value = False
            if case in {label + "-error", "combined-errors"}: fn.side_effect = OSError(label + " failure")
        if case == "gate-release-error": gate.release.side_effect = OSError("thread gate release failure")
        caught, chain = None, []
        with patch.object(d, "time", SimpleNamespace(monotonic=lambda: clock[0], sleep=sleep)), \
                patch.object(d, "_IO_LOCK", gate), patch.object(d, "_windows_mutex_api", return_value=api), \
                patch.object(msvcrt, "locking", byte), patch.object(Path, "open", opening), \
                patch.object(ctypes, "get_last_error", return_value=5), \
                patch.object(Path, "is_symlink", side_effect=[False, case == "lock-link-after-wait"]):
            try:
                with d._file_lock(root):
                    entered.append(True)
                    assert clock[0] < 0.05
                    if case in {"body-error", "combined-errors"}: raise LookupError("body failure")
            except (OSError, LookupError) as error:
                caught = type(error).__name__
                if case in {"create-null", "wait-failed", "release-failed", "close-failed"}:
                    assert error.winerror == 5
                while error is not None:
                    chain.append(str(error))
                    error = error.__context__
        body_cases = {"success", "abandoned", "release-failed", "release-error", "close-failed",
                      "close-error", "body-error", "unlock-error", "shared-budget", "file-close-error",
                      "gate-release-error", "combined-errors"}
        assert bool(entered) == (case in body_cases), (case, entered, caught)
        assert (caught is None) == (case in {"success", "abandoned", "shared-budget"}), (case, caught)
        assert gate.release.call_count == (case != "thread-timeout"), case
        created = case not in {"thread-timeout", "thread-late", "create-null", "create-error"}
        assert api.CloseHandle.call_count == int(created), case
        owned = created and case not in {"create-late", "wait-timeout", "wait-failed", "wait-unexpected", "wait-error"}
        assert api.ReleaseMutex.call_count == int(owned), case
        if case in {"byte-late", "unlock-error"}:
            assert byte.call_args.args[1] == msvcrt.LK_UNLCK
        if case in {"sleep-cap", "sleep-late"}:
            assert byte.call_count == 1 and len(sleeps) == 1
        if case == "sleep-cap": assert sleeps[0] < 0.005
        if case == "shared-budget":
            assert api.WaitForSingleObject.call_args.args[1] <= 30 and clock[0] == 0.045
        if case == "combined-errors":
            assert chain == ["close failure", "release failure", "body failure"], chain
        receipts.append({"case": case, "error": caught, "body_entered": bool(entered),
                         "api_counts": {key: getattr(api, key).call_count for key in vars(api)}})

    # Refuse links before the thread gate or any new native side effect.
    with patch.object(Path, "is_symlink", return_value=True), \
            patch.object(d, "_windows_mutex_api") as api_factory, patch.object(d, "_IO_LOCK") as gate:
        rejected(lambda: d._file_lock(root).__enter__())
        rejected(lambda: d.JsonlSink(root, d.DEFAULTS)({"timestamp": d.utc()}))
        api_factory.assert_not_called()
        gate.acquire.assert_not_called()

    child = root / "child"
    child.mkdir(exist_ok=True)
    name = d._windows_admission_name(root)
    assert name.startswith("Local\\ProcessForge.Diagnostics.") and str(root) not in name
    with patch.object(Path, "resolve", side_effect=AssertionError("admission name resolved the filesystem")):
        assert name == d._windows_admission_name(child / "..")
    assert name == d._windows_admission_name(child / "..")
    assert name == d._windows_admission_name(Path(str(root).swapcase()))
    other = root / "other"
    other.mkdir(exist_ok=True)
    assert name != d._windows_admission_name(other)
    @contextlib.contextmanager
    def held_by_peer(lock_factory):
        ready, release, errors = threading.Event(), threading.Event(), []
        def hold():
            try:
                # The admission budget starts in the requesting thread, not
                # before the OS has scheduled that thread's startup.
                with lock_factory():
                    ready.set()
                    assert release.wait(5)
            except BaseException as error:
                errors.append(type(error).__name__)
        holder = threading.Thread(target=hold)
        holder.start()
        try:
            assert ready.wait(5), errors
            yield
        finally:
            release.set()
            holder.join(5)
        assert not holder.is_alive() and not errors, errors

    # Another thread's held root gate must not block this root's admission.
    with held_by_peer(lambda: d._windows_admission(other, time.monotonic() + 0.05)):
        with d._file_lock(root):
            pass
    with held_by_peer(lambda: d._IO_LOCK), patch.object(d, "_windows_mutex_api") as api_factory:
        rejected(lambda: d._file_lock(root).__enter__())
        api_factory.assert_not_called()

    posix = SimpleNamespace(flock=Mock(), LOCK_EX=1, LOCK_NB=2, LOCK_UN=4)
    with patch.object(d, "os", SimpleNamespace(name="posix")), patch.dict(sys.modules, {"fcntl": posix}), \
            patch.object(d, "_windows_mutex_api", side_effect=AssertionError("Windows API on POSIX")):
        with d._file_lock(root):
            pass
    assert [call.args[1] for call in posix.flock.call_args_list] == [3, 4]

    barrier, active, overlaps, waits = threading.Barrier(2), [0], [], []
    observe = threading.Lock()
    actual_lock = d._file_lock
    @contextlib.contextmanager
    def observed_lock(target):
        start = time.perf_counter()
        with actual_lock(target):
            waits.append((time.perf_counter() - start) * 1000)
            with observe:
                if active[0]: overlaps.append(True)
                active[0] += 1
            try:
                yield
            finally:
                with observe: active[0] -= 1

    target = root / "threads"
    limits = config(record_bytes=2048, file_bytes=8192, quota_bytes=16384, files=2)
    def writer(identity):
        logger = d.Logger(limits, root=target)
        barrier.wait(5)
        with d.operation(logger, "test", "threads", request_id=identity, session_id=identity):
            for i in range(20): logger.info("thread", {"index": i})
        return logger.health
    with patch.object(d, "_file_lock", observed_lock), ThreadPoolExecutor(2) as pool:
        health = list(pool.map(writer, ["A", "B"]))
    assert not overlaps and len(waits) == 42 and all(h["sink_failures"] == h["dropped"] == 0 for h in health), health
    files = [path for path in d.log_files(target) if path.exists()]
    assert len(files) <= 2 and sum(path.stat().st_size for path in files) <= 16384
    for path in files:
        for line in path.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            assert row["identity"]["request_id"] == row["identity"]["session_id"]
    (root / "mock-receipts.json").write_text(json.dumps(receipts, indent=2), encoding="utf-8")
    return {"mock_cases": len(receipts), "aliases_and_root_isolation": "passed", "thread_gate_timeout": "passed", "posix_dispatch_mock": "passed",
            "same_root_threads": health, "body_overlaps": len(overlaps), "max_wait_ms": max(waits)}


def _admission_worker():
    """Isolated peer: real new lock or the original legacy byte-lock algorithm."""
    target, identity, mode = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
    counts = dict(create=0, wait=0, release=0, close=0, timeout=0, abandoned=0, failed=0)
    events, active = [], []
    original_open = Path.open

    @contextlib.contextmanager
    def observed_open(path, mode="r", *args, **kwargs):
        with original_open(path, mode, *args, **kwargs) as handle:
            if mode != "ab" or path.name != "diagnostics.jsonl":
                yield handle
                return
            # Observe the real append, including its byte count, before rotation
            # can retire the record. A returned sink call alone is not proof.
            def write(data):
                size = handle.write(data)
                assert size == len(data)
                row = json.loads(data)
                assert row["identity"]["request_id"] == row["identity"]["session_id"] == identity
                assert "written_bytes" not in active[0]
                active[0]["written_bytes"] = size
                return size
            yield SimpleNamespace(write=write)
    if mode == "legacy":
        @contextlib.contextmanager
        def legacy_lock(root):
            path = root / ".diagnostics.lock"
            if path.is_symlink():
                raise OSError("diagnostic lock symlink")
            with d._IO_LOCK, path.open("a+b") as handle:
                if handle.tell() == 0:
                    handle.write(b"0")
                    handle.flush()
                deadline = time.monotonic() + 0.05
                while True:
                    try:
                        handle.seek(0)
                        import msvcrt
                        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                        break
                    except OSError:
                        if time.monotonic() >= deadline:
                            raise
                        time.sleep(0.005)
                try:
                    yield
                finally:
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        selected_lock = legacy_lock
    else:
        selected_lock = d._file_lock
        api = d._windows_mutex_api()
        def call(key, fn):
            def observed(*args):
                counts[key] += 1
                result = fn(*args)
                if key == "wait":
                    if result == 0x102: counts["timeout"] += 1
                    if result == 0x80: counts["abandoned"] += 1
                    if result == 0xFFFFFFFF: counts["failed"] += 1
                elif not result:
                    counts["failed"] += 1
                return result
            return observed
        observed_api = SimpleNamespace(CreateMutexW=call("create", api.CreateMutexW),
            WaitForSingleObject=call("wait", api.WaitForSingleObject),
            ReleaseMutex=call("release", api.ReleaseMutex), CloseHandle=call("close", api.CloseHandle))
        d._windows_mutex_api = lambda: observed_api

    @contextlib.contextmanager
    def observed_lock(root):
        event = {"entry": time.perf_counter_ns()}
        active.append(event)
        try:
            with selected_lock(root):
                event["grant"] = time.perf_counter_ns()
                try:
                    yield
                    event["body_completed"] = time.perf_counter_ns()
                finally:
                    event["release_start"] = time.perf_counter_ns()
        except BaseException as error:
            event["error"] = type(error).__name__
            event["errno"] = getattr(error, "errno", None)
            raise
        finally:
            event["done"] = time.perf_counter_ns()
            events.append(event)
            active.pop()

    d._file_lock = observed_lock
    logger = d.Logger(config(record_bytes=2048, file_bytes=8192, quota_bytes=16384, files=2), root=target)
    print("ready", flush=True)
    assert sys.stdin.readline().strip() == "go"
    with patch.object(Path, "open", observed_open):
        with d.operation(logger, "mcp", "writer", request_id=identity, session_id=identity):
            for i in range(100): logger.info("parallel", {"index": i})
    print(json.dumps({"health": logger.health, "api": counts, "events": events}), flush=True)


def _admission_accounting(receipt, mode, attempts=101):
    """Every attempt is a verified append or an explicit pre-body refusal."""
    health, events, api = receipt["health"], receipt["events"], receipt["api"]
    assert health["emitted"] == len(events) == attempts
    assert health["serialization_failures"] == api["failed"] == 0
    assert health["filtered"] == 1  # operation-start debug record, at info threshold
    refused = 0
    for event in events:
        assert event["entry"] <= event["done"]
        if "error" in event:
            # Body/append/unwind failures are not reclassified as admission loss.
            assert "grant" not in event and "written_bytes" not in event, event
            assert event["error"] == "TimeoutError" or (
                event["error"] in {"OSError", "PermissionError"} and
                event["errno"] in {errno.EACCES, errno.EAGAIN, errno.EDEADLK}), event
            refused += 1
        else:
            assert event["entry"] <= event["grant"] <= event["body_completed"] <= event["release_start"] <= event["done"]
            assert 0 < event["written_bytes"] <= 2048, event
    assert health["sink_failures"] == health["dropped"] == refused, receipt
    if mode == "new":
        # A deadline can expire before create/wait, or after native ownership
        # but before the serialized body. Do not equate native grant with body.
        assert 0 <= api["wait"] <= api["create"] <= attempts, api
        assert api["close"] == api["create"], api
        assert api["release"] + api["timeout"] == api["wait"], api
        assert attempts - refused <= api["release"], api
        assert api["abandoned"] == 0, api
    return {"attempts": attempts, "appended": attempts - refused, "refused": refused}


def _admission_intervals(receipts):
    overlaps, peer_grants, wait_ms = [], [], []
    for a, b in ((receipts[0], receipts[1]), (receipts[1], receipts[0])):
        for event in a["events"]:
            end = event.get("grant", event["done"])
            peer_grants.append(sum(event["entry"] <= peer.get("grant", -1) < end for peer in b["events"]))
            wait_ms.append((end - event["entry"]) / 1e6)
            if "grant" in event:
                overlaps.extend(peer for peer in b["events"] if "grant" in peer and
                                max(event["grant"], peer["grant"]) < min(event["release_start"], peer["release_start"]))
    assert not overlaps, overlaps
    return peer_grants, wait_ms


def windows_parallel_admission(root):
    if os.name != "nt":
        return {"status": "not_applicable"}
    root.mkdir(parents=True, exist_ok=True)
    script = f"import sys;sys.path[:0]=[{str(ROOT / 'tools')!r},{str(ROOT / 'src')!r}];import smoke_diagnostics as s;s._admission_worker()"
    summaries = []
    for index, modes in enumerate([("new", "new")] * 5 + [("new", "legacy"), ("legacy", "new")]):
        trial = root / f"trial-{index:02}"
        trial.mkdir()
        target = trial / "storage"
        workers = [subprocess.Popen([sys.executable, "-B", "-c", script, str(target), identity, mode],
                   cwd=trial, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                   for identity, mode in zip(("A", "B"), modes)]
        receipts = []
        with ThreadPoolExecutor(2) as pool:
            try:
                ready = [pool.submit(worker.stdout.readline) for worker in workers]
                assert all(future.result(timeout=15).strip() == "ready" for future in ready)
                for worker in workers:
                    worker.stdin.write("go\n")
                    worker.stdin.flush()
                for worker in workers:
                    stdout, stderr = worker.communicate(timeout=30)
                    assert worker.returncode == 0 and not stderr, (stdout, stderr)
                    receipts.append(json.loads(stdout))
            finally:
                for worker in workers:
                    if worker.poll() is None:
                        worker.kill()
                        worker.communicate(timeout=5)
        # Persist before assertions so real OS tails/losses remain inspectable.
        (trial / "receipts.json").write_text(json.dumps({"modes": modes, "workers": receipts}, indent=2), encoding="utf-8")
        peer_grants, wait_ms = _admission_intervals(receipts)
        files = [path for path in d.log_files(target) if path.exists()]
        assert files and len(files) <= 2 and sum(path.stat().st_size for path in files) <= 16384
        for path in files:
            assert path.stat().st_size <= 8192
            for line in path.read_text(encoding="utf-8").splitlines():
                row = json.loads(line)
                assert len(line.encode()) < 2048 and row["severity"] == "info"
                assert row["identity"]["request_id"] == row["identity"]["session_id"]
        accounting = [_admission_accounting(receipt, mode) for mode, receipt in zip(modes, receipts)]
        lost = sum(receipt["health"]["sink_failures"] for receipt in receipts)
        summaries.append({"trial": index, "modes": modes, "sink_failures": lost,
                          "accounting": accounting,
                          "body_overlaps": 0, "max_peer_grants_while_pending": max(peer_grants),
                          "max_wait_ms": max(wait_ms), "api": [receipt["api"] for receipt in receipts]})
    (root / "summary.json").write_text(json.dumps(summaries, indent=2), encoding="utf-8")
    return summaries


def _admission_owner():
    import msvcrt
    target, mode = Path(sys.argv[1]), sys.argv[2]
    if mode == "byte":
        with (target / ".diagnostics.lock").open("a+b") as handle:
            if handle.tell() == 0:
                handle.write(b"0")
                handle.flush()
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            try:
                print("ready", flush=True)
                assert sys.stdin.readline().strip() == "go"
            finally:
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        api = d._windows_mutex_api()
        handle = api.CreateMutexW(None, False, d._windows_admission_name(target))
        assert handle and api.WaitForSingleObject(handle, 50) == 0
        print("ready", flush=True)
        assert sys.stdin.readline().strip() == "go"
        os._exit(0)  # Deliberately abandon only this isolated fixture's mutex.


def windows_owner_recovery(root):
    if os.name != "nt":
        return {"status": "not_applicable"}
    script = f"import sys;sys.path[:0]=[{str(ROOT / 'tools')!r},{str(ROOT / 'src')!r}];import smoke_diagnostics as s;s._admission_owner()"
    results = {}
    for mode in ("byte", "mutex"):
        target = root / mode
        target.mkdir(parents=True)
        worker = subprocess.Popen([sys.executable, "-B", "-c", script, str(target), mode], cwd=target,
                   stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        api, retained = d._windows_mutex_api(), None
        with ThreadPoolExecutor(1) as pool:
            try:
                assert pool.submit(worker.stdout.readline).result(timeout=15).strip() == "ready"
                if mode == "byte":
                    logger, stderr = d.Logger(config(), root=target), io.StringIO()
                    with contextlib.redirect_stderr(stderr):
                        logger.error("legacy byte held")
                        logger.error("legacy byte still held")
                    assert logger.health["sink_failures"] == logger.health["dropped"] == 2
                    assert stderr.getvalue().count("diagnostic_delivery_failed") == 1
                    assert not (target / "diagnostics.jsonl").exists()
                else:
                    retained = api.CreateMutexW(None, False, d._windows_admission_name(target))
                    assert retained
                worker.stdin.write("go\n")
                worker.stdin.flush()
                stdout, stderr = worker.communicate(timeout=15)
                assert worker.returncode == 0 and not stdout and not stderr, (stdout, stderr)
                if mode == "byte":
                    logger.info("legacy owner released")
                    assert logger.health["sink_failures"] == 2 and (target / "diagnostics.jsonl").exists()
                    results[mode] = {"held_byte_refusals": 2, "serious_warning_count": 1, "recovered": True}
                else:
                    old = {"timestamp": "2020-01-01T00:00:00Z", "message": "expired fixture"}
                    (target / "diagnostics.jsonl").write_bytes(d.encode(old))
                    waits = []
                    def wait(*args):
                        result = api.WaitForSingleObject(*args)
                        waits.append(result)
                        return result
                    observed = SimpleNamespace(CreateMutexW=api.CreateMutexW, WaitForSingleObject=wait,
                                               ReleaseMutex=api.ReleaseMutex, CloseHandle=api.CloseHandle)
                    logger = d.Logger(config(), root=target)
                    with patch.object(d, "_windows_mutex_api", return_value=observed):
                        logger.info("after abandonment")
                        logger.info("after recovery")
                    assert waits == [0x80, 0] and logger.health["sink_failures"] == 0, (waits, logger.health)
                    rows = [json.loads(line) for line in (target / "diagnostics.jsonl").read_text(encoding="utf-8").splitlines()]
                    assert [row["message"] for row in rows] == ["after abandonment", "after recovery"]
                    results[mode] = {"wait_results": waits, "retention_revalidated": True, "health": logger.health}
            finally:
                if worker.poll() is None:
                    worker.kill()
                    worker.communicate(timeout=5)
                if retained:
                    assert api.CloseHandle(retained)
    return results


def mcp_project_binding(root):
    from pf_runtime import mcp_server, session_read

    cases = [
        ("same-id-foreign", "foreign", "bound", None, False),
        ("argument-session-foreign", "foreign", "", "bound", False),
        ("bound-root", "bound", "bound", None, True),
        ("normalized-bound-root", "normalized", "bound", None, True),
        ("argument-bound-root", "bound", "", "bound", True),
        ("session-only", None, "bound", None, True),
        ("different-id", "different", "bound", None, False),
        ("session-mismatch", "bound", "bound", "other", False),
        ("invalid-session", "bound", "invalid", None, False),
        ("invalid-root", "missing", "bound", None, False),
        ("garage-no-session", "foreign", "", None, True),
    ]
    for label, selector, configured, requested, expected_logging in cases:
        base = root / label
        projects = {}
        for name in ("bound", "foreign", "different"):
            project = base / name
            (project / ".pf").mkdir(parents=True)
            project_id = "different" if name == "different" else "same-id"
            (project / ".pf/process-forge.yaml").write_text(
                f"schema_version: 1\nproject:\n  id: {project_id}\n", encoding="utf-8")
            projects[name] = project
        (projects["bound"] / "child").mkdir()
        projects["normalized"] = projects["bound"] / "child" / ".."
        projects["missing"] = base / "missing"

        def resolve_project(raw, _core):
            path = Path(raw)
            if path == projects["missing"]:
                raise session_read.SessionReadError("project_not_found")
            return path

        def project_for_session(args, _workplace, _core):
            if args.session != "bound":
                raise session_read.SessionReadError("session_not_found")
            return projects["bound"]

        # Real wrapper, dispatcher and file sink; explicit session/freshness ports.
        runtime = SimpleNamespace(
            host=SimpleNamespace(resolve_project=resolve_project, project_for_session=project_for_session),
            core=SimpleNamespace(project_id=core.project_id,
                project_context_check_result=lambda *args, **kwargs: {"status": "broken"}))
        arguments = {"resource_id": "fixture:root"}
        if selector is not None:
            arguments["project_root"] = str(projects[selector])
        if requested is not None:
            arguments["session_id"] = requested
        request = {"jsonrpc": "2.0", "id": label, "method": "tools/call",
            "params": {"name": "pf.resolve", "arguments": arguments}}
        expected = mcp_server._respond(request, base, configured, runtime)
        with patch.dict(os.environ, {"PF_DIAGNOSTICS": json.dumps({"profile": "normal", "sink": "jsonl"})}):
            actual = mcp_server.respond(request, base, configured, runtime)
        assert actual == expected, (label, actual, expected)
        written, records = [], []
        for name in ("bound", "foreign", "different"):
            directory = projects[name] / ".pf/runtime/diagnostics"
            if directory.exists():
                written.append(name)
                for file in d.log_files(directory):
                    if file.is_file():
                        records.extend(json.loads(line) for line in file.read_text(encoding="utf-8").splitlines())
        assert bool(written) == expected_logging, (label, written)
        if written:
            assert written == ["foreign" if label == "garage-no-session" else "bound"], (label, written)
            assert records and all(row["identity"]["request_id"] == label for row in records), (label, records)


def main():
    with tempfile.TemporaryDirectory(prefix="pf-diagnostics-") as raw:
        root = Path(raw)
        (root / ".pf").mkdir()
        (root / ".pf/process-forge.yaml").write_text("schema_version: 1\nproject:\n  id: fixture\n", encoding="utf-8")
        levels_config_privacy(root)
        failure_correlation_journal(root)
        protocol(root)
        mcp_project_binding(root / "mcp-binding")
        metrics = storage_export_performance(root)
        multiprocess_storage(root)
        metrics["admission_controls"] = lock_admission_controls(root / "admission-controls")
        metrics["admission_parallel"] = windows_parallel_admission(root / "admission-parallel")
        metrics["owner_recovery"] = windows_owner_recovery(root / "owner-recovery")
    print(json.dumps({"result": "PASS", "checks": ["severity/profile/config", "privacy", "journal invariance", "sink failures", "parallel correlation", "hook protocol", "MCP diagnostic project binding", "rotation/retention/export", "performance", "bounded admission", "mixed-version exclusion", "abandoned recovery"], "metrics": metrics}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
