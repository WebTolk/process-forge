# Отчёт ревью: нормализация контрактов Process / Stage

## Итог
`BLOCK` — есть блокирующие архитектурные расхождения и недостаточное покрытие валидации/тестов для разделения `process_transitions` и `process-routes`.

## Находки (по убыванию приоритета)

1. [КРИТИЧНО] Валидация runtime route-map не требует обязательного/строгого контракта.
- `tools/processforge.py:16543-16548` — если `.pf/process-routes.yaml` отсутствует, `load_process_route_map()` возвращает пустой map без предупреждения.
- `tools/processforge.py:16573-16594` — `process-route-doctor` делает только базовые структурные проверки (id/from/to/mode), без полной проверки по `schemas/process-route-map.schema.json`.
- В репозитории `.pf/process-routes.yaml` отсутствует, но отсутствие файла не приводит к явной hard-fail-проверке в общих сценариях. Это скрывает дефект проектного маршрута при переходах к/из процесса в рантайме.

2. [КРИТИЧНО] Нет строгой нормализации/проверки связности `required_evidence`.
- `schemas/process-definition.schema.json:126` допускает список `required_evidence`, но это поле не обязательное для `evidence_definitions` (по-прежнему только рекомендация контрактной полноты).
- `tools/processforge.py:142?` и `143?` (`validate_process_contract`) проверяют совпадение `required_evidence` с `evidence_definitions` в режиме предупреждений и не всегда переводят это в fail для всех контекстов.
- Это даёт полуформальный уровень контракта по доказательствам и риск недопустимых ссылок в процессах, не заметных вне строгого режима.

3. [СЕРЬЁЗНО] Остаточные legacy-алиасы продолжают создавать двойную семантику.
- `schemas/process-definition.schema.json:290` и `315` — `automation_bindings` и `technical_obligations` coexist, а в `stage` также есть legacy-смысл `gates` через `exit_gates`.
- `tools/processforge.py:13668-13670` и `14326-14328` только пишут WARN для legacy-алиасов, не запрещают их.
- При смешении старых/новых полей это сохраняет неоднозначность трактовки стадии (WHAT/WHEN/HOW), хотя нормализация должна их упорядочить.

4. [СЕРЬЁЗНО] Проверка `process_transitions` и route-переходов частично независима и может рассинхроняться.
- `tools/processforge.py:141?` (`validate_process_contract`) проверяет `process_transitions` в пределах процесса (id/from/to/mode), но не проверяет связность с реальными маршрутами `.pf/process-routes.yaml`.
- `schemas/process-transition.schema.json` и `schemas/process-route-map.schema.json` описывают разные контракты, но в рантайм-путь/doctor нет сквозной сверки двух слоёв.

5. [СРЕДНЕ] Набор smoke не закрывает регрессии на уровне маршрутов и negative paths.
- `tools/smoke_process_stage_contract_normalization.py` проверяет happy-path для пользовательского процесса и базовые свойства наблюдателей/гейтов.
- Не проверяется: отсутствующий `process-routes.yaml`, некорректная привязка `process_transitions` → route map, и негативные сценарии для stale/неполных контекстов.

## Что уже корректно подтверждено
- Runtime-обработка стадии больше не тянет «жёстко» literal `prepare/start/collect`; есть приоритеты в `execution_stage`, fallback через `runtime_execution_boundary` и durable-state:
  - `tools/pf_runtime/host.py:83-90`, `127-151`, `694-718`.
- Авторинг и материализация уже поддерживают `automation_bindings` и используют `evidence_definitions`:
  - `tools/processforge.py:13455`, `118`, и smoke-fixture в `tools/smoke_process_stage_contract_normalization.py`.
- Документация процесса содержит правильную трактовку separation WHAT/WHEN/HOW:
  - `docs/authoring/process-authoring.md:44-55`.

## Рекомендуемая доработка для прохождения ревью
- Добавить hard-fail правило для отсутствующего `.pf/process-routes.yaml` в сценариях, где используется route-based handoff.
- Расширить `process-route-doctor` до проверки по `schemas/process-route-map.schema.json` и сквозной валидации связей `process_transitions` ↔ route map.
- Ужесточить политику по legacy alias: либо удалить из активного schema, либо переводить в fail при новом режиме нормализации, хотя WARN оставить только для режима совместимости.
- Добить smoke тестами: отсутствие route-map, некорректные ссылки в `required_evidence`, конфликт переходов и route map.