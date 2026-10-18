"""Worker sandbox selection and process command composition."""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any

from processforge_core.common.ids import safe_id
from processforge_core.common.paths import rel
from processforge_core.runtime.drivers import RuntimeDriverDefinitionPolicy
from processforge_core.runtime.environment import WorkerEnvironmentPolicy
from processforge_core.work.context_documents import ContextContractInputs
from processforge_core.work.outputs import WorkOutputPolicy
from processforge_core.work.paths import WorkPaths


class WorkerCommandBuilder:
    """Compose worker commands with the existing concrete Core policies."""

    def __init__(self, distribution_root: Path):
        self.distribution_root = distribution_root
        self.paths = WorkPaths()
        self.inputs = ContextContractInputs()
        self.outputs = WorkOutputPolicy(self.inputs)
        self.environment = WorkerEnvironmentPolicy()
        self.drivers = RuntimeDriverDefinitionPolicy()

    def sandbox(self, task: dict[str, Any]) -> str:
        execution = task.get("execution_mode") if isinstance(task.get("execution_mode"), dict) else {}
        ownership = task.get("ownership") if isinstance(task.get("ownership"), dict) else {}
        writable = ownership.get("writer") is True and (
            execution.get("code_changes_allowed") is True
            or execution.get("artifact_changes_allowed") is True
        )
        return "workspace-write" if writable else "read-only"

    def build(
        self,
        project_root: Path,
        task: dict[str, Any],
        driver: dict[str, Any],
        executable_override: str | None = None,
        *,
        attempt: int = 1,
        prepared_input: dict[str, str] | None = None,
    ) -> tuple[dict[str, Any], dict[str, Path]]:
        task_id = safe_id(str(task.get("id") or "task"), "task")
        run_id = safe_id(str(task.get("run_id") or "run"), "run")
        paths = self.paths.worker_run(project_root, run_id, task_id)
        capsule_path = self.inputs.locate_flow_root(project_root) / "contexts" / "assignment-capsules" / f"{task_id}.capsule.yaml"
        prompt_path = self.paths.worker_prompt(project_root, run_id, task_id)
        try:
            report_path = self.outputs.path(project_root, self.outputs.expected_report(task))
            for output in self.inputs.normalize_required_outputs(task.get("required_outputs")):
                if output.get("path"):
                    self.outputs.path(project_root, str(output["path"]))
        except (OSError, ValueError) as exc:
            raise SystemExit(f"FAIL: invalid worker output path: {exc}") from exc
        variables = {
            "project_root": str(project_root),
            "processforge_root": str(self.distribution_root),
            "run_id": run_id,
            "task_id": task_id,
            "attempt": str(attempt),
            "agent_run_dir": str(paths["root"]),
            "driver_id": str(driver.get("id") or "manual"),
            "capsule_path": str(capsule_path),
            "worker_prompt_path": str(prompt_path),
            "workspace_access_path": str(paths["workspace_access"]),
            "prepared_input_path": str(project_root / prepared_input["path"]) if prepared_input else "",
            "prepared_input_checksum": prepared_input["checksum"] if prepared_input else "",
            "expected_report_path": str(report_path),
            "python_executable": sys.executable,
            "executable": executable_override or "",
            "stdout_path": str(paths["stdout"]),
            "stderr_path": str(paths["stderr"]),
            "heartbeat_path": str(paths["heartbeat"]),
            "exit_path": str(paths["exit"]),
            "agent_model": self.inputs.normalize_agent_model(task.get("agent_model") or task.get("model") or ""),
            "agent_reasoning_effort": self.inputs.normalize_agent_reasoning_effort(task.get("agent_reasoning_effort") or task.get("reasoning_effort") or ""),
            "agent_sandbox": self.sandbox(task),
        }
        io = driver.get("io") if isinstance(driver.get("io"), dict) else {}
        stdout_path = Path(str(self.environment.expand(io.get("stdout") or rel(paths["stdout"], project_root), variables)))
        stderr_path = Path(str(self.environment.expand(io.get("stderr") or rel(paths["stderr"], project_root), variables)))
        if not stdout_path.is_absolute():
            stdout_path = (project_root / stdout_path).resolve()
        if not stderr_path.is_absolute():
            stderr_path = (project_root / stderr_path).resolve()
        paths["stdout"] = stdout_path
        paths["stderr"] = stderr_path
        heartbeat = driver.get("heartbeat") if isinstance(driver.get("heartbeat"), dict) else {}
        heartbeat_path = Path(str(self.environment.expand(heartbeat.get("path") or rel(paths["heartbeat"], project_root), variables)))
        if not heartbeat_path.is_absolute():
            heartbeat_path = (project_root / heartbeat_path).resolve()
        paths["heartbeat"] = heartbeat_path
        variables.update(
            {
                "stdout_path": str(paths["stdout"]),
                "stderr_path": str(paths["stderr"]),
                "heartbeat_path": str(paths["heartbeat"]),
                "exit_path": str(paths["exit"]),
            }
        )
        command_spec = driver.get("command") if isinstance(driver.get("command"), dict) else {}
        executable = executable_override or str(self.environment.expand(command_spec.get("executable") or "", variables))
        args = self.environment.expand(command_spec.get("args") if isinstance(command_spec.get("args"), list) else [], variables)
        if variables["agent_model"]:
            model_args_raw = command_spec.get("model_args") if "model_args" in command_spec else ["--model", "{agent_model}"]
            if not isinstance(model_args_raw, list):
                raise SystemExit("FAIL: runtime driver command.model_args must be a list when model is set")
            args.extend(self.environment.expand(model_args_raw, variables))
        env, inherit_env = self.environment.build(driver, variables)
        if driver.get("prepared_lifecycle_wrapper") is True and executable:
            if not prepared_input:
                raise SystemExit("FAIL: prepared_input_required")
            args = [str(self.distribution_root / "tools" / "prepared_executor.py"), "--prepared-input", variables["prepared_input_path"],
                    "--prepared-sha256", variables["prepared_input_checksum"], "--heartbeat", str(paths["heartbeat"]),
                    "--exit-path", str(paths["exit"]), "--", executable, *args]
            executable = sys.executable
        working_directory = str(self.environment.expand(driver.get("working_directory") or "{project_root}", variables))
        command = {
            "schema_version": 1,
            "run_id": run_id,
            "task_id": task_id,
            "attempt": str(attempt),
            "driver_id": str(driver.get("id") or "manual"),
            "agent_model": variables["agent_model"],
            "agent_reasoning_effort": variables["agent_reasoning_effort"],
            "kind": str(driver.get("kind") or "manual"),
            "prepared_input": prepared_input or {},
            "executable_override": executable_override or "",
            "command": {
                "executable": executable,
                "args": args,
                "argv": [executable, *args] if executable else [],
                "working_directory": working_directory,
                "environment": {str(key): str(value) for key, value in env.items()},
                "environment_inherit": inherit_env,
                "shell": False,
            },
            "paths": {key: rel(path, project_root) for key, path in paths.items() if key != "root"},
            "limits": self.drivers.parse_limits(driver)[0],
        }
        driver_ref = driver.get("_driver_ref")
        if isinstance(driver_ref, str) and driver_ref.strip():
            command["driver_ref"] = driver_ref.strip()
        return command, paths
