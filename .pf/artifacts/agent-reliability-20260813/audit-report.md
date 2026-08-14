# Аудит надёжности ProcessForge для длинных агентских сессий

- date: `2026-08-13`
- run: `agent-reliability-20260813`
- assignment: `audit-and-architecture`
- source prompt: `задания/process-forge-agent-reliability-master-prompt.md`
- mode: planning-only; product code was read, not modified

## Executive Summary

Гипотеза master-prompt подтверждена частично, но не как отсутствие механизмов.
В ProcessForge уже есть события, hooks/outbox, session-start, agent ledger,
run/task lifecycle, required-output gates, worker runtime state, handoff flows,
doctor checks и smoke-тесты. Главная проблема в другом: эти механизмы не
собраны в один исполняемый контракт стадии/сессии. CLI-команды фиксируют
отдельные факты, но не всегда поддерживают производные технические артефакты,
не всегда защищают содержательные артефакты от шаблонной перезаписи и не
имеют общего transactional/projector слоя для служебного состояния.

Крупные архитектурные изменения не реализованы в этом slice. Следующий этап
требует operator approval и отдельной implementation assignment с write scope
на `tools/processforge.py`, tests/smokes, schemas/templates/docs and checksum
inventory.

## A. Что уже существует

### События, hooks, telemetry

- `processforge_event`, `append_process_event`, `emit_process_event` пишут
  события в `.pf/runtime/events/events.ndjson` и dispatch hooks.
- `hooks.yaml` уже включает outbox target `wtaicc-outbox` на все события,
  network send выключен по умолчанию, command/webhook targets отключены.
- `events-validate` валидирует runtime events и chat transcripts, а
  `iter_ndjson` читает повреждённые строки как отдельные errors.
- `chat-record` пишет transcript и событие `chat.message.recorded` с
  metadata-only режимом по умолчанию.

### Session, agent ledger, presence

- `session-start` имеет два режима: telemetry bootstrap без `--agent` и
  agent check-in через `agent-checkin` при наличии `--agent`.
- Agent presence session-safe: текущая модель хранит agent/session presence,
  current-session refs, heartbeat, checkout and status.
- В отчёте `agent-session-model-report.md` зафиксированы smokes для
  single-agent, multi-project and composed multi-agent sessions.

### Run/task lifecycle

- `run-create`, `task-create`, `task-start`, `task-complete`, `run-complete`
  существуют и эмитят события.
- `task-complete` уже проверяет required outputs and expected report, включая
  explicit waiver.
- `run-complete` уже вызывает `run-summary` перед завершением run.
- `run-doctor` и `task-doctor` проверяют структуру, статусы, process existence,
  references and required outputs.
- `task-create` для missing run сейчас не оставляет phantom assignment.

### Worker/runtime orchestration

- `worker-run prepare/start/status/stop/collect`, `execution-inspector-*`,
  supervisor drain and worker state files уже существуют.
- Director/Ledger/Execution Inspector boundary документирован отдельно:
  Director routes handoffs/leases, Inspector observes worker runtime, Ledger
  stores presence and lease state.

### Scope, handoff, process definitions

- Assignment YAML stores execution mode, allowed/read/forbidden files,
  ownership, non-overlap, required outputs and expected report.
- `validate_assignment_scope_overlaps` checks active assignment write scopes.
- Process definitions already describe stages, produced artifacts, gates,
  handoff requirements and stage completion metadata.

## B. Какие проблемы подтверждены

### B1. Current project context refresh остаётся broken после refresh

Evidence:

```text
project-context-refresh -> STATUS: fresh, WROTE snapshot, exit code 1
project-context-check -> STATUS: broken, POLICY_ACTION: block
BROKEN: markdown_editing/repository_read/schema_validation required capability missing
STALE: project classification changed
assignment-capsule -> FAIL: project context snapshot is not fresh
```

- Причина: snapshot refresh writes a new snapshot, but capability resolution
  and classification freshness still make the effective context broken.
- Уровень: state + doctor + context architecture.
- Автовоспроизведение: yes, `project-context-check --project-root .`.
- Риск: capsule generation blocks even after refresh; agent may bypass the
  capsule path and continue manually.

### B2. `run-summary` перезаписывает содержательный handoff шаблоном

Evidence from temp project:

```text
HANDOFF_BEFORE_LEN=100
HANDOFF_AFTER_LEN=93
HANDOFF_RETAINED_CRITICAL=False
```

`command_run_summary` writes summary and handoff with `write_text` every time.
Existing handoff content is not merged or protected.

- Причина: generated technical handoff and semantic handoff share one path and
  command has overwrite semantics.
- Уровень: CLI + artifact model.
- Автовоспроизведение: yes, create rich `.pf/handoffs/runs/<run>-handoff.md`,
  run `run-summary --apply`.
- Риск: meaningful handoff can be lost by a maintenance command.

### B3. Служебные writes для run/task/events не имеют общего atomic primitive

Evidence:

- generic `write_file` uses direct `path.write_text`;
- `write_yaml_file` uses direct `path.write_text`;
- `append_telemetry_event` and `append_process_event` append directly;
- `write_yaml_file_atomic` and `registry_file_lock` exist, but run/task save
  paths do not use them.

- Причина: atomic/locked write exists only for selected registry-style paths.
- Уровень: runtime + CLI + state.
- Автовоспроизведение: partially; crash/interruption failure needs fault
  injection, but implementation path is direct and non-transactional.
- Риск: long sessions and parallel shell agents can leave partial YAML,
  stale task index, or interleaved NDJSON.

### B4. `session-status-report.md` is stale but still looks authoritative

Evidence:

```text
.pf/artifacts/session-status-report.md LastWriteTime = 2026-07-13 15:59:15
Flow Version = 0.1.0
Current snapshot generated = 2026-08-13
current manifest version = 1.0.2
```

`render_session_status` can render a current report, but it is written only
when `session-start --allow-write` succeeds without `--report-only`. With a
broken context it blocks before writing. The old artifact has no explicit
stale marker.

- Причина: status report is a static artifact, not a managed projection with
  freshness metadata.
- Уровень: artifact model + session bootstrap.
- Автовоспроизведение: yes, compare file timestamp/content to manifest/context.
- Риск: agents obeying "read latest session-status if present" can consume
  obsolete state.

### B5. Process definitions describe stage responsibilities, but CLI does not
use a stage-owned maintenance runner

Evidence:

- `session-bootstrap.yaml` defines status-scan and session-report stages.
- `task-batch-execution.yaml` defines task execution loop, run-review,
  run-summary and handoff artifacts.
- `process-supervisor.yaml` defines prepare/start/collect and required outputs.
- CLI commands implement isolated operations; there is no shared stage engine
  that derives required technical artifacts after each transition.

- Причина: process YAML is richer than the executable state transition layer.
- Уровень: process + architecture.
- Автовоспроизведение: yes by code/process comparison.
- Риск: the model must remember which maintenance commands to run.

### B6. Write-scope overlap checks are useful but noisy for a single writer

Evidence:

`validate_assignment_scope_overlaps` checks all active assignments and all repo
files for glob/file overlap. There is an explicit `--force-with-handoff` and
an `allow_write_scope_overlap` policy, but current checks are assignment-level,
not session-role-aware.

- Причина: overlap policy does not distinguish one sequential primary agent
  updating a shared log from parallel writers on the same product file.
- Уровень: CLI + process policy.
- Автовоспроизведение: yes with active assignments sharing a log/write glob.
- Риск: false conflicts train agents to bypass ProcessForge state.

### B7. `events-validate` treats old damaged history as current failure

Evidence:

`iter_ndjson` isolates line errors, and current checkout passes
`events-validate`. However command semantics fail the whole validation if any
old line is damaged; there is no archive/quarantine boundary for historical
bad rows.

- Причина: event validation has no time window/current-session boundary.
- Уровень: doctor + runtime history.
- Автовоспроизведение: yes by injecting a bad old NDJSON line in a temp copy.
- Риск: old corruption can block current work unless manually repaired or
  deleted, which the prompt explicitly forbids hiding.

### B8. Confirmed negative: missing-run `task-create` is already safe

Evidence:

```text
MISSING_RUN_EXIT=1
PHANTOM_ASSIGNMENT_EXISTS=False
MISSING_RUN_OUTPUT=FAIL: run not found: missing-run
```

- Причина: `command_task_create` loads run before writing assignment.
- Уровень: CLI.
- Автовоспроизведение: yes.
- Status: not currently a defect for the missing-run scenario. Broader
  multi-file transaction failure after assignment write remains covered by B3.

## C. Общая причина

Several incidents share one root: ProcessForge has facts and contracts, but no
single process-state projector/transition service that owns the boring
maintenance work.

Symptoms:

- context refresh can write a candidate while check still blocks;
- session status is a hand-written/generated artifact rather than a projection;
- run-summary writes technical output over semantic handoff content;
- run/task commands update several files without one transaction boundary;
- process stages declare obligations, but individual CLI commands do not
  consistently complete them;
- runtime history validation has no current-vs-archived boundary.

This is not primarily an MCP problem and not fixable by adding more text to
AGENTS. The fix belongs in PF Core: state transitions, event projection,
artifact freshness and overwrite policy.

## D. Semantic `.webtolk` losses

No live `.webtolk` directory or direct Git history for `.webtolk` exists in
this checkout, so this section is semantic rather than file-by-file evidence.

Likely lost capabilities:

- one cohesive current-work surface instead of scattered assignments, runs,
  artifacts, logs, handoffs and runtime;
- clear distinction between current session state and historical reports;
- automatic maintenance of service state during work, not at final cleanup;
- lower chance of retroactively creating run/task history to satisfy doctor;
- simpler mental model for "what is current, what is stale, what is required";
- shell/workflow hooks that capture facts without asking the model to remember
  every bookkeeping action.

These should be reintroduced as ProcessForge-native behavior, not by copying
`.webtolk` back wholesale.

## E. Proposed Target Architecture

Use existing PF entities. Add the smallest missing layer:

### 1. Process Event Journal Stays The Fact Source

Keep `.pf/runtime/events/events.ndjson` as private fact stream. Add a durable,
public-safe digest/projection only when needed by doctors or releases.

Events record facts:

- command invoked/completed/failed;
- file changed;
- test/build command result;
- task/run/stage transition;
- required output observed;
- context candidate/check result;
- handoff updated/protected.

The model supplies meaning only when a semantic artifact requires judgement.

### 2. Transactional State Mutator

Introduce one shared primitive for PF state mutations:

- lock relevant `.pf` state group;
- validate preconditions;
- write temp files;
- replace atomically;
- update indexes/projections;
- emit one transition event;
- on failure, leave a recovery note and no half-created public state.

Apply first to run/task YAML, task-index, run-summary, handoff writes and
session-status projection. Reuse existing `write_yaml_file_atomic` and
`registry_file_lock`; do not build a separate database.

### 3. Projection Layer For Technical Artifacts

Classify artifacts:

- `semantic`: model-authored decisions, audit reports, handoff details, ADRs;
- `projection`: task-index, changed-files, command log, test/build summary,
  session-status, run status summary;
- `hybrid`: handoff shell plus semantic body.

Generated projections may be overwritten by PF. Semantic artifacts are append,
merge, or protected. Hybrid artifacts need managed sections.

### 4. Stage-Owned Maintenance

Each process stage owns its service obligations:

- on stage start: record stage event and expected outputs;
- during stage: collect command/file/test facts;
- on stage exit: refresh projections, required-output observation, handoff
  state if required, doctor checks;
- on block: write current blocker without closing or inventing history.

This removes the need for the model to remember "update log/status/handoff" as
separate actions.

### 5. Current-State Views

Replace stale static status with generated current-state views:

- `.pf/runtime/current-session.json` remains private pointer;
- `.pf/artifacts/session-status-report.md` becomes a projection with
  `generated_at`, `source_event_id`, `valid_for_session`, `stale_when`;
- stale reports render visibly stale and `session-start` can refresh or refuse
  based on policy.

### 6. Handoff Protection

`run-summary` should not overwrite rich handoff content. Options:

- write generated summary to a managed section inside handoff;
- preserve non-managed sections;
- if handoff is semantic and unmanaged, write `<handoff>.candidate` and warn;
- record overwrite decision as an explicit event.

### 7. Context Candidate Promotion

Context refresh should separate:

- last-good snapshot;
- candidate snapshot;
- check result;
- promotion decision.

A broken candidate must not be reported as "fresh" in isolation. `assignment-capsule`
should state whether it is blocked by candidate freshness, missing capability,
or policy.

## F. Migration Plan

### Phase 0: Freeze And Baseline

- Create implementation assignment with sole writer for `tools/processforge.py`.
- Run baseline: `project-context-check`, `events-validate`, targeted smokes,
  `git status`.
- Do not backfill fake runs/tasks for prior work.

### Phase 1: Safe Writes And Handoff Protection

- Use atomic write for run/task YAML and task-index.
- Add protected write helper for generated Markdown/handoff sections.
- Fix `run-summary` overwrite behavior.
- Add regression for rich handoff preservation.

### Phase 2: Current-State Projection

- Add projection metadata for session status.
- Make stale status explicit.
- Generate session status from snapshot/current-session/run/task state without
  asking the model to maintain it manually.
- Add regression for old session-status not accepted as current.

### Phase 3: Context Candidate Promotion

- Split refresh candidate from promoted current snapshot.
- Ensure broken refresh cannot leave ambiguous "fresh but broken" state.
- Add regression for current project case.

### Phase 4: Stage Maintenance Runner

- Add a narrow transition helper for stage start/exit events and projection
  refresh.
- Wire only task-batch/session-bootstrap first.
- Keep process definitions as source of stage obligations.

### Phase 5: Runtime History Boundaries

- Add event validation modes: `current`, `all`, `archive-diagnostics`.
- Preserve old damaged rows as diagnostics, not hidden deletion.
- Add regression for bad historical row not breaking current session checks.

### Phase 6: Release Integration

- Add public/extracted archive smokes for the eight scenarios in the prompt.
- Refresh checksum inventory and release archive only after implementation and
  review.

## Required Regression Tests

Minimum tests for the next implementation slice:

- long interactive session projection: changed files, commands, tests, build
  and decision are derived without manual artifact reconstruction;
- `task-create` failure leaves no partial task/run state;
- `run-summary` preserves rich handoff body;
- old `session-status-report.md` is visibly stale or ignored;
- bad old `events.ndjson` line is diagnosed separately from current session;
- sequential single-agent shared log writes do not create false conflict;
- work without formal run still records facts if process policy allows it;
- "fill missing artifacts" does not create fake historical run/tasks.

## Verification Performed

Passed:

- `python tools/processforge.py events-validate --project-root .`
- `python tools/processforge.py run-doctor --project-root . --run agent-reliability-20260813 --runtime-events`
- `python tools/processforge.py task-doctor --project-root . --task audit-and-architecture`
- Temp repro: rich handoff is overwritten by `run-summary`.
- Temp repro: missing-run `task-create` exits 1 and leaves no phantom assignment.

Blocked/Warning:

- `project-context-check --project-root .` remains `STATUS: broken`.
- `assignment-capsule` for this task remains blocked by broken project context.

## Approval Boundary

This report is the requested audit/design checkpoint. Product implementation
should start only after approval of the target architecture and first slice.
