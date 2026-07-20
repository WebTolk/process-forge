# Multiagent Assignment Handoff Contract

Date: 2026-07-20
Run: `pf-update-framework-implementation-20260720`
Task: `task-002-multiagent-assignment-contract`
Status: planning-ready; no code changes

## 1. Purpose

ProcessForge needs a first-class assignment/handoff contract for multiagent runs where several active workers operate in the same repository.

The contract must make each worker's boundary machine-readable before work starts:

- what context the worker must read
- what files the worker may write
- what files and scopes are explicitly forbidden
- who owns each write scope
- what outputs are required
- which active assignments must not overlap
- what report or handoff the worker must return

The immediate goal is to support safe subagent assignment capsules. The implementation should remain file-first and compatible with the current `.pf/` layout.

## 2. Assignment YAML Fields

### 2.1. Identity And Lifecycle

Assignments should continue to carry stable identity fields:

```yaml
schema_version: 1
id: task-002-multiagent-assignment-contract
title: Design non-overlapping multiagent assignment contract
run_id: pf-update-framework-implementation-20260720
process: software-feature-development
stage: design
status: in_progress
created_at: "2026-07-20T08:27:41Z"
updated_at: "2026-07-20T08:28:08Z"
order: 2
```

Recommended status values:

- `pending`
- `in_progress`
- `blocked`
- `ready_for_review`
- `completed`
- `cancelled`
- `superseded`

### 2.2. Objective And Execution Mode

Each assignment should state the work boundary in human-readable and machine-readable form:

```yaml
objective: Produce a planning artifact for the multiagent assignment contract.
execution_mode:
  kind: planning_only
  code_changes_allowed: false
  artifact_changes_allowed: true
  requires_review: true
```

Recommended `execution_mode.kind` values:

- `read_only`
- `planning_only`
- `docs_only`
- `implementation`
- `assurance`
- `release_delivery`

`code_changes_allowed` must be explicit for multiagent work. If omitted, orchestrator tools should treat the assignment as not safe for writes outside artifacts.

### 2.3. Context Artifacts

`context_artifacts` should list durable inputs the worker must read or consider:

```yaml
context_artifacts:
  - path: .pf/artifacts/update-framework-implementation-spec-20260720.md
    role: background
    required: true
    mutable_by_worker: false
  - path: .pf/assignments/task-001-update-contracts-readonly.yaml
    role: parallel_scope_reference
    required: true
    mutable_by_worker: false
```

For backward compatibility, a plain list of paths can remain valid:

```yaml
context_artifacts:
  - .pf/artifacts/update-framework-implementation-spec-20260720.md
```

The normalized internal model should expand plain paths to:

```yaml
role: input
required: true
mutable_by_worker: false
```

### 2.4. Required Sources

`required_sources` should list sources that must be bundled into or referenced by the assignment capsule:

```yaml
required_sources:
  - .pf/AGENTS.md
  - .pf/process-forge.yaml
  - .pf/contexts/project-context.snapshot.yaml
  - .pf/assignments/task-002-multiagent-assignment-contract.yaml
```

This field is stricter than `context_artifacts`: missing required sources should block capsule generation.

### 2.5. File Scope Fields

Assignments should separate readable context from writable scope.

```yaml
allowed_files:
  - .pf/artifacts/multiagent-assignment-contract-20260720.md

allowed_read_files:
  - .pf/AGENTS.md
  - .pf/process-forge.yaml
  - .pf/contexts/project-context.snapshot.yaml
  - .pf/assignments/task-002-multiagent-assignment-contract.yaml
  - .pf/artifacts/update-framework-implementation-spec-20260720.md

forbidden_files:
  - tools/processforge.py
  - tools/validate-process-forge-schemas.py
  - schemas/*
  - templates/*
```

Recommended semantics:

- `allowed_files` means write scope.
- `allowed_read_files` means explicit read scope for narrow capsules.
- `forbidden_files` blocks writes and can optionally warn on reads when the path belongs to another active worker.
- if `allowed_files` is present, writes outside it require a handoff or assignment update.
- forbidden scope wins over allowed scope.

Path patterns should use repository-relative POSIX-style paths in stored YAML. Runtime tools may normalize Windows paths before comparison.

### 2.6. Ownership

`ownership` should identify the worker and scope owner:

```yaml
ownership:
  owner_id: task-002-multiagent-assignment-contract
  owner_label: worker-task-002
  role: planning-worker
  writer: true
  owned_files:
    - .pf/artifacts/multiagent-assignment-contract-20260720.md
  owned_globs: []
```

Recommended rules:

- `owned_files` and `owned_globs` are write ownership claims.
- `writer: false` means the assignment may read but should not change project files.
- every writable `allowed_files` path should be covered by `ownership`.
- one file or glob scope must have only one active writer.

### 2.7. Non-Overlap Contract

`non_overlap` should define active tasks and scope constraints that must be checked before worker launch:

```yaml
non_overlap:
  policy: block_on_write_overlap
  active_parallel_tasks:
    - id: task-001-update-contracts-readonly
      owner: Descartes
      write_scope:
        - schemas/*
        - templates/*
        - tools/processforge.py
        - tools/validate-process-forge-schemas.py
  current_write_scope:
    - .pf/artifacts/multiagent-assignment-contract-20260720.md
  rule: Do not edit files owned by active parallel tasks.
```

For backward compatibility, existing singular fields can remain valid:

```yaml
non_overlap:
  active_parallel_task: task-001-update-contracts-readonly
  active_parallel_owner: Descartes
  active_parallel_scope:
    - schemas/*
```

The normalized model should convert singular values to `active_parallel_tasks`.

### 2.8. Required Outputs

`required_outputs` should support named output contracts, not only labels:

```yaml
required_outputs:
  - id: changed_files
    type: list
    required: true
  - id: proposed_assignment_schema_fields
    type: markdown_section
    required: true
  - id: capsule_generation_requirements
    type: markdown_section
    required: true
  - id: non_overlap_rules
    type: markdown_section
    required: true
  - id: implementation_followup_tasks
    type: markdown_section
    required: true
```

Plain string entries can remain valid and normalize to:

```yaml
type: unspecified
required: true
```

### 2.9. Expected Report

`expected_report` should tell the worker what the final answer or durable report must contain:

```yaml
expected_report:
  language: ru
  format: concise_markdown
  include:
    - changed_files
    - checks_run
    - checks_not_run
    - blockers
  artifact: .pf/artifacts/multiagent-assignment-contract-20260720.md
```

For multiagent runs, the expected report is part of the handoff boundary. It prevents workers from returning chat-only conclusions when durable artifacts are required.

### 2.10. Dependencies And Blocking

Assignments should keep dependency data machine-readable:

```yaml
dependencies:
  blocked_by: []
  blocks:
    - task-003-implement-assignment-contract
  reads_from:
    - task-001-update-contracts-readonly
  must_not_start_with:
    - task-conflicting-writer
```

`reads_from` permits informational dependency without making the assignment blocked. `must_not_start_with` blocks concurrent launch.

### 2.11. Result

`result` should remain writable by the orchestrator or worker only after task completion:

```yaml
result:
  status: pending
  summary: ""
  artifacts: []
  changed_files: []
  checks:
    run: []
    not_run: []
  residual_risks: []
```

For the current planning-only slice, updating the assignment result is out of scope because the task explicitly permits only the planning artifact.

## 3. Assignment Capsule Fields

The assignment capsule should be a launch-ready immutable handoff snapshot. It should include enough context for a worker to start without rediscovering mutable orchestration state.

Recommended capsule shape:

```yaml
schema_version: 1
capsule:
  id: task-002-multiagent-assignment-contract-capsule
  generated_at: "2026-07-20T08:28:08Z"
  assignment_id: task-002-multiagent-assignment-contract
  assignment_path: .pf/assignments/task-002-multiagent-assignment-contract.yaml
  snapshot: .pf/contexts/project-context.snapshot.yaml
  snapshot_checksum: sha256hex
  worker_may_rebuild_context: false

assignment:
  id: task-002-multiagent-assignment-contract
  path: .pf/assignments/task-002-multiagent-assignment-contract.yaml
  status: in_progress
  objective: ...
  execution_mode: ...

context:
  snapshot_id: project-context
  freshness: fresh
  required_sources:
    - .pf/contexts/project-context.snapshot.yaml
    - .pf/assignments/task-002-multiagent-assignment-contract.yaml
  context_artifacts:
    - path: .pf/artifacts/update-framework-implementation-spec-20260720.md
      checksum: optional-sha256
      role: background

scope:
  allowed_files:
    - .pf/artifacts/multiagent-assignment-contract-20260720.md
  allowed_read_files:
    - .pf/AGENTS.md
    - .pf/process-forge.yaml
  forbidden_files:
    - schemas/*
    - templates/*
  ownership:
    owner_id: task-002-multiagent-assignment-contract
    writer: true
    owned_files:
      - .pf/artifacts/multiagent-assignment-contract-20260720.md
  non_overlap:
    policy: block_on_write_overlap
    active_parallel_tasks: []

outputs:
  required_outputs: []
  expected_report: {}

capabilities:
  required: []
  optional: []

telemetry:
  events: .pf/runtime/telemetry/task-002-multiagent-assignment-contract.ndjson
  event_correlation_id: assignment-task-002-multiagent-assignment-contract
```

Capsule generation should freeze:

- assignment id and path
- assignment status at launch time
- context snapshot checksum
- required source list
- context artifact list
- allowed and forbidden scopes
- ownership claims
- non-overlap checks observed at launch time
- required outputs and expected report
- telemetry/event correlation id

Capsules should not freeze mutable task results unless the capsule is generated for review or archival purposes.

## 4. Orchestrator Task Creation Rules

The orchestrator should create multiagent tasks in this order:

1. Split the parent objective into independent deliverables.
2. Assign each deliverable a stable task id and output artifact.
3. Derive the minimal write scope for each task.
4. Derive read-only context artifacts separately from write scope.
5. Build an ownership table for all planned write scopes.
6. Check write-scope overlap before launching any worker.
7. Add explicit `forbidden_files` from other active write scopes to every assignment.
8. Generate a capsule for each worker after the overlap check passes.
9. Launch workers only after capsules and assignment files agree.
10. Re-check active scopes before accepting worker output.

The orchestrator should prefer one output artifact per planning worker. Implementation workers may own multiple files only when the ownership is explicit and narrow.

## 5. Future `task-create` Support

`task-create` should become the main entry point for safe assignment creation.

Recommended behavior:

- accept `--id`, `--title`, `--process`, `--objective`, `--run-id`
- accept `--allowed-file` and `--allowed-glob` as write scopes
- accept `--read-file` and `--context-artifact`
- accept `--forbidden-file` and `--forbidden-glob`
- accept `--owner`, `--role`, and `--writer true|false`
- accept `--execution-mode`
- accept `--required-output`
- accept `--expected-report-language`
- discover active assignments from `.pf/assignments`
- fail on write overlap unless `--force-with-handoff` is provided
- write the assignment only after validation passes

Example future command:

```text
pf task-create --root . --run-id pf-update-framework-implementation-20260720 --id task-002-multiagent-assignment-contract --process software-feature-development --execution-mode planning_only --allowed-file .pf/artifacts/multiagent-assignment-contract-20260720.md --context-artifact .pf/artifacts/update-framework-implementation-spec-20260720.md --required-output proposed_assignment_schema_fields
```

`task-create` should print the normalized write scope and any active conflicts before writing files.

## 6. Future `assignment-capsule` Support

`assignment-capsule` should generate and validate immutable worker handoff capsules.

Recommended commands:

```text
pf assignment-capsule create --root . --assignment .pf/assignments/task-002-multiagent-assignment-contract.yaml
pf assignment-capsule validate --root . --capsule .pf/contexts/assignment-capsules/task-002-multiagent-assignment-contract.capsule.yaml
pf assignment-capsule scope-check --root . --capsule .pf/contexts/assignment-capsules/task-002-multiagent-assignment-contract.capsule.yaml
```

Required behavior:

- verify assignment path exists
- verify required sources exist
- verify snapshot checksum when provided
- copy normalized scope fields from assignment to capsule
- include active parallel assignment summaries
- fail if capsule scope differs from assignment scope
- fail if current active write scopes overlap
- record `event_correlation_id`

The capsule generator should not make broad context snapshots by default. It should include references and checksums, with optional embedded excerpts only for small stable files if a future mode needs offline workers.

## 7. Write-Scope Overlap Checks

Overlap checks should operate on normalized repository-relative paths.

Recommended normalization:

- convert backslashes to slashes
- remove leading `./`
- reject absolute paths in public assignment files unless explicitly private/local
- normalize case for Windows comparisons
- expand known file paths from `allowed_files`
- compare globs against files when a git file list is available
- compare glob-to-glob conservatively when no file list is available

Blocking cases:

- same concrete file appears in two active write scopes
- a file is allowed in one task and forbidden in the same task
- a file is allowed in one task and matched by another active task's owned glob
- two owned globs may match the same repository files
- parent directory glob such as `tools/*` overlaps a child file such as `tools/processforge.py`
- one worker's output artifact is another worker's writable artifact

Allowed cases:

- two workers read the same context artifact
- one worker writes an artifact while another only reads it as a dependency
- one worker owns `schemas/*` while another owns `.pf/artifacts/*.md`
- sequential tasks with overlapping write scopes when the previous task is completed or superseded

Conflict report shape:

```yaml
overlap_check:
  status: fail
  conflicts:
    - current_assignment: task-002
      current_scope: .pf/artifacts/report.md
      other_assignment: task-001
      other_scope: .pf/artifacts/*
      reason: glob_matches_same_file
```

The default policy should be `block_on_write_overlap`. A softer `warn_on_read_overlap` policy can be added for narrow read conflicts.

## 8. Handoff Behavior

When a worker needs a file outside its write scope, it should not edit the file. It should produce a handoff request:

```markdown
# Handoff: task-002 -> orchestrator

Objective:
Requested scope change:
Reason:
Files requested:
Conflicting active tasks:
Risk if deferred:
```

The orchestrator may then:

- reject the request
- update the assignment after checking overlap
- wait until the conflicting task completes
- create a new sequential follow-up task

## 9. Implementation Follow-Up Tasks

Recommended implementation slices after this planning artifact:

1. Extend assignment schema to accept structured `execution_mode`, `allowed_read_files`, `ownership`, structured `required_outputs`, and `expected_report`.
2. Preserve backward compatibility for existing plain-list fields.
3. Add assignment normalization helpers for singular-to-list and string-to-object conversion.
4. Add write-scope overlap validation across active assignments.
5. Update `task-create` to generate ownership and non-overlap fields.
6. Update `assignment-capsule` generation to include normalized scope, output, and report contracts.
7. Add CLI checks that fail before writing assignment/capsule files when active write scopes overlap.
8. Add fixture assignments for non-overlap pass and fail cases.

## 10. Acceptance Criteria

The slice is acceptable when:

- assignment YAML supports explicit context artifacts, read scope, write scope, forbidden scope, ownership, non-overlap, required outputs, and expected report fields
- current plain-list assignment fields remain valid
- assignment capsule includes the normalized assignment path, required sources, context artifacts, scope, ownership, non-overlap, outputs, capabilities, and telemetry fields
- `task-create` can create a planning-only assignment with one output artifact and no code write scope
- `assignment-capsule create` can generate a capsule that mirrors the assignment scope exactly
- overlap validation blocks two active assignments from owning the same concrete file
- overlap validation blocks a concrete file under another active assignment's owned glob
- overlap validation permits shared read-only context artifacts
- conflict messages identify both assignments, both scopes, and the overlap reason
- tests cover Windows path normalization and glob matching

## 11. Minimal Tests

### Schema Tests

- valid assignment with structured context artifacts
- valid assignment with legacy plain path lists
- invalid assignment with missing `id`
- invalid assignment with `allowed_files` intersecting `forbidden_files`
- valid capsule with scope matching assignment
- invalid capsule with stale or mismatched assignment path

### Normalization Tests

- backslash paths normalize to slash paths
- leading `./` is removed
- singular `active_parallel_task` converts to `active_parallel_tasks`
- string `required_outputs` converts to structured output objects
- Windows case-insensitive comparison catches `Tools/ProcessForge.py` vs `tools/processforge.py`

### Overlap Tests

- same file in two active `allowed_files` lists fails
- `schemas/*` conflicts with `schemas/assignment.schema.json`
- `.pf/artifacts/*.md` conflicts with `.pf/artifacts/report.md`
- shared `context_artifacts` pass
- completed assignment with overlapping old scope does not block a new active assignment

### CLI Tests

- `task-create` refuses overlapping write scope
- `task-create` writes assignment when scopes are disjoint
- `assignment-capsule create` includes normalized scope fields
- `assignment-capsule validate` fails when capsule scope differs from assignment
- `assignment-capsule scope-check` reports active conflict details

## 12. Current Task Output

Changed files intended for this task:

- `.pf/artifacts/multiagent-assignment-contract-20260720.md`

Files intentionally not changed:

- `tools/processforge.py`
- `tools/validate-process-forge-schemas.py`
- `schemas/*`
- `templates/*`
- `.pf/assignments/task-001-update-contracts-readonly.yaml`
- `.pf/artifacts/update-framework-implementation-spec-20260720.md`

This artifact is a planning specification only. It does not implement schema, template, CLI, or validator changes.
