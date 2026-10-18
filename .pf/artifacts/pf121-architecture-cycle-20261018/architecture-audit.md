# Архитектурный цикл ProcessForge после 1.2.0

Дата: 2026-10-18. Автор: primary-orchestrator. Содержательное исследование завершено. Результат — проверенный обзор действующей архитектуры, решения по предложениям четырёх native PF-воркеров и границы следующих срезов; продуктовый код в этом Work не менялся.

## Восстановление и доказательства

Прерванный основной Work возобновлён через native continuation `pf121-architecture-cycle-crash-resume-20261018`. Сохранены прежние run, assignment, capsule и stage investigation. Три прежних запуска продолжили работу; отсутствовавший MCP attempt подготовлен и запущен в уже созданном assignment. Все четыре attempt 1 завершились с exit 0, после чего выполнен native collect.

Основная identity: `garage-pf121-postrelease-architecture-cycle-20261018-orchestrate-four-na` / `pf121-postrelease-architecture-cycle-20261018-orchestrate-four-native-pf` / `pf121-postrelease-architecture-cycle-20261018-orchestrate-four-native-pf-capsule`. SHA-256 капсулы: `bb5c83b517d5690e6f0d3690a230a4f62a3935e3e83ef8be071d4275ee5a3638`.

Исходный CLI подтвердил snapshot `ctx-20261018-083156-60cda1` как fresh/ready/continue и Work как valid/ready. Подключённый installed MCP считает этот snapshot stale. Использован прежний source CLI-путь, уже описанный в handoff выпуска; обновление контекста, установка, ремонт и перезапуск инфраструктуры не выполнялись.

База исходников при исследовании — `2f027b9ff56019b96e17280dfe7e50bc7f5a43bc`, VERSION 1.2.0. SHA-256 монолита `tools/processforge.py`: `e99d35af720db9e0d9a1c2c2e5736d7f93004aea98bf25e34edeb5a49cd14855`. Отсутствие изменений проверено для продуктовых каталогов; всё рабочее дерево чистым не объявляется.

| Ответственность | Отчёт | Приёмка основным агентом |
| --- | --- | --- |
| Архитектура и остаток монолита | [topology](../pf121-oop-topology-20261018/report.md) | Приняты карта владельцев, различение исторических планов и текущего кода, три последовательных среза. Статическая инвентаризация не является процентом готовности. |
| Прикладные библиотеки | [libraries](../pf121-oop-libraries-20261018/report.md) | Принято сохранение существующей композиции и зависимостей. Предложение немедленно изменить operator logging сужено до будущего отдельного изменения с собственным контрактом. |
| Установка и обновление | [installation](../pf121-oop-installation-20261018/report.md) | Принята основа на текущих answers/proposal/review и разделение операций. Мастер и новые проверки входа остаются предложением. |
| MCP tools/resources | [MCP](../pf121-oop-mcp-20261018/report.md) | Приняты конкретные уточнения описаний и необходимость отдельного body-read контракта. Извлечение каталога и изменение его метаданных следует разделять по доказательствам. |

Подробные решения: [decision-log.md](decision-log.md). Домен: [domain-model.md](domain-model.md). Следующие срезы: [implementation-plan.md](implementation-plan.md).

## Фактическая готовность ООП

Самостоятельные Core owners уже есть для документов, Work records/metadata/context reads, process catalogue, project metadata/snapshot sources, чистых политик, resource material, конфигурации, диагностики, journals и других обязанностей. Их следует использовать повторно.

Остаток принципиален: `bootstrap_runtime` вызывает `_load_legacy_core`; normal composition ряда сценариев передаёт `core: Any` либо callbacks монолита. `ProjectContextService` без поля core всё ещё может получать legacy freshness callback. `ProcessExecutionService`, полный context compiler, worker/attendance/handoff и часть maintenance остаются неполностью перенесёнными.

Поэтому OOP-01–OOP-05 остаются открытыми. Число классов, строк и завершённых Work не даёт обоснованного процента. Принятый срез должен владеть алгоритмом и данными, переводить всех затронутых consumers и работать в normal default use без возврата в монолит.

Независимым чтением Serena основной агент подтвердил `bootstrap_runtime`, реальные legacy-связи composition, `append_operator_log`, алгоритм `merge_parameter_maps` и его вызов из `work/context.py`. Topology-воркер сообщил отсутствие Serena в своём окружении и использовал ограниченный AST/rg; остальные работали с доступной Serena. Общее ограничение не скрывается.

## Ближайший выбор

Первым рекомендуется перенос слияния параметров и provenance в `configuration/parameters.py` с одним владельцем `ParameterMergePolicy`. Операция уже существует, не требует I/O или новой зависимости и устраняет конкретный `core.merge_parameter_maps` вызов из Work compiler. Сохранить `None` как удаление, условия ID-list merge, порядок, дубликаты, deepcopy, provenance и ошибки.

Следом рассматриваются classifier rule matching и process artifact declarations. Все три среза затрагивают монолит, поэтому их полные реализации выполняются последовательно одним writer. Нельзя считать разные строки одного файла непересекающимися scopes. План содержит consumers, ловушки и необходимые узкие проверки.

Это следующий implementation scope, а не уже выполненный перенос. В текущем Work сформированы исследовательские документы; для продуктовой реализации нужно новое ограниченное admission с исходными specs/ADR/domain/direction и действующим migration contract.

## Библиотеки, установка и MCP

Новых обязательных пакетов сейчас не требуется. У PF уже есть явные factories, Protocol и dataclass. Собственная диагностика обеспечивает PF-specific envelopes, санитизацию, лимиты, корреляцию и межпроцессную запись. Прямой переход на обычный FileHandler не сохраняет весь контракт: стандартная библиотека отдельно оговаривает многопроцессную запись. [Python Logging Cookbook](https://docs.python.org/3/howto/logging-cookbook.html#logging-to-a-single-file-from-multiple-processes)

`append_operator_log` — полезный кандидат на отдельного владельца. Извлечение существующей записи и добавление санитизации/retention/quota имеют разный наблюдаемый результат; их нельзя объединить незаметно. `psutil` рассматривается только после определения нужных метрик, периода и потребителя; вес YAML-кэша не является лимитом RSS. [Документация psutil](https://psutil.io/)

Мастер установки должен использовать существующие прикладные операции и отдельный интерактивный адаптер, сохраняя неинтерактивный CLI. Проверка bindings между review и применяемым планом, строгие boolean/path проверки и исправление прежних fallback/force особенностей — самостоятельные изменения поведения. Core update, workplace setup, onboarding и миграция journals сохраняют отдельные подтверждения и границы восстановления; автоматический rollback всех данных не обещается.

MCP-каталог текущих исходников содержит 31 инструмент и 13 mutating tools. AST-проверка воркера подтвердила tools-only capability, прежнюю версию протокола и отсутствие resources/prompts handlers. Это исходная статическая проверка с запрещённым business dispatch, а не запуск нового MCP и не actual connected-host acceptance.

`pf.work_state` и `pf.work.state` имеют разные выпущенные payloads/селекторы; текст об алиасе нельзя исправлять изменением маршрута. `pf.search` может обслуживать производный SQLite index, несмотря на readOnlyHint; это отдельное решение об эффектах. Уточнения descriptions, schema fingerprints и выделение каталога требуют раздельной оценки, сохраняя имена, порядок, schemas, errors и dispatch.

Resources могут быть отдельным адаптером общего bounded read service. Успешный resolve, manifest или URI не разрешают отдавать тело документа. Нужны явная identity, body-read policy, current access, budgets и переносимое представление без private roots. Протокол разделяет list/read и поддерживает pagination; конкретные PF grants этим не задаются. [MCP Resources](https://modelcontextprotocol.io/specification/2025-11-25/server/resources)

## Актуальность документов

Справочник Core требует уточнения общей retention YAML-разбора и нынешних параметров factories. Исторические flat paths, предписания сохранить удалённые внутренние adapters, NDJSON journal планы и описание MCP как исключительно read-only не должны управлять сегодняшней реализацией. Старые approved материалы не переписываются; современная навигация и новые решения фиксируются отдельно.

Текущий контракт переноса от 10 октября приоритетнее ранних bridge/container предложений. Архитектурная цель общего Core сохраняется без обязательного универсального DI framework. File-only use cases остаются самостоятельными; будущие web/multi-workplace/device интерфейсы не дают повода хранить current Work/grants в глобальном singleton.

## Временные материалы и границы проверки

После проверки точных абсолютных целей, native Git ownership, отсутствия live process references, reparse points и сохранности доказательств удалены три чистых worktree, две consumer-распаковки и каталог `t` предыдущего выпуска. Учтено 26 166 файлов, 234 814 150 байт, около 223.94 MiB. `stable-preview` с шестью изменениями сохранён. [Preview](cleanup/preview.json), [выполнение](cleanup/applied.json).

Сохранённые ZIP обеих площадок имеют SHA-256 `0cd5c1f48ca0e94ddf5b0298b774a3498baf20e5a64b84dd9c05bbc0f36a2880`, оба manifest — `2881c62ff279c9d418d7bb88ad01a321817c1c7454ec03e10227d3f6791d40bd`. Сохранены документы и квитанции выпуска. Ранее отклонённые удаления concepts/audit и запись служебного checkpoint не повторялись другим механизмом.

Квалификация этой задачи: статическое исследование, native prepare/start/collect и Work validation, проверки документов/хешей/области изменений и cleanup readback. Полные release suites, установка, обновление устройства, Runtime и actual connected MCP acceptance не выполнялись. Независимое ревью продуктовой реализации относится к следующему срезу.

Handoff: завершить native стадии с содержательными evidence, закрепить исследовательские результаты отдельными коммитами, проверить обе dev-доставки и сохранить точную финальную передачу. Новую продуктовую Work данный документ не создаёт.
