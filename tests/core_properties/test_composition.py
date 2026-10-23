"""Isolated default composition, relocation, restart and concurrency probes."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import textwrap
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def run_python(
    code: str, source: Path, cwd: Path, *arguments: str
) -> subprocess.CompletedProcess[str]:
    """Run a fresh interpreter without reusing application singletons or bytecode."""
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONIOENCODING": "utf-8"}
    env["PYTHONPATH"] = os.pathsep.join([str(source / "src"), str(source / "tools")])
    result = subprocess.run(
        [sys.executable, "-B", "-c", textwrap.dedent(code), *arguments],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return result


def test_default_factory_bootstrap_and_cli_from_relocated_archive(
    tmp_path, write_distribution
):
    source = tmp_path / "archive-source"
    write_distribution(source, "7.1.2-dev.3+archive")
    for directory in ("src", "tools"):
        shutil.copytree(
            ROOT / directory,
            source / directory,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
        )
    archive = tmp_path / "fixture.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as stream:
        for file in source.rglob("*"):
            if file.is_file():
                stream.write(file, file.relative_to(source).as_posix())
    relocated = tmp_path / "перенос-漢字" / "core"
    with zipfile.ZipFile(archive) as stream:
        stream.extractall(relocated)
    neighbour = tmp_path / "neighbour"
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
            isolated_boot, root, neighbour, str(root), "7.1.2-dev.3+archive"
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
        mutate_in_process, relocated, neighbour, str(relocated), CORE_MANIFEST_NAME
    )
    assert before.stdout == (
        "ProcessForge 7.1.2-dev.3+archive\nSpec: 1.0\nSchema bundle: 1.0\n"
    )
    cli_version = (
        "import processforge; raise SystemExit(processforge.main(['version']))"
    )
    after = run_python(cli_version, relocated, neighbour)
    assert after.stdout == (
        "ProcessForge 8.2.3-rc.7+restart\nSpec: 1.0\nSchema bundle: 1.0\n"
    )
    assert before.stderr == after.stderr == ""
    # Missing metadata must not borrow the neighbouring installation's label.
    (relocated / "VERSION").unlink()
    missing = run_python(cli_version, relocated, neighbour)
    assert missing.stdout == "ProcessForge unknown\nSpec: 1.0\nSchema bundle: 1.0\n"
    assert missing.stderr == ""


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
