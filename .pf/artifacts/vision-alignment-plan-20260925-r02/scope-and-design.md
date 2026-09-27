# Ревизия плана: scope и решения

- date: 2026-09-25
- process: software-feature-development@1.1.0
- run: garage-revise-the-vision-alignment-plan-with-explicit-mcp-operability-ac
- assignment: revise-the-vision-alignment-plan-with-explicit-mcp-operability-acceptanc
- lifecycle_mode: feature, documentation-only
- coordination: single_agent, без делегирования

## Task record / execution context / lifecycle decision

Запрос: дополнить план работоспособностью MCP и режимами диагностики и
логирования разной детализации по аналогии с PSR Log. Этот Run обновляет
план; исправление продукта и установленного MCP не объявляется выполненным.
MCP pf.context отвечает, но считает ctx-20260925-134006-95c757 stale;
source CLI project-context-check --session-start --json вернул fresh,
execution ready, policy continue, health warn. Work создана штатным source CLI;
assignment/capsule прочитаны, процесс закреплён. Хост не перезапускался.

## Brief / scope

Ручные записи разрешены только в .pf/artifacts/vision-alignment-plan-20260925-r02/**, новом журнале
.pf/logs/vision-alignment-plan-20260925-r02.md и новом handoff
.pf/handoffs/vision-alignment-plan-20260925-r02.md. PF самостоятельно
сохраняет текущий Run/Assignment/capsule, snapshot, отчёты и проекции.
Старый план, его evidence и завершённый Run остаются неизменными.

Generic code_changes_allowed в созданном assignment не расширяет эту область.
Не менять продуктовые src/tools/schemas/templates/docs, установленный Core,
Runtime/MCP/Ledger, исторические runs или чужие dirty-изменения.
Будущая T08 явно ставит достижение работоспособности MCP целью, а не вечным
исключением; конкретные live-операции выполняются в её согласованном scope.

Приёмка текущего среза: T08 и T09 имеют файлы/сложность/зависимости/проверки;
T01 и T06 учитывают их; нет циклов или зависимости ремонта MCP от полного
логгера; серьёзность отдельно от детализации; MCP startup не равен работоспособности;
старые документы побайтно сохранены. Продуктовый release не нужен.

## Investigation / impact analysis

Исследованы локальные docs/concepts/session-telemetry.md, runtime-mcp.md,
tools/processforge.py:11038–11053 и точки MCP в tools/pf_runtime/mcp_server.py.
append_telemetry_event пишет ts/event/payload в NDJSON с redaction; в этой
функции нет порога severity или диагностического профиля. Это не заявление
об отсутствии любой диагностики в PF. Существующие события переиспользовать,
а не создавать второй процессный журнал.

Serena повторно не извлекла символы: Active languages: []; применены точечные
rg/UTF-8 чтения. Локально найден справочник DelegatingPsrLogger Joomla
(только пример адаптера; Joomla не платформа этого проекта). Нормативная
семантика проверена в [PHP-FIG PSR-3](https://www.php-fig.org/psr/psr-3/).
Старое наблюдение о classifier provenance из памяти — гипотеза для T08,
не подтверждённая причина текущего отказа. Нужны свежие effective-root/version
и classification comparison, а не предположение о зависшем сервере.

Текущий impact — только документы. Будущий impact T08: транспорт, core loading,
freshness/provenance и доступность инструментов; T09: общий логгер,
сбор диагностик, приватность, stderr/JSON-RPC, затраты и хранение.

## Domain model / rules

Severity — серьёзность события. Verbosity/profile — сколько безопасных
подробностей собирать. Threshold — какие severity пропускать в диагностический
приёмник. Trace — профиль/трассировки, не девятый стандартный PSR-3 уровень.
Process journal/evidence остаются обязательными независимо от diagnostic off.
MCP live acceptance и CLI fallback — разные доказательства. Logger facade
не зависит от модели или транспорта; PSR-3 является аналогией, не PHP-зависимостью.

## Architecture / implementation plan текущего среза

Создать отдельную ревизию r02: plan.md — актуальный порядок T00–T09;
tasks.md — новые T08/T09 и явные поправки T01/T06, ссылки на неизменные
карточки T00–T07. Документировать разницу ревизий, исключить дублирование
старой доказательной базы. Добавить машинный граф task-graph.json.
Затем проверить ссылки, граф, уровни, старые хэши, scope и git diff --check;
записать review/test-report, delivery/handoff, evolution, пройти PF до завершения.

## Decision log / verification outline

T08 — восстановление MCP, P1; T09 — общий диагностический контракт, P1.
T08 зависит от T00, не от полного T09. T09 зависит от T01.
Практический порядок: ранний MCP T08 → T01 → T09 → T02 → T03 → T04 → T05 → T06.
T06 зависит от T02–T05, T08, T09 и повторно проверяет MCP после интеграции.
T07 остаётся отдельной веткой после T01/T05.

Точные продуктовые API/числовые уровни/расположение нового логгера выбираются
при исполнении задач, не закрепляются этим документальным Run.
Проверить DOC links, JSON graph/DAG, severity vocabulary, privacy/stdout/journal
границы, git scope и сохранение r01. Self-review без независимого аудитора.
