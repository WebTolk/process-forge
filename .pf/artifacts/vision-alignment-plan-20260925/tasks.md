# Карточки предлагаемых задач

Карточки T01–T07 имеют статус proposed и не являются активными assignments.
T00 выполнена для текущего планирования; перед продуктовой реализацией
потребуются повторный preflight и отдельная Work.
Пути ниже определяют предполагаемые точки изменения; окончательный file scope
проверяется при investigation и закрепляется в новом назначении.
Новые пути помечены как предлагаемые, чтобы не выдавать их за существующий API.

## T00 — Подготовить PF-контекст и процесс

- Приоритет: prerequisite. Сложность: S. Зависимости: нет.
- Статус: environment_prepared_for_planning. Source CLI подтвердил fresh/ready
  и создал Work процесса software-feature-development. Подключённый MCP
  продолжает показывать старую картину; использован source CLI без ремонта хоста.
- Исходная проблема: stale snapshot; в allowed был только task-batch-execution.
- Область: .pf/process-forge.yaml, контекст и стандартные генерируемые
  артефакты его обновления. Возможные local overrides сначала проверить.
- Работа: сверить текущую конфигурацию; отразить выбранный оператором
  software-feature-development поддерживаемым способом; актуализировать
  контекст и создать новое Work с точной целью среза. Не продолжать r01 и
  другие старые runs по автоматической рекомендации.
- Приёмка: pf.context показывает ожидаемый процесс и свежий контекст;
  pf.work.start возвращает корректное новое Work/продолжение именно этого
  среза; pf.work.state и capsule совпадают по процессу и идентичности.
- Артефакты: execution-context-summary, task-record, lifecycle-mode-decision.
- Ограничение: эта карточка не предписывает запуск/ремонт инфраструктуры.

## T01 — Общий контракт работы и исполнителя

- Приоритет: P1. Сложность: L. Зависимости: T00.
- Область исследования: src/processforge_core/process_execution.py,
  src/processforge_core/garage.py, tools/processforge.py,
  tools/pf_runtime/host.py, schemas/context-capsule.schema.json,
  schemas/run.schema.json, schemas/runtime-driver.schema.json,
  docs/concepts/context-capsule.md, docs/concepts/declarative-process-execution.md.
- Работа: описать Work identity, snapshot generation, текущие запреты,
  stage resource subset, область файлов, outputs и capability requirements;
  разделить общий контракт и формат транспорта. Описать доверенную
  регистрацию адаптеров и владение provider-specific provenance rules.
- Решения: как остановить Work при недоступном закреплённом ресурсе;
  как явно сменить контекст без переписывания старой капсулы; какие поля
  принадлежат immutable-контракту, а какие — производной проекции стадии;
  как читать legacy records и когда требуется явная миграция.
- Приёмка: для каждого решения есть пример, отрицательный сценарий,
  правило совместимости и ожидаемая диагностика; базовый сценарий не зависит
  от имени модели, MCP или запущенного Runtime.
- Артефакты: domain-model/domain-rules, architecture, decision-log,
  implementation-plan и матрица тестов. Предлагаемый ADR — новый файл .pf/adr/.
- Ограничение: продуктовый код на этой задаче не изменяется.

## T02 — Контекстное чтение ресурсов конкретной Work

- Приоритет: P1. Сложность: L. Зависимости: T01.
- Основание: воспроизведение A → B из baseline.md.
- Область: src/processforge_core/process_execution.py,
  src/processforge_core/garage.py, src/processforge_core/local_resource_search.py,
  tools/pf_runtime/mcp_server.py, tools/processforge.py; схемы по решению T01.
- Работа: добавить явное чтение с идентичностью Work/контекста через общий
  прикладной сервис. Сохранить project-level навигацию с ясной областью.
  Передавать generation/resource identity в результат и evidence.
- Приёмка:
  - смена проектного выбора A на B не добавляет B к старой Work;
  - отзыв доступа к A даёт явный отказ/блокировку, а не обход через old snapshot;
  - изменение, удаление или недоступная версия A обнаруживаются;
  - две Work с разными контекстами не смешивают результаты;
  - CLI и MCP одинаково применяют правила; continuation сохраняет идентичность;
  - разрешения stage subset не расширяют Work и проектную авторизацию.
- Проверки: новая регрессия A/B (предлагаемый файл
  tools/smoke_work_resource_binding.py), существующие проверки project resource
  narrowing, multi-process capsule и pinned process.
- Артефакты: reproduction, change-summary, test-report, review, handoff.
- Совместимость: расширять публичный контракт версионно/аддитивно;
  не переопределять project-level search молча и не переписывать старые капсулы.

## T03 — Единое построение полного рабочего контекста

- Приоритет: P1. Сложность: L. Зависимости: T02.
- Область: ProcessExecutionService._write_capsule;
  tools/processforge.py:command_assignment_capsule,
  normalized_assignment_contract, resolve_assignment_parameters;
  schemas/context-capsule.schema.json, schemas/assignment.schema.json;
  новый общий модуль контекста — путь определяется T01.
- Работа: свести нормализацию контракта обоих путей к общей реализации.
  Формировать явные sources, scope, outputs, capabilities, ссылки на знания,
  tools/templates и доступ к ним. Статические данные отделить от текущей стадии.
- Приёмка:
  - одинаковое задание через оба входа даёт одинаковые существенные ограничения;
  - пустой scope/набор ресурсов имеет явное значение и не означает полный доступ;
  - analysis-only задание не получает право менять продукт по умолчанию;
  - отсутствующие обязательные источники/возможности явно диагностируются;
  - private paths не появляются в публичном контракте;
  - изменение assignment не позволяет незаметно использовать старую капсулу;
  - legacy capsules либо читаются совместимо, либо требуют описанного перехода.
- Проверки: новая parity-регрессия (предлагаемый файл
  tools/smoke_work_capsule_contract_parity.py), capsule pinning и workspace access.
- Артефакты: mapping полей двух путей, migration-notes, test-report, handoff.
- Ограничение: локальный extraction общего сервиса; общий рефакторинг CLI исключён.

## T04 — Доверенные адаптеры без условий провайдера в общем Host

- Приоритет: P1. Сложность: L. Зависимости: T01.
- Область: tools/pf_runtime/host.py:_allowed_conversation_message и связанные
  worker/session-end ветки; tools/pf_runtime/codex_hooks.py;
  tools/codex_exec_worker.py; src/processforge_core/project_initialization.py;
  tools/pf_runtime/mcp_server.py. Новая adapter registry/контракт — по T01.
- Работа: вынести Codex-specific интерпретацию и provenance validation в
  соответствующий адаптер; общий Host проверяет нейтральный результат и
  общие права. Универсальная регистрация не должна разрешать произвольную
  загрузку кода из недоверенного события. Рассмотреть перенос host-specific
  repair action из общего initialization API с сохранением совместимости.
- Приёмка:
  - тестовый другой провайдер подключается адаптером/доверенной регистрацией
    без правки host.py и raw_ingress_kernel.py;
  - неизвестный адаптер, подмена identity, неверный session/hash/path отвергаются;
  - raw-first запись, quarantine, deduplication и replay сохраняют поведение;
  - Codex hooks и worker-report capture проходят прежние регрессии;
  - отсутствие Codex не препятствует общему initialization/status.
- Проверки: новая provider-neutral integration fixture; существующие ingress,
  replay, worker provenance и Codex capture regressions, выбранные по impact.
- Артефакты: adapter contract, threat/compatibility notes, test-report, handoff.
- Ограничение: не снимать проверки безопасности для получения симметрии.

## T05 — Подготовленный вход для сменного исполнителя

- Приоритет: P2. Сложность: L. Зависимости: T03, T04.
- Область: tools/processforge.py:prepare_worker_run,
  render_worker_launch_prompt, write_workspace_access_runtime_file;
  templates/runtime-drivers/generic-shell.yaml,
  templates/runtime-drivers/manual.yaml,
  templates/runtime-drivers/codex-exec.yaml; tools/codex_exec_worker.py.
- Работа: до запуска разрешать источники, проверять доступ и формировать
  ограниченный пакет входа. Драйвер передаёт пакет подходящим способом:
  файл/CLI/MCP. События запуска, heartbeat, итог и сбор evidence по возможности
  выполняет обвязка. Из промпта убрать дублирование уже выполненной навигации.
- Приёмка:
  - детерминированный generic-shell fixture без MCP/сети получает только
    разрешённые материалы и возвращает проверяемый результат;
  - отсутствующий доступ блокирует подготовку до запуска исполнителя;
  - запускается только один Work, существующая капсула не вызывает новый bootstrap;
  - переключение драйвера не меняет процесс, scope и обязательные outputs;
  - большие ресурсы выдаются ограниченными ссылками/порциями по контракту,
    весь корпус не копируется автоматически;
  - результат корректно принимается после restart/retry без дубликатов.
- Проверки: новый tools/smoke_prepared_execution_context.py (предлагаемый путь),
  generic shell, manual preparation и Codex payload compatibility.
- Артефакты: delivery contract, before/after обязанностей агента, test-report.
- Ограничение: fixture доказывает контракт исполнения, а не качество или
  фактическую поддержку произвольной локальной языковой модели.

## T06 — Сквозная приёмка и передача

- Приоритет: P1, обязательный gate. Сложность: M. Зависимости: T02–T05.
- Область: затронутые smokes и release-test registration;
  docs/concepts/context-capsule.md, garage-core.md,
  declarative-process-execution.md, runtime-drivers.md, runtime-mcp.md;
  соответствующие существующие RU-документы и PF evidence.
- Работа: провести review после реализации; проверить общий сценарий
  Work → ограниченный контекст → generic executor → результат → смена
  сессии/исполнителя → продолжение. Выполнить матрицу совместимости и
  негативных проверок, синхронизировать документацию с фактическим API.
- Приёмка:
  - выполнены критерии T02–T05 и согласованная в T01 матрица;
  - источник каждого результата: declaration, deterministic check или
    semantic review — явно различим;
  - свежая сессия продолжает именно нужную Work по долговечным данным;
  - регрессии входят в стандартный QA-контур, публичные данные безопасны;
  - summary/handoff, известные ограничения и migration-notes согласованы.
- Поставка: локальный результат по умолчанию. При запросе пакета/релиза —
  clean source gate, archive parity и extracted-test отдельным delivery-срезом.
- Артефакты: review-findings, test-report, delivery-report с применимостью,
  evolution-report, run-summary и handoff. Нельзя объявлять релизный PASS по
  одним сфокусированным тестам.

## T07 — Спецификация локальной фильтрации исходящих данных

- Приоритет: P3, отдельное развитие. Сложность: L с уточнением после discovery.
- Зависимости: T01, T05.
- Отдельная ветка: не блокирует T06.
- Область исследования: подготовленный вход T05, tools/codex_exec_worker.py,
  общий запуск generic-shell, tools/processforge.py:redact_chat_content,
  privacy/public export contracts.
- Работа: описать классификацию данных, получателя local/remote, политику
  redact/block/allow и место проверки перед передачей данных исполнителю.
  Учесть не только начальный payload, но и последующие file/tool reads:
  проверка одного промпта не доказывает защиту всего взаимодействия.
- Приёмка спецификации: описаны trust boundaries, нерешённые вопросы,
  ограничения, audit trail и тесты для секретов/персональных данных,
  ложных срабатываний и одинакового применения правил всеми драйверами.
- Артефакты: privacy-domain notes, threat model, architecture options,
  отдельный implementation-plan с оценкой объёма.
- Ограничение: готовый privacy engine и интеграция локальной модели не
  входят в основную последовательность без новой предметной задачи.
