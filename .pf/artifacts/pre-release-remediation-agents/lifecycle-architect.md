# Отчёт lifecycle architect

- Дата: 2026-07-30
- Assignment: `remediation-lifecycle-design-20260730`
- Agent Ledger: `codex-remediation-lifecycle-architect` /
  `pre-release-remediation-20260730-lifecycle-architect` /
  `lease-remediation-lifecycle-architect-20260730`
- Режим: read-only architecture; product code не изменялся

## Результат

Подготовлен ADR
`.pf/adr/pre-release-remediation-lifecycle-design-20260730.md`. В нём
зафиксированы exact symbols, единый executable-process contract, immutable
version/upgrade policy, creator=doctor postconditions, blocking context
propagation, strict catalog collision result и terminal iteration state
machine.

## Exact symbols

Исследованы следующие группы:

- process authoring: `normalize_process_authoring_answers`,
  `process_from_authoring_answers`, `command_process_authoring_apply`,
  `command_process_create`, `semantic_version_key`, `build_parser`;
- process resolution/catalog: `ProcessDefinitionRef`,
  `process_override_declared`, `process_catalog_entries`,
  `resolve_process_definition`, `require_official_process_active`,
  `builtin_process_catalog_report`,
  `command_builtin_process_catalog_doctor`;
- run/task lifecycle: `validate_run_consistency`,
  `validate_task_consistency`, `command_run_create`, `command_run_doctor`,
  `command_task_create`, `command_task_start`, `command_task_doctor`;
- context/snapshot: `build_execution_route`,
  `resolve_specialization_context`, `build_project_context_snapshot`,
  `write_project_context_snapshot_outputs`,
  `command_project_context_refresh`, `command_context_resolve`;
- iteration lifecycle: `ITERATION_STATUSES`,
  `command_iteration_add`, `command_iteration_complete`,
  `validate_task_consistency`.

## Invariant matrix

| Область | До исправления | Принятый invariant |
|---|---|---|
| Process version | существующий target перезаписывается | `process-create` только для нового id; upgrade только через audited monotonic flow; same version неизменяема |
| Run/task creator | process может не существовать; terminal run сразу невалиден | candidate проходит тот же pure validator, что doctor, до commit |
| Context | resolver error превращается в пустой successful route | выбранный unknown/inactive process всегда создаёт blocking conflict |
| Snapshot | blocked candidate маркируется fresh и продвигается | broken candidate возвращает exit 1 и не заменяет last-good snapshot |
| Catalog | strict warning не влияет на doctor | structured collision входит в checks, summary и exit |
| Iteration | complete принимает nonterminal target и смешивает event | только terminal target; transition, `completed_at` и event согласованы |

## Collision policy

Разделены две разные операции:

1. version upgrade — отдельный audited flow, сохраняющий immutable history;
2. catalog override — declarative
   `process_override.overrides + process_override.reason`.

Same-version content override запрещён. Approved catalog override не даёт права
перезаписывать immutable version.

Обнаружена связанная контрактная дыра: код читает `process_override`, но
`schemas/process-definition.schema.json` его не объявляет при
`additionalProperties: false`. Поэтому schema включена в будущий sole-writer
scope; обход через `x_` или ослабление schema отвергнуты.

## Context failure contract

Ошибка `resolve_process_definition` больше не должна исчезать в
`build_execution_route`. Conflict проходит через specialization resolution,
explicit context и project snapshot. Snapshot candidate получает
`health=blocked`, `freshness=broken`; current snapshot не заменяется.

Executable process определён как:

- resource разрешён в effective catalog;
- official pack активирован;
- manifest status один из `active`, `experimental`, `internal`.

`draft`, `deprecated`, `archived`, unknown и inactive official pack блокируют
execution.

## Lifecycle transition contract

`iteration-complete` принимает только
`completed|passed|failed|cancelled`. Planned iteration можно только отменить;
in-progress — завершить любым terminal result; terminal retry с тем же status
является no-op, а смена terminal result запрещена.

Event mapping:

- completed/passed → `iteration.completed`;
- failed → `iteration.failed`;
- cancelled → `iteration.cancelled`.

## Test matrix и implementation scope

ADR задаёт пять новых negative/positive smoke files и перечисляет существующие
regressions. Точный sole-writer scope ограничен `tools/processforge.py`,
`schemas/process-definition.schema.json`, пятью новыми smokes и двумя
существующими collision/official-process smokes. Run/assignment/iteration
schemas, process manifests, docs, checksum inventory и ZIP не включены.

## Проверка и tooling

Serena использована первой, но symbol backend недоступен:

```text
Cannot extract symbols from file tools/processforge.py.
Active languages: []
```

После этого применён разрешённый точечный shell fallback: `rg` для поиска
definitions/call sites и ограниченные line slices. Полные product files не
переписывались и тесты, меняющие repository state, не запускались, поскольку
assignment является planning-only.

Проверено, что изменения рабочего дерева этого agent ограничены двумя
разрешёнными Markdown artifacts.

## Остаточные риски

- Новая upgrade command и history layout являются новым public behavior и
  требуют отдельного implementation review.
- Last-good snapshot preservation должен быть согласован с transaction slice,
  чтобы два agents не реализовали параллельные promotion primitives.
- Pure creator/doctor validators затрагивают большой центральный CLI-файл;
  необходим один writer и последовательный integration run.
- Полный release-test остаётся за orchestrator после implementation, review,
  checksum refresh и archive rebuild.
