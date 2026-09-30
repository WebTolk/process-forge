# Аудит документации ProcessForge относительно кода

Дата: 2026-09-30. Source baseline: `25952e6d65a306054b0c29c33912267add7b2c0e`.

**Вердикт: документация не соответствует кодовой базе полностью.** Найдено 20 подтверждённых расхождений: 4 P1, 15 P2 и 1 P3. Смысловые утверждения проверены отдельным слоем: наличие команды, поля, шаблона или успешного smoke не считается доказательством обещанного поведения.

P1 — в первую очередь исправить ложные гарантии контроля/приватности; P2 — исправить поведение, конфигурацию и сценарии; P3 — уточнить терминологию. Приоритет описывает риск документации, а не CVSS или доказанную эксплуатацию.

## Охват и метод

Проинвентаризированы 427 отслеживаемых Markdown-файлов. В разрешённой области — 415 файлов (21 093 строки) и 3 SVG: README/QUICKSTART, docs EN/RU, authoring/process guides, prompts, templates, examples, official packs, migration notes и tools README. 12 исторических файлов logs перечислены как исключённые: они не являются актуальным публичным руководством и не входят в read scope этой Work. Локальная .pf использована для контекста и доказательств, не как нормативная документация продукта.

Сопоставлены тексты, исполняемые ветви, схемы, Process YAML и реальные CLI handlers. Проверены как положительные возможности, так и отрицательные обещания («нет», «только», «не допускает»). Нормативное требование к агенту отделено от автоматической проверки PF; историческая запись не трактуется как обещание текущей версии. Переводы проверены отдельно, поскольку часть RU страниц уже исправлена при устаревшем EN.

Serena не предоставила Python symbols (Active languages: []); для анализа использованы её поиск, bounded shell reads и AST (2 959 определений). Службы, host и установленный Core не обновлялись. Доказательства относятся к текущему source; внешний клиент, release archive и connected-host acceptance не переаттестованы.

## Структурные и исполняемые проверки

- Расширенный разбор: 809 fenced CLI-примеров приняты настоящим parser и имеют handler; ошибок нет (`cli-handler-map.json`). Штатный smoke покрывает 660 примеров и 425 ссылок и завершился PASS; это меньший набор, а не противоречивые счётчики.
- 425 локальных Markdown-ссылок ведут к существующим файлам; единственный локальный anchor совпадает. Внешние ссылки и актуальность сторонних клиентов не проверялись сетью.
- 83 YAML/JSON-блока проверены синтаксически: 82 самостоятельных документа валидны; один блок egress содержит четыре альтернативных JSON-операции, каждая проверена отдельно. Он не является единым JSON document.
- Списки стадий 29 процессов сопоставлены с YAML: 27 совпали, 2 имеют пропуск D13. Сводные EN/RU таблицы имеют тот же пропуск.
- Изолированные контрпримеры подтвердили D01, D02, D03, D12, D19. Они не меняют product state. Дополнительные native regression receipts находятся в supporting-checks.json.

Результат проверки синтаксиса или отсутствие найденного расхождения не является универсальным доказательством всех свойств файла. Для конкретных гарантий используйте ссылки на ветви кода и контрпримеры ниже; границы положительных свидетельств описаны в mechanism-evidence.md. Полный реестр корпуса — coverage.json.

## Реестр расхождений

### D01 · P1 · Handoff может завершиться без ожидаемых файлов

**Документация:** `docs/concepts/handoff-contracts.md:7`, `docs/ru/concepts/handoff-contracts.md:7`.

**Код:** `tools/processforge.py:17816`, `tools/processforge.py:17834`.

**Фактически:** return проверяет только явно переданные --artifact; пустой список допустим. expected_results не сопоставляется с результатами. finalize допускает даже accepted/in_progress без return.

**Последствие:** Документ обещает проверку полноты, которой нет; завершённый handoff нельзя считать доказательством получения ожидаемых результатов.

**Исправление:** Описать проверку переданных файлов отдельно от полноты expected_results. Автоматическую проверку полноты реализовать отдельной задачей, если это требуемый контракт.

**Доказательство:** counterexamples.json:handoff_without_expected_output.

### D02 · P2 · Artifact area не заменяет разрешённую область записи

**Документация:** `docs/concepts/multi-agent-orchestration.md:31`, `docs/ru/concepts/multi-agent-orchestration.md:31`, `docs/getting-started/multi-agent-orchestration.md:3`.

**Код:** `tools/processforge.py:20062`, `tools/processforge.py:18072`, `src/processforge_core/work_context.py:219`, `src/processforge_core/work_context.py:392`.

**Фактически:** Старый validator разрешает output в .pf/artifacts вне allowed_files, но execution_contract требует совпадения с allowlist. Default plan содержит .pf/artifacts/fixture-a/** и выход .pf/artifacts/fixture-a-report.md: validator PASS, право записи false.

**Последствие:** Успешная проверка плана не доказывает готовность worker; штатная заготовка требует исправления scope до запуска.

**Исправление:** Убрать исключение для artifact area, согласовать default plan, шаблоны и руководство с execution_contract; проверять готовность полного пути.

**Доказательство:** counterexamples.json:artifact_area_does_not_grant_write.

### D03 · P2 · Не все неподдерживаемые поля плана отклоняются

**Документация:** `docs/concepts/multi-agent-orchestration.md:26`, `docs/ru/concepts/multi-agent-orchestration.md:26`.

**Код:** `tools/processforge.py:19980`, `tools/processforge.py:20082`.

**Фактически:** Allowlist применяется к отдельным уровням, а неизвестные поля run, orchestrator и integration остаются без ошибки. Внесение unsupported_behavior во все три объекта не даёт FAIL.

**Последствие:** Опечатка или предполагаемая настройка могут молча не влиять на поведение вопреки обещанию документа.

**Исправление:** Перечислить реально проверяемые уровни; остальные назвать metadata-only либо добавить рекурсивную валидацию.

**Доказательство:** counterexamples.json:unknown_nested_fields.

### D04 · P2 · Ограничения захвата ответов отстали от адаптера

**Документация:** `docs/concepts/chat-relay.md:23`, `docs/ru/concepts/chat-relay.md:5`, `docs/concepts/agent-session-model.md:109`, `docs/ru/concepts/agent-session-model.md:134`, `docs/known-limitations.md:62`.

**Код:** `tools/pf_runtime/codex_hooks.py:123`, `tools/pf_runtime/codex_adapters.py:43`, `tools/pf_runtime/host.py:910`.

**Фактически:** Адаптер создаёт сообщения из last_assistant_message для Stop, SubagentStop и SessionEnd. Host допускает их после проверки provenance и project/session authorization. RU known-limitations уже описывает часть этого поведения правильно.

**Последствие:** Утверждение, что автоматически фиксируется только пользовательский prompt, занижает фактический объём записи. Универсальный перехват всех ответов по-прежнему не заявляется.

**Исправление:** Перечислить поддержанные финальные сообщения и условия допуска; сохранить ограничения streaming, отсутствующих полей и реальной регистрации hooks.

**Доказательство:** source.

### D05 · P2 · Документация указывает неверный fallback диагностики

**Документация:** `docs/concepts/diagnostics.md:23`, `docs/ru/concepts/diagnostics.md:36`.

**Код:** `src/processforge_core/diagnostics.py:573`.

**Фактически:** При ошибке конфигурации действует off/none. Отдельно допускается фиксированное сообщение здоровья в stderr. На той же странице ниже это уже описано правильно.

**Последствие:** Оператор ожидает работающий quiet/stderr collector, хотя необязательный сбор отключён.

**Исправление:** Заменить раннее описание quiet/stderr на off/none плюс фиксированное уведомление, согласовать EN/RU.

**Доказательство:** source.

### D06 · P2 · Перечень текущих MCP tools неполон

**Документация:** `docs/concepts/runtime-mcp.md:31`, `docs/ru/concepts/runtime-mcp.md:32`.

**Код:** `tools/pf_runtime/mcp_server.py:16`.

**Фактически:** В опубликованном TOOLS есть pf.continuation.create/status/resume и pf.work.cancel. Перечень, названный текущим source-контрактом, их не содержит.

**Последствие:** Читатель получает устаревший путь продолжения и не видит штатную отмену Work.

**Исправление:** Обновить каталог и связать continuation/cancel с точными selectors; генерировать перечень из TOOLS.

**Доказательство:** source.

### D07 · P1 · Semantic policy merge описан как более общий механизм, чем реализовано

**Документация:** `docs/concepts/context-resolution.md:45`, `docs/ru/concepts/context-resolution.md:46`, `docs/concepts/instruction-conflicts.md:27`, `docs/concepts/cascade-merge.md:35`, `docs/ru/concepts/cascade-merge.md:37`.

**Код:** `tools/processforge.py:11622`, `tools/processforge.py:11732`, `tools/processforge.py:8774`.

**Фактически:** build_context_payload собирает источники, capabilities и несколько конкретных конфликтов, затем формирует фиксированные hard/locked/gate записи и пустые preferences. Общий классификатор произвольных инструкций, semantic merge и распознавание ослабления locked policies отсутствуют. Структурный merge parameters работает, но не выполняет эту смысловую задачу.

**Последствие:** Обещание общего технического контроля hard/locked/gate создаёт ложную гарантию. Это не отменяет конкретных работающих проверок Work, ресурсов, diagnostics или egress.

**Исправление:** Разделить реализованные проверки и нормативные обязанности агента. Неподдержанные semantic merge/approval назвать проектным замыслом либо реализовать отдельно.

**Доказательство:** source.

### D08 · P2 · Граница governed Work смешана с legacy handoff target Run

**Документация:** `docs/concepts/process-transitions.md:9`.

**Код:** `tools/processforge.py:17799`, `src/processforge_core/process_execution.py:215`.

**Фактически:** handoff-start-target-run создаёт или повторно использует legacy Run через run-create; Assignment и immutable capsule этой командой не создаются. Новый governed Work создаётся отдельным Work API.

**Последствие:** Читатель может принять появление target Run за готовый bounded Work с capsule.

**Исправление:** Уточнить, что новый Run+capsule — контракт governed Work и отдельной операции старта; явно описать ограничение legacy handoff-start-target-run.

**Доказательство:** source.

### D09 · P1 · Документированы неработающие настройки chat_capture и hooks задания

**Документация:** `docs/concepts/chat-relay.md:63`, `docs/concepts/assignment-front-matter.md:30`, `docs/concepts/assignment-front-matter.md:55`, `templates/assignment-front-matter-template.md:20`.

**Код:** `tools/processforge.py:11375`, `tools/processforge.py:11393`, `src/processforge_core/work_context.py:161`.

**Фактически:** Production-код не читает assignment chat_capture, max_message_chars, notify_wtaicc или emit_on_complete. append_chat_message применяет фиксированную redaction/длину; include_content передаётся реальным аргументом вызова, а не этим assignment-блоком.

**Последствие:** Пользователь может полагаться на enabled:false, allow_private_paths:false или send_to_outbox как действующие средства управления приватностью. Наличие такого YAML их не включает.

**Исправление:** Удалить рекомендации неподдержанных настроек или явно пометить их metadata-only/future. Описать фактические CLI/host настройки и фиксированные ограничения.

**Доказательство:** semantic-probes.json:production_literal_consumers; source trace.

### D10 · P2 · Known limitations отрицает уже реализованные leases и Codex driver

**Документация:** `docs/known-limitations.md:14`, `docs/ru/known-limitations.md:14`.

**Код:** `tools/processforge.py:17523`, `tools/processforge.py:17902`, `templates/runtime-drivers/codex-exec.yaml:1`, `tools/codex_exec_worker.py:1`.

**Фактически:** Есть agent-lease-grant/release/revoke и Director scheduling с leases. Штатный codex-exec запускает реальную оболочку Codex; далее на странице он даже перечислен.

**Последствие:** Неверно описаны доступные механизмы координации и исполнения.

**Исправление:** Отделить существующую bounded lease-координацию от несуществующего распределённого scheduler и перечислить реальные поддержанные драйверы.

**Доказательство:** source.

### D11 · P2 · В authoring указан неверный ключ requires_capabilities

**Документация:** `docs/authoring/process-authoring.md:177`, `docs/ru/authoring/process-authoring.md:121`.

**Код:** `schemas/process-definition.schema.json:124`, `schemas/process-definition.schema.json:286`, `src/processforge_core/work_context.py:550`.

**Фактически:** Код и схема используют required_capabilities. Ключ requires_capabilities из руководства не является полем требований stage.

**Последствие:** Автор может записать требования в поле, которое не участвует в проверке capabilities.

**Исправление:** Исправить обе страницы на required_capabilities и добавить проверку примера against schema/normalizer.

**Доказательство:** source.

### D12 · P2 · Gate не является единственной блокирующей поверхностью перехода

**Документация:** `docs/authoring/process-authoring.md:42`.

**Код:** `src/processforge_core/process_execution.py:1110`, `src/processforge_core/process_execution.py:1136`.

**Фактически:** Помимо gates, _stage_requirements непосредственно возвращает required_input_missing, artifact_evidence_missing, required_evidence_missing и automation_not_ready. Связь obligation с gate не устраняет независимую проверку.

**Последствие:** Обещание единственного blocker surface и отсутствия второго blocker list не соответствует устройству движка.

**Исправление:** Описать все текущие условия перехода; либо изменить движок под заявленный единый gate-контракт в отдельной работе.

**Доказательство:** semantic-probes.json:non_gate_blockers.

### D13 · P2 · Карты инициализации пропускают search-index-maintenance

**Документация:** `docs/processes/project-initialization.md:25`, `docs/processes/workplace-initialization.md:25`, `docs/processes/built-in-processes.md:72`, `docs/ru/processes/built-in-processes.md:76`.

**Код:** `processes/core/project-initialization.yaml:263`, `processes/core/workplace-initialization.yaml:329`.

**Фактически:** В обеих YAML definitions есть завершающий search-index-maintenance со своим артефактом и gate. Его нет в соответствующих списках стадий и сводной таблице EN/RU.

**Последствие:** Человекочитаемая карта показывает неполный lifecycle.

**Исправление:** Синхронизировать подробные страницы и таблицы с YAML; включить этот diff в docs-check.

**Доказательство:** process-documentation.json: two mismatches.

### D14 · P1 · Private runtime outputs названы публичными

**Документация:** `docs/processes/process-supervisor.md:28`.

**Код:** `.processforge-releaseignore:7`, `tools/processforge.py:92`.

**Фактически:** Раздел Public Outputs перечисляет command/process/status, stdout/stderr и другие файлы .pf/runtime/agent-runs. Эта область является приватной и исключена из публичной поставки.

**Последствие:** Такой заголовок может привести к публикации локальных путей, команд или содержимого worker output.

**Исправление:** Назвать раздел Private runtime outputs; отдельно перечислить разрешённые санитизированные delivery artifacts.

**Доказательство:** source.

### D15 · P3 · Диаграмма приписывает summary завершение session

**Документация:** `docs/assets/processforge-run-lifecycle.svg:47`.

**Код:** `tools/processforge.py:20843`, `tools/processforge.py:20871`.

**Фактически:** run-summary сохраняет summary/handoff и событие run.summary.created, но не переводит Run в completed и не делает session checkout. run-complete — отдельная операция; session-end относится к Ledger.

**Последствие:** Смешиваются артефакт отчёта, завершение Run и завершение сессии.

**Исправление:** Показать отдельные шаги summary, run-complete и при необходимости session-end; не называть summary закрытием session.

**Доказательство:** source.

### D16 · P2 · Evolve extraction представлено как автоматическое поведение

**Документация:** `docs/concepts/evolve-mechanism.md:8`, `docs/concepts/evolve-mechanism.md:25`, `docs/ru/concepts/evolve-mechanism.md:9`, `docs/ru/concepts/evolve-mechanism.md:29`.

**Код:** `tools/processforge.py:16159`, `tools/processforge.py:16182`, `tools/processforge.py:16028`.

**Фактически:** evolve-run создаёт каталоги и отчёт с пустым candidates; добавляет только явно переданные candidate_file. Смысловое извлечение и выбор narrowest safe scope выполняет агент/автор кандидата, а не общий автоматический extractor или таймер end_of_run.

**Последствие:** Наличие evolve.enabled и timing не гарантирует автоматическое создание осмысленных кандидатов.

**Исправление:** Описать разделение: агент извлекает и оформляет кандидаты; CLI валидирует, сохраняет и перемещает явно переданные записи. Отдельно отметить декларативность timing/hooks.

**Доказательство:** source.

### D17 · P2 · Lifecycle modes и delivery_profile не являются машинными переключателями

**Документация:** `docs/concepts/execution-context-package.md:3`, `docs/concepts/resource-management.md:9`, `packs/official/software-development/docs/processes/software-feature-development.md:17`, `examples/process-authoring/software-feature-development/README.md:12`.

**Код:** `packs/official/software-development/processes/software-feature-development.yaml:12`, `packs/official/software-development/processes/software-feature-development.yaml:62`, `src/processforge_core/process_execution.py:215`, `src/processforge_core/work_context.py:161`.

**Фактически:** lifecycle_modes и preferred_shape execution_profile живут в metadata процесса. В production нет потребителей lifecycle_mode, stage_decisions, execution_profile. Движок не выбирает сокращённый маршрут и не запускает delivery profile по этим полям; действует pinned stages и обычное evidence API.

**Последствие:** Примеры выглядят как исполняемая конфигурация, хотя это соглашение агента. Нельзя считать выбор implementation_only разрешением автоматически пропустить стадии.

**Исправление:** Явно назвать поля агентскими метаданными/соглашением и показать реальный путь not_applicable evidence. Не обещать загрузку/исполнение delivery profile без отдельного механизма.

**Доказательство:** semantic-probes.json:production_literal_consumers; process metadata.

### D18 · P2 · Onboarding prompt ошибочно обещает создание START

**Документация:** `prompts/project-onboarding-agent.md:34`.

**Код:** `tools/processforge.py:5989`, `tools/processforge.py:5993`, `src/processforge_core/agent_start_prompt.py:108`.

**Фактически:** Initializer исключает .pf/START_AGENT_HERE.md даже из старого file map. Создание возможно только отдельным явным agent-start-prompt --apply. Пример minimal-project и project-init-proposal-template описывают это правильно.

**Последствие:** Инструкция агенту расходится с фактическим onboarding и остальными актуальными страницами.

**Исправление:** Исправить пункт 18: новый onboarding START не создаёт; preview и явное compatibility placement — отдельные действия.

**Доказательство:** source.

### D19 · P2 · Отсутствие promotion approval не всегда удерживает кандидат вне curated notes

**Документация:** `docs/concepts/knowledge-hub.md:25`, `docs/ru/concepts/knowledge-hub.md:30`, `docs/ru/concepts/platform-inheritance.md:80`.

**Код:** `tools/processforge.py:15973`, `tools/processforge.py:16311`.

**Фактически:** candidate_ready_for_curated_package допускает parent_platform_rule и universal_rule независимо от promotion.status. Схемно валидный parent_platform_rule с proposed/unreviewed проходит текущую валидацию и попадает в candidate-notes.md, где назван Reviewed.

**Последствие:** Документ обещает более строгий барьер curation, чем проверяет builder; название уровня не доказывает фактическое review.

**Исправление:** Документировать явное исключение и ручную ответственность либо требовать approved promotion/review для всех широких правил.

**Доказательство:** semantic-probes.json:unapproved_parent_rule_curated.

### D20 · P2 · Tools README ошибочно обещает только стандартную библиотеку

**Документация:** `tools/README.md:35`.

**Код:** `requirements.txt:1`, `src/processforge_core/work_context.py:18`, `src/processforge_core/continuation.py:12`.

**Фактически:** В requirements объявлен PyYAML>=6.0, а несколько основных сервисов импортируют yaml напрямую. Это внешняя зависимость.

**Последствие:** Инструкция по зависимостям не соответствует запускаемому инструменту.

**Исправление:** Указать Python stdlib плюс зависимости requirements.txt; согласовать с корневым README.

**Доказательство:** source.

## Рекомендуемый порядок исправления

1. Убрать ложные гарантии D01/D07/D09 и ошибочную публичность D14. Если обещанная гарантия нужна продукту, создать отдельную задачу реализации; не маскировать отсутствие механизма переименованием поля.
2. Согласовать Work/legacy boundaries, orchestration readiness, gates, evolve и metadata-only поля (D02/D03/D08/D12/D16/D17/D19).
3. Синхронно исправить EN/RU, каталоги, onboarding prompt и зависимости (D04–D06/D10/D11/D13/D18/D20), затем диаграмму D15.
4. В regression docs-check добавить негативные контрпримеры гарантий, сравнение TOOLS и стадий YAML. Парсер CLI оставить как отдельную структурную проверку.

В этой Work подготовлен аудит; публичные документы и код не исправлялись. Итог не утверждает соответствия всего продукта, безопасности произвольного host или полноты всех возможных сценариев. Исторические proof reports и утверждения о внешних клиентах остаются привязаны к своей версии и уровню доказательства.
