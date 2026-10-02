#!/usr/bin/env python3
"""Real record semantics, budget/invalid truth and publisher/viewer contract."""
from __future__ import annotations
import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import threading
from unittest.mock import patch
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import processforge as core
from processforge_core import runtime_metrics as metrics
from pf_runtime import service, monitor
from processforge_core.configuration import ConfigService, ConfigurationError, PFConfig
from processforge_core.configuration.yaml_store import YamlConfigStore


def put(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def main():
    with tempfile.TemporaryDirectory(prefix="pf-metrics-") as temp:
        base = Path(temp)
        wp, project = base / "workplace", base / "project"
        now = datetime.now(timezone.utc).timestamp()
        stamp = lambda seconds: datetime.fromtimestamp(now + seconds, timezone.utc).isoformat()
        presence = dict(agent_id="test", session_id="opaque/private", status="online", last_seen_at=stamp(-2), heartbeat_ttl_seconds=10)
        canonical = core.agent_presence_path(wp, "test", "opaque/private")
        put(canonical, presence)
        put(core.legacy_agent_presence_path(wp, "test"), {**presence, "status": "offline"})
        put(core.agent_presence_path(wp, "other", "stale"), {**presence, "agent_id": "other", "session_id": "stale", "last_seen_at": stamp(-20)})
        put(project / ".pf/process-forge.yaml", {})
        worker = project / ".pf/runtime/agent-runs/task/attempt/status.json"
        put(worker, {"status": "running", "private": "SECRET-MARKER"})
        put(project / ".pf/runs/one/run.yaml", {"status": "blocked"})
        put(project / ".pf/runs/two/run.yaml", {"status": "in_progress"})
        for key, status, expires in (("one", "active", 20), ("two", "active", -1), ("three", "revoked", 20)):
            put(wp / ("runtime/agent-leases/" + key + ".yaml"), dict(status=status, issued_at=stamp(-30), expires_at=stamp(expires)))
        cache = {"projects": [{"project_root": str(project)}], "sessions": {"old": {}}}
        put(wp / "runtime/pf-runtime-host/state.json", cache)
        result = metrics.collect(wp, [project], core, "instance", metrics.registrations(cache), now=now)
        groups = result["groups"]
        assert groups["sessions"]["counts"] == dict(online=1, stale=1, offline=0), groups["sessions"]
        assert groups["workers"]["counts"]["running"] == 1
        assert groups["work"]["counts"] == dict(in_progress=1, blocked=1)
        assert groups["leases"]["counts"] == dict(held=1, expired=1, inactive=1)
        assert metrics.shutdown_workers(wp, core)["counts"]["running"] == 1
        raw = json.dumps(result)
        assert all(s not in raw for s in ("SECRET-MARKER", str(base), "opaque/private"))
        schema = json.loads((ROOT / "schemas/runtime-metrics.schema.json").read_text())
        assert set(result) == set(schema["required"])
        assert metrics.project(result, "instance", now=now)
        for mutant in (None, {}, {**result, "instance_id": "other"}, {**result, "observed_at": stamp(1)}, {**result, "observed_at": stamp(-46)}):
            assert metrics.project(mutant, "instance", now=now) is None
        for field in ("counts", "observed"):
            mutant = copy.deepcopy(result)
            mutant["groups"]["workers"][field]["running"] = True
            assert metrics.project(mutant, "instance", now=now) is None
        put(canonical, {**presence, "heartbeat_ttl_seconds": True})
        assert metrics.observe("sessions", wp, [], core, now=now)["counts"]["online"] is None
        limited = metrics.observe("work", wp, [project], core, now=now, budget=metrics.Budget(entries=0))
        assert limited["coverage"] == "partial" and "budget" in limited["issues"] and limited["counts"]["blocked"] is None
        put(worker, {"status": "lost"})
        assert metrics.shutdown_workers(wp, core)["counts"]["running"] is None
        worker.write_bytes(b"x" * 131073)
        assert metrics.observe("workers", wp, [project], core, now=now)["coverage"] == "partial"
        put(worker, {"status": "completed"})
        assert metrics.shutdown_workers(wp, core)["counts"]["running"] == 0
        put(wp / "runtime/pf-runtime-host/state.json", {**cache, "projects": [*cache["projects"], {"project_root": str(base / "missing")} ]})
        assert metrics.shutdown_workers(wp, core)["counts"]["running"] is None
        # Real publisher -> atomic state -> monitor, including oversized cache.
        runtime = service.RuntimeProcess(wp, core, interval=2)
        runtime.state.update(status="ready", health="ready", endpoint="http://127.0.0.1:12345")
        runtime._registrations = metrics.registrations(cache)
        runtime.publish_metrics([project])
        runtime.save()
        put(service.lock_path(wp), {"pid": os.getpid(), "instance_id": runtime.instance_id})
        (wp / "runtime/pf-runtime-host/state.json").write_bytes(b"x" * 1048577)
        snapshot = monitor.collect_snapshot(wp, "1.1.0", alive=lambda _: True, probe=lambda _: (True, "ready"))
        assert snapshot["metrics"] and snapshot["registrations"]["sessions"] == 1 and "cache_oversize" not in snapshot["issues"]
        assert "partial" in "\n".join(monitor.render(snapshot, 120, 35))
        stopped = monitor.collect_snapshot(wp, "1.1.0", alive=lambda _: False)
        assert stopped["metrics"] is None
        # Empty directories consume budget too; no unbounded glob walk.
        for n in range(5):
            (project / f".pf/runs/empty-{n}").mkdir()
        assert "budget" in metrics.observe("work", wp, [project], core, now=now, budget=metrics.Budget(entries=2))["issues"]
        # Real observer thread keeps publishing while ordinary routing is blocked.
        put(wp / "runtime/pf-runtime-host/state.json", cache)
        runtime = service.RuntimeProcess(wp, core, interval=2)
        runtime.state.update(status="ready", health="ready", endpoint="http://127.0.0.1:12345")
        entered, release = threading.Event(), threading.Event()
        def slow_routing():
            entered.set()
            assert release.wait(5)
            return []
        with patch.object(runtime, "known_project_roots", slow_routing):
            slow = threading.Thread(target=runtime.known_project_roots)
            observer = threading.Thread(target=runtime.metrics_loop)
            slow.start()
            assert entered.wait(1)
            observer.start()
            deadline = time.monotonic() + 4
            try:
                while service.read_json(service.service_path(wp)).get("metrics", {}).get("instance_id") != runtime.instance_id and time.monotonic() < deadline:
                    time.sleep(0.02)
                observed = service.read_json(service.service_path(wp))
                assert observed.get("metrics", {}).get("instance_id") == runtime.instance_id
                assert slow.is_alive(), "routing was not blocked during publication"
            finally:
                release.set()
                runtime.stop_event.set()
                slow.join(2)
                observer.join(2)
        # Configuration reload is independent of routing; invalid input retains
        # the last applied model, while deletion restores the default.
        settings = ConfigService(YamlConfigStore(wp / "configuration.yaml"))
        settings.create(PFConfig().with_changes({"runtime.metrics.interval_seconds": 1}))
        runtime = service.RuntimeProcess(wp, core, interval=2, configuration=settings)
        assert runtime.metrics_interval == 1
        first, second = threading.Event(), threading.Event()
        periods = []
        publish = runtime.publish_metrics
        def record_sample(*args, **kwargs):
            publish(*args, **kwargs)
            periods.append(runtime.state["metrics"]["interval_seconds"])
            (first if len(periods) == 1 else second).set()
        with patch.object(runtime, "publish_metrics", side_effect=record_sample):
            observer = threading.Thread(target=runtime.metrics_loop)
            observer.start()
            try:
                assert first.wait(5), "one-second observer failed to publish"
                settings.update({"runtime.metrics.interval_seconds": 2})
                assert second.wait(5), "observer failed to reload configuration on its next cycle"
                assert periods[:2] == [1, 2], periods
            finally:
                runtime.stop_event.set()
                observer.join(5)
                assert not observer.is_alive()
        settings.update({"runtime.metrics.interval_seconds": 2})
        runtime.reload_configuration()
        assert runtime.metrics_interval == 2 and runtime.interval == 2
        valid_bytes = (wp / "configuration.yaml").read_bytes()
        (wp / "configuration.yaml").write_text("runtime: [PRIVATE_CANARY", encoding="utf-8")
        runtime.reload_configuration()
        assert runtime.metrics_interval == 2 and runtime.state["configuration"]["status"] == "invalid"
        assert "PRIVATE_CANARY" not in json.dumps(runtime.state["configuration"])
        (wp / "configuration.yaml").write_bytes(valid_bytes)
        settings.delete()
        runtime.reload_configuration()
        assert runtime.metrics_interval == 10 and runtime.state["configuration"]["status"] == "valid"
        # Deterministic clock/event adapter exercises the production observer:
        # monotonic cadence, overruns, and no catch-up/parallel collection.
        class OneCycle:
            def is_set(self):
                return False
            def wait(self, delay):
                self.delay = delay
                return True
        for period, elapsed in ((1, .2), (2, .3), (10, .5), (60, .5), (1, 3)):
            if settings.read().exists:
                settings.update({"runtime.metrics.interval_seconds": period})
            else:
                settings.create(PFConfig().with_changes({"runtime.metrics.interval_seconds": period}))
            runtime.stop_event = OneCycle()
            with patch.object(service.time, "monotonic", side_effect=[0, elapsed]), patch.object(metrics, "registered_projects", return_value=([], metrics.registrations({}), True)), patch.object(runtime, "publish_metrics") as publish, patch.object(runtime, "save"):
                runtime.metrics_loop()
                assert publish.call_count == 1
            assert runtime.stop_event.delay == (period - elapsed if elapsed < period else period)
            sample = metrics.collect(wp, [], core, "test", metrics.registrations({}), now=now, interval_seconds=period)
            ttl = max(5, 4.5 * period)
            assert metrics.project(sample, "test", now=now + ttl - .1)
            assert metrics.project(sample, "test", now=now + ttl + .1) is None
            assert metrics.project({**sample, "interval_seconds": True}, "test", now=now) is None
        broken = base / "broken"
        broken.mkdir()
        (broken / "configuration.yaml").write_text("runtime: [", encoding="utf-8")
        try:
            service.RuntimeProcess(broken, core, interval=2)
        except ConfigurationError:
            pass
        else:
            raise AssertionError("invalid startup must fail before creating runtime files")
        assert set(p.name for p in broken.iterdir()) == {"configuration.yaml"}
    print("PASS: metrics semantics, canonical dedup, bounds, privacy, schema and publisher/monitor")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
