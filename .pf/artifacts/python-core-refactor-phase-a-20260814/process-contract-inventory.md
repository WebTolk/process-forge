# Инвентаризация контрактов процесса (Python Core)

## Источники для инвентаризации
- `.pf/AGENTS.md`
- `.pf/contexts/project-context.snapshot.yaml`
- `.pf/artifacts/process-stage-contract-normalization-20260814/process-contract-static-inventory.md`
- `.pf/artifacts/process-stage-contract-normalization-20260814/process-contract-normalization-audit.md`
- `.pf/artifacts/process-stage-contract-normalization-20260814/process-transition-route-inventory.md`
- `schemas/process-definition.schema.json`
- `tools/processforge.py`
- `tools/validate-process-forge-schemas.py`
- `tools/smoke_process_stage_contract_normalization.py`
- `tools/smoke_process_transition_handoff.py`
- `tools/smoke_process_definition_schema_contract.py`

## 1) Карта владения и маршрутизации контрактов
- Ядро контрактной логики и публичных CLI-команд процесса в текущей сборке находится в `tools/processforge.py`.
- Формальная схема процесса хранится в `schemas/process-definition.schema.json` и поддерживается валидатором схем в `tools/validate-process-forge-schemas.py`.
- Поведение выполнения/состояний процесса в runtime фактически делегируется в `tools/pf_runtime/*` из команд `processforge.py` (`command_runtime_host_*`), поэтому конкретные мутации состояния здесь косвенные.
- Текущие проверки поведения описаны в smoke-скриптах в `tools/smoke_process_*.py` и являются фактическим источником ожидаемого поведения после нормализации/валидации.

## 2) Загрузка Process Definition (владение, вход, выход, зависимости)
- Владелец: `process_catalog_entries` и `resolve_process_definition` в `tools/processforge.py`.
- Вход:
  - Наборы корней/каталогов процессов (core/user/custom/legacy_flat и пр.).
  - Идентификатор процесса или путь/локальный путь к YAML-файлу.
- Выход:
  - Список `ProcessEntry` с полями `process_id`, `path`, `source` и флагами доступности/активности.
- Зависимости:
  - Учет порядка источников каталога (детерминированный),
  - Дубликаты `process_id` детектируются с предупреждением, при этом поведение выбора источника определяется иерархией приоритета источников.
- Проверка целостности на этапе загрузки:
  - Для конфликтов и дублей выводятся предупреждения (`stderr`/лог) и продолжается разрешение итогового источника.

## 3) Нормализация авторинга (Authoring-конвейер)
- Владелец: `normalize_process_authoring_answers` и `process_from_authoring_answers` в `tools/processforge.py`.
- Вход:
  - Ответы пользователя/ассистента по авторингу (name/id/version/stages/gates/artifacts/evidence и др.).
- Выход:
  - Нормализованная структура `process_definition`.
- Ключевое:
  - `command_process_create` использует этот конвейер для материализации нового процесса, затем применяет валидацию/выпуск.
- Переходы/aliases:
  - Поддерживаются исторические/совместимые поля на этапе нормализации и конвертации (в том числе gate-алиасы, где применяются устоявшиеся правила совместимости).

## 4) Валидация контрактов
- Ядро проверки: `validate_process_contract` в `tools/processforge.py`.
- Вход:
  - Загруженное определение процесса (и опционально флаги strict/force/режимы).
- Проверки:
  - Совпадение/структурная целостность переходов между процессами (`process_transitions`) и handoff-логикой.
  - Переходы/региcтры маршрутов: валидация `route_id` через карту маршрутов (`.pf/process-routes.yaml`).
  - Проверка устаревших полей/конфликтов (например, депрецированное использование `stage.handoff_required` в строгом режиме).
  - Проверки по gate/technical obligations: корректность обязательств, соответствие gate/alias-поведению и совместимости.
  - Проверки доказательств и артефактов в стейджах (см. `required_artifacts`, `required_evidence`, `produced_artifacts`).
- Скрипт `tools/validate-process-forge-schemas.py`:
  - Загружает схему `schemas/process-definition.schema.json`,
  - Валидирует файлы по сопоставленным схемам,
  - Включает процессную и маршрутную схему (`schemas/process-route-map.schema.json`) и проверяет их совместно.

## 5) Doctor/контроль (Audit & readiness)
- `command_process_doctor` в `tools/processforge.py` — главный диагностический вход для контракта процесса; выполняет контрактную проверку и печатает отчёт состояния.
- `command_process_route_doctor` / `command_process_route_validate` — специализированные проверки карты маршрутов.
- `command_task_doctor` — проверка задачи (task) на уровне runtime/контракта.
- Режимы (`--contract-only`, `--force`) влияют на тип проверок: smoke-тесты показывают ожидаемую ошибку при неполном контракте доказательств и прохождение после их добавления.

## 6) Stage / Gate инвентаризация
- Формальная модель стадий и шлюзов в `schemas/process-definition.schema.json`.
- Stage:
  - Поля для ввода/выхода артефактов (`required_inputs`, `produced_artifacts`, `required_artifacts`),
  - Обязательства доказательств (`required_evidence`),
  - Жизненный цикл через `entry_gates` / `exit_gates`,
  - Секция автоматизации (`automation_bindings`) и технические обязательства.
- Gate:
  - Имеет отдельный раздел верхнего уровня и связь со стейджами через `entry_gates`/`exit_gates`.
  - В схеме и логике поддерживаются alias-переходы для backward compatibility, но часть устаревших форматов помечена как deprecated и требует нормализации.
- Сопоставление с авторингом:
  - Во время нормализации и валидации используются как “чистые” поля `gates`/`technical_obligations`, так и совместимые/устаревшие алиасы при необходимости.

## 7) Artifact / Evidence
- Схема требует обязательных верхнеуровневых блоков:
  - `artifact_definitions`
  - `evidence_definitions`
- На уровне стейджей и контрактов обязательны перечисления:
  - `required_artifacts`, `produced_artifacts`, `required_evidence`.
- Риски совместимости:
  - Неполные `evidence_definitions`/артефакты приводят к падению в строгом контрактном режиме, что подтверждается smoke-проверкой по `process-doctor --contract-only --force`.
- Авторы/интеграторы должны использовать единый словарь артефактов/доказательств между `process_definition` и этапами, иначе контракт валидатор отмечает рассогласование.

## 8) Process Transition (переходы процессов)
- Владелец/логика:
  - Секция `process_transitions` в `schemas/process-definition.schema.json`,
  - Дополнительная обработка в `validate_process_contract`,
  - Точка маппинга в `process-route` механизме `command_process_route_*` и `load_process_route_map`.
- Входной контракт перехода:
  - `from_process`, `to_process`, `mode`, `route_id` (опционально),
  - input/output contract и return-поля на переход/hand-off.
- Фактическая маршрутизация:
  - В текущей реализации переходы не исполняются как автономная модель из `process_transitions`; фактический runtime-путь идёт через handoff + карту маршрутов в `.pf/process-routes.yaml`.
  - `command_handoff_create` формирует handoff-объект по runtime контракту (`from_process`, `to_process`, `mode`, `requires_agent`, `input_contract`, `output_contract`, `return`).

## 9) Состояние, I/O и кластеры вызовов
- Состояние процесса в CLI-слое процесса:
  - Наблюдается управление состоянием задач через `command_task_create`, `command_task_start`, `command_task_complete`.
  - Логический state machine для процесса/задач выполняет `tools/pf_runtime/host.py` (через проксирующие `command_runtime_host_*`), поэтому `processforge.py` держит orchestration boundary, а не состояние напрямую.
- I/O по состоянию:
  - Входные состояния из команд/CLI и маршрутизаторов (process/task/runtime/route/doctor/handoff),
  - Выходы: отчеты, статусы выполнения, обновлённые runtime-стейты.
- Утверждение runtime-состояния:
  - Smoke-тесты фиксируют, что после старт/завершения задачи в состояние записываются `active_process` и `active_stage`.

## 10) Наблюдаемые ограничения и пробелы
- Модель переходов (`process_transitions`) частично декларативна: ключевой исполняемый маршрут строится картой `.pf/process-routes.yaml` и handoff-объектами.
- Capability-профиль контекста явно отмечает отсутствие `research/process_governance`; это не блокирует чтение/описание, но влияет на процессный трек и требования этапов.
- Для полного Runtime контроля требуется отдельный обзор `tools/pf_runtime/*`, который по ограничениям задачи вне доступной области чтения.
