# Инвентаризация `process transition` ↔ `process route`

## 1) Канонические определения маршрутов

- **Явный контракт маршрутов сейчас в двух схемах:**
  - `schemas/process-transition.schema.json`
    - `id`, `from_process`, `to_process`, `mode` обязательны.
    - Дополнительно поддерживаются `requires_agent`, `input_contract`, `output_contract`, `return`.
    - Допуск `additionalProperties: true`.
  - `schemas/process-route-map.schema.json`
    - `schema_version`, `routes` обязательны.
    - Для каждого route обязательны `id`, `from_process`, `to_process`, `mode`.
    - Дополнительно допустимы `required_capabilities`, `required_specializations`, `preferred_specializations`.
    - Допуск `additionalProperties: true`.
- **Кодовая точка входа маршрутов**:
  - `tools/processforge.py` ожидает маршрутный файл только по пути:
    - `.pf/process-routes.yaml`.
  - Код опирается на функции `load_process_route_map`, `validate_process_route_map`, `route_by_id`, `command_process_route_list/validate`.
- **Режимы handoff (`mode`) централизованно задаются в `HANDOFF_MODES`**:
  - `wait_for_result`, `delegate_and_continue`, `consultation`, `final_transfer`, `fork`, `return_required`.

## 2) Использование маршрутов в runtime‑потоке

- `error-route --mode route_to_process` требует наличие `.pf/process-routes.yaml`; при отсутствии выдаёт hard fail.
- Создание handoff-а (`command_handoff_create`) строит контракт из route:
  - `from.process`/`to.process`/`mode` ← `from_process`/`to_process`/`mode`.
  - `to.required_role` ← `requires_agent.role`.
  - `to.required_capabilities` ← `required_capabilities`.
  - `to.required_specializations` / `to.preferred_specializations`.
  - `input_artifacts` ← `(input_contract.required_artifacts)`.
  - `expected_results` ← `(output_contract.required_artifacts)`.
  - `return_to` ← `return` (или fallback к исходному process/run).
- Для статуса availability/route фильтрации используются поля, materialized в handoff-контракте (`required_role`, `required_capabilities`, `required_specializations`).

## 3) Процессные (процесс-уровневые) поля и потенциальные дубли

- В `process-definition.schema.json` есть `process_transitions` (разрешено, без строгой структуры).
- В `tools/processforge.py` это поле практически **не используется для исполнения маршрута**; его влияние — диагностическое:
  - в `process-doctor` определяется тип handoff-семантики:
    - `handoff_semantics: process_transition` если задано `process_transitions`,
    - иначе fallback к `run_completion`/`stage_completion`/`none`.
- Вывод:
  - `process_transitions` = **metadata/hint уровня процесса**, а не активный runtime route-механизм.
  - Активный routing для runtime сейчас идёт через `.pf/process-routes.yaml` + handoff контракт.

## 4) Каноничный vs дублирующий/устаревший набор полей

- **Каноническая рабочая пара для маршрутизации:** `schemas/process-route-map.schema.json` + `tools/processforge.py` (исполнение через handoff).
- **Высокая вероятность дублирования/расхода ответственности:** `process_transitions` в процессе и route-map в `.pf/process-routes.yaml`.
  - Сейчас это два разных местa смысла: процессный декларативный маркер vs. фактический маршрут исполнения.
- **Схемные расхождения/заметы:**
  - В route-map-схеме перечислены минимальные обязательные поля, но фактический runtime-исполнитель также использует расширенные поля (`requires_agent`, `input_contract`, `output_contract`, `return`, `required_*`/`preferred_*`).
  - Из-за `additionalProperties: true` это не валидируется жёстко на уровне JSON Schema, контроль уходит в runtime-логику.

## 5) Жёстко заданные процесс/стадии (hardcode)

- В авторинг-процессе по умолчанию:
  - если `stages` не заданы, подставляется `intake`;
  - `stage_completion` и `run_completion` получают дефолтные структуры (`handoff_note_required`, `summary_required`, `handoff_artifact_required`) из authoring-логики.
- Это не влияет на саму route-схему, но влияет на поведение отчётности/handoff-семантики по умолчанию.

## 6) Конкретный вывод по текущему дереву

- В текущей рабочей копии `.pf/process-routes.yaml` отсутствует (`MISSING`), при этом код ожидает его в runtime.
- Следствие: без этого файла route-driven error workflow и handoff routing через `route` не смогут работать в простом режиме.