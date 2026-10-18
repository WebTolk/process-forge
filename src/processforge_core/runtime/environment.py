"""Worker environment construction, launch materialization and value expansion."""

from __future__ import annotations

import os
import re
from typing import Any

from processforge_core.runtime.drivers import RESERVED_WORKER_ENV_KEYS


class WorkerEnvironmentPolicy:
    """Keep persisted worker values separate from inherited launch environment."""

    def minimal(self) -> dict[str, str]:
        if os.name != "nt":
            return {}
        names = ["SystemRoot", "WINDIR", "COMSPEC", "PATHEXT", "TEMP", "TMP"]
        return {name: value for name in names if (value := os.environ.get(name))}

    def build(self, driver: dict[str, Any], variables: dict[str, str]) -> tuple[dict[str, str], bool]:
        env_spec = driver.get("environment") if isinstance(driver.get("environment"), dict) else {}
        inherit = bool(env_spec.get("inherit", True))
        # Persist only PF-owned and explicitly configured values. Inherited host
        # environment may contain credentials and is materialized only at launch.
        env = {} if inherit else self.minimal()
        env.update(
            {
                "PF_RUN_ID": variables["run_id"],
                "PF_TASK_ID": variables["task_id"],
                "PF_AGENT_RUN_DIR": variables["agent_run_dir"],
                "PF_AGENT_EXIT_PATH": variables["exit_path"],
                "PF_AGENT_MODEL": variables["agent_model"],
                "PF_AGENT_REASONING_EFFORT": variables["agent_reasoning_effort"],
                "PF_PROJECT_ROOT": variables["project_root"],
                "PF_RUNTIME_DRIVER_ID": variables["driver_id"],
                "PF_WORKSPACE_ACCESS_FILE": variables["workspace_access_path"],
                "PF_WORKER_RUN_ID": variables["run_id"],
                "PF_WORKER_TASK_ID": variables["task_id"],
                "PF_WORKER_ATTEMPT": variables["attempt"],
                "PF_PREPARED_INPUT_FILE": variables.get("prepared_input_path", ""),
                "PF_PREPARED_INPUT_SHA256": variables.get("prepared_input_checksum", ""),
            }
        )
        explicit = env_spec.get("variables") if isinstance(env_spec.get("variables"), dict) else {}
        reserved = sorted(str(key) for key in explicit if str(key) in RESERVED_WORKER_ENV_KEYS)
        if reserved:
            raise SystemExit("FAIL: runtime driver cannot override reserved ProcessForge environment variables: " + ", ".join(reserved))
        expanded = self.expand(explicit, variables)
        env.update({str(key): str(value) for key, value in expanded.items()})
        return env, inherit

    def materialize(self, command_spec: dict[str, Any]) -> dict[str, str]:
        inherit = bool(command_spec.get("environment_inherit", False))
        env = os.environ.copy() if inherit else self.minimal()
        persisted = command_spec.get("environment") if isinstance(command_spec.get("environment"), dict) else {}
        env.update({str(key): str(value) for key, value in persisted.items()})
        return env

    def expand(self, value: Any, variables: dict[str, str]) -> Any:
        if isinstance(value, str):
            def replace(match: re.Match[str]) -> str:
                key = match.group(1)
                if key not in variables:
                    raise SystemExit(f"FAIL: unsupported runtime placeholder: {{{key}}}")
                return variables[key]

            return re.sub(r"\{([a-zA-Z0-9_]+)\}", replace, value)
        if isinstance(value, list):
            return [str(self.expand(item, variables)) for item in value]
        if isinstance(value, dict):
            return {str(key): self.expand(item, variables) for key, item in value.items()}
        return value
