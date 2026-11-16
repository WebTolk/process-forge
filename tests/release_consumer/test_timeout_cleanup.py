"""Real process-tree regression for release consumer cleanup."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "consumer_timeout_adapter", ROOT / "tools/smoke_release_project_validators.py"
)
assert spec is not None and spec.loader is not None
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)


class ConsumerTreeCleanup(unittest.TestCase):
    def test_run_step_preserves_native_stdout_and_stderr(self):
        with tempfile.TemporaryDirectory(prefix="pf-output-test-") as temporary:
            root = Path(temporary)
            (root / "bin").mkdir()
            (root / "bin/pf.py").write_text(
                "import sys\nprint('consumer-stdout')\nprint('consumer-stderr', file=sys.stderr)\n",
                encoding="utf-8",
            )
            code = """
import importlib.util, os, sys
from pathlib import Path
source, root = map(Path, sys.argv[1:])
spec = importlib.util.spec_from_file_location('consumer_output', source / 'tools/smoke_release_project_validators.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.ROOT = root
module.run_step(root, dict(os.environ), 'fixture')
"""
            result = subprocess.run(
                [sys.executable, "-B", "-c", code, str(ROOT), str(root)],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("consumer-stdout", result.stdout)
            self.assertIn("consumer-stderr", result.stderr)

    def exercise(self, mode, *, cleanup_failure=False, stop_failure=False):
        with tempfile.TemporaryDirectory(prefix="pf-tree-test-") as temporary:
            root = Path(temporary)
            (root / "bin").mkdir()
            grandchild = (
                "import pathlib,sys,time; p=pathlib.Path(sys.argv[1]); "
                "f=(p / 'grandchild.lock').open('w'); "
                "(p / 'grandchild.ready').touch(); time.sleep(60)"
            )
            child = (
                "import pathlib,subprocess,sys,time; p=pathlib.Path(sys.argv[1]); "
                "f=(p / 'child.lock').open('w'); "
                f"subprocess.Popen([sys.executable, '-c', {grandchild!r}, str(p)]); "
                "(p / 'child.ready').touch(); time.sleep(60)"
            )
            (root / "bin/pf.py").write_text(
                "import pathlib,subprocess,sys,time\n"
                "p=pathlib.Path.cwd()\n"
                "(p / 'child.ready').unlink(missing_ok=True)\n"
                "(p / 'grandchild.ready').unlink(missing_ok=True)\n"
                f"subprocess.Popen([sys.executable, '-c', {child!r}, str(p)])\n"
                "deadline=time.monotonic()+10\n"
                "while not (p / 'grandchild.ready').exists():\n"
                "    assert time.monotonic()<deadline\n"
                "    time.sleep(0.01)\n"
                + ("time.sleep(60)\n" if mode == "timeout" else f"sys.exit({mode})\n"),
                encoding="utf8",
            )
            spawn = adapter.spawn_owned
            rmtree = shutil.rmtree
            jobs = []
            exits = []
            fixtures = []
            cleanup_observed: list[Path] = []

            def launched(*args, **kwargs):
                process = spawn(*args, **kwargs)
                job = process.native_job
                jobs.append((process, job))
                close = job.close

                def closed():
                    exits.append(job.active())
                    job.close = close
                    close()

                job.close = closed
                if stop_failure:
                    stop = job.stop

                    def uncertain_stop(*, deadline):
                        stop(deadline=deadline)
                        return False

                    job.stop = uncertain_stop
                return process

            def prepare(base, env):
                fixtures.append(base)
                adapter.run_step(base, env, "fixture")
                return base

            def removed(path, *args, **kwargs):
                base = Path(path)
                if base in fixtures and not cleanup_observed:
                    cleanup_observed.append(base)
                    self.assertTrue((base / "child.ready").exists())
                    self.assertTrue((base / "grandchild.ready").exists())
                    self.assertTrue(exits)
                    self.assertTrue(all(count == 0 for count in exits))
                rmtree(path, *args, **kwargs)
                if cleanup_failure and base in fixtures:
                    raise PermissionError("injected fixture cleanup failure")

            stderr = io.StringIO()
            stdout = io.StringIO()
            try:
                with (
                    mock.patch.object(adapter, "ROOT", root),
                    mock.patch.object(adapter, "STEP_TIMEOUT", 3),
                    mock.patch.object(adapter, "spawn_owned", side_effect=launched),
                    mock.patch.object(adapter, "prepare_consumer", side_effect=prepare),
                    mock.patch.object(adapter.shutil, "rmtree", side_effect=removed),
                    contextlib.redirect_stderr(stderr),
                    contextlib.redirect_stdout(stdout),
                ):
                    result = adapter.main(["--check", "events-validate"])
                if stop_failure:
                    self.assertTrue(fixtures[0].exists())
                    self.assertIn("fixture retained", stderr.getvalue())
                else:
                    self.assertFalse(fixtures[0].exists(), stderr.getvalue())
                    self.assertTrue(jobs)
                    self.assertTrue(all(count == 0 for count in exits))
                return result, stdout.getvalue(), stderr.getvalue()
            finally:
                # Exact retained native objects only; never scan or signal PIDs.
                for process, job in jobs:
                    if job.handle if os.name == "nt" else not job.closed:
                        job.stop(deadline=time.monotonic() + 10)
                        job.close()
                    process.wait(timeout=10)
                for base in fixtures:
                    if base.exists():
                        rmtree(base)

    def test_timeout_waits_for_real_child_and_grandchild_before_cleanup(self):
        result, stdout, stderr = self.exercise("timeout")
        self.assertEqual(result, 1)
        self.assertIn("TimeoutExpired", stderr)
        self.assertNotIn("PASS:", stdout)

    def test_failure_with_descendants_preserves_exit_code(self):
        result, stdout, stderr = self.exercise(17)
        self.assertEqual(result, 17)
        self.assertIn("command exited 17", stderr)
        self.assertNotIn("PASS:", stdout)

    def test_success_with_descendants_waits_before_cleanup(self):
        result, stdout, stderr = self.exercise(0)
        self.assertEqual(result, 0)
        self.assertIn("PASS: events-validate", stdout)
        self.assertEqual(stderr, "")

    def test_fixture_cleanup_failure_retains_primary_exit_code(self):
        result, stdout, stderr = self.exercise(17, cleanup_failure=True)
        self.assertEqual(result, 17)
        self.assertIn("command exited 17", stderr)
        self.assertIn("fixture cleanup", stderr)
        self.assertIn("PermissionError", stderr)
        self.assertNotIn("PASS:", stdout)

    def test_unconfirmed_tree_exit_retains_fixture_and_timeout(self):
        result, stdout, stderr = self.exercise("timeout", stop_failure=True)
        self.assertEqual(result, 1)
        self.assertIn("TimeoutExpired", stderr)
        self.assertIn("process cleanup failed", stderr)
        self.assertNotIn("PASS:", stdout)

    def test_fixture_cleanup_failure_retains_primary_timeout(self):
        result, stdout, stderr = self.exercise("timeout", cleanup_failure=True)
        self.assertEqual(result, 1)
        self.assertIn("TimeoutExpired after 3 seconds", stderr)
        self.assertIn("fixture cleanup", stderr)
        self.assertIn("PermissionError", stderr)
        self.assertNotIn("PASS:", stdout)

    def test_cleanup_failure_prevents_success(self):
        result, stdout, stderr = self.exercise(0, cleanup_failure=True)
        self.assertEqual(result, 1)
        self.assertIn("fixture cleanup", stderr)
        self.assertNotIn("PASS:", stdout)


if __name__ == "__main__":
    unittest.main()
