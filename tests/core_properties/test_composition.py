"""Isolated default composition, relocation, restart and concurrency probes."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import textwrap
import zipfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]


def _copy_distribution(
    source: Path,
    destination: Path,
    directories: tuple[str, ...],
    *,
    include_version: bool = False,
) -> None:
    """Select release-filtered rows before reading bodies; verify copied pins."""
    from processforge_core.maintenance.release_sources import ReleaseSourcePolicy

    policy = ReleaseSourcePolicy()
    patterns = policy.release_ignore_patterns(source)
    selected = []
    for directory in directories:
        for parent_name, dirs, files in os.walk(source / directory, followlinks=False):
            parent = Path(parent_name)
            assert not _redirected(parent), "redirected distribution directory"
            dirs[:] = [
                name
                for name in dirs
                if not policy.release_path_is_forbidden(
                    (parent / name).relative_to(source).as_posix() + "/"
                )
                and not policy.release_ignore_match(
                    (parent / name).relative_to(source).as_posix() + "/", patterns
                )
            ]
            for name in files:
                path = parent / name
                relative = path.relative_to(source).as_posix()
                if not policy.release_path_is_forbidden(
                    relative
                ) and not policy.release_ignore_match(relative, patterns):
                    selected.append((relative, path))
    if include_version:
        assert not policy.release_path_is_forbidden("VERSION")
        assert not policy.release_ignore_match("VERSION", patterns)
        selected.append(("VERSION", source / "VERSION"))
    rows: list[dict[str, Any]] = []
    for relative, path in sorted(selected):
        assert not _redirected(path), "redirected distribution member"
        raw = path.read_bytes()
        rows.append(
            {
                "path": relative,
                "size": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    for row in rows:
        path = source / row["path"]
        assert not _redirected(path), "redirected distribution member"
        raw = path.read_bytes()
        assert len(raw) == row["size"]
        assert hashlib.sha256(raw).hexdigest() == row["sha256"], "fixture source drift"
        target = destination / row["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    (destination / "fixture-selected-sources.json").write_text(
        json.dumps(rows, indent=2) + "\n", encoding="utf-8"
    )


def _redirected(path: Path) -> bool:
    """Refuse links, junctions and other Windows reparse points."""
    return (
        path.is_symlink()
        or path.is_junction()
        or bool(getattr(path.lstat(), "st_file_attributes", 0) & 0x400)
    )


def _remove_case(item: Path, parent: Path) -> None:
    """Remove one resolved owned child only; never retry a refusal."""
    assert not _redirected(parent) and not _redirected(item)
    assert item.resolve().parent == parent.resolve(), "fixture escaped owned parent"
    for root, dirs, files in os.walk(item, followlinks=False):
        for name in (*dirs, *files):
            assert not _redirected(Path(root) / name), "fixture cleanup redirected"
    shutil.rmtree(item)


def run_python(
    code: str, source: Path, cwd: Path, *arguments: str, owned_case: Path | None = None
) -> subprocess.CompletedProcess[str]:
    """Run a fresh interpreter without reusing application singletons or bytecode."""
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONIOENCODING": "utf-8"}
    env["PYTHONPATH"] = os.pathsep.join([str(source / "src"), str(source / "tools")])
    options: dict[str, Any] = {
        "cwd": cwd,
        "env": env,
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "text": True,
        "encoding": "utf-8",
    }
    argv = [sys.executable, "-B", "-c", textwrap.dedent(code), *arguments]
    if owned_case is None:
        result = subprocess.run(argv, check=False, timeout=30, **options)
    else:
        import pf_native_control as native

        marker = owned_case / ".retain-recovery.json"
        marker.write_text(
            '{"reason":"child_launch_or_closure_pending"}', encoding="utf-8"
        )
        child = native.spawn_owned(argv, **options)
        job = getattr(child, "native_job", None)
        try:
            stdout, stderr = child.communicate(timeout=30)
            assert job is not None and job.active() == 0, (
                "relocation descendants not closed"
            )
            result = subprocess.CompletedProcess(argv, child.returncode, stdout, stderr)
            marker.unlink()
        finally:
            if job is not None:
                job.close()
        evidence = owned_case.parent / "relocation-evidence"
        evidence.mkdir(exist_ok=True)
        with (evidence / "interpreters.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(
                json.dumps(
                    {
                        "exit": result.returncode,
                        "stdout": result.stdout,
                        "stderr": result.stderr,
                        "children_closed": True,
                    }
                )
                + "\n"
            )
    assert result.returncode == 0, result.stdout + result.stderr
    return result


def test_default_factory_bootstrap_and_cli_from_relocated_archive(
    tmp_path, write_distribution
):
    case = tmp_path / "relocation-case"
    case.mkdir()
    try:
        source = case / "archive-source"
        write_distribution(source, "7.1.2-dev.3+archive")
        _copy_distribution(ROOT, source, ("src", "tools"))
        archive = case / "fixture.zip"
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as stream:
            for file in source.rglob("*"):
                if file.is_file():
                    stream.write(file, file.relative_to(source).as_posix())
        relocated = case / "перенос-漢字" / "core"
        with zipfile.ZipFile(archive) as stream:
            stream.extractall(relocated)
        neighbour = case / "neighbour"
        write_distribution(neighbour, "99.0.1+other")
        isolated_boot = """
            import socket
            import subprocess
            import sys
            from pathlib import Path
            from types import ModuleType
            from unittest.mock import patch
            from processforge_core.bootstrap import RuntimeBootstrap
            from processforge_core.common.properties import CoreProperties
            from processforge_core.composition import build_core_properties
            with (
                patch.object(subprocess, 'run', side_effect=AssertionError('process')),
                patch.object(socket, 'socket', side_effect=AssertionError('network')),
            ):
                properties = build_core_properties()
                assert properties is build_core_properties()
                expected = CoreProperties.from_distribution(Path(sys.argv[1])).loaded
                assert properties.loaded == expected
                inert = ModuleType('borrowed-inert-adapter')
                runtime = RuntimeBootstrap(Path(sys.argv[1]), inert, inert, inert)
                assert runtime.properties is properties
                assert properties.loaded.version == sys.argv[2]
                assert 'processforge' not in sys.modules
                assert 'processforge_core._legacy_processforge' not in sys.modules
                assert not any(
                    name.startswith(('pf_cli', 'pf_runtime')) for name in sys.modules
                )
            print('isolated-boot-ok')
        """
        for root in (source, relocated):
            result = run_python(
                isolated_boot,
                root,
                neighbour,
                str(root),
                "7.1.2-dev.3+archive",
                owned_case=case,
            )
            assert result.stdout == "isolated-boot-ok\n"
        # A long-lived CLI keeps loaded identity; a genuinely new interpreter sees disk.
        mutate_in_process = """
            import sys
            from pathlib import Path
            import processforge as cli
            from processforge_core.common.properties import CoreProperties
            from processforge_core.composition import build_core_properties
            root = Path(sys.argv[1])
            owner = build_core_properties()
            assert cli.CORE_PROPERTIES is owner
            loaded = owner.loaded
            (root / 'VERSION').write_text('8.2.3-rc.7+restart', encoding='utf-8')
            manifest = root / sys.argv[2]
            import json
            data = json.loads(manifest.read_bytes())
            data['version'] = '8.2.3-rc.7+restart'
            manifest.write_text(json.dumps(data), encoding='utf-8')
            assert owner.loaded is loaded
            assert owner.installed().version == '8.2.3-rc.7+restart'
            assert CoreProperties.from_distribution(root).loaded == owner.installed()
            assert cli.main(['version']) == 0
        """
        from processforge_core.maintenance.update import CORE_MANIFEST_NAME

        before = run_python(
            mutate_in_process,
            relocated,
            neighbour,
            str(relocated),
            CORE_MANIFEST_NAME,
            owned_case=case,
        )
        assert before.stdout == (
            "ProcessForge 7.1.2-dev.3+archive\nSpec: 1.0\nSchema bundle: 1.0\n"
        )
        cli_version = (
            "import processforge; raise SystemExit(processforge.main(['version']))"
        )
        after = run_python(cli_version, relocated, neighbour, owned_case=case)
        assert after.stdout == (
            "ProcessForge 8.2.3-rc.7+restart\nSpec: 1.0\nSchema bundle: 1.0\n"
        )
        assert before.stderr == after.stderr == ""
        # Missing metadata must not borrow the neighbouring installation's label.
        (relocated / "VERSION").unlink()
        missing = run_python(cli_version, relocated, neighbour, owned_case=case)
        assert missing.stdout == "ProcessForge unknown\nSpec: 1.0\nSchema bundle: 1.0\n"
        assert missing.stderr == ""

    finally:
        evidence = tmp_path / "relocation-evidence"
        evidence.mkdir(exist_ok=True)
        try:
            manifest = case / "archive-source/fixture-selected-sources.json"
            if manifest.is_file():
                (evidence / "selected-sources.json").write_bytes(manifest.read_bytes())
            assert not (case / ".retain-recovery.json").exists(), (
                "child recovery required"
            )
            _remove_case(case, tmp_path)
        except BaseException as error:
            (evidence / "cleanup.json").write_text(
                json.dumps(
                    {
                        "cleanup": "retained",
                        "residue": case.name,
                        "reason": type(error).__name__,
                    }
                ),
                encoding="utf-8",
            )
            raise
        else:
            (evidence / "cleanup.json").write_text(
                '{"cleanup":"removed"}', encoding="utf-8"
            )


def test_parallel_first_use_constructs_exactly_one_loaded_snapshot(tmp_path):
    code = """
        from concurrent.futures import ThreadPoolExecutor
        from pathlib import Path
        from threading import Barrier, Event, Lock
        from unittest.mock import patch
        from processforge_core.common.properties import CoreIdentity, CoreProperties
        from processforge_core.composition import build_core_properties

        start = Barrier(9)
        all_calling = Event()
        entered = Event()
        second = Event()
        release = Event()
        guard = Lock()
        constructed = []
        callers = []

        class Reader:
            def __init__(self, index):
                self.value = CoreIdentity(version='7.0.0+snapshot.' + str(index))
            def read(self):
                return self.value

        def construct(root):
            with guard:
                index = len(constructed)
                value = CoreProperties(Reader(index))
                constructed.append(value)
                entered.set()
                if index:
                    second.set()
            assert release.wait(5), 'constructor was never released'
            return value

        def call(index):
            start.wait(timeout=5)
            with guard:
                callers.append(index)
                if len(callers) == 8:
                    all_calling.set()
            return build_core_properties()

        with patch.object(CoreProperties, 'from_distribution', side_effect=construct):
            with ThreadPoolExecutor(max_workers=8) as pool:
                futures = [pool.submit(call, index) for index in range(8)]
                try:
                    start.wait(timeout=5)
                    assert entered.wait(5)
                    assert all_calling.wait(5)
                    duplicated = second.wait(0.3)
                finally:
                    release.set()
                results = [future.result(timeout=5) for future in futures]
            assert not duplicated, 'parallel first use captured multiple snapshots'
            assert len(constructed) == 1
            assert all(value is constructed[0] for value in results)
            assert build_core_properties() is constructed[0]
        print('once-only-ok')
    """
    result = run_python(code, ROOT, tmp_path)
    assert result.stdout == "once-only-ok\n"
