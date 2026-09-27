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
from unittest.mock import patch

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


def main():
    with tempfile.TemporaryDirectory(prefix="pf-diagnostics-") as raw:
        root = Path(raw)
        (root / ".pf").mkdir()
        (root / ".pf/process-forge.yaml").write_text("schema_version: 1\nproject:\n  id: fixture\n", encoding="utf-8")
        levels_config_privacy(root)
        failure_correlation_journal(root)
        protocol(root)
        metrics = storage_export_performance(root)
        multiprocess_storage(root)
    print(json.dumps({"result": "PASS", "checks": ["severity/profile/config", "privacy", "journal invariance", "sink failures", "parallel correlation", "hook protocol", "rotation/retention/export", "performance"], "metrics": metrics}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
