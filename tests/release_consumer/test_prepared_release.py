"""Public release gates execute and collect through a real prepared worker."""

from __future__ import annotations

import importlib.util
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "prepared_release_helpers", Path(__file__).with_name("test_gates.py")
)
assert SPEC is not None and SPEC.loader is not None
HELPERS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HELPERS)

TARGET = r"""
import json, os, subprocess, sys
from pathlib import Path
distribution, report = map(Path, sys.argv[1:])
sys.path.insert(0, str(distribution / 'tools'))
if sys.platform.startswith('linux'):
    from pf_linux_native_control import inherited
    before = inherited(dict(os.environ))
    assert before is not None
    def proof():
        return inherited(dict(os.environ))
else:
    from pf_native_control import inherited_job
    owner = inherited_job(dict(os.environ))
    assert owner is not None and owner.active() > 0
    before = owner.name
    def proof():
        assert owner.active() > 0
        return owner.name
command = [
    sys.executable, '-B', str(distribution / 'tools/processforge.py'),
    'release-test', '--root', str(distribution), '--public', '--no-clean',
    '--only', 'events-validate', '--only', 'doctor-project', '--fail-fast',
]
result = subprocess.run(command, capture_output=True, text=True, timeout=180)
assert result.returncode == 0, result.stdout + result.stderr
path = distribution / '.pf/runtime/release-test/latest-report.json'
release = json.loads(path.read_text(encoding='utf-8'))
assert release['result'] == 'PASS'
assert {c['label'] for c in release['checks']} == {'events-validate', 'doctor-project'}
assert all(c['exit_code'] == 0 for c in release['checks'])
assert proof() == before
report.parent.mkdir(parents=True, exist_ok=True)
report.write_text('# Prepared release qualified\n\n' + json.dumps({
    'release': 'PASS', 'checks': 2, 'enclosing_owner_unchanged': True,
}), encoding='utf-8')
"""


class PreparedConsumerRelease(unittest.TestCase):
    def call(self, base, cli, label, *args, required=True):
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        for key, name in (
            ("LOCALAPPDATA", "appdata"),
            ("XDG_CONFIG_HOME", "xdg"),
            ("TEMP", "temp"),
            ("TMP", "temp"),
            ("TMPDIR", "temp"),
        ):
            directory = base / name
            directory.mkdir(exist_ok=True)
            env[key] = str(directory)
        command = [sys.executable, "-B", str(cli), *args]
        result = subprocess.run(
            command,
            env=env,
            cwd=base,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=300,
            check=False,
        )
        (base / (label + ".json")).write_text(
            json.dumps(
                {
                    "command": command,
                    "exit_code": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        if required:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def test_source_and_sealed_release_in_prepared_owned_target(self):
        for kind in ("source", "sealed"):
            with self.subTest(distribution=kind):
                self.exercise(kind)

    def exercise(self, kind):
        base = Path(tempfile.mkdtemp(prefix="pf-prepared-release-")).resolve()
        project = base / "project"
        project.mkdir()
        distribution = project / "distribution"
        HELPERS.source_fixture(distribution)
        if kind == "sealed":
            native = sys.modules["pf_native_control"]
            payload = {
                path.relative_to(distribution).as_posix(): path.read_bytes()
                for path in distribution.rglob("*")
                if path.is_file()
            }
            build = native.build_publication(
                payload,
                version=(distribution / "VERSION").read_text().strip(),
                source={"fixture": True},
                generated_at="fixture",
            )
            for name, content in {
                **build.payload,
                native.MANIFEST: build.manifest,
            }.items():
                (distribution / name).write_bytes(content)
        cli = distribution / "tools/processforge.py"
        workplace = base / "workplace"
        work = None
        safe_cleanup = True
        primary = None
        try:
            self.call(
                base,
                cli,
                "workplace",
                "workplace-init",
                "--workplace",
                str(workplace),
                "--profile",
                "software-development",
                "--apply",
            )
            self.call(
                base,
                cli,
                "project",
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
            script = project / "release-worker.py"
            script.write_text(TARGET, encoding="utf-8")
            driver = project / ".pf/runtime/drivers/prepared-release.yaml"
            driver.parent.mkdir(parents=True)
            driver.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "id": "prepared-release",
                        "title": "Prepared release fixture",
                        "kind": "shell",
                        "prepared_lifecycle_wrapper": True,
                        "command": {
                            "executable": sys.executable,
                            "args": [
                                "-B",
                                "{project_root}/release-worker.py",
                                "{project_root}/distribution",
                                "{expected_report_path}",
                            ],
                            "model_args": [],
                        },
                        "working_directory": "{project_root}",
                        "environment": {"inherit": True, "variables": {}},
                        "io": {
                            "stdin": "none",
                            "stdout": ".pf/runtime/agent-runs/{run_id}/{task_id}/stdout.log",
                            "stderr": ".pf/runtime/agent-runs/{run_id}/{task_id}/stderr.log",
                        },
                        "heartbeat": {
                            "mode": "file",
                            "path": ".pf/runtime/agent-runs/{run_id}/{task_id}/heartbeat.json",
                            "optional": True,
                        },
                        "limits": {"timeout_seconds": 240, "max_retries": 0},
                        "security": {
                            "allow_shell": False,
                            "require_explicit_executable": True,
                            "allow_network": False,
                        },
                    }
                ),
                encoding="utf-8",
            )
            registry = project / ".pf/runtime/registries/runtime-drivers.local.yaml"
            registry.parent.mkdir(parents=True, exist_ok=True)
            registry.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "runtime_drivers": [
                            {
                                "id": "prepared-release",
                                "path": "../drivers/prepared-release.yaml",
                                "status": "available",
                                "builtin": False,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            self.call(
                base,
                cli,
                "driver",
                "runtime-driver",
                "validate",
                "--project-root",
                str(project),
                "--driver",
                "prepared-release",
            )
            scope = base / "scope.json"
            scope.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "assignment": {
                            "allowed_actions": ["read", "write_artifact"],
                            "forbidden_actions": ["write_product"],
                            "allowed_read_files": [
                                ".pf/**",
                                "AGENTS.md",
                                "release-worker.py",
                                "distribution/**",
                            ],
                            "allowed_files": [
                                ".pf/artifacts/prepared-release/**",
                                "distribution/.pf/runtime/release-test/**",
                            ],
                            "required_sources": ["release-worker.py"],
                            "execution_mode": "docs_only",
                            "ownership": {
                                "owner_id": "prepared-release-fixture",
                                "writer": True,
                            },
                            "expected_report": {
                                "artifact": ".pf/artifacts/prepared-release/report.md",
                                "format": "markdown",
                            },
                        },
                    }
                ),
                encoding="utf-8",
            )
            work = json.loads(
                self.call(
                    base,
                    cli,
                    "work",
                    "work-start",
                    "--project-root",
                    str(project),
                    "--objective",
                    "Qualify public consumer gates in a prepared owned target.",
                    "--process-id",
                    "software-feature-development",
                    "--scope-file",
                    str(scope),
                    "--json",
                ).stdout
            )
            self.assertEqual(work["action"], "created_new")
            selectors = [
                "--project-root",
                str(project),
                "--task",
                work["assignment_id"],
            ]
            self.call(
                base,
                cli,
                "prepare",
                "worker-run",
                "prepare",
                *selectors,
                "--driver",
                "prepared-release",
            )
            self.call(
                base,
                cli,
                "start",
                "worker-run",
                "start",
                *selectors,
                "--driver",
                "prepared-release",
                "--wait",
            )
            self.call(base, cli, "collect", "worker-run", "collect", *selectors)
            runtime = (
                project
                / ".pf/runtime/agent-runs"
                / work["run_id"]
                / work["assignment_id"]
            )
            status = json.loads((runtime / "status.json").read_bytes())
            self.assertEqual(
                (status["status"], status["exit_code"], status["failure_reason"]),
                ("completed", 0, None),
            )
            report = (project / ".pf/artifacts/prepared-release/report.md").read_text(
                encoding="utf-8"
            )
            self.assertEqual(
                json.loads(report.split("\n\n", 1)[1]),
                {
                    "release": "PASS",
                    "checks": 2,
                    "enclosing_owner_unchanged": True,
                },
            )
            self.assertFalse((distribution / ".pf/process-forge.yaml").exists())
            binding = json.loads(
                (project / ".pf/data/execution-storage.json").read_bytes()
            )
            database = project / ".pf" / binding["target_relative_path"]
            with closing(
                sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True)
            ) as sql:
                self.assertEqual(
                    sql.execute("PRAGMA integrity_check").fetchone()[0], "ok"
                )
                self.assertEqual(
                    sql.execute("SELECT COUNT(*) FROM execution_current").fetchone()[0],
                    0,
                )
        except BaseException as error:
            primary = error
            raise
        finally:
            if work is not None:
                selectors = [
                    "--project-root",
                    str(project),
                    "--task",
                    work["assignment_id"],
                ]
                try:
                    stopped = self.call(
                        base,
                        cli,
                        "stop",
                        "worker-run",
                        "stop",
                        *selectors,
                        required=False,
                    )
                    safe_cleanup = stopped.returncode == 0
                except Exception as cleanup:
                    safe_cleanup = False
                    if primary is None:
                        raise
                    primary.add_note("Prepared worker stop failed: " + repr(cleanup))
            if safe_cleanup and primary is None:
                HELPERS.adapter.remove_fixture(str(base))
            elif primary is not None:
                primary.add_note(
                    "Prepared fixture retained for failure evidence: " + str(base)
                )
            else:
                self.fail(
                    "Prepared fixture retained because native stop was unconfirmed"
                )


if __name__ == "__main__":
    unittest.main()
