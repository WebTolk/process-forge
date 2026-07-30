# ADR: process, context и lifecycle invariants

- Дата: 2026-07-30
- Статус: accepted for implementation
- Assignment: `remediation-lifecycle-design-20260730`
- Findings: PF-AUD-007, PF-AUD-008, PF-AUD-009, PF-AUD-017 и iteration-часть PF-AUD-020

## Контекст

Пять дефектов имеют общую причину: одна и та же сущность разрешается и
проверяется разными путями. Creator проверяет меньше, чем doctor; context
превращает ошибку resolver в пустой успешный route; catalog сохраняет strict
collision только как текстовое поле строки; `iteration-complete` использует
полный enum состояния вместо множества terminal targets.

Решение должно сохранить file-first модель, immutable process versions,
наблюдательность doctors и отсутствие частичных product-состояний.

## Точная карта символов

| Finding | Текущий путь | Дефект | Точка исправления |
|---|---|---|---|
| PF-AUD-007 | `command_process_create` → `process_from_authoring_answers` → `command_process_authoring_apply` (`tools/processforge.py:11535`, `11589`, `12049`, `12111`) | `target_process` записывается без проверки существующего `id/version` | preflight в `command_process_authoring_apply`; отдельный `command_process_version_upgrade`; parser в `build_parser` |
| PF-AUD-008 | `command_run_create` / `command_task_create` → `require_official_process_active`; doctor: `validate_run_consistency` / `validate_task_consistency` (`11035`, `11160`, `11211`, `16727`, `16868`) | helper блокирует inactive official pack, но пропускает unknown; creator не применяет полный doctor invariant set | общий `resolve_executable_process`; чистые document validators, используемые creator и doctor |
| PF-AUD-009 | `build_execution_route` → `resolve_specialization_context` → `command_context_resolve` или `build_project_context_snapshot` → `write_project_context_snapshot_outputs` (`3900`, `3992`, `8053`, `8543`, `9682`, `17232`) | `SystemExit` от resolver превращается в `route, []`; context получает `resolved`, snapshot — `fresh` | blocking process conflict в `build_execution_route`; promotion gate для snapshot |
| PF-AUD-017 | `process_catalog_entries` → `builtin_process_catalog_report` → `command_builtin_process_catalog_doctor` (`10913`, `12338`, `12427`) | collision остаётся в `ProcessDefinitionRef.warnings`, но не попадает в `checks`, summary и exit | структурированный collision result и его обязательное включение в report checks |
| PF-AUD-020 | `command_iteration_add`, `command_iteration_complete`, `validate_task_consistency`, `ITERATION_STATUSES` (`10452`, `11211`, `17029`, `17062`) | complete принимает nonterminal target, всегда пишет `completed_at`, а `cancelled` публикует `iteration.failed` | отдельные terminal constants, transition validator и согласованная event mapping |

Номера строк фиксируют состояние checkout на дату ADR; обязательными точками
контракта являются имена символов, а не номера.

## Решение 1: единый executable-process contract

Вводится чистый resolver:

```text
resolve_executable_process(project_root, process_id) -> ProcessDefinitionRef
```

Он обязан:

1. вызвать `resolve_process_definition`, а не отдельно просматривать catalog;
2. вернуть ошибку для unknown id;
3. вернуть ошибку для official process из неактивированного pack
   (`ProcessDefinitionRef.active == false`);
4. запретить execution для manifest status `draft`, `deprecated`, `archived`;
5. разрешить `active`, `experimental`, `internal`, сохраняя текущие
   experimental/internal служебные процессы;
6. выдавать одну и ту же диагностическую причину всем consumers.

`require_official_process_active` заменяется этим resolver либо становится его
тонким compatibility wrapper. `run-create`, `task-create`, `task-start`,
context resolution и snapshot используют один contract.

## Решение 2: immutable versions и audit upgrade

### Обычное создание

`process-create` создаёт только новый process id. До записи public outputs
`command_process_authoring_apply` проверяет effective target:

- target отсутствует — создание разрешено;
- тот же `id` и та же `version` — blocking `FAIL`, даже если содержимое
  совпадает;
- тот же `id`, другая `version` — blocking `FAIL` с указанием использовать
  `process-version-upgrade`;
- target содержит invalid YAML или иной id — blocking `FAIL`, без перезаписи.

Для same-version overwrite нет force-флага: immutable версия не имеет
«одобренного изменения».

### Upgrade

Отдельная команда:

```text
process-version-upgrade
  --project-root <path>
  --process <id>
  --answers <path>
  --from-version <version>
  --to-version <version>
  --reason <non-empty>
  [--apply]
```

Контракт:

- текущие `id/version` обязаны совпасть с `--process/--from-version`;
- `to-version` должен быть валидным semver и строго больше current; сравнение
  использует `semantic_version_key`, lexical fallback здесь запрещён;
- candidate проходит process schema и semantic doctor checks до commit;
- старая версия сохраняется как immutable history
  `.pf/history/processes/<id>/<from-version>.yaml`;
- если history path уже существует, допустим только byte-identical
  idempotent retry; иное содержимое — `FAIL`;
- audit record содержит from/to, reason, timestamp, before/after SHA-256 и
  output paths;
- событие `process.version.upgraded` публикуется только после полного commit.

Этот upgrade flow не является catalog override.

## Решение 3: declarative catalog override

Catalog collision допускается только для осознанного user/custom shadowing
core/official process. Побеждающий manifest содержит:

```yaml
process_override:
  overrides: <same-process-id>
  reason: <non-empty-human-reason>
```

`schemas/process-definition.schema.json` должен объявить этот объект явно:
оба поля обязательны, `overrides` использует process id grammar,
`additionalProperties: false`.

Strict collision policy:

| Collision | Strict result |
|---|---|
| user/custom над core/official, корректный `process_override` | PASS collision check; deterministic winner сохраняется |
| user/custom над core/official без полного declaration | FAIL |
| duplicate между корнями, не соответствующий разрешённой модели override | FAIL |
| нет duplicate | collision check не требуется |

`ProcessDefinitionRef` должен нести structured collision records/checks, а не
только строки `warnings`. `builtin_process_catalog_report` добавляет их в
top-level `checks`, `summary.fail/warn` и row result. Exit code doctor
вычисляется по тому же top-level набору. Парсинг префикса `STRICT:` как
источника истины запрещён.

## Решение 4: creator = doctor postcondition

Из существующих file-based validators выделяются чистые функции:

```text
validate_run_document(project_root, run, *, terminal_outputs) -> list[Check]
validate_task_document(project_root, task) -> list[Check]
```

`validate_run_consistency` и `validate_task_consistency` загружают YAML и
делегируют им. Creator строит candidate в памяти и применяет те же функции до
первой записи.

### `run-create`

Preflight включает:

- `run.schema.json`;
- executable process;
- status и все doctor semantic checks;
- terminal invariant: `completed` требует summary и handoff. Поскольку
  `run-create` их не принимает и не создаёт до commit, initial `completed`
  отвергается;
- отсутствие private absolute paths.

`cancelled` и `failed` могут быть initial только если проходят тот же doctor
contract. При любом `FAIL` не создаются directory, YAML, plan, index и events.

### `task-create`

Preflight включает:

- `assignment.schema.json`;
- существующий и doctor-valid run;
- executable process;
- task candidate checks;
- post-upsert run candidate checks, включая невозможность добавить open task в
  completed run;
- overlap и required-output shape checks.

Только после двух успешных candidates атомарно публикуются task и обновлённый
run; events идут после commit. `task-start` повторно проверяет executable
process до смены состояния.

Doctors остаются observational. Creator вызывает pure validators, а не
`command_*_doctor`, поэтому postcondition не порождает doctor events.

## Решение 5: blocking context и snapshot

`build_execution_route` сохраняет заявленный process id в route, но при ошибке
resolver возвращает structured conflict:

```yaml
id: does-not-exist
kind: process
reason: process not found
blocking: true
```

Для inactive official pack причина сохраняет pack id и remediation hint.
Пустой route допустим только когда process вообще не выбран. Если process был
выбран, но не разрешён, route не может считаться resolved.

Дальнейшее распространение:

- `resolve_specialization_context.status: conflict`;
- `command_context_resolve` печатает conflict и возвращает `1`;
- `build_project_context_snapshot` ставит
  `snapshot.health.status: blocked`, `freshness.status: broken` и сохраняет
  conflict;
- `project-context-refresh --dry-run` показывает `after.status: broken` и
  возвращает `1`;
- `write_project_context_snapshot_outputs` не продвигает broken candidate в
  current/generation/workplace snapshot и не удаляет stale marker;
- last-known-good current snapshot сохраняется;
- событие `context.snapshot.refreshed` не публикуется; допустимо отдельное
  `context.snapshot.blocked` без утверждения, что snapshot fresh.

Unknown и inactive process должны давать одинаковый blocking outcome в explicit
context и project-manifest snapshot paths.

## Решение 6: terminal iteration transitions

Определяются два множества:

```text
ITERATION_NONTERMINAL_STATUSES = {planned, in_progress}
ITERATION_TERMINAL_STATUSES = {completed, passed, failed, cancelled}
```

`iteration-complete --status` принимает только terminal target.

| Исходное состояние | Target | Результат |
|---|---|---|
| `planned` | `cancelled` | разрешено |
| `planned` | `completed`, `passed`, `failed` | FAIL: iteration не стартовала |
| `in_progress` | любой terminal | разрешено |
| terminal | тот же terminal | idempotent no-op; исходный `completed_at` сохраняется, event не дублируется |
| terminal | другой terminal | FAIL |
| любое | `planned` или `in_progress` через `iteration-complete` | FAIL |

Cross-field invariants для creator и `validate_task_consistency`:

- nonterminal iteration не имеет `completed_at`;
- terminal iteration имеет непустой `completed_at`;
- `iteration-add` с terminal status создаёт согласованную terminal запись;
- `iteration-complete` меняет candidate в памяти, валидирует всю task и только
  затем сохраняет.

Event mapping:

| Final status | Event |
|---|---|
| `completed`, `passed` | `iteration.completed` |
| `failed` | `iteration.failed` |
| `cancelled` | `iteration.cancelled` |

Payload status всегда совпадает с сохранённым status.

## Regression matrix

| Test | Сценарий | Ожидаемый результат |
|---|---|---|
| `smoke_remediation_process_versioning.py` | второй `process-create` same id/version | exit 1; public process/prompt/doc/examples и их hashes неизменны |
| тот же | `process-create` same id с большей version | exit 1; hint на `process-version-upgrade` |
| тот же | upgrade с неверным from, равной/меньшей/non-semver target version | exit 1; current/history/events неизменны |
| тот же | valid upgrade с reason | old version и audit record сохранены; new doctor PASS; одно upgrade event |
| `smoke_remediation_lifecycle_postconditions.py` | run/task с unknown process | exit 1; нет entity, index mutation и events |
| тот же | inactive official pack process | exit 1 с pack activation hint |
| тот же | `run-create --status completed` без summary/handoff | exit 1; run directory отсутствует |
| тот же | task в completed run | exit 1; run byte-for-byte неизменен |
| тот же | valid run/task | creator exit 0; немедленные doctors PASS |
| `smoke_remediation_context_process_resolution.py` | explicit unknown/inactive process | conflict, status conflict, exit 1 |
| тот же | manifest snapshot unknown/inactive process | blocked/broken, exit 1; last-good snapshot не заменён |
| тот же | process не выбран | пустой route разрешён, false conflict отсутствует |
| `smoke_remediation_process_catalog_collisions.py` | duplicate без declaration | top-level FAIL, summary.fail > 0, doctor exit 1 |
| тот же | declaration только с reason или только overrides | schema/collision FAIL |
| тот же | полный approved declaration | deterministic winner, collision PASS, doctor exit 0 |
| тот же | неразрешённый same-tier duplicate | doctor exit 1 |
| `smoke_remediation_iteration_transitions.py` | каждый target из полного enum для planned/in_progress/terminal source | результат соответствует transition table |
| тот же | completed/passed/failed/cancelled | `completed_at` и event согласованы |
| тот же | terminal retry | no-op без смены timestamp и duplicate event |

После targeted tests последовательно запускаются существующие:

- `smoke_process_authoring_writes_user_root.py`;
- `smoke_process_authoring_materialization_parity.py`;
- `smoke_process_run_task_batch.py`;
- `smoke_official_process_can_start_minimal_run.py`;
- `smoke_process_root_collision_policy.py`;
- context/specialization snapshot smokes;
- schema validator и public release gates.

## Exact future sole-writer scope

До freeze один implementation agent владеет всеми связанными product writes:

```text
tools/processforge.py
schemas/process-definition.schema.json
tools/smoke_remediation_process_versioning.py
tools/smoke_remediation_lifecycle_postconditions.py
tools/smoke_remediation_context_process_resolution.py
tools/smoke_remediation_process_catalog_collisions.py
tools/smoke_remediation_iteration_transitions.py
tools/smoke_process_root_collision_policy.py
tools/smoke_official_process_can_start_minimal_run.py
```

Другие agents могут в этот период выполнять только read-only review этих
файлов. `schemas/run.schema.json`, `schemas/assignment.schema.json`,
`schemas/iteration.schema.json`, process manifests и docs не требуют изменения
для принятого контракта и исключены из scope. Checksum inventory и release ZIP
обновляются отдельным release owner только после freeze и review.

## Acceptance

Срез принят, если:

1. same-version process невозможно перезаписать ни обычным, ни upgrade flow;
2. approved upgrade сохраняет предыдущую версию и проверяемый audit trail;
3. creator не может создать run/task, который немедленно отвергает doctor;
4. unknown/inactive process блокирует explicit context и snapshot promotion;
5. strict catalog collision управляет checks, summary и exit code;
6. terminal iteration status, timestamp и event всегда согласованы;
7. targeted negative tests доказывают отсутствие файловых и event side effects
   при каждом отказе.
