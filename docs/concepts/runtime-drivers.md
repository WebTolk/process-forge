# Runtime Drivers

Runtime drivers describe how ProcessForge may prepare or start a worker task.
They are optional. The default driver is `manual`, which writes launch material
and requires a human or external workplace to run the task.

Built-in neutral drivers:

- `manual`: prepares state and never starts a process.
- `generic-shell`: starts an explicit executable with configured arguments.
- `test-echo-worker`: local smoke-test worker that writes the expected report.

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
`{run_id}`, `{task_id}`, `{capsule_path}`, `{worker_prompt_path}`,
`{expected_report_path}`, `{stdout_path}`, `{stderr_path}`, and
`{heartbeat_path}`. Unknown placeholders fail validation.

Shell execution uses `shell=False` and no network permission by default.
ProcessForge does not install agents, create agent folders, or require a daemon
for driver registry use.
