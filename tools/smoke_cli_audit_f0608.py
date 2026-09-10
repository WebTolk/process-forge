"""Focused CLI regression smoke for the F06-F08 audit fixes."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import uuid
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import processforge as pf  # noqa: E402


def run_python(code: str, *, timeout: float = 10.0) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=timeout,
    )


def lock_path(path: Path) -> Path:
    return path.with_name(f".{path.name}.lock")


def lock_child_code(target: Path, *, abandon: bool = False) -> str:
    target_text = repr(str(target))
    return f"""
import os, sys, time
sys.path.insert(0, {str(ROOT / 'tools')!r})
import processforge as pf
target = __import__('pathlib').Path({target_text})
lock = pf.registry_file_lock(target, timeout_seconds=5, stale_after_seconds=0)
lock.__enter__()
print('READY', flush=True)
if {abandon!r}:
    os._exit(0)
time.sleep(5.0)
lock.__exit__(None, None, None)
"""


def legacy_lock_child_code(target: Path) -> str:
    target_text = repr(str(target))
    return f"""
import json, os, time
from pathlib import Path
target = Path({target_text})
lock = target.with_name(f'.{{target.name}}.lock')
lock.parent.mkdir(parents=True, exist_ok=True)
lock.write_text(json.dumps({{'path': str(target), 'pid': os.getpid(), 'created_at': '2026-09-10T10:00:00Z'}}) + '\\n', encoding='utf-8')
print('READY', flush=True)
time.sleep(5.0)
lock.unlink(missing_ok=True)
"""


def wait_ready(process: subprocess.Popen[str]) -> None:
    line = process.stdout.readline() if process.stdout else ""
    if line.strip() != "READY":
        output = process.stderr.read() if process.stderr else ""
        raise AssertionError(f"lock owner did not become ready: {line!r} {output!r}")


def smoke_live_old_lock_contention(root: Path) -> None:
    target = root / "live-old.yaml"
    owner = subprocess.Popen(
        [sys.executable, "-c", legacy_lock_child_code(target)],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )
    try:
        wait_ready(owner)
        existing = lock_path(target)
        old = time.time() - 3600
        os.utime(existing, (old, old))
        contender = run_python(
            f"""
import sys
sys.path.insert(0, {str(ROOT / 'tools')!r})
import processforge as pf
from pathlib import Path
try:
    with pf.registry_file_lock(Path({str(target)!r}), timeout_seconds=0.25, stale_after_seconds=0):
        raise SystemExit('unexpected acquisition')
except SystemExit as exc:
    if 'locked by another writer' not in str(exc):
        raise
""",
            timeout=5,
        )
        assert contender.returncode == 0, contender.stdout + contender.stderr
    finally:
        owner.wait(timeout=5)


def smoke_reacquire_after_owner_death(root: Path) -> None:
    target = root / "dead-owner.yaml"
    owner = subprocess.Popen(
        [sys.executable, "-c", lock_child_code(target, abandon=True)],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )
    wait_ready(owner)
    owner.wait(timeout=5)
    assert lock_path(target).is_file(), "abandoned owner should leave a recoverable lock record"
    with pf.registry_file_lock(target, timeout_seconds=2, stale_after_seconds=0):
        pass
    assert not lock_path(target).exists()


def smoke_exception_and_foreign_release(root: Path) -> None:
    target = root / "cleanup.yaml"
    try:
        with pf.registry_file_lock(target, timeout_seconds=1, stale_after_seconds=0):
            raise RuntimeError("expected cleanup")
    except RuntimeError:
        pass
    assert not lock_path(target).exists(), "exception cleanup must release the owned lock"

    target = root / "foreign.yaml"
    lock = lock_path(target)
    with pf.registry_file_lock(target, timeout_seconds=1, stale_after_seconds=0):
        foreign = {
            "path": str(target),
            "pid": os.getpid(),
            "host": "foreign-owner",
            "created_at": pf.now_utc(),
            "token": uuid.uuid4().hex,
        }
        lock.write_text(json.dumps(foreign) + "\n", encoding="utf-8")
    assert lock.is_file(), "releasing owner must preserve a foreign lock record"
    lock.unlink()

    malformed_target = root / "malformed.yaml"
    malformed_lock = lock_path(malformed_target)
    malformed_lock.parent.mkdir(parents=True, exist_ok=True)
    malformed_lock.write_text("{not-json\n", encoding="utf-8")
    os.utime(malformed_lock, (time.time() - 3600, time.time() - 3600))
    try:
        with pf.registry_file_lock(malformed_target, timeout_seconds=0.2, stale_after_seconds=0):
            raise AssertionError("malformed legacy lock must not be stolen")
    except SystemExit as exc:
        assert "locked by another writer" in str(exc)
    assert malformed_lock.is_file()


def write_coordination_fixture(root: Path) -> tuple[Path, Path]:
    workplace = root / "workplace"
    project = root / "project"
    (workplace / "runtime" / "agent-presence" / "agent-1").mkdir(parents=True)
    (project / ".pf").mkdir(parents=True)
    (workplace / "workplace.yaml").write_text(
        "schema_version: 1\ncoordination:\n  director_enabled: true\n  default_project_mode: simple\n",
        encoding="utf-8",
    )
    (project / ".pf" / "process-forge.yaml").write_text(
        "schema_version: 1\ncoordination:\n  mode: organized\n",
        encoding="utf-8",
    )
    presence = workplace / "runtime" / "agent-presence" / "agent-1" / "session-1.json"
    presence.write_text(
        json.dumps({"status": "online", "agent_id": "agent-1", "session_id": "session-1", "project_root": str(project)})
        + "\n",
        encoding="utf-8",
    )
    return workplace, project


def smoke_presence_and_public_mode(root: Path) -> None:
    empty = root / "empty-workplace"
    assert pf.active_organized_project_sessions(empty) == []
    workplace, project = write_coordination_fixture(root)
    active = pf.active_organized_project_sessions(workplace)
    assert len(active) == 1 and active[0]["agent_id"] == "agent-1", active

    offline = workplace / "runtime" / "agent-presence" / "agent-1" / "offline.json"
    offline.write_text(json.dumps({"status": "offline", "project_root": str(project)}), encoding="utf-8")
    corrupt = workplace / "runtime" / "agent-presence" / "agent-1" / "corrupt.json"
    corrupt.write_text("{not-json", encoding="utf-8")
    assert len(pf.active_organized_project_sessions(workplace)) == 1

    args = type("Args", (), {"workplace": str(workplace), "director_enabled": "false", "director_office_enabled": None, "force": False, "json": True})()
    try:
        pf.command_workplace_mode_set(args)
    except SystemExit as exc:
        assert "organized project sessions are active" in str(exc)
    else:
        raise AssertionError("public workplace mode disabling must be blocked by an active organized session")


def smoke_plan_default_parity(root: Path) -> None:
    plan = {"run": {"id": "run"}, "workers": [{"id": "worker-a"}]}
    normalized = pf.normalized_orchestrator_plan(ROOT, plan)
    expected = pf.expected_report_artifact({"id": "worker-a"})
    assert normalized["workers"][0]["expected_report_artifact"] == expected == ".pf/artifacts/worker-a-report.md"
    # A missing required plan field is still a validation error, but writing
    # its diagnostic normalization must not crash with NameError.
    plan_path = root / "plan.yaml"
    normalized_path = root / "normalized.yaml"
    (root / ".pf").mkdir(exist_ok=True)
    (root / ".pf/process-forge.yaml").write_text("schema_version: 1\nproject:\n  id: cli-plan-test\n")
    plan_path.write_text(json.dumps(plan), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(ROOT / "tools/processforge.py"), "orchestrator-plan-validate",
         "--project-root", str(root), "--plan", str(plan_path),
         "--write-normalized", str(normalized_path)],
        cwd=ROOT, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 1 and "Traceback" not in result.stderr, result.stdout + result.stderr
    assert pf.read_yaml_file(normalized_path)["workers"][0]["expected_report_artifact"] == expected


def smoke_parallel_recovery(root: Path) -> None:
    target = root / "parallel.yaml"
    # Obtain a real dead PID and leave an aged record for simultaneous reapers.
    dead = subprocess.Popen([sys.executable, "-c", "pass"])
    dead.wait(timeout=10)
    lock_path(target).write_text(json.dumps({"pid": dead.pid, "created_at": "2000-01-01T00:00:00Z"}))
    marker, counter = root / "exclusive", root / "counter"
    counter.write_text("0")
    code = f"""
import os, sys, time
from pathlib import Path
sys.path.insert(0, {str(ROOT / 'tools')!r})
import processforge as pf
target, marker, counter = Path({str(target)!r}), Path({str(marker)!r}), Path({str(counter)!r})
for _ in range(8):
    with pf.registry_file_lock(target, timeout_seconds=15, stale_after_seconds=0):
        fd = os.open(marker, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        try:
            value = int(counter.read_text())
            time.sleep(.015)
            counter.write_text(str(value + 1))
        finally:
            os.close(fd)
            marker.unlink()
"""
    children = [subprocess.Popen([sys.executable, "-c", code], cwd=ROOT,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for _ in range(4)]
    try:
        for child in children:
            stdout, stderr = child.communicate(timeout=25)
            assert child.returncode == 0, stdout + stderr
    finally:
        for child in children:
            if child.poll() is None:
                child.kill()
                child.wait(timeout=5)
    assert counter.read_text() == "32", "concurrent registry update was lost"
    assert not lock_path(target).exists()


def smoke_public_director_mode(root: Path) -> None:
    workplace, project = write_coordination_fixture(root / "public-mode")
    command = [sys.executable, str(ROOT / "tools/processforge.py"), "workplace-mode", "set",
               "--workplace", str(workplace), "--director-enabled", "false", "--json"]
    before = (workplace / "workplace.yaml").read_bytes()
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=30)
    assert result.returncode == 1 and "organized project sessions are active" in result.stderr
    assert (workplace / "workplace.yaml").read_bytes() == before
    presence = workplace / "runtime/agent-presence/agent-1/session-1.json"
    presence.write_text(json.dumps({"status": "offline", "project_root": str(project)}))
    presence.with_name("corrupt.json").write_text("{bad")
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    assert pf.read_yaml_file(workplace / "workplace.yaml")["coordination"]["director_enabled"] is False


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-cli-f0608-") as temp:
        raw = Path(temp)
        smoke_live_old_lock_contention(raw)
        smoke_reacquire_after_owner_death(raw)
        smoke_exception_and_foreign_release(raw)
        smoke_parallel_recovery(raw)
        smoke_presence_and_public_mode(raw)
        smoke_public_director_mode(raw)
        smoke_plan_default_parity(raw)
    print("PASS: smoke_cli_audit_f0608")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
