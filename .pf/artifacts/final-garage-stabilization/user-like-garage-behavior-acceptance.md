# User-Like Garage Behavior Acceptance

Date: 2026-08-24
Result: pass

Original user-like prompt:

```text
Load the project by .pf and complete the task from task.md.
```

Verified tool-call sequence:

```text
tools/list
pf.context
pf.search
pf.resolve
pf.work.start
```

PF calls:

- `pf.context`: project context and search readiness;
- `pf.search`: project-local `project-profile` metadata hit;
- `pf.resolve`: project-local profile resource;
- `pf.work.start`: created governed work from a high-level objective.

Fallbacks and manual infrastructure actions:

```text
manual session-start count: 0
manual search-index refresh count: 0
manual run-create count: 0
manual task-create count: 0
manual stage guessing count: 0
global workplace rg count: 0
```

Evidence:

```text
python tools/smoke_user_like_garage_path.py
PASS: user-like Garage path reaches governed work without manual infrastructure
```
