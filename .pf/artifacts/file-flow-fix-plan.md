# File Flow Fix Plan

- date: `2026-07-25`
- source audit: `.pf/artifacts/file-flow-audit-report.md`
- scope: repair ProcessForge file-flow contracts, validators, CLI lifecycle, and autonomous multi-agent execution boundaries
- mode: plan only; no product code changes in this slice

## Design Principles

1. One durable fact has one canonical owner.
   - Run state is owned by `.pf/runs/<run>/run.yaml`.
   - Task state is owned by `.pf/assignments/<task>.yaml`.
   - Public deliverables are owned by `.pf/artifacts/**`, `.pf/reviews/**`, `.pf/handoffs/**`, and `.pf/logs/**`.
   - Private runtime observations stay under `.pf/runtime/**` and must not be required for durable validation.

2. Autonomous agents need immutable launch input.
   - A worker must be able to prove which assignment, context snapshot, scope, required outputs, and capability contract it received.
   - If launch input changes, create a new immutable package or versioned capsule path instead of overwriting the same path.

3. Schemas, doctors, and CLI commands must enforce the same lifecycle.
   - JSON Schema is the public structural gate.
   - Doctor commands are semantic gates.
   - Mutating commands must not create states that their matching doctor rejects.

4. Automation must be explicit.
   - If process subscriptions are documentation-only, mark them as declarative/future.
   - If they are executable, add a real executor and tests.

5. Escape hatches require waivers.
   - A CLI option may bypass required outputs or stale context only with an explicit `waiver` record stored in the durable task/run file.

## Phase 0 - Freeze Target Contract

Owner: architecture agent.

Tasks:

- Define canonical status enums:
  - run: `draft`, `open`, `in_progress`, `blocked`, `review`, `completed`, `cancelled`, `failed`
  - executable task: `open`, `in_progress`, `blocked`, `debugging`, `review`, `done`, `cancelled`, `failed`
  - non-executable authoring status, if still needed, must be a separate field such as `authoring_status`.
- Decide the context launch model:
  - Option A: immutable ECP is canonical and capsule references ECP.
  - Option B: capsule is canonical, immutable, and versioned; ECP docs/schemas are deprecated or narrowed.
- Decide artifact roots:
  - Canonical public artifacts: `.pf/artifacts/**`
  - Canonical reviews: `.pf/reviews/**`
  - Canonical handoffs: `.pf/handoffs/**`
  - Remove or explicitly reserve `.pf/runs/<run>/artifacts` and `.pf/runs/<run>/reviews`.

Deliverables:

- ADR: `.pf/adr/file-flow-canonical-contract.md`
- Contract patch list for schemas/docs/CLI.

Exit gate:

- No implementation starts until the canonical model is explicit enough for tests to encode.

## Phase 1 - Align Schemas With Executable Records

Owner: schema/contracts agent.

Tasks:

- Extend `tools/validate-process-forge-schemas.py` mappings:
  - `.pf/runs/*/run.yaml` -> `schemas/run.schema.json`
  - real machine-readable review/handoff/log/artifact records, if supported, -> matching schemas
  - if current `.md` files are intentionally human-readable and not schema-backed, rename or document schemas as template schemas rather than release gates.
- Tighten `schemas/assignment.schema.json`:
  - require `schema_version`, `id`, `title`, `run_id`, `process`, `status`, `iterations`, `result`
  - align `status` enum with executable task statuses
  - make `required_outputs[].path` required for object form
  - make `expected_report.artifact` validate as a normalized project-relative path when present.
- Tighten `schemas/run.schema.json` where schema can safely enforce durable state:
  - task refs stay aligned with task statuses
  - completed run may require `final_artifacts`, or doctor remains the semantic owner for summary/handoff existence.

Deliverables:

- Schema updates.
- Negative fixtures proving schema rejects invalid statuses and missing executable fields.

Exit gate:

- `python tools/validate-process-forge-schemas.py` fails on intentionally bad fixtures and passes on current valid fixtures.

## Phase 2 - Make Mutating CLI Commands Doctor-Safe

Owner: lifecycle CLI agent.

Tasks:

- Fix `run-complete`:
  - require existing `.pf/runs/<run>/summary.md` and `.pf/handoffs/runs/<run>-handoff.md`, or call the same summary/handoff generation path before marking completed.
  - after mutation, run the same checks as `run-doctor` except runtime-only checks.
- Fix `task-complete`:
  - validate every required output with `required: true`.
  - validate `expected_report.artifact` when present.
  - fail if required output is missing unless `--waive-required-output <id>:<reason>` is provided.
  - persist waivers in `task.result.waivers`.
- Extend `task-doctor`:
  - check required outputs and expected report artifact.
  - show waiver status explicitly.

Deliverables:

- CLI changes.
- Smoke tests for:
  - completing task without required output fails
  - completing task with required output passes
  - completing run without summary/handoff fails or auto-generates them
  - completed run doctor passes after the official completion command.

Exit gate:

- No official mutating command can create a state rejected by its doctor.

## Phase 3 - Repair Context Launch Immutability

Owner: context/capsule agent.

Tasks for Option A, ECP canonical:

- Rewire `assignment-capsule` to compile or reference an immutable `.ecp.yaml`.
- Store ECP path and checksum inside capsule.
- Replace `force=True` overwrites with new versioned paths:
  - `.pf/contexts/assignment-capsules/<task>/<timestamp-or-hash>.capsule.yaml`
  - optional stable pointer file only if it is clearly mutable, such as `<task>.latest.yaml`.
- Update worker launch prompt to reference the immutable capsule version.

Tasks for Option B, capsule canonical:

- Update docs and schema to remove mandatory ECP reference.
- Make capsule path immutable/versioned.
- Keep snapshot checksum and assignment checksum as the reproducibility proof.

Deliverables:

- One chosen implementation path, not both.
- Migration note for existing `.ecp.yaml` and `.capsule.yaml` files.
- Smoke test proving a second prepare does not overwrite the first launch input.

Exit gate:

- Worker handoff can cite a stable capsule file that never changes after launch.

## Phase 4 - Separate Durable Doctor From Runtime Diagnostics

Owner: assurance/tooling agent.

Tasks:

- Remove private runtime event lookup from default `run-doctor`.
- Add an explicit runtime diagnostic command or flag:
  - `run-doctor --runtime-events`
  - or `runtime-events-doctor --run <run>`
- If durable event evidence is needed, write a public digest into `run.events.emitted` or a public summary artifact, not `.pf/runtime/**`.

Deliverables:

- Updated doctor behavior.
- Test showing old completed run can pass doctor without `.pf/runtime/events/events.ndjson`.
- Runtime-specific test still detects missing runtime events when the runtime flag is requested.

Exit gate:

- Release/clean checkout does not warn solely because private runtime was cleaned.

## Phase 5 - Collapse Or Document Duplicate Roots

Owner: file-layout agent.

Tasks:

- Remove creation of unused `.pf/runs/<run>/artifacts` and `.pf/runs/<run>/reviews`, unless a real semantic role is assigned.
- If retained, rename/document them as run-local scratch and keep them private or excluded from public artifact language.
- Update docs and examples to show one normal artifact path.

Deliverables:

- CLI path cleanup.
- Documentation cleanup.
- Migration note for existing empty directories.

Exit gate:

- Creating a new run produces no empty conceptual duplicate dirs.

## Phase 6 - Clarify Hooks And Process Subscriptions

Owner: process semantics agent.

Tasks:

- Decide whether `hooks.subscriptions.actions` are executable now.
- If not executable:
  - rename to `intended_reactions`, `observed_events`, or `future_subscriptions`
  - remove action names such as `create_handoff` from active process contracts
  - update docs to say handoff generation is performed by `run-summary` or `run-complete`.
- If executable:
  - implement a subscription dispatcher with explicit non-network, file-only actions
  - add idempotency keys and replay protection.

Deliverables:

- Process definition cleanup or executor implementation.
- Tests proving `run.completed` behavior matches docs.

Exit gate:

- A reader cannot infer automatic handoff creation unless the CLI actually does it.

## Phase 7 - Protect Reserved Worker Environment

Owner: runtime driver agent.

Tasks:

- Define reserved environment names:
  - `PF_RUN_ID`
  - `PF_TASK_ID`
  - `PF_AGENT_RUN_DIR`
  - `PF_PROJECT_ROOT`
  - `PF_RUNTIME_DRIVER_ID`
  - any heartbeat/report path variables owned by ProcessForge.
- Reject driver templates that set reserved names, or apply explicit variables first and canonical variables last.
- Add schema validation for reserved environment variables in runtime driver templates.

Deliverables:

- Runtime driver schema/check update.
- Smoke test proving a driver cannot override `PF_RUN_ID` or heartbeat identity.

Exit gate:

- Worker identity used in heartbeat/report paths is controlled only by ProcessForge.

## Multi-Agent Execution Plan

Recommended orchestration:

1. `architecture-agent` owns Phase 0 and writes the ADR.
2. `schema-agent` owns Phase 1 after ADR is accepted.
3. `cli-lifecycle-agent` owns Phase 2.
4. `context-agent` owns Phase 3.
5. `doctor-agent` owns Phase 4.
6. `layout-docs-agent` owns Phase 5 and docs updates after CLI path choices are stable.
7. `hooks-agent` owns Phase 6.
8. `runtime-agent` owns Phase 7.
9. `assurance-agent` runs cross-cutting smoke/release gates after each merge point.

Parallelization rules:

- Phase 0 is serial.
- Phases 1 and 2 can run partly in parallel after status enums are frozen, but they must reconcile before tests are final.
- Phase 3 should not run in parallel with docs updates that mention ECP/capsule semantics.
- Phases 4, 6, and 7 can run in parallel because they touch disjoint concerns.
- Phase 5 should run after Phase 2/3 path decisions.

Writer boundaries:

- `schema-agent`: `schemas/**`, schema validator fixtures/tests.
- `cli-lifecycle-agent`: run/task lifecycle sections in `tools/processforge.py`, task/run smokes.
- `context-agent`: capsule/ECP generation code, context schemas, context docs.
- `doctor-agent`: doctor commands and runtime diagnostic smokes.
- `layout-docs-agent`: docs/examples/path references only after code contracts settle.
- `hooks-agent`: `processes/*` hook/subscription sections, hooks docs, hooks tests.
- `runtime-agent`: runtime driver schemas/templates and environment construction.

## Assurance Gates

Required before delivery:

- `python tools/validate-process-forge-schemas.py`
- `python tools/validate-process-forge-checksums.py --root . --check`
- `python tools/processforge.py doctor-context --project-root .`
- targeted run/task lifecycle smoke tests
- targeted capsule immutability smoke test
- targeted runtime driver reserved-env smoke test
- release/public cleanliness validation
- `git diff --check`

Expected final proof:

- A newly created run can be created, assigned, completed, summarized, and pass doctor.
- A required-output task cannot be completed without its durable output or explicit waiver.
- A worker launch capsule is immutable and uniquely citable.
- A clean checkout does not warn because private runtime logs are absent.
- Process docs and process YAML describe only behavior that actually exists.

## Recommended First Implementation Slice

Start with a small vertical slice:

1. Freeze task/run status enums in ADR.
2. Align `assignment.schema.json` with `task-doctor`.
3. Make `task-complete` enforce `required_outputs`.
4. Add one negative and one positive smoke.

This gives immediate safety for autonomous workers because completion status becomes trustworthy.
