"""Check project isolation, configuration precedence and safe QA invocations."""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "shared_python_qa", ROOT / "tools/python-qa/qa.py"
)
qa = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = qa
SPEC.loader.exec_module(qa)


class LauncherTests(unittest.TestCase):
    """Exercise real project configuration files and explicit command boundaries."""

    def setUp(self):
        parent = Path(
            os.environ.get("PF_PYTHON_QA_TEST_ROOT", ROOT / ".pf/tmp/python-qa-tests")
        )
        parent.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(prefix="launcher-", dir=parent)
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.project = self.root / "project with spaces"
        self.project.mkdir()
        self.tools = self.root / "shared QA"
        self.runner = qa.QualityRunner(self.tools)
        self.runner.python.parent.mkdir(parents=True)
        self.runner.python.touch()

    def test_lint_uses_shared_fallback_without_project_configuration(self):
        plan = self.runner.plan(self.project, "lint", ("source with spaces.py",))
        self.assertEqual(plan.directory, self.project)
        self.assertEqual(plan.command[-1], "source with spaces.py")
        offset = plan.command.index("--config")
        self.assertEqual(plan.command[offset + 1], str(self.tools / "config/ruff.toml"))
        self.assertNotIn("--fix", plan.command)

    def test_unrelated_pyproject_does_not_suppress_ruff_fallback(self):
        (self.project / "pyproject.toml").write_text(
            '[project]\nname = "example"\n', encoding="utf-8"
        )
        self.assertIn("--config", self.runner.plan(self.project, "lint").command)

    def test_local_ruff_configuration_is_authoritative(self):
        for name, content in (
            ("ruff.toml", "line-length = 100\n"),
            (".ruff.toml", "line-length = 100\n"),
            ("pyproject.toml", "[tool.ruff]\nline-length = 100\n"),
        ):
            with self.subTest(name=name):
                path = self.project / name
                path.write_text(content, encoding="utf-8")
                self.assertNotIn(
                    "--config", self.runner.plan(self.project, "lint").command
                )
                path.unlink()

    def test_forwarded_explicit_ruff_configuration_wins(self):
        for arguments in (
            ("--config", "own.toml"),
            ("--config=own.toml",),
            ("--isolated",),
        ):
            with self.subTest(arguments=arguments):
                command = self.runner.plan(self.project, "lint", arguments).command
                self.assertNotIn(str(self.tools / "config/ruff.toml"), command)

    def test_invalid_toml_is_reported_instead_of_silently_overridden(self):
        (self.project / "pyproject.toml").write_text("[tool.ruff\n", encoding="utf-8")
        with self.assertRaises(qa.QualityError):
            self.runner.plan(self.project, "lint")

    def test_format_is_read_only_until_explicit_fix(self):
        self.assertIn("--check", self.runner.plan(self.project, "format").command)
        self.assertNotIn(
            "--check", self.runner.plan(self.project, "format-fix").command
        )
        self.assertIn("--fix", self.runner.plan(self.project, "fix").command)
        self.assertNotIn(
            "--unsafe-fixes", self.runner.plan(self.project, "fix").command
        )

    def test_docstring_rules_are_an_explicit_operation(self):
        self.assertNotIn("D", self.runner.plan(self.project, "lint").command)
        self.assertIn("D", self.runner.plan(self.project, "docstrings").command)

    def test_project_fix_settings_cannot_enable_writes_in_check_operations(self):
        (self.project / "ruff.toml").write_text(
            "fix = true\nfix-only = true\nunsafe-fixes = true\n", encoding="utf-8"
        )
        for task in ("lint", "docstrings"):
            with self.subTest(task=task):
                command = self.runner.plan(self.project, task).command
                self.assertIn("--no-fix", command)
                self.assertIn("--no-fix-only", command)

    def test_check_operations_reject_explicit_mutating_flags(self):
        for task in ("lint", "docstrings"):
            for option in ("--fix", "--fix-only", "--unsafe-fixes"):
                with self.subTest(task=task, option=option):
                    with self.assertRaises(qa.QualityError):
                        self.runner.plan(self.project, task, (option, "example.py"))

    def test_fix_requires_explicit_unsafe_option_even_when_configured(self):
        (self.project / "ruff.toml").write_text(
            "unsafe-fixes = true\n", encoding="utf-8"
        )
        self.assertIn(
            "--no-unsafe-fixes", self.runner.plan(self.project, "fix").command
        )
        command = self.runner.plan(
            self.project, "fix", ("--unsafe-fixes", "example.py")
        ).command
        self.assertIn("--unsafe-fixes", command)
        self.assertNotIn("--no-unsafe-fixes", command)

    def test_selected_venv_symlink_is_preserved_for_auto_and_explicit_python(self):
        executable = self.root / "base-python"
        executable.touch()
        selected = self.project / ".venv/bin/python"
        selected.parent.mkdir(parents=True)
        try:
            selected.symlink_to(executable)
        except OSError as exc:
            self.skipTest("Creating interpreter symlinks is unavailable: " + str(exc))
        for explicit in (None, ".venv/bin/python"):
            with self.subTest(explicit=explicit):
                result = self.runner.project_python(self.project, explicit)
                self.assertEqual(result, selected.absolute())
                self.assertNotEqual(result, executable)

    def test_mypy_setup_cfg_without_its_section_uses_shared_defaults(self):
        path = self.project / "setup.cfg"
        path.write_text("[metadata]\nname = example\n", encoding="utf-8")
        self.assertIn(
            str(self.tools / "config/mypy.ini"),
            self.runner.plan(self.project, "typecheck").command,
        )
        path.write_text("[mypy]\nstrict = True\n", encoding="utf-8")
        self.assertNotIn(
            "--config-file", self.runner.plan(self.project, "typecheck").command
        )

    def test_mypy_uses_project_interpreter_for_dependencies(self):
        plan = self.runner.plan(
            self.project, "typecheck", ("src",), python=sys.executable
        )
        offset = plan.command.index("--python-executable")
        self.assertEqual(Path(plan.command[offset + 1]), Path(sys.executable).resolve())

    def test_explicit_mypy_interpreter_is_not_overridden(self):
        arguments = ("--python-executable", "chosen-python", "src")
        command = self.runner.plan(self.project, "typecheck", arguments).command
        self.assertEqual(command.count("--python-executable"), 1)

    def test_project_venv_precedes_the_installation_base(self):
        interpreter = (
            self.project
            / ".venv"
            / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        )
        interpreter.parent.mkdir(parents=True)
        interpreter.touch()
        self.assertEqual(
            self.runner.project_python(self.project, None), interpreter.resolve()
        )

    def test_test_bootstrap_keeps_project_interpreter_and_appends_qa_packages(self):
        metadata = {
            "version": [3, 14],
            "platform": sys.platform,
            "site": "shared packages",
        }
        (self.project / "src").mkdir()
        with patch.object(self.runner, "interpreter_info", return_value=metadata):
            plan = self.runner.plan(
                self.project, "test", ("tests", "-q"), python=sys.executable
            )
        self.assertEqual(plan.command[0], str(Path(sys.executable).resolve()))
        self.assertIn("site.addsitedir", plan.command[2])
        self.assertEqual(plan.command[-3:], ("pytest", "tests", "-q"))
        self.assertTrue(
            plan.environment["PYTHONPATH"].startswith(str(self.project / "src"))
        )

    def test_cross_version_binary_package_injection_is_refused(self):
        values = [
            {"version": [3, 14], "platform": sys.platform, "site": "qa"},
            {"version": [3, 12], "platform": sys.platform, "site": "project"},
        ]
        with patch.object(self.runner, "interpreter_info", side_effect=values):
            with self.assertRaisesRegex(qa.QualityError, "same major/minor"):
                self.runner.plan(self.project, "test")

    def test_same_version_with_other_binary_abi_is_refused(self):
        values = [
            {
                "version": [3, 14],
                "platform": sys.platform,
                "abi": "cp314-amd64",
                "site": "qa",
            },
            {
                "version": [3, 14],
                "platform": sys.platform,
                "abi": "cp314t-amd64",
                "site": "project",
            },
        ]
        with patch.object(self.runner, "interpreter_info", side_effect=values):
            with self.assertRaises(qa.QualityError):
                self.runner.plan(self.project, "test")

    def test_audit_uses_project_requirements(self):
        requirements = self.project / "requirements.txt"
        requirements.write_text("example==1.0\n", encoding="utf-8")
        command = self.runner.plan(self.project, "audit").command
        self.assertEqual(command[-2:], ("-r", str(requirements)))

    def test_audit_never_defaults_to_shared_qa_dependencies(self):
        (self.tools / "requirements.txt").write_text(
            "pytest==9.1.1\n", encoding="utf-8"
        )
        with self.assertRaisesRegex(qa.QualityError, "shared QA environment"):
            self.runner.plan(self.project, "audit")

    def test_audit_honors_explicit_requirement_arguments(self):
        self.assertEqual(
            self.runner.plan(self.project, "audit", ("-r", "custom.txt")).command[-2:],
            ("-r", "custom.txt"),
        )

    def test_failed_tool_exit_is_preserved(self):
        plan = qa.CommandPlan(("selected-python", "-m", "pytest"), self.project, {})
        with patch.object(
            qa.subprocess,
            "run",
            return_value=subprocess.CompletedProcess(plan.command, 5),
        ) as run:
            self.assertEqual(self.runner.run(plan), 5)
        self.assertEqual(run.call_args.args[0], plan.command)
        self.assertNotIn("shell", run.call_args.kwargs)

    def test_invalid_project_and_missing_installation_fail(self):
        with self.assertRaises(qa.QualityError):
            self.runner.plan(self.root / "missing", "lint")
        self.runner.python.unlink()
        with self.assertRaisesRegex(qa.QualityError, "not installed"):
            self.runner.plan(self.project, "lint")

    def test_cli_passes_spaced_arguments_without_splitting(self):
        with (
            patch.object(
                qa.QualityRunner,
                "plan",
                return_value=qa.CommandPlan(("tool",), self.project),
            ) as plan,
            patch.object(qa.QualityRunner, "run", return_value=7),
        ):
            result = qa.main(
                [
                    "--project-root",
                    str(self.project),
                    "--tools-root",
                    str(self.tools),
                    "lint",
                    "--",
                    "source with spaces.py",
                ]
            )
        self.assertEqual(result, 7)
        self.assertEqual(plan.call_args.args[2], ("source with spaces.py",))


if __name__ == "__main__":
    unittest.main()
