"""Real Windows/Linux source and sealed init and lifecycle in fresh SQL storage.

Fixture publications exercise fresh roots; this does not attest legacy adoption
or execution of a model. Existing authority and native APIs are used unchanged.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

import pf_native_control as native
import pytest
from project_initialization.test_first_worker_preparation import run, successful

from .test_native_control import native_root as native_root

pytestmark = pytest.mark.skipif(
    os.name != "nt" and not sys.platform.startswith("linux"),
    reason="Native owned backend required",
)
SOURCE = Path(__file__).resolve().parents[2]


def source_payload() -> dict[str, bytes]:
    """Export current public source bytes with their current canonical inventory."""
    spec = importlib.util.spec_from_file_location(
        "checksum_inventory", SOURCE / "tools/validate-process-forge-checksums.py"
    )
    assert spec and spec.loader
    inventory = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(inventory)
    payload = {
        name: inventory.released_content(path)
        for name, path in inventory.public_file_entries(SOURCE)
    }
    payload[native.INVENTORY] = native.inventory_bytes(payload)
    return payload


def source_cli(root: Path) -> Path:
    """Exercise direct source installation, without a fixture publication seal."""
    source = root / "source"
    for name, content in source_payload().items():
        target = source / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    assert native.leaf_seal((source / native.LEAF).read_bytes()) is None
    assert not (source / native.MANIFEST).exists()
    return source / "tools/processforge.py"


def publish(root: Path) -> Path:
    """Build a complete fixture using the existing public inventory and builder."""
    payload = source_payload()
    build = native.build_publication(
        payload,
        version=(SOURCE / "VERSION").read_text(encoding="utf-8").strip(),
        source={"fixture": True},
        generated_at="fixture",
    )
    publication = root / "publication"
    publication.mkdir()
    for name, content in {**build.payload, native.MANIFEST: build.manifest}.items():
        target = publication / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    return publication / "tools/processforge.py"


@pytest.mark.parametrize(
    "damage",
    ["payload", "missing", "duplicate", "traversal", "manifest", "managed", "hardlink"],
)
def test_source_entry_refuses_invalid_input_before_project_creation(
    tmp_path: Path, damage: str
) -> None:
    cli = source_cli(tmp_path)
    source = cli.parents[1]
    target = source / "src/processforge_core/common/markdown.py"
    inventory = source / native.INVENTORY
    if damage == "payload":
        target.write_bytes(target.read_bytes() + b"\nraise AssertionError(12345)\n")
    elif damage == "missing":
        target.unlink()
    elif damage == "duplicate":
        inventory.write_bytes(
            inventory.read_bytes() + inventory.read_bytes().splitlines()[0] + b"\n"
        )
    elif damage == "traversal":
        inventory.write_bytes(b"0" * 64 + b"  ../outside.py\n")
    elif damage == "manifest":
        (source / native.MANIFEST).write_text("{}", encoding="utf-8")
    elif damage == "managed":
        state = source / "runtime/managed-ingress/baseline.json"
        state.parent.mkdir(parents=True)
        state.write_text("{}", encoding="utf-8")
    else:
        os.link(target, tmp_path / "alias.py")
    project = tmp_path / "project"
    result = run(
        tmp_path,
        "invalid-source",
        str(cli),
        "project-init",
        "--project-root",
        str(project),
        "--workplace",
        str(tmp_path / "workplace"),
        "--type",
        "generic",
        "--process",
        "software-feature-development",
        "--apply",
    )
    assert result.returncode != 0
    reason = {
        "payload": "source_payload_drift",
        "missing": "source_unreadable",
        "duplicate": "duplicate_path",
        "traversal": "unsafe_path",
        "manifest": "source_has_installation_state",
        "managed": "source_has_installation_state",
        "hardlink": "not_regular",
    }[damage]
    assert reason in result.stderr, result.stdout + result.stderr
    assert "AssertionError: 12345" not in result.stderr
    assert not (project / ".pf").exists()
    assert not (source / "runtime/native-control").exists()


def test_source_mcp_entry_help_uses_verified_source(tmp_path):
    source = source_cli(tmp_path).parents[1]
    result = run(
        tmp_path,
        "source-mcp-help",
        str(source / "tools/pf_runtime/mcp_server.py"),
        "--help",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "usage:" in result.stdout
    assert result.stderr == ""


@pytest.mark.parametrize(
    "relative",
    [
        "tools/pf_runtime/codex_hooks.py",
        "tools/pf_runtime/kimi_hooks.py",
        "tools/pf_runtime/service.py",
        "tools/migrate-storage.py",
        "tools/migrate-hook-journals.py",
    ],
)
def test_source_runtime_adapters_capture_verified_entry(tmp_path, relative):
    source = source_cli(tmp_path).parents[1]
    code = """
import contextlib, io, runpy, sys
from pathlib import Path
entry_path = Path(sys.argv[1])
sys.argv = [str(entry_path), '--help']
sys.stdin = io.StringIO('{}')
with contextlib.redirect_stdout(io.StringIO()):
    try:
        if entry_path.name == 'service.py':
            sys.path.insert(0, str(entry_path.parent.parent))
            runpy.run_module('pf_runtime.service', run_name='__main__')
        else:
            runpy.run_path(str(entry_path), run_name='__main__')
    except SystemExit as result:
        assert result.code == 0
import pf_native_control as native
entry = native.current_entry()
assert entry is not None and entry.publication is not None and entry.image is not None
assert entry.control is None
assert entry.storage_safety(None)[0] == 'unknown'
assert native.supports_owned_execution()
"""
    result = run(tmp_path, "source-adapter", "-c", code, str(source / relative))
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stderr == ""
    assert not (source / "runtime/native-control").exists()
    assert not (source / "runtime/managed-ingress").exists()


@pytest.mark.parametrize("core_first", [True, False])
def test_source_library_imports_leave_developer_files_available(core_first):
    code = """
import sys
from pathlib import Path
root = Path(sys.argv[1])
if sys.argv[2] == "core":
    import processforge_core
    import processforge
else:
    import processforge
    import processforge_core
import pf_native_control as native
assert native.current_entry() is None
assert not native.supports_owned_execution()
assert (root / "tests/release_consumer/test_gates.py").read_bytes()
"""
    result = subprocess.run(
        [
            sys.executable,
            "-B",
            "-c",
            code,
            str(SOURCE),
            "core" if core_first else "cli",
        ],
        cwd=SOURCE,
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("native_first", [True, False])
def test_source_test_collection_is_independent_of_import_order(native_first):
    files = [
        "tests/work/test_start_reliability.py",
        "tests/execution_migration/test_fresh_native_sql.py",
    ]
    if native_first:
        files.reverse()
    result = subprocess.run(
        [
            sys.executable,
            "-B",
            "-m",
            "pytest",
            *files,
            "--collect-only",
            "-q",
            "-p",
            "no:cacheprovider",
        ],
        cwd=SOURCE,
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "tests collected" in result.stdout


SOURCE_CAPTURE_PROBE = """
import contextlib, importlib.util, io, json, runpy, sys, time
from pathlib import Path
cli, ready, proceed = map(Path, sys.argv[1:])
sys.argv = [str(cli), "--help"]
with contextlib.redirect_stdout(io.StringIO()):
    try:
        runpy.run_path(str(cli), run_name="__main__")
    except SystemExit as result:
        assert result.code == 0
import pf_native_control as native
entry = native.current_entry()
assert entry is not None and entry.publication is not None and entry.image is not None
assert entry.control is None
assert entry.storage_safety(None)[0] == "unknown"
assert native.leaf_seal(entry.publication.payload[native.LEAF]) is not None
assert native.supports_owned_execution()
relative = "src/processforge_core/common/markdown.py"
expected = entry.image.read(relative)
ready.write_text("ready")
deadline = time.monotonic() + 120
while not proceed.exists():
    if time.monotonic() >= deadline:
        raise AssertionError("parent did not finish mutation")
    time.sleep(0.02)
assert (entry.root / relative).read_bytes() == expected
spec = importlib.util.spec_from_file_location("retained_markdown", entry.root / relative)
retained = importlib.util.module_from_spec(spec)
spec.loader.exec_module(retained)
assert native.supports_owned_execution()
print(json.dumps({"retained": True, "owned_execution": True, "managed": False}))
"""


@pytest.mark.parametrize("crlf", [False, True])
def test_source_retains_verified_bytes_and_refuses_changed_new_entry(
    tmp_path: Path,
    crlf: bool,
) -> None:
    cli = source_cli(tmp_path)
    source = cli.parents[1]
    if crlf:
        for relative in (native.LEAF, native.INVENTORY, "tools/processforge.py"):
            target = source / relative
            target.write_bytes(target.read_bytes().replace(b"\n", b"\r\n"))
    ready, proceed = tmp_path / "ready", tmp_path / "proceed"
    process = subprocess.Popen(
        [
            sys.executable,
            "-B",
            "-c",
            SOURCE_CAPTURE_PROBE,
            str(cli),
            str(ready),
            str(proceed),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        deadline = time.monotonic() + 120
        while not ready.exists():
            if process.poll() is not None or time.monotonic() >= deadline:
                raise AssertionError(process.communicate(timeout=5))
            time.sleep(0.02)
        target = source / "src/processforge_core/common/markdown.py"
        target.write_bytes(b"raise AssertionError(12345)\n")
        proceed.write_text("continue", encoding="utf-8")
        stdout, stderr = process.communicate(timeout=60)
        assert process.returncode == 0, stdout + stderr
        assert json.loads(stdout) == {
            "retained": True,
            "owned_execution": True,
            "managed": False,
        }
        result = run(tmp_path, "changed-source", str(cli), "--help")
        assert result.returncode != 0
        assert "AssertionError: 12345" not in result.stderr
        assert not (source / native.MANIFEST).exists()
        assert not (source / "runtime/native-control").exists()
    finally:
        if process.poll() is None:
            process.kill()
        process.wait(timeout=5)


@pytest.mark.parametrize("distribution", ["source", "sealed"])
def test_fresh_sql_initialization_in_owned_parent(native_root: Path, distribution: str):
    cli = source_cli(native_root) if distribution == "source" else publish(native_root)
    workplace, project = native_root / "workplace", native_root / "project"
    successful(
        native_root,
        "owned-workplace",
        str(cli),
        "workplace-init",
        "--workplace",
        str(workplace),
        "--profile",
        "software-development",
        "--apply",
    )
    command = [
        sys.executable,
        "-B",
        str(cli),
        "project-init",
        "--project-root",
        str(project),
        "--workplace",
        str(workplace),
        "--type",
        "generic",
        "--process",
        "software-feature-development",
        "--apply",
    ]
    environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    for key, name in (
        ("LOCALAPPDATA", "appdata"),
        ("XDG_CONFIG_HOME", "xdg"),
        ("TEMP", "temp"),
        ("TMP", "temp"),
    ):
        environment[key] = str(native_root / name)
    process = native.spawn_owned(
        command,
        cwd=cli.parents[1],
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    job = getattr(process, "native_job")
    try:
        stdout, stderr = process.communicate(timeout=120)
        (native_root / "owned-init.stdout.log").write_bytes(stdout)
        (native_root / "owned-init.stderr.log").write_bytes(stderr)
        assert process.returncode == 0, (stdout + stderr).decode("utf-8", "replace")
        assert b"status: complete" in stdout and b"status: pass" in stdout
    finally:
        assert job.stop(deadline=time.monotonic() + 10)
        process.wait(timeout=10)
        assert job.active() == 0
        job.close()
    flow = project / ".pf"
    binding = json.loads((flow / "data/execution-storage.json").read_bytes())
    database = flow / binding["target_relative_path"]
    with sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True) as sql:
        assert sql.execute(
            "SELECT authority,readiness,active_coverage FROM execution_state WHERE singleton=1"
        ).fetchone() == ("sql", "ready", "complete")


@pytest.mark.parametrize("distribution", ["source", "sealed"])
def test_fresh_sql_worker_lifecycle_clears_resolved_unknown(
    native_root: Path,
    distribution: str,
) -> None:
    cli = str(
        source_cli(native_root) if distribution == "source" else publish(native_root)
    )
    workplace, project = native_root / "workplace", native_root / "project"
    successful(
        native_root,
        "workplace",
        cli,
        "workplace-init",
        "--workplace",
        str(workplace),
        "--profile",
        "software-development",
        "--apply",
    )
    successful(
        native_root,
        "init",
        cli,
        "project-init",
        "--project-root",
        str(project),
        "--workplace",
        str(workplace),
        "--type",
        "generic",
        "--process",
        "software-feature-development",
        "--apply",
    )
    flow = project / ".pf"
    binding = json.loads((flow / "data/execution-storage.json").read_bytes())
    database = flow / binding["target_relative_path"]
    with sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True) as sql:
        state = sql.execute(
            "SELECT project_id,authority,readiness,active_coverage "
            "FROM execution_state WHERE singleton=1"
        ).fetchone()
        assert state == (binding["project_id"], "sql", "ready", "complete")
    scope = native_root / "scope.json"
    scope.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "assignment": {
                    "allowed_actions": ["read", "write_artifact"],
                    "forbidden_actions": ["write_product"],
                    "allowed_read_files": [".pf/**", "AGENTS.md"],
                    "allowed_files": [".pf/artifacts/native-fixture/**"],
                    "execution_mode": "docs_only",
                    "ownership": {"owner_id": "native-fixture", "writer": True},
                    "expected_report": {
                        "artifact": ".pf/artifacts/native-fixture/report.md",
                        "format": "markdown",
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    work = json.loads(
        successful(
            native_root,
            "work-start",
            cli,
            "work-start",
            "--project-root",
            str(project),
            "--objective",
            "Deterministic native SQL fixture without a model.",
            "--process-id",
            "software-feature-development",
            "--scope-file",
            str(scope),
            "--json",
        )
    )
    assert work["action"] == "created_new"
    selectors = ["--project-root", str(project), "--task", work["assignment_id"]]
    successful(
        native_root,
        "prepare",
        cli,
        "worker-run",
        "prepare",
        *selectors,
        "--driver",
        "test-echo-worker",
    )
    successful(
        native_root,
        "start",
        cli,
        "worker-run",
        "start",
        *selectors,
        "--driver",
        "test-echo-worker",
        "--wait",
    )
    successful(native_root, "collect", cli, "worker-run", "collect", *selectors)
    runtime = flow / "runtime/agent-runs" / work["run_id"] / work["assignment_id"]
    status = json.loads((runtime / "status.json").read_bytes())
    assert status["status"] == "completed" and status["exit_code"] == 0
    assert status["failure_reason"] is None
    assert (project / ".pf/artifacts/native-fixture/report.md").is_file()
    with sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True) as sql:
        assert sql.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert sql.execute("SELECT COUNT(*) FROM execution_current").fetchone()[0] == 0
        attempt = sql.execute(
            "SELECT phase,outcome,collection,payload_json FROM execution_attempts WHERE task_id=?",
            (work["assignment_id"],),
        ).fetchone()
        assert attempt is not None and attempt[:3] == (
            "absent",
            "completed",
            "collected",
        )
        assert json.loads(attempt[3])["failure_reason"] is None
