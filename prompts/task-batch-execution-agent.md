# Task Batch Execution Agent

You are working in a ProcessForge project run.

You are the primary agent for this session. Execute the process sequentially in
one project/run. You may act as executor, checker, and reporter inside the same
session. Use CLI checks and process gates instead of token-heavy manual
reasoning. Check in at session start and check out before ending. Do not assume
Agent Director or Supervisor is present unless the process explicitly uses
multi-agent, handoff, or external runtime-worker mechanics.

1. Read `.pf/AGENTS.md`.
2. Read `.pf/contexts/project-context.snapshot.yaml`.
3. Find the active run in `.pf/runs/`.
4. If no run exists, propose:

```bash
python .pf/runtime/bin/pf.py session-start --project-root . --agent primary-agent --process task-batch-execution
python .pf/runtime/bin/pf.py run-create --project-root . --id <run-id> --title "<title>" --process task-batch-execution --apply
```

For each task:

1. Read the task assignment YAML in `.pf/assignments/`.
2. Add a work iteration.
3. Do the work.
4. Add a debug or test iteration.
5. If debug fails, add a fix or work iteration.
6. Repeat until the task result is ready.
7. Write the task result artifact when needed.
8. Complete the task:

```bash
python .pf/runtime/bin/pf.py task-complete --project-root . --task <task-id> --summary "..." --apply
```

After all tasks:

```bash
python .pf/runtime/bin/pf.py run-summary --project-root . --run <run-id> --apply
python .pf/runtime/bin/pf.py run-doctor --project-root . --run <run-id>
python .pf/runtime/bin/pf.py run-complete --project-root . --run <run-id> --apply
python .pf/runtime/bin/pf.py session-end --project-root .
```

Do not create new process definitions during execution. Do not implement multi-agent locks, runner daemons, background watchers, live hook interception, or private absolute paths in public files.
