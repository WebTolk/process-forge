"""Worker sandbox selection and process command composition."""

from __future__ import annotations

import hashlib
import json
import re
import stat
import sys
from pathlib import Path
from typing import Any

from processforge_core.common.ids import safe_id
from processforge_core.common.paths import rel
from processforge_core.configuration import ConfigurationProvider, PFConfig
from processforge_core.runtime.drivers import RuntimeDriverDefinitionPolicy
from processforge_core.runtime.environment import WorkerEnvironmentPolicy
from processforge_core.work.context_documents import ContextContractInputs
from processforge_core.work.outputs import WorkOutputPolicy
from processforge_core.work.paths import WorkPaths

CONFIGURATION_SNAPSHOT_LIMIT = 65536


def configuration_snapshot_bytes(
    configuration: ConfigurationProvider,
    identity: dict[str, Any],
    *,
    device_config_path: Path | None = None,
) -> bytes:
    """Encode one operation snapshot without consulting live config again."""
    snapshot = configuration.snapshot()
    if (
        set(identity) != {"project_id", "run_id", "task_id", "attempt"}
        or type(identity["attempt"]) is not int
        or identity["attempt"] < 1
        or any(
            not isinstance(identity[key], str) or not identity[key]
            for key in ("project_id", "run_id", "task_id")
        )
    ):
        raise ValueError("configuration_snapshot_identity_invalid")
    payload = {
        "schema_version": 1,
        **identity,
        "configuration": snapshot.config.to_dict(),
        "errors": list(snapshot.errors),
    }
    if device_config_path is not None:
        if not device_config_path.is_absolute() or ".." in device_config_path.parts:
            raise ValueError("configuration_snapshot_identity_invalid")
        payload["native_selection"] = {"device_config_path": str(device_config_path)}
    raw = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    if len(raw) > CONFIGURATION_SNAPSHOT_LIMIT:
        raise ValueError("configuration_snapshot_too_large")
    return raw


def load_configuration_snapshot(
    document: dict[str, Any], prepared_path: Path, environ: dict[str, str]
) -> ConfigurationProvider | None:
    """Read only a body explicitly granted to the native launch adapter.

    A pointer or a metadata-only reference does not authorize this read. Old
    immutable prepared documents without this native contract stay on their
    existing path and do not discover application configuration in a wrapper.
    """
    pointer = environ.get("PF_CONFIGURATION_SNAPSHOT_PATH", "")
    digest = environ.get("PF_CONFIGURATION_SNAPSHOT_SHA256", "")
    native = document.get("native_launch")
    if native is None:
        if pointer or digest:
            raise ValueError("configuration_snapshot_grant_required")
        return None
    grant = native.get("configuration") if isinstance(native, dict) else None
    if (
        not isinstance(grant, dict)
        or set(grant) != {"reader", "access", "path", "sha256", "size"}
        or grant["reader"] != "native"
        or grant["access"] != "body"
        or grant["sha256"] != digest
        or not isinstance(digest, str)
        or re.fullmatch(r"sha256:[0-9a-f]{64}", digest) is None
        or type(grant["size"]) is not int
        or not 1 <= grant["size"] <= CONFIGURATION_SNAPSHOT_LIMIT
    ):
        raise ValueError("configuration_snapshot_grant_invalid")
    root = Path(document["project_root"])
    expected = prepared_path.parent / "configuration.snapshot.json"
    if (
        not root.is_absolute()
        or not expected.is_absolute()
        or not pointer
        or Path(pointer) != expected
        or grant["path"] != expected.relative_to(root).as_posix()
    ):
        raise ValueError("configuration_snapshot_path_mismatch")
    for path in (expected, *expected.parents):
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise ValueError("configuration_snapshot_path_invalid")
        if path == expected and not stat.S_ISREG(info.st_mode):
            raise ValueError("configuration_snapshot_path_invalid")
        if path == root:
            break
    else:
        raise ValueError("configuration_snapshot_path_invalid")
    with expected.open("rb") as stream:
        import os

        opened = os.fstat(stream.fileno())
        before = expected.lstat()
        if (before.st_dev, before.st_ino) != (opened.st_dev, opened.st_ino):
            raise ValueError("configuration_snapshot_path_invalid")
        raw = stream.read(CONFIGURATION_SNAPSHOT_LIMIT + 1)
    if (
        len(raw) != grant["size"]
        or "sha256:" + hashlib.sha256(raw).hexdigest() != digest
    ):
        raise ValueError("configuration_snapshot_digest_mismatch")

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ValueError("configuration_snapshot_invalid")
            result[key] = value
        return result

    payload = json.loads(raw, object_pairs_hook=pairs)
    identity = document["identity"]
    if (
        not isinstance(payload, dict)
        or set(payload)
        not in (
            {
                "schema_version",
                "project_id",
                "run_id",
                "task_id",
                "attempt",
                "configuration",
                "errors",
            },
            {
                "schema_version",
                "project_id",
                "run_id",
                "task_id",
                "attempt",
                "configuration",
                "errors",
                "native_selection",
            },
        )
        or type(payload["schema_version"]) is not int
        or payload["schema_version"] != 1
        or type(payload["attempt"]) is not int
        or payload["attempt"] < 1
        or payload["attempt"] != identity["attempt"]
        or payload["project_id"] != identity["project_id"]
        or payload["run_id"] != identity["run_id"]
        or payload["task_id"] != identity["assignment_id"]
        or not isinstance(payload["errors"], list)
        or any(
            not isinstance(code, str) or re.fullmatch(r"[a-z][a-z0-9_]*", code) is None
            for code in payload["errors"]
        )
    ):
        raise ValueError("configuration_snapshot_identity_mismatch")
    selected_device = None
    if "native_selection" in payload:
        selection = payload["native_selection"]
        if (
            not isinstance(selection, dict)
            or set(selection) != {"device_config_path"}
            or not isinstance(selection["device_config_path"], str)
        ):
            raise ValueError("configuration_snapshot_identity_mismatch")
        selected_device = Path(selection["device_config_path"])
        if not selected_device.is_absolute() or ".." in selected_device.parts:
            raise ValueError("configuration_snapshot_identity_mismatch")
    pinned = ConfigurationProvider.pinned(
        PFConfig.from_dict(payload["configuration"]), errors=tuple(payload["errors"])
    )
    # Native provenance, authenticated by the exact body grant/hash above.
    # The provider remains value-pinned: this path is never a new read grant.
    object.__setattr__(pinned, "device_path", selected_device)
    return pinned


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
        execution_value = task.get("execution_mode")
        execution = execution_value if isinstance(execution_value, dict) else {}
        ownership_value = task.get("ownership")
        ownership = ownership_value if isinstance(ownership_value, dict) else {}
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
        capsule_path = (
            self.inputs.locate_flow_root(project_root)
            / "contexts"
            / "assignment-capsules"
            / f"{task_id}.capsule.yaml"
        )
        prompt_path = self.paths.worker_prompt(project_root, run_id, task_id)
        try:
            report_path = self.outputs.path(
                project_root, self.outputs.expected_report(task)
            )
            for output in self.inputs.normalize_required_outputs(
                task.get("required_outputs")
            ):
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
            "prepared_input_path": str(project_root / prepared_input["path"])
            if prepared_input
            else "",
            "prepared_input_checksum": prepared_input["checksum"]
            if prepared_input
            else "",
            "expected_report_path": str(report_path),
            "python_executable": sys.executable,
            "executable": executable_override or "",
            "stdout_path": str(paths["stdout"]),
            "stderr_path": str(paths["stderr"]),
            "heartbeat_path": str(paths["heartbeat"]),
            "exit_path": str(paths["exit"]),
            "agent_model": self.inputs.normalize_agent_model(
                task.get("agent_model") or task.get("model") or ""
            ),
            "agent_reasoning_effort": self.inputs.normalize_agent_reasoning_effort(
                task.get("agent_reasoning_effort") or task.get("reasoning_effort") or ""
            ),
            "agent_sandbox": self.sandbox(task),
        }
        io_value = driver.get("io")
        io = io_value if isinstance(io_value, dict) else {}
        stdout_path = Path(
            str(
                self.environment.expand(
                    io.get("stdout") or rel(paths["stdout"], project_root), variables
                )
            )
        )
        stderr_path = Path(
            str(
                self.environment.expand(
                    io.get("stderr") or rel(paths["stderr"], project_root), variables
                )
            )
        )
        if not stdout_path.is_absolute():
            stdout_path = (project_root / stdout_path).resolve()
        if not stderr_path.is_absolute():
            stderr_path = (project_root / stderr_path).resolve()
        paths["stdout"] = stdout_path
        paths["stderr"] = stderr_path
        heartbeat_value = driver.get("heartbeat")
        heartbeat = heartbeat_value if isinstance(heartbeat_value, dict) else {}
        heartbeat_path = Path(
            str(
                self.environment.expand(
                    heartbeat.get("path") or rel(paths["heartbeat"], project_root),
                    variables,
                )
            )
        )
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
        command_value = driver.get("command")
        command_spec = command_value if isinstance(command_value, dict) else {}
        executable = executable_override or str(
            self.environment.expand(command_spec.get("executable") or "", variables)
        )
        args = self.environment.expand(
            command_spec.get("args")
            if isinstance(command_spec.get("args"), list)
            else [],
            variables,
        )
        if (
            driver.get("id") == "native-maintenance-fixed-v1"
            and isinstance(command_spec.get("args"), list)
            and command_spec["args"][2:3]
            == ["{processforge_root}/tools/pf_native_maintenance.py"]
        ):
            args[2] = str(self.distribution_root / "tools" / "pf_native_maintenance.py")
        if variables["agent_model"]:
            model_args_raw = (
                command_spec.get("model_args")
                if "model_args" in command_spec
                else ["--model", "{agent_model}"]
            )
            if not isinstance(model_args_raw, list):
                raise SystemExit(
                    "FAIL: runtime driver command.model_args must be a list when model is set"
                )
            args.extend(self.environment.expand(model_args_raw, variables))
        env, inherit_env = self.environment.build(driver, variables)
        if driver.get("prepared_lifecycle_wrapper") is True and executable:
            if not prepared_input:
                raise SystemExit("FAIL: prepared_input_required")
            args = [
                str(self.distribution_root / "tools" / "prepared_executor.py"),
                "--prepared-input",
                variables["prepared_input_path"],
                "--prepared-sha256",
                variables["prepared_input_checksum"],
                "--heartbeat",
                str(paths["heartbeat"]),
                "--exit-path",
                str(paths["exit"]),
                "--",
                executable,
                *args,
            ]
            if driver.get("id") == "native-maintenance-fixed-v1":
                args = ["-I", "-B", *args]
            executable = sys.executable
        working_directory = str(
            self.environment.expand(
                driver.get("working_directory") or "{project_root}", variables
            )
        )
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
            "paths": {
                key: rel(path, project_root)
                for key, path in paths.items()
                if key != "root"
            },
            "limits": self.drivers.parse_limits(driver)[0],
        }
        driver_ref = driver.get("_driver_ref")
        if isinstance(driver_ref, str) and driver_ref.strip():
            command["driver_ref"] = driver_ref.strip()
        return command, paths
