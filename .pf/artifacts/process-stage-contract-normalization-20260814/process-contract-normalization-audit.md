# Аудит нормализации контрактов Process / Stage

Дата: 2026-08-14
Основание: `задания/process-forge-process-stage-contract-normalization-master-prompt.md`.

## Подтверждённое состояние

| Объект | Фактический источник | Класс | Проблема |
| --- | --- | --- | --- |
| Process | `schemas/process-definition.schema.json`, `processes/**` | канонический | `process_transitions` допускает произвольный объект или массив и не проверяется как переход. |
| Stage | `$defs.stage` в schema | канонический, но с дублями | `gates` и `exit_gates` выражают одно и то же; `technical_obligations` смешивает контракт с механизмом Runtime. |
| Gate | top-level `gates` | канонический | Doctor проверяет часть ссылок, но не все артефактные/evidence-ссылки и не вводит один семантический маршрут. |
| Artifact | `artifact_definitions` | канонический | `produced_artifacts`, `required_inputs` и `required_artifacts` не проверяются как полный граф ссылок. |
| Evidence | только строковые `required_evidence` / `acceptance.requires` | неоднозначный | нет `evidence_definitions`, поэтому ссылочная целостность невозможна. |
| `technical_obligations` | stage field, читает `tools/pf_runtime/host.py` | legacy automation binding | создаёт второй список блокеров, не являющийся Gate. |
| Process Transition | `process_transitions` в Process | декларативный, недоопределённый | не нормализован к schema перехода и не отделён документированно от project route. |
| Process Route | `.pf/process-routes.yaml` | project runtime routing | собственная повторная схема; требует route map для `route_to_process`, в текущем проекте файла нет. |

Проверка исходников подтверждает два критичных дефекта. `tools/pf_runtime/host.py:83-92` возвращает literal `prepare`, `start` или `collect` из статуса воркера. Затем `declared_stage_obligations()` выбирает `technical_obligations` этой угаданной стадии (`host.py:138-144`). `work_state_payload()` берёт первый projection-row как `active_process`/`active_stage` (`host.py:671-677`). Это не durable execution state и не универсальная семантика Stage.

Проверка authoring подтверждает неполный round-trip: schema допускает stage `required_artifacts`, `required_evidence`, `parameters`, `technical_obligations`, но `process_from_authoring_answers()` материализует только ограниченный набор (`tools/processforge.py:13421-13453`). При этом `PROCESS_AUTHORING_SUPPORTED_TOP_LEVEL` создаёт ложное впечатление полноты. Запрошенный `docs/concepts/process-authoring.md` отсутствует; фактическая документация находится в `docs/authoring/process-authoring.md`.

## Нормализованный публичный контракт

1. **Stage отвечает только на WHAT.** Его семантические поля: `id`, роль/actor, входы, produced/required artifacts, `required_evidence`, `entry_gates`, `exit_gates`, параметры и допустимые инструменты.
2. **Gate отвечает на WHETHER.** Единственный blocker surface — top-level Gate, на который ссылается Stage. Поле `gates` считается legacy alias для `exit_gates`: читается для совместимости, при materialization записывается только `exit_gates`, а Doctor выдаёт предупреждение до управляемой миграции.
3. **Artifact и Evidence — результаты.** Добавляется top-level `evidence_definitions`; `required_evidence` обязан ссылаться на него. Артефактные ссылки Stage должны резолвиться в `artifact_definitions` (кроме явно declared external/virtual artifacts).
4. **Automation bindings отвечают только на HOW.** Новое stage-поле `automation_bindings` заменяет `technical_obligations`. Оно описывает projector/источник/наблюдение и не создаёт самостоятельных блокеров. `technical_obligations` остаётся read-compatible legacy alias с Doctor WARN.
5. **Transition не является Stage.** `process_transitions` — нормализованный список Process Transition между процессами. `.pf/process-routes.yaml` — project-local executable route map для Director/handoff. Нужен один shared definition/validator для полей перехода, но эти два владельца остаются раздельными.

## План реализации

1. В schema/template/default answers/normalizer/materializer/docs ввести `evidence_definitions`, `automation_bindings` и один round-trip contract; убрать authoring default с конкретными стадиями как обязательную семантику generated process.
2. Усилить `process-doctor`: уникальность ID, полная резолюция Stage→Artifact/Evidence/Gate, Gate→Artifact, binding→declared stage/gate и Transition→Process/route-contract. В generic validation убрать правило с подстрокой `review`.
3. Перевести Runtime на declarative `runtime_execution_boundary.stage_by_worker_status` конкретного процесса: приоритет имеет durable `assignment.stage`, затем process-declared mapping; неизвестное состояние не подменяется названием стадии. `current_work_state` строится из assignment/run/journal execution facts, а projection остаётся наблюдением.
4. Перевести `process-supervisor.yaml` на `automation_bindings` и его явную mapping статусов в `prepare/start/collect`. Убрать технические обязательства из `blockers`; сохранить их как `automation_bindings` observations.
5. Добавить user-process fixture и smoke-проверки: custom stages без hardcode, authoring round-trip, doctor negative references, transition/route separation, запуск CLI без поднятого Runtime. Затем reviewer отдельно проверит изменение и regression-smokes.

## Делегированная и независимая проверка

- `process-contract-static-inventory.md`: воркер подтвердил hardcode в Runtime; выборочно перепроверено в `host.py`.
- `process-authoring-parity-inventory.md`: воркер подтвердил materializer parity gaps; выборочно перепроверено в schema и `processforge.py`.
- `process-transition-route-inventory.md`: воркер подтвердил два раздельных contract surface; выборочно перепроверено в schemas и route commands.

Все три воркера запускались с `gpt-5.3-codex-spark`. У двух PID завершился без финальной записи статуса `codex-exec`; их отчёты приняты только после отсутствия PID и ручной сверки источников. Это наблюдательский дефект, не доказательство завершения продукта.
