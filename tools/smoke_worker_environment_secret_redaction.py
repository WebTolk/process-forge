from __future__ import annotations

import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import processforge as pf  # noqa: E402


def main() -> int:
    inherited_key = "PF_TEST_INHERITED_VALUE"
    inherited_value = "sentinel-private-value"
    previous = os.environ.get(inherited_key)
    os.environ[inherited_key] = inherited_value
    try:
        variables = {
            "run_id": "run-a",
            "task_id": "task-a",
            "agent_run_dir": "runtime/agent-runs/run-a/task-a",
            "exit_path": "runtime/agent-runs/run-a/task-a/exit.json",
            "agent_model": "model-a",
            "agent_reasoning_effort": "low",
            "project_root": str(ROOT),
            "driver_id": "generic-shell",
            "workspace_access_path": "runtime/agent-runs/run-a/task-a/workspace-access.json",
            "attempt": "1",
        }
        driver = {
            "environment": {
                "inherit": True,
                "variables": {"PF_TEST_EXPLICIT_VALUE": "explicit-value"},
            }
        }

        persisted, inherit = pf.build_worker_environment(driver, variables)
        assert inherit is True
        assert inherited_key not in persisted
        assert persisted["PF_TEST_EXPLICIT_VALUE"] == "explicit-value"
        assert persisted["PF_RUN_ID"] == "run-a"
        assert inherited_value not in json.dumps(persisted, sort_keys=True)

        launch_env = pf.materialize_worker_launch_environment(
            {"environment": persisted, "environment_inherit": inherit}
        )
        assert launch_env[inherited_key] == inherited_value
        assert launch_env["PF_TEST_EXPLICIT_VALUE"] == "explicit-value"
    finally:
        if previous is None:
            os.environ.pop(inherited_key, None)
        else:
            os.environ[inherited_key] = previous

    print("PASS: inherited worker environment is launch-only and absent from durable command state")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
