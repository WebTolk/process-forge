"""Runtime driver definitions and document validation policy."""

from __future__ import annotations

import re
from typing import Any

from processforge_core.common.checks import Check, check


RESERVED_WORKER_ENV_KEYS = {
    "PF_RUN_ID",
    "PF_TASK_ID",
    "PF_AGENT_RUN_DIR",
    "PF_AGENT_EXIT_PATH",
    "PF_AGENT_MODEL",
    "PF_AGENT_REASONING_EFFORT",
    "PF_PROJECT_ROOT",
    "PF_RUNTIME_DRIVER_ID",
    "PF_WORKSPACE_ACCESS_FILE",
    "PF_WORKER_RUN_ID",
    "PF_WORKER_TASK_ID",
    "PF_WORKER_ATTEMPT",
    "PF_PREPARED_INPUT_FILE",
    "PF_PREPARED_INPUT_SHA256",
}


RUNTIME_DRIVER_PLACEHOLDERS = {
    "attempt",
    "prepared_input_path",
    "project_root",
    "processforge_root",
    "run_id",
    "task_id",
    "agent_run_dir",
    "driver_id",
    "capsule_path",
    "worker_prompt_path",
    "workspace_access_path",
    "expected_report_path",
    "python_executable",
    "executable",
    "stdout_path",
    "stderr_path",
    "heartbeat_path",
    "exit_path",
    "agent_model",
    "agent_reasoning_effort",
    "agent_sandbox",
}


class RuntimeDriverDefinitionPolicy:
    """Build and validate runtime driver documents without executing drivers."""

    def default_documents(self) -> dict[str, dict[str, Any]]:
        return {
            "manual": {
                "schema_version": 1,
                "id": "manual",
                "title": "Manual Worker Execution",
                "kind": "manual",
                "behavior": {
                    "create_worker_prompt": True,
                    "create_capsule": True,
                    "do_not_start_process": True,
                },
            },
            "generic-shell": {
                "schema_version": 1,
                "id": "generic-shell",
                "title": "Generic Shell Runtime",
                "kind": "shell",
                "prepared_lifecycle_wrapper": True,
                "command": {
                    "executable": "{executable}",
                    "args": ["{worker_prompt_path}", "{capsule_path}"],
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
                "limits": {"timeout_seconds": 3600, "max_retries": 0},
                "security": {
                    "allow_shell": False,
                    "require_explicit_executable": True,
                    "allow_network": False,
                },
            },
            "codex-exec": {
                "schema_version": 1,
                "id": "codex-exec",
                "title": "Codex Exec Worker",
                "kind": "shell",
                "command": {
                    "executable": "{python_executable}",
                    "args": [
                        "{processforge_root}/tools/codex_exec_worker.py",
                        "--worker-prompt",
                        "{worker_prompt_path}",
                        "--capsule",
                        "{capsule_path}",
                        "--workspace-access",
                        "{workspace_access_path}",
                        "--output",
                        "{expected_report_path}",
                        "--heartbeat",
                        "{heartbeat_path}",
                    ],
                    "model_args": [],
                },
                "working_directory": "{project_root}",
                "environment": {
                    "inherit": True,
                    "variables": {
                        "PF_CODEX_REASONING_EFFORT": "{agent_reasoning_effort}",
                        "PF_CODEX_SANDBOX": "{agent_sandbox}",
                        "PF_CODEX_MEMORIES": "false",
                    },
                },
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
                "limits": {"timeout_seconds": 3600, "max_retries": 0},
                "security": {
                    "allow_shell": False,
                    "require_explicit_executable": False,
                    "allow_network": True,
                    "network_reason": "Codex CLI requires network access to reach its configured model provider.",
                },
            },
            "test-echo-worker": {
                "schema_version": 1,
                "id": "test-echo-worker",
                "title": "Test Echo Worker",
                "kind": "shell",
                "command": {
                    "executable": "{python_executable}",
                    "args": [
                        "{processforge_root}/tools/test_workers/echo_worker.py",
                        "--capsule",
                        "{capsule_path}",
                        "--output",
                        "{expected_report_path}",
                        "--heartbeat",
                        "{heartbeat_path}",
                    ],
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
                "limits": {"timeout_seconds": 30, "max_retries": 0},
                "security": {
                    "allow_shell": False,
                    "require_explicit_executable": False,
                    "allow_network": False,
                },
            },
            "test-shell-agent": {
                "schema_version": 1,
                "id": "test-shell-agent",
                "title": "Test Shell Agent",
                "kind": "shell",
                "command": {
                    "executable": "{python_executable}",
                    "args": [
                        "{processforge_root}/tools/test_agents/pf_shell_agent.py",
                        "--capsule",
                        "{capsule_path}",
                        "--worker-prompt",
                        "{worker_prompt_path}",
                        "--output",
                        "{expected_report_path}",
                        "--heartbeat",
                        "{heartbeat_path}",
                        "--mode",
                        "success",
                    ],
                    "model_args": ["--model", "{agent_model}"],
                },
                "working_directory": "{project_root}",
                "environment": {
                    "inherit": False,
                    "variables": {},
                },
                "io": {
                    "stdin": "none",
                    "stdout": ".pf/runtime/agent-runs/{run_id}/{task_id}/stdout.log",
                    "stderr": ".pf/runtime/agent-runs/{run_id}/{task_id}/stderr.log",
                },
                "heartbeat": {
                    "mode": "file",
                    "path": ".pf/runtime/agent-runs/{run_id}/{task_id}/heartbeat.json",
                    "optional": False,
                },
                "limits": {"timeout_seconds": 30, "max_retries": 0},
                "security": {
                    "allow_shell": False,
                    "require_explicit_executable": False,
                    "allow_network": False,
                },
            },
        }

    def default_registry(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "runtime_drivers": [
                {
                    "id": driver_id,
                    "path": f"../runtime-drivers/{driver_id}.yaml",
                    "status": "available",
                    "builtin": True,
                }
                for driver_id in ["manual", "generic-shell", "codex-exec", "test-echo-worker", "test-shell-agent"]
            ],
        }

    def placeholder_errors(self, value: Any, label: str) -> list[str]:
        errors: list[str] = []
        if isinstance(value, str):
            for match in re.findall(r"\{([a-zA-Z0-9_]+)\}", value):
                if match not in RUNTIME_DRIVER_PLACEHOLDERS:
                    errors.append(f"{label}: unsupported placeholder {{{match}}}")
        elif isinstance(value, list):
            for index, item in enumerate(value):
                errors.extend(self.placeholder_errors(item, f"{label}[{index}]"))
        elif isinstance(value, dict):
            for key, item in value.items():
                errors.extend(self.placeholder_errors(item, f"{label}.{key}"))
        return errors

    def parse_limits(self, driver: dict[str, Any]) -> tuple[dict[str, int], list[str]]:
        raw_limits = driver.get("limits") if isinstance(driver.get("limits"), dict) else {}
        parsed: dict[str, int] = {}
        errors: list[str] = []
        defaults = {"timeout_seconds": 30, "max_retries": 0}
        minimums = {"timeout_seconds": 1, "max_retries": 0}
        for key, default in defaults.items():
            raw_value = raw_limits.get(key, default)
            if isinstance(raw_value, bool):
                errors.append(f"limits.{key}: expected integer, got boolean")
                parsed[key] = default
                continue
            try:
                value = int(raw_value)
            except (TypeError, ValueError):
                errors.append(f"limits.{key}: expected integer, got {raw_value!r}")
                parsed[key] = default
                continue
            if value < minimums[key]:
                errors.append(f"limits.{key}: expected >= {minimums[key]}, got {value}")
            parsed[key] = value
        return parsed, errors

    def start_readiness(self, driver: dict[str, Any], executable_override: str | None = None) -> list[Check]:
        checks: list[Check] = []
        kind = str(driver.get("kind") or "")
        if kind != "shell":
            return checks
        command = driver.get("command") if isinstance(driver.get("command"), dict) else {}
        raw_executable = str(command.get("executable") or "")
        security = driver.get("security") if isinstance(driver.get("security"), dict) else {}
        resolved_executable = executable_override or ("" if raw_executable == "{executable}" else raw_executable)
        if security.get("require_explicit_executable") is True and raw_executable == "{executable}" and not executable_override:
            checks.append(check("FAIL", "start readiness executable override required for {executable}"))
        elif not resolved_executable:
            checks.append(check("FAIL", "start readiness executable resolves to empty value"))
        else:
            checks.append(check("PASS", f"start readiness executable: {resolved_executable}"))
        return checks

    def validate(self, driver: dict[str, Any], executable_override: str | None = None, include_start_readiness: bool = False) -> list[Check]:
        checks: list[Check] = []
        driver_id = str(driver.get("id") or "")
        kind = str(driver.get("kind") or "")
        checks.append(check("PASS" if driver.get("schema_version") else "FAIL", "schema_version present"))
        checks.append(check("PASS" if driver_id else "FAIL", "id present"))
        checks.append(check("PASS" if kind in {"manual", "shell"} else "FAIL", f"kind valid: {kind or 'missing'}"))
        if "prepared_lifecycle_wrapper" in driver:
            checks.append(check("PASS" if type(driver["prepared_lifecycle_wrapper"]) is bool else "FAIL", "prepared_lifecycle_wrapper is boolean"))
        security = driver.get("security") if isinstance(driver.get("security"), dict) else {}
        env_spec = driver.get("environment") if isinstance(driver.get("environment"), dict) else {}
        explicit_env = env_spec.get("variables") if isinstance(env_spec.get("variables"), dict) else {}
        reserved_env = sorted(str(key) for key in explicit_env if str(key) in RESERVED_WORKER_ENV_KEYS)
        checks.append(check("FAIL" if reserved_env else "PASS", "reserved ProcessForge env vars not overridden" + (f": {', '.join(reserved_env)}" if reserved_env else "")))
        if kind == "shell":
            command = driver.get("command") if isinstance(driver.get("command"), dict) else {}
            executable = str(command.get("executable") or "")
            args = command.get("args") if isinstance(command.get("args"), list) else []
            model_args = command.get("model_args") if "model_args" in command else []
            checks.append(check("PASS" if executable else "FAIL", "shell command executable present"))
            checks.append(check("PASS" if isinstance(args, list) else "FAIL", "shell command args list present"))
            checks.append(check("PASS" if isinstance(model_args, list) else "FAIL", "shell command model_args list when present"))
            checks.append(check("WARN" if security.get("allow_shell") is True else "PASS", "allow_shell false by default"))
            network_reason = str(security.get("network_reason") or "").strip()
            checks.append(check("PASS" if security.get("allow_network") is not True or network_reason else "FAIL", "allow_network explicit reason when enabled"))
        if kind == "manual":
            behavior = driver.get("behavior") if isinstance(driver.get("behavior"), dict) else {}
            checks.append(check("PASS" if behavior.get("do_not_start_process") is True else "FAIL", "manual driver does not start process"))
        limits, limit_errors = self.parse_limits(driver)
        for error in limit_errors:
            checks.append(check("FAIL", error))
        if not limit_errors:
            checks.append(check("PASS", f"limits valid: timeout_seconds={limits['timeout_seconds']} max_retries={limits['max_retries']}"))
        for error in self.placeholder_errors(driver, "driver"):
            checks.append(check("FAIL", error))
        if include_start_readiness:
            checks.extend(self.start_readiness(driver, executable_override))
        return checks
