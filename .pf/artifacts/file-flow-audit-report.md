# File Flow Audit Report

- date: `2026-07-25T15:15:18+04:00`
- scope: current ProcessForge file-flow contracts, schemas, CLI behavior, docs, and project-local `.pf/` layout
- mode: audit only; product code was not changed

## Findings

### HIGH - Schema validation does not validate most durable flow records

`tools/validate-process-forge-schemas.py:592-636` maps the manifest, process/package files, assignments, contexts/capsules, runtime sessions, workplace, and hooks. It does not map:

- `.pf/runs/*/run.yaml` to `schemas/run.schema.json`
- `.pf/handoffs/**` to `schemas/handoff.schema.json`
- `.pf/reviews/**` to `schemas/review.schema.json`
- `.pf/logs/**` to `schemas/log.schema.json`
- `.pf/artifacts/**` to `schemas/artifact.schema.json`

Those schemas exist, but release schema validation can pass while actual run, handoff, review, log, or artifact files are malformed. This is a false-confidence gate.

Recommended fix: extend schema mappings for real `.pf` flow files or explicitly mark unused schemas as authoring-only/non-enforced.

### HIGH - Assignment schema and doctor contract disagree on task status and required fields

`schemas/assignment.schema.json:6` requires only `id`, `title`, `process`, and `status`. `tools/processforge.py:7937-7940` requires `schema_version`, `run_id`, `iterations`, and `result`, and checks status against `TASK_STATUSES`.

The status enum in `schemas/assignment.schema.json:46` allows `draft`, `ready`, `pending`, `ready_for_review`, `completed`, and `superseded`, but `tools/processforge.py:7740-7743` / `tools/processforge.py:7939-7940` accept only `open`, `in_progress`, `blocked`, `debugging`, `review`, `done`, `cancelled`, and `failed`.

Result: an assignment can be schema-valid and doctor-invalid. This is a contract split in the core task model.

Recommended fix: choose one canonical task status lifecycle. If richer authoring statuses are needed, model them separately from executable task status.

### HIGH - ECP/capsule docs promise immutability, but the active path overwrites capsules

`docs/concepts/context-capsule.md:3-5` says a capsule references an Execution Context Package. `docs/concepts/context-capsule.md:41-42` says the orchestrator compiles one ECP per assignment. `docs/concepts/execution-context-package.md:3-9` says the ECP is immutable.

The active CLI path does something else:

- `tools/processforge.py:7690-7719` builds a capsule directly from the assignment contract and project snapshot, with no ECP reference.
- `tools/processforge.py:7724-7726` allows overwriting an existing capsule with `--force`.
- `tools/processforge.py:9865` and `tools/processforge.py:10633` call capsule generation with `force=True`.

Result: the same `.pf/contexts/assignment-capsules/<task>.capsule.yaml` path can silently point to a different generated-at timestamp and source snapshot after prepare/apply. That breaks reproducibility for worker handoffs.

Recommended fix: either revive ECP as the immutable canonical input and make capsules immutable/versioned, or update the docs/schema to say capsules are mutable launch descriptors.

### MEDIUM - `run-complete` can create a doctor-invalid completed run

`tools/processforge.py:10783-10800` marks a run `completed` once blocking tasks are `done`. It does not require or create the summary/handoff. But `tools/processforge.py:7917-7923` makes completed runs fail doctor if `.pf/runs/<run>/summary.md` and `.pf/handoffs/runs/<run>-handoff.md` are missing.

Result: an official close command can create an invalid completed run unless the caller knows to run `run-summary` first.

Recommended fix: make `run-complete` call `run-summary`, require existing summary/handoff, or refuse with a clear message.

### MEDIUM - `task-complete` bypasses required output contracts

`tools/processforge.py:10836-10878` stores `required_outputs` and `expected_report` on task creation. `tools/processforge.py:10925-10940` completes the task with any summary/artifact list passed by the user and does not check that required output paths exist. `tools/processforge.py:7962-7966` only checks that a completed task has some summary or artifact.

Result: manual `task-complete` can mark a task `done` while required deliverables are missing.

Recommended fix: validate `required_outputs` in `task-complete` and `task-doctor`; keep any bypass behind an explicit waiver field.

### MEDIUM - `run-doctor` depends on private runtime events for durable runs

`tools/processforge.py:7924-7926` warns when the run id is absent from `.pf/runtime/events/events.ndjson`. Runtime paths are private/cleanable by contract, and `.gitignore` excludes `.pf/runtime/`.

Live check on this checkout: all 13 existing runs produced `WARN: run events exist` because runtime event history is not durable.

Result: historical, public-safe run records cannot become clean doctor results after runtime cleanup/release packaging.

Recommended fix: remove this warning for durable doctor checks, downgrade it behind a runtime-specific mode, or store a public event digest in the run record.

### MEDIUM - Artifact and review roots are split without clear ownership

`.pf/process-forge.yaml:37-43` declares project-local `assignments`, `artifacts`, `contexts`, `logs`, `handoffs`, `reviews`, and `adr`. `tools/processforge.py:10693-10695` also creates `.pf/runs/<run>/artifacts` and `.pf/runs/<run>/reviews`. Task artifact roots use `.pf/artifacts/runs/<run>/<task>` in `tools/processforge.py:7758-7759` and `tools/processforge.py:10884-10893`.

Live check: all 13 `.pf/runs/*/artifacts` dirs and all 13 `.pf/runs/*/reviews` dirs exist, with zero files.

Result: the model advertises parallel places for the same concepts. This increases path ambiguity and produces dead directories.

Recommended fix: remove unused per-run subdirs, or document a strict split such as run-local scratch vs public durable artifacts.

### MEDIUM - Process subscriptions look executable, but hooks are observational

`processes/task-batch-execution.yaml:29-35` declares subscriptions such as `run.completed -> create_handoff`. But `docs/known-limitations.md:8-10` and `docs/concepts/process-definition-run-task-iteration.md:22-23` state that hooks are observational/outbox-only and do not execute local commands.

Result: process YAML reads like it will automatically refresh task index or create handoff, while the runtime does not perform those actions from subscriptions.

Recommended fix: move such actions into documentation/examples, mark them as future/intended, or implement an explicit subscription executor.

### MEDIUM - Reserved worker environment variables can be overridden by driver config

`tools/processforge.py:9505-9516` sets canonical `PF_RUN_ID`, `PF_TASK_ID`, `PF_AGENT_RUN_DIR`, `PF_PROJECT_ROOT`, and `PF_RUNTIME_DRIVER_ID`, then applies explicit driver variables over them.

Result: a driver template can override canonical ProcessForge identifiers and break heartbeat/report path identity without an error.

Recommended fix: reject or ignore explicit variables using reserved `PF_*` names that ProcessForge owns.

## Secondary Observations

- `schemas/run.schema.json:21-23` allows completed runs without final artifacts at schema level, while doctor enforces summary/handoff only when status is completed.
- `schemas/assignment.schema.json:11-18` accepts both string and object process forms, while executable task creation writes a normalized string. This weakens interoperability unless both forms are truly supported everywhere.
- The active file flow now mixes historical ECP files and newer assignment capsules. This is manageable only if the migration boundary is documented.

## Suggested Fix Order

1. Align executable task/run contracts first: schemas, doctor checks, `run-complete`, and `task-complete`.
2. Decide the canonical context launch model: immutable ECP plus capsule, or mutable snapshot capsule.
3. Remove or formalize duplicate artifact/review roots.
4. Reconcile process subscriptions with the hooks/outbox limitation.
5. Protect reserved worker environment variables.

## Verification Performed

- Read project-local `.pf/AGENTS.md` and `.pf/process-forge.yaml`.
- Audited `tools/processforge.py` run/task/capsule/worker environment paths.
- Audited schema validation mappings and core run/assignment schemas.
- Audited context capsule and ECP docs.
- Ran live run-doctor sweep over 13 runs: `failed=0`, `warn=13`, all warnings were runtime event warnings.
- Counted run-local artifact/review dirs: 13 artifact dirs and 13 review dirs, all empty.
