# Runtime Drivers

Runtime drivers describe how ProcessForge may prepare or start a worker task.
They are optional. The default driver is `manual`, which writes launch material
and requires a human or external workplace to run the task.

Built-in drivers:

- `manual`: prepares state and never starts a process.
- `generic-shell`: starts an explicit executable with configured arguments.
- `codex-exec`: starts a Codex CLI worker with the assignment capsule, worker
  prompt, and private workspace access file.
- `test-echo-worker`: local smoke-test worker that writes the expected report.
- `test-shell-agent`: local smoke-test shell agent that writes report,
  stdout/stderr, process, heartbeat, and exit proof artifacts.

Driver manifests live under `templates/runtime-drivers/`. The built-in registry
is `templates/registries/runtime-drivers.yaml`. A project may add local registry
overrides under `.pf/runtime/registries/runtime-drivers.local.yaml`.

Use the CLI from an onboarded project:

```bash
python .pf/runtime/bin/pf.py runtime-driver list --project-root .
python .pf/runtime/bin/pf.py runtime-driver validate --project-root . --driver manual
python .pf/runtime/bin/pf.py runtime-driver describe --project-root . --driver test-echo-worker
```

Driver placeholders are restricted to runtime facts such as `{project_root}`,
`{run_id}`, `{task_id}`, `{agent_run_dir}`, `{driver_id}`,
`{capsule_path}`, `{worker_prompt_path}`, `{workspace_access_path}`,
`{expected_report_path}`, `{stdout_path}`, `{stderr_path}`,
`{heartbeat_path}`, `{exit_path}`, `{agent_model}`, and
`{agent_reasoning_effort}`.
Unknown placeholders fail validation.

ProcessForge always injects reserved worker environment variables including
`PF_RUN_ID`, `PF_TASK_ID`, `PF_AGENT_RUN_DIR`, `PF_AGENT_EXIT_PATH`,
`PF_AGENT_MODEL`, `PF_PROJECT_ROOT`, `PF_RUNTIME_DRIVER_ID`,
`PF_AGENT_REASONING_EFFORT`, `PF_WORKSPACE_ACCESS_FILE`, `PF_WORKER_RUN_ID`,
and `PF_WORKER_TASK_ID`. Shell drivers cannot override those names. A detached
contract-aware worker should write its final marker to `PF_AGENT_EXIT_PATH`;
if the supervisor later observes a lost process without that marker, it records
`unknown_exit` instead of inferring success from a report artifact.

When a shell worker has an agent model, ProcessForge exposes it as
`PF_AGENT_MODEL` and `{agent_model}`. If the driver command does not define
`model_args`, ProcessForge appends `--model {agent_model}` only when the model
is non-empty.

## Codex Exec

`codex-exec` is the built-in driver for launching shell-agents through the
Codex CLI. ProcessForge writes the assignment capsule, worker prompt, expected
report path, heartbeat path, and private `workspace-access.json` file, then the
driver runs `tools/codex_exec_worker.py`.

The driver does not choose the model. The orchestrator must provide one through
`agent_model`, `--model`, plan-level `runtime.model`, or worker-level `model`.
As an operator override, `PF_CODEX_MODEL` is accepted when `PF_AGENT_MODEL` is
empty; if neither is set, `codex-exec` fails before starting Codex.

Reasoning effort is selected separately. Valid values are `minimal`, `low`,
`medium`, and `high`. ProcessForge stores the selected value as
`agent_reasoning_effort`, exposes it as `PF_AGENT_REASONING_EFFORT`, and the
`codex-exec` manifest maps it to `PF_CODEX_REASONING_EFFORT`. The wrapper then
passes it to Codex as `-c model_reasoning_effort="<value>"`. When the value is
empty, no reasoning config argument is added.

Workspace access is resolved privately at runtime. Public assignments and
capsules may contain resource ids or `path_ref` values, but private absolute
paths are written only to `.pf/runtime/agent-runs/.../workspace-access.json`.
`codex-exec` reads that runtime file and grants resolved directories to Codex
with `--add-dir`.

Prepare and start one Codex shell-agent directly:

```bash
python .pf/runtime/bin/pf.py task-create --project-root . --run docs-run --id docs-worker --title "Docs worker" --process task-batch-execution --allowed-file ".pf/artifacts/**" --workspace-knowledge-resource <knowledge-resource-id> --reasoning-effort high --apply
python .pf/runtime/bin/pf.py worker-run start --project-root . --task docs-worker --driver codex-exec --model chatgpt-5.3-codex-spark --reasoning-effort high
```

Run another worker with the same model and medium reasoning:

```bash
python .pf/runtime/bin/pf.py worker-run start --project-root . --task test-worker --driver codex-exec --model chatgpt-5.3-codex-spark --reasoning-effort medium
```

For orchestrated shell-agent plans, set the default in the plan and override per
worker only when needed:

```yaml
runtime:
  default_driver: codex-exec
  model: chatgpt-5.3-codex-spark
  reasoning_effort: medium
workers:
  - id: docs-worker
    title: Docs worker
    process: task-batch-execution
    reasoning_effort: high
    workspace_access:
      knowledge_resources:
        - docs.joomla
```

Apply the plan:

```bash
python bin/pf.py orchestrator-shell-plan-apply --project-root . --run docs-run --apply
```

`orchestrator-shell-plan-apply --model <model>` can override the plan model for
all generated shell workers. Reasoning effort is currently selected in the plan,
in the generated assignment, or on `worker-run prepare/start` with
`--reasoning-effort`.

Shell execution uses `shell=False`. Generic shell drivers have no network
permission by default; `codex-exec` explicitly declares network access because
the Codex CLI must reach its configured model provider.

ProcessForge does not install agents, create agent folders, or require a daemon
for driver registry use.
