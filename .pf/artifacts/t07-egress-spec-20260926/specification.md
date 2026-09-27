# T07: локальная фильтрация исходящих данных исполнителя

Статус: **design-only specification**. Этот пакет определяет будущую реализацию и её приёмку. Он не включает privacy engine, интеграцию модели или подтверждение контроля текущих adapters. Текущая `.pf` capsule имеет contract v1 и остаётся неизменной; proposed v2 ниже относится только к будущим egress-bound Work.

## Задача и состав пакета

PF должен отдельно решать два вопроса: можно ли исполнителю прочитать источник и можно ли раскрыть конкретные данные конкретному получателю. Требуется проверять начальный пакет, последующие чтения файлов, результаты инструментов и экспорт. Фильтрация выполняется локально до выпуска bytes; отправлять секрет модели для классификации нельзя.

| Документ | Назначение |
|---|---|
| [Scope R01–R09](scope.md) | Граница T07 и требования |
| [Investigation](investigation.md), [source map](source-map.json) | Текущее поведение по локальному исходному коду, точные symbols/lines/hashes |
| [Privacy domain](privacy-domain.md) | Классы данных, доверие и allow/redact/block |
| [Threat model H01–H14](threat-model.md) | Угрозы, меры и остаточные ограничения |
| [Architecture](architecture.md), [decisions D01–D10](decision-log.md) | Компоненты, contracts, dispatch, budgets, audit/export |
| [Implementation plan I01–I08](implementation-plan.md) | Отдельная реализация, зависимости, оценка 31–52 дня |
| [Acceptance matrix A01–A28](acceptance-matrix.json) | Будущие тесты, ожидаемые результаты и необходимые доказательства |
| [Synthetic examples E01–E05](examples.json) | Примеры формы решений; не действующая схема/API |

Домен и архитектура задают правила; таблицы примеров иллюстрируют их и не создают обходов. В случае неразрешимого противоречия строгая операция блокируется до уточнения versioned policy. Правила не подменяют authorization Work, tool effects и stage gates.

## Политика по умолчанию

| Класс | Решение при отсутствии специального разрешения |
|---|---|
| public | allow лишь при подтверждённой классификации, scope, purpose и зарегистрированном recipient |
| internal | block внешнему получателю; разрешение требует явного recipient/purpose rule |
| restricted / personal_data | block; допустима явно описанная, проверенная redaction либо отдельная разрешённая локальная обработка |
| secret / credential | Значение модели не передавать; разрешённое удаление значения может дать derived view, если обязательный смысл сохранён |
| unknown / unsupported | block в strict режиме; отсутствие regex совпадения не переводит в public |

Теги независимы от класса. Locked deny, scope denial и запрет current policy всегда сильнее разрешения, исключения false positive и результата redaction. При разных полевых решениях mandatory block блокирует envelope. Optional omission возможен только по явному правилу и с локальной записью omission. Обязательный смысл задаётся контрактом поля/задачи и квалифицированным transformation rule; произвольный пересказ модели не считается доказательством его сохранения.

## Граница API, предлагаемая для реализации

Логические операции, не существующие сейчас вызовы MCP:

- `prepare_view(context, attempt, recipient, units)` проверяет grants/policy/capabilities, возвращает immutable local view handle и безопасное решение либо block.
- `read_resource(session, opaque_handle, bounded_request)` заново проверяет scope, source identity и текущие запреты; возвращает только утверждённое представление. Raw local_root и contents не возвращаются без проверки.
- `invoke_tool(session, operation, arguments)` сначала авторизует effect и arguments, выполняет доверенный локальный tool в разрешённой среде, затем фильтрует весь результат для получателя.
- `dispatch(view_handle, binding)` локально проверяет nonce/digest/budget/current deny, сохраняет обязательную receipt и передаёт exact approved bytes. Caller не подставляет произвольный body в обход view.
- `export_view(source, audience, policy)` создаёт отдельный derivative, не изменяет source/capsule и не наследует их оценку doctor автоматически.

Причины отказа включают `egress_contract_required`, `authorization_denied`, `invalid_binding`, `source_changed`, `recipient_denied`, `enforcement_unavailable`, `unsupported_content`, `classification_failed`, `budget_exceeded`, `required_semantics_lost`, `audit_unavailable`. Внешнее сообщение содержит безопасную категорию и opaque request id; полная private диагностика не копируется в модель. Причины различаются от transport исхода `delivery_unknown` после возможного раскрытия.

## Проверяемое поведение

Начальный prepared input остаётся локальным оригиналом. Модель получает только allowlist view. Все последующие выдачи повторяют ту же policy; если backend не способен принудительно закрыть native обход, он не получает `mediated_session`. `payload_only` означает ровно проверенный начальный пакет. `isolated_local` требует проверки отсутствия внешнего обмена и не следует из места запуска CLI.

Binding включает Work/context/stage/attempt, policy/detectors, recipient/route, view digest и одноразовый nonce. Смена policy/route требует повторной проверки; ослабление immutable intent — successor. Доставленные ранее bytes отозвать невозможно. Неопределённый исход передачи остаётся неопределённым и не запускает слепой retry.

Первый срез поддерживает bounded UTF-8/JSON. Слишком большой материал, timeout, unsupported binary/stream или невозможность сохранить обязательный смысл приводят к block до выдачи. Файловые имена, IDs, hashes, ошибки, stderr, env и tool metadata рассматриваются как данные. Разделение credential channel и model data обязательно.

Audit не хранит raw совпадения секретов. Внешний export не содержит private linkage к originals. Исторический T06 metadata finding покрывается сценарием A19: новый очищенный export может пройти свою проверку, при этом original и его doctor FAIL сохраняются. Настоящее исправление механизма export не выполнено этим пакетом.

## Критерии приёмки T07 и будущего engine

Для **документов T07**: требования R01–R09 и угрозы H01–H14 связаны с будущими A01–A28; внутренние ссылки и JSON читаемы; source anchors соответствуют текущим hashes; архитектура не обещает неподтверждённую isolation; границы неизменяемых записей и существующая рабочая копия сохранены; результаты документной проверки записаны отдельно.

Для **будущего engine**: выполнить acceptance-matrix со synthetic corpus, fault injection, проверкой exact outbound bytes и квалификацией конкретного backend. Все 28 строк сейчас имеют `not_run`. Проверка JSON/ссылок/документов не является успешным выполнением этих тестов. Local/remote parity относится к одинаковым policy/permissions, а не к разным уровням доверия.

Не покрываются готовой гарантией: произвольный desktop/browser executor, скомпрометированная ОС, все возможные кодировки и семантические утечки, правовая оценка данных, криптографическая анонимизация, удаление уже переданных данных. Следующий ограниченный шаг — I01 feasibility одного backend; реализация Core и интеграция модели требуют отдельного Work.
