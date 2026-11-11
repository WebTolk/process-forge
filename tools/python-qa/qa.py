"""Run shared Python quality tools with a project's configuration and dependencies."""

from __future__ import annotations

import argparse
import configparser
import json
import os

# The launcher executes argument vectors and never opens a command shell.
import subprocess  # nosec B404
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path


class QualityError(Exception):
    """Describe an unavailable interpreter, configuration or shared installation."""


@dataclass(frozen=True)
class CommandPlan:
    """Describe one tool invocation without executing it."""

    command: tuple[str, ...]
    directory: Path
    environment: dict[str, str] = field(default_factory=dict)


def _has_option(arguments: tuple[str, ...], *options: str) -> bool:
    return any(
        arg == option or arg.startswith(option + "=")
        for arg in arguments
        for option in options
    )


def _configuration(project: Path, names: tuple[str, ...], section: str) -> Path | None:
    for name in names:
        path = project / name
        if not path.is_file():
            continue
        if name == "pyproject.toml":
            try:
                data = tomllib.loads(path.read_text(encoding="utf-8"))
            except (OSError, tomllib.TOMLDecodeError) as exc:
                raise QualityError(
                    "Cannot read project configuration: " + str(path)
                ) from exc
            if section not in data.get("tool", {}):
                continue
        elif name == "setup.cfg":
            config = configparser.ConfigParser()
            try:
                config.read(path, encoding="utf-8")
            except configparser.Error as exc:
                raise QualityError(
                    "Cannot read project configuration: " + str(path)
                ) from exc
            if not config.has_section(section):
                continue
        return path
    return None


class QualityRunner:
    """Select concrete tools while keeping project configuration authoritative."""

    def __init__(self, tools_root: Path) -> None:
        """Keep the shared bundle location without launching a process."""
        self.tools_root = tools_root

    @property
    def python(self) -> Path:
        """Return the shared environment's interpreter path."""
        directory = "Scripts/python.exe" if os.name == "nt" else "bin/python"
        return self.tools_root / ".venv" / directory

    def project_python(self, project: Path, explicit: str | None) -> Path:
        """Select an explicit interpreter, a project venv, or the installation base."""
        selected: Path | None
        if explicit:
            selected = Path(explicit).expanduser()
            if not selected.is_absolute():
                selected = project / selected
        else:
            candidates = [
                project / folder / suffix
                for folder in (".venv", "venv")
                for suffix in ("Scripts/python.exe", "bin/python")
            ]
            selected = next((path for path in candidates if path.is_file()), None)
            if selected is None:
                manifest = self.tools_root / "installed.json"
                if manifest.is_file():
                    try:
                        selected = Path(
                            json.loads(manifest.read_text(encoding="utf-8"))[
                                "base_python"
                            ]
                        )
                    except (OSError, ValueError, KeyError, TypeError) as exc:
                        raise QualityError(
                            "Invalid shared installation manifest"
                        ) from exc
                else:
                    selected = Path(sys.executable)
        # A venv's bin/python may be a symlink to the base executable. Preserve
        # that entrypoint: resolving it would silently leave the selected venv.
        selected = Path(os.path.abspath(selected))
        if not selected.is_file():
            raise QualityError("Project interpreter is unavailable: " + str(selected))
        return selected

    @staticmethod
    def interpreter_info(python: Path) -> dict:
        """Read interpreter version and site paths without importing project code."""
        script = "import json,sys,sysconfig; print(json.dumps({'version':list(sys.version_info[:2]),'platform':sysconfig.get_platform(),'abi':sysconfig.get_config_var('SOABI'),'site':sysconfig.get_path('purelib')}))"
        result = subprocess.run(
            [str(python), "-I", "-c", script],
            capture_output=True,
            text=True,
            check=False,
        )  # nosec B603
        if result.returncode:
            raise QualityError("Cannot inspect interpreter: " + str(python))
        try:
            return json.loads(result.stdout)
        except ValueError as exc:
            raise QualityError("Interpreter returned invalid metadata") from exc

    def _test_command(
        self, project_python: Path, module: str, arguments: tuple[str, ...]
    ) -> tuple[str, ...]:
        shared = self.interpreter_info(self.python)
        project = self.interpreter_info(project_python)
        if (shared["version"], shared["platform"], shared.get("abi")) != (
            project["version"],
            project["platform"],
            project.get("abi"),
        ):
            raise QualityError(
                "Project Python and shared QA must use the same major/minor version and platform; install another shared bundle for this interpreter"
            )
        # Append trusted QA packages after the project's dependencies. Run tests
        # in the actual project interpreter; never substitute a different runtime.
        bootstrap = "import runpy,site,sys; site.addsitedir(sys.argv.pop(1)); name=sys.argv.pop(1); sys.argv[0]=name; runpy.run_module(name,run_name='__main__',alter_sys=True)"
        return (
            str(project_python),
            "-c",
            bootstrap,
            shared["site"],
            module,
            *arguments,
        )

    def plan(
        self,
        project: Path,
        task: str,
        arguments: tuple[str, ...] = (),
        *,
        python: str | None = None,
    ) -> CommandPlan:
        """Build one command using local configuration before shared defaults.

        Args:
            project: Existing project root, used as the tool working directory.
            task: The requested quality operation.
            arguments: Arguments passed individually to the selected tool.
            python: Optional project interpreter, relative to the project or absolute.

        Returns:
            A command, working directory and command-local environment.

        Raises:
            QualityError: The project, tool installation or interpreter is invalid.
        """
        project = project.expanduser().resolve()
        if not project.is_dir():
            raise QualityError("Project root is not a directory: " + str(project))
        if not self.python.is_file():
            raise QualityError(
                "Shared Python QA is not installed; run install.py first"
            )
        environment = os.environ.copy()
        prefix = (str(self.python), "-m")
        command: tuple[str, ...]
        if task in {"lint", "fix", "format", "format-fix", "docstrings"}:
            operation = "format" if task in {"format", "format-fix"} else "check"
            command = (*prefix, "ruff", operation)
            if task == "format":
                command += ("--check",)
            elif task == "fix":
                command += ("--fix",)
                if not _has_option(arguments, "--unsafe-fixes"):
                    command += ("--no-unsafe-fixes",)
            elif task == "docstrings":
                command += ("--extend-select", "D")
            if task in {"lint", "docstrings"}:
                if _has_option(arguments, "--fix", "--fix-only", "--unsafe-fixes"):
                    raise QualityError("Use the explicit fix operation for Ruff fixes")
                # Project fix/fix-only settings must not turn assurance into a
                # writing operation. CLI mode flags override configuration.
                command += ("--no-fix", "--no-fix-only")
            local = _configuration(
                project, (".ruff.toml", "ruff.toml", "pyproject.toml"), "ruff"
            )
            if local is None and not _has_option(arguments, "--config", "--isolated"):
                command += ("--config", str(self.tools_root / "config" / "ruff.toml"))
            command += arguments or (".",)
        elif task == "typecheck":
            command = (*prefix, "mypy")
            local = _configuration(
                project,
                ("mypy.ini", ".mypy.ini", "pyproject.toml", "setup.cfg"),
                "mypy",
            )
            if local is None and not _has_option(arguments, "--config-file"):
                command += (
                    "--config-file",
                    str(self.tools_root / "config" / "mypy.ini"),
                )
            if not _has_option(arguments, "--python-executable", "--no-site-packages"):
                command += (
                    "--python-executable",
                    str(self.project_python(project, python)),
                )
            command += arguments or (".",)
        elif task in {"test", "coverage"}:
            selected = self.project_python(project, python)
            if task == "coverage":
                arguments = ("run", "--branch", "-m", "pytest", *arguments)
            command = self._test_command(
                selected, "coverage" if task == "coverage" else "pytest", arguments
            )
            source = project / "src"
            if source.is_dir():
                environment["PYTHONPATH"] = str(source) + (
                    os.pathsep + environment["PYTHONPATH"]
                    if environment.get("PYTHONPATH")
                    else ""
                )
        elif task == "security":
            command = (*prefix, "bandit")
            local = _configuration(
                project, ("bandit.yaml", ".bandit.yaml", "pyproject.toml"), "bandit"
            )
            if (
                not _has_option(arguments, "-c", "--configfile", "--ini")
                and not (project / ".bandit").is_file()
            ):
                command += (
                    "-c",
                    str(local or self.tools_root / "config" / "bandit.yaml"),
                )
            command += ("-r", *(arguments or (".",)))
        elif task == "audit":
            command = (*prefix, "pip_audit")
            if _has_option(
                arguments, "-r", "--requirement", "--path", "--help", "-h", "--version"
            ):
                pass
            elif (project / "requirements.txt").is_file():
                command += ("-r", str(project / "requirements.txt"))
            elif (project / "pyproject.toml").is_file():
                command += (str(project),)
            elif python:
                info = self.interpreter_info(self.project_python(project, python))
                command += ("--path", info["site"])
            else:
                raise QualityError(
                    "Dependency audit needs project requirements.txt, pyproject.toml, explicit -r/--path, or --python; the shared QA environment is not the project"
                )
            command += arguments
        elif task == "versions":
            script = "import importlib.metadata as m,json,sys; print(json.dumps({'python':sys.version.split()[0], 'tools':{n:m.version(n) for n in ('ruff','pytest','pytest-cov','coverage','mypy','bandit','pip-audit')}},indent=2))"
            command = (str(self.python), "-I", "-c", script)
        else:
            raise QualityError("Unknown quality operation: " + task)
        return CommandPlan(command, project, environment)

    @staticmethod
    def run(plan: CommandPlan) -> int:
        """Execute exactly one command and preserve its failure status."""
        return subprocess.run(
            plan.command, cwd=plan.directory, env=plan.environment, check=False
        ).returncode  # nosec B603


def main(argv: list[str] | None = None) -> int:
    """Parse an explicit operation and run the shared tool."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument(
        "--tools-root", type=Path, default=Path(__file__).resolve().parent
    )
    parser.add_argument(
        "--python",
        help="Project interpreter; defaults to project venv or installation base",
    )
    parser.add_argument(
        "operation",
        choices=(
            "lint",
            "fix",
            "format",
            "format-fix",
            "docstrings",
            "typecheck",
            "test",
            "coverage",
            "security",
            "audit",
            "versions",
        ),
    )
    parser.add_argument("arguments", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    arguments = tuple(
        args.arguments[1:] if args.arguments[:1] == ["--"] else args.arguments
    )
    try:
        runner = QualityRunner(args.tools_root.resolve())
        return runner.run(
            runner.plan(
                args.project_root, args.operation, arguments, python=args.python
            )
        )
    except (QualityError, OSError) as exc:
        print("Python QA: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
