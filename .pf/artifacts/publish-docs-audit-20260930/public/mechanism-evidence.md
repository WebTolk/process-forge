# Реальные механизмы и границы доказательств

Узкие положительные утверждения ниже подтверждены указанными ветвями кода. Это не сертификат всех свойств каждого документа. Для CLI есть отдельное сопоставление каждого из 809 примеров с handler. Семантические расхождения представлены в report.md; отсутствие находки не равно доказательству всех возможных сценариев.

## M01: CLI и MCP

CLI parser принимает зафиксированные примеры и связывает их с настоящими handlers; MCP публикует TOOLS.

Код: `tools/processforge.py:26418`, `tools/pf_runtime/mcp_server.py:16`.

Проверка: cli-handler-map.json; semantic-probes.json:native_docs_smoke.

Граница: Разбор аргументов не доказывает результат команды. D06, D20.

## M02: Процесс и переходы Work

Движок использует pinned definition, проверяет selectors, contract и evidence перед переходом.

Код: `src/processforge_core/process_execution.py:586`, `src/processforge_core/process_execution.py:1136`.

Проверка: semantic-probes.json:non_gate_blockers; process-documentation.json.

Граница: Gate attestation не доказывает качество работы. D08, D11, D12, D13, D17.

## M03: Области и ресурсы Work

Work resource service проверяет run/assignment/capsule identity и process pin; доступ ограничен разрешёнными ресурсами.

Код: `src/processforge_core/work_resources.py:130`, `src/processforge_core/work_context.py:219`.

Проверка: supporting-checks.json:smoke_work_resource_binding.

Граница: Это проверки операций PF, а не sandbox произвольного shell или агента. Symlink fixture не поддержана host. D02.

## M04: Продолжение Work

Continuation v2 возвращает точные selectors; session binding сохраняется явно; legacy v1 не объявляется resumed Work.

Код: `src/processforge_core/continuation.py:252`.

Проверка: source review; текущая Work использует явные selectors.

Граница: Не выбирает newest/first assignment. Текущий аудит не повторяет все crash/reconnect сценарии.

## M05: Контекст и параметры

Структурный merge параметров использует реальные источники и provenance; контекст формируется отдельным builder.

Код: `tools/processforge.py:8783`, `tools/processforge.py:8900`, `tools/processforge.py:11622`.

Проверка: supporting-checks.json:smoke_parameter_cascade_resolution.

Граница: Общий semantic policy merge этим не реализован: D07.

## M06: Поиск и resolve

Project search проверяет freshness; resolve отказывает ресурсу вне snapshot, Work navigation проверяет отдельную привязку.

Код: `src/processforge_core/garage.py:140`, `src/processforge_core/garage.py:167`, `src/processforge_core/local_resource_search.py:831`.

Проверка: source review; supporting-checks.json:smoke_work_resource_binding.

Граница: Fresh индекс с нулевым authorized coverage возможен; поиск не разрешает произвольное чтение.

## M07: Agent entry и onboarding

Renderer и migration раздельны; plan/apply/rollback имеют реальные реализации; onboarding защищает START от обычной записи.

Код: `src/processforge_core/agent_entry.py:82`, `src/processforge_core/agent_entry_migration.py:330`, `src/processforge_core/agent_entry_migration.py:526`, `tools/processforge.py:5989`.

Проверка: source review; существующие E10 receipts считаются историческими, не новым host proof.

Граница: Source не доказывает фактическую загрузку клиентом, POSIX или повторный host reconnect. D18.

## M08: Director, leases, handoff

Есть явные lease и handoff операции; legacy return/finalize имеют более слабые проверки, чем обещает текст.

Код: `tools/processforge.py:17523`, `tools/processforge.py:17799`, `tools/processforge.py:17816`, `tools/processforge.py:17902`.

Проверка: counterexamples.json.

Граница: D01, D02, D03, D08, D10. Операция summary не завершает session: D15.

## M09: Worker и prepared resources

Worker command строится из driver; prepared resources проходят отдельную авторизацию.

Код: `tools/processforge.py:18659`, `src/processforge_core/prepared_resources.py:276`, `tools/codex_exec_worker.py:1`.

Проверка: source review; driver manifests.

Граница: Не запускались реальные внешние модели/worker; private runtime output не становится public: D14.

## M10: Host, adapters, chat

Codex adapter преобразует поддержанные assistant events; host проверяет provenance и полномочия session/project.

Код: `tools/pf_runtime/codex_hooks.py:123`, `tools/pf_runtime/codex_adapters.py:43`, `tools/pf_runtime/host.py:910`, `tools/processforge.py:11393`.

Проверка: supporting-checks.json:smoke_provider_adapter_admission; semantic-probes.json:production_literal_consumers.

Граница: Это не универсальный transcript capture. Assignment chat_capture/hooks не исполняются: D04, D09.

## M11: Диагностика

Сбор имеет отдельные уровни/config, sanitizer и sinks; неисправная конфигурация отключает необязательный сбор.

Код: `src/processforge_core/diagnostics.py:112`, `src/processforge_core/diagnostics.py:573`.

Проверка: supporting-checks.json:smoke_diagnostics.

Граница: Fallback отличается от раннего текста: D05. Фиксированное stderr health notice не означает quiet collector.

## M12: Egress

Session проверяет operation shape и допускает read/tool/finish; лимиты disclosure и bytes проверяются до выдачи.

Код: `src/processforge_core/egress/engine.py:300`, `src/processforge_core/egress/engine.py:330`, `src/processforge_core/egress/transport.py:59`.

Проверка: source review; alternative-json.json.

Граница: Доказательство bounded mediated session, а не произвольной работы внешнего агента; сетевой recipient не запускался.

## M13: Knowledge/evolve

CLI принимает и валидирует явно переданных кандидатов; package builder формирует curation notes.

Код: `tools/processforge.py:15973`, `tools/processforge.py:16159`, `tools/processforge.py:16277`.

Проверка: semantic-probes.json:unapproved_parent_rule_curated.

Граница: Автоматический смысловой extractor отсутствует; approval barrier неполон: D16, D19.

## M14: Пакеты, платформы и capabilities

Root/path/resource resolution и registries представлены конкретными resolver функциями.

Код: `tools/processforge.py:8178`, `tools/processforge.py:8553`, `tools/processforge.py:8727`, `tools/processforge.py:9674`.

Проверка: source review; schemas и samples; cli-handler-map.json.

Граница: Наличие registry не доказывает установленный внешний tool. Agent conventions и машинные checks различаются.

## M15: Поставка и Core update

Manifest plan/apply, проверка payload и backup реализованы отдельно от release pack/test.

Код: `src/processforge_core/core_update.py:167`, `src/processforge_core/core_update.py:453`, `src/processforge_core/core_update.py:587`, `tools/processforge.py:7501`.

Проверка: supporting-checks.json:smoke_core_update_manifest.

Граница: В этом аудите нет новой сборки/установки/публикации; две symlink ветви теста пропущены Windows.
