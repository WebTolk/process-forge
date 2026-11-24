# Хранение исполнений и границы authority

Неизменяемые DTO находятся в `processforge_core.executions.model`, синхронный
Protocol `ExecutionRepository` — в `executions.ports`. Импорт и конструирование
не выполняют I/O и не создают backend. Repository, service, наблюдение ОС,
миграция и композиция адаптеров относятся к отдельным слоям. Этот срез DTO сам
по себе не включает SQL route и не доказывает интеграционную приёмку Runtime.

## Семантическое версионирование и обязательная миграция

Разработка строго следует [Semantic Versioning 2.0.0](https://semver.org/) и
[долгосрочным правилам контрибьютера](../../../CONTRIBUTING.ru.md#готовность-хранилища-и-обязательная-миграция).
Совместимость оценивается по опубликованным контрактам глазами пользователя
и его агентов: поддерживаемые сценарии, публичные интерфейсы, интеграции,
гарантии данных и идентичности. Несовместимые публичные изменения требуют MAJOR,
совместимые возможности — MINOR, совместимые исправления — PATCH. Правило
не привязано к фиксированному релизу. Промежуточные нерелизные реализации и тесты
не добавляют публичных контрактов.

Небольшая поддерживаемая миграция проекта сама по себе не требует MAJOR. Внутренние
форматы хранения могут меняться через явную миграцию предоставленными инструментами
с сохранением этих пользовательских контрактов без переделки интеграций.
Процедуры миграции и восстановления нужно документировать и проверять.
Наличие инструмента миграции не делает сломанный публичный контракт совместимым.

Новый проект сразу создаёт актуальные журналы и хранилища. Старый проект обязан
завершить применимую квалифицированную миграцию до возобновления обычной записи.
Выпущенные гарантии данных и идентичности сохраняются; обход миграции обычной
legacy-записью не допускается. Отсутствие доказательств readiness или safety
означает отказ, а не успешное обновление.

## Идентичность и валидация

`ExecutionKey(project_id, run_id, task_id, attempt)` обозначает попытку
существующего назначения; `task_id` равен assignment ID, новой сущности нет.
Непустые UTF-8 идентификаторы без NUL сохраняются точно: регистр, пробелы вокруг
непустого значения и форма Unicode не меняются. Пустые и состоящие только из
пробельных символов строки отвергаются. Нет повторной нормализации, идентичности
из пути или замены ID. Проверка допустимости filesystem selectors остаётся у
вызывающего слоя. Attempt — точный int >= 1; bool отвергается.

DTO — frozen dataclasses. Revision >= 1, generation >= 0,
`0 <= projected_revision <= revision`. Process identity содержит host,
необязательный boot, положительный PID, непрозрачный birth ID и необязательный
owned-tree ID. Проверка формы не доказывает существование процесса или отсутствие
его дерева.

Payload — JSON object без повторных ключей, нечисловых/бесконечных чисел, NUL
и строк, непредставимых в UTF-8. Модель сохраняет исходный текст и unknown fields.
Адаптер проверяет compatibility schema и канонизирует transaction payload:
sorted keys, compact separators, UTF-8, `ensure_ascii=False`, `allow_nan=False`.
Конструктор не проверяет подлинность receipt или соответствие checksum исходным
байтам, которых в DTO нет. Timestamp наблюдения требует явного UTC offset;
launch/store ID имеют форму UUID hex, checksum — `sha256:` и 64 строчных hex-цифры.

## Независимые владельцы

| Факты | Источник authority |
| --- | --- |
| Стадии Run и Assignment | Существующий Work YAML |
| Канонические knowledge и file resources | Существующие файлы |
| Capsules, prepared inputs, содержательные artifacts | Неизменяемые файлы |
| Интерпретированные execution facts после committed SQL cutover | Project SQL |
| Process/heartbeat/exit receipts | Evidence, допускаемое по exact launch identity |
| `status.json` после cutover | Производная compatibility projection |
| Владение сессиями Ledger | Существующий Agent Ledger |

Legacy events/hooks/accounting/search сохраняют распознанные пути, domain
application IDs, domain versions и данные. Search остаётся отдельной производной
БД. Добавление UUID metadata в распознанные legacy stores отличается от PF main
envelope и execution JSON import: оно не переносит domain rows и не включает SQL
execution authority. Будущий workplace main store не активируется. Топология
остаётся переходной; другие драйверы, RAG, scheduler и полная консолидация legacy
domains не входят в этот контракт.

`pf_store_meta` сохраняет UUID/scope/stable owner identity, `pf_schema_versions` —
code-owned namespaces, версии и checksums. Legacy adoption регистрирует только
`store_identity@1`, сохраняя квалифицированные domain schemas, constraints и FTS
objects. Main использует собственный envelope с `execution@1` и
`execution_migration@1`. Legacy identity pins и execution binding закрепляют
точные targets; у execution main нет дублирующего legacy identity pin. UUID
metadata сама не выдаёт доступ и не заменяет domain validation. Чужие,
повреждённые, будущие, изменённые или конфликтующие stores отвергаются без
переименования формата или обхода через rebuild.

## Конфигурация и неизменяемые снимки

Один native `ConfigurationProvider`, привязанный к точному контексту, предоставляет
полный application `PFConfig` для CLI, standalone Core, MCP/Runtime/hooks, workers
и maintenance. Для разрешённых ключей порядок: builtin -> device -> явно
сохранённые поля выбранного workplace -> project -> authorized context. Presence
берётся из того же валидированного чтения YAML; явно заданные false/default
перекрывают базу, отсутствующие workplace keys наследуют device. Project/context
используют typed allowlist `ProjectPFConfig` и null-inherit. Они не меняют locked
policy или поля вне allowlist. Конфигурация не выдаёт filesystem, SQL,
инфраструктурные права или доступ к телам model-visible inputs.

Device source содержит полный PFConfig, а не driver-only global reader.
`database.driver` следует тому же merge; SQLite — operational default при
отсутствии selector и единственный реализованный драйвер. Отсутствующая
конфигурация не требует нового файла или сериализации секции `database`.
Profiles остаются отдельным валидированным механизмом targets: collisions и
нарушение scope отвергаются; refresh не переключает bound store UUID/path.
Объявленный device path выбирается один раз на command/session без disk scan
или CWD discovery. Provider и CRUD описаны в
[Runtime configuration](runtime-configuration.md).

Host получает один явный snapshot на operation и передаёт pinned provider
downstream. Refresh влияет только на следующие операции; существующий snapshot
не меняется. Mutable global current-project config отсутствует. Cold construction
ничего не читает и не инициализирует. Pure reads не создают config, DB или
maintenance files. Первый invalid input даёт ошибку; later invalid reload
сохраняет last-valid source вместе с presence и diagnostics по прежним правилам.

Новый native launch передаёт private attempt-local `configuration.snapshot.json`,
закреплённый до spawn и проверяемый по exact authorized path, hash, attempt
identity, размеру <= 65536 bytes и strict PFConfig shape. Wrapper передаёт тот же pointer/hash
дочернему процессу без чтения live config посреди attempt. Sidecar не является
policy, prompt input, публичным status field или изменением capsule. Его native
scope должен быть явно выдан; нехватка прав блокирует dependent launch.
Уже работающие legacy wrappers сохраняют прежний route. Standalone wrapper без
pinned transport может использовать provider только при собственном разрешённом
read scope. Metadata-only visibility не разрешает чтение тела.

## Физическая активность, outcome и collection

Внутренние фазы: prepared, starting, running, stopping, unresolved, absent.
Current snapshot содержит только starting/running/stopping/unresolved.
Prepared attempt не создаёт current row. Reservation коммитится до создания
процесса. Смерть контроллера сохраняет unresolved ownership; TTL не доказывает
освобождение. Запрос stop и успешный сигнал не доказывают физическое отсутствие.
Повторное использование PID, запрет OS inspection, недоказанное отсутствие
потомков или нехватка evidence сохраняют unknown activity.

Доказанное отсутствие полного дерева атомарно связывает outcome с монотонным
history sequence и удаляет current ownership. Внутренние outcomes: completed,
failed, timed_out, cancelled, unknown_exit, lost, blocked. Они не добавляют
публичных status enum values: в частности, unknown_exit отображается адаптером
в существующий внешний статус. Public payload schema остаётся версии 1;
launch token, revision и generation не добавляются в публичный status.

Collection независимо принимает pending/collected/failed/refused. Ошибка сбора
не возрождает процесс, semantic refusal не означает принятие результата.
Поздний receipt/collection не меняет порядок history. Evidence старой попытки
может менять только её точный key; load_latest не выбирает цель такой мутации.

## Repository и гарантии чтения

Мутации сравнивают generation и expected revision. Receipt допускается по exact
key, launch token, kind, sequence и checksum: уже принятое идентичное evidence —
no-op, тот же sequence с другим содержимым — конфликт, меньший sequence — stale
no-op. Birth identity прикреплённого процесса неизменяема. Domain ports не
принимают SQL session, CLI object или filesystem path. Транзакция не охватывает
spawn, сигналы, wait, чтение output, backup, сканирование или projection I/O.

`current(limit=128, deadline=None)` читает readiness и только индексированные
current rows в одном snapshot. Limit — 1..1000. Переполнение, unknown coverage,
отсутствующая/неподдержанная БД и истёкший deadline не превращают неполный пустой
результат в доказательство нулевой активности. Deadline — absolute monotonic.
Guard не сканирует history, не читает terminal receipts, не reconciles и не
посылает сигналы. History pages используют монотонный sequence, закреплённый
high water и default limit 256; `after=None` означает конец страниц.
Projection ack выполняет CAS latest key/revision/generation без увеличения
lifecycle revision.

SQL heads/current/history sequence, launch tokens, process identity, receipt
admissions и projection ack остаются отдельными фактами с разными ролями.
Под существующим task lifecycle lock projection публикует последний authoritative
compatibility DTO через atomic replace `status.json`, затем выполняет CAS ack.
Сбой оставляет head dirty для indexed/exact-task repair; старая попытка не
перезаписывает latest projection. CLI/MCP/continuation после cutover читают SQL,
даже если projection устарела.

## Admission и ограниченное наблюдение

Capable spawn paths берут workplace admission при enrollment, затем project
admission, existing task lifecycle lock и SQL transaction. Reservation коммитится
до spawn; SQL transaction не охватывает создание процесса. Shutdown и registration
используют тот же admission protocol и durable Runtime stopping fence. Unknown
routing/ownership/tree state или gate timeout сохраняет unknown activity; TTL и
PID-only probes не доказывают idle. Enrolled project не обходит недоступный
workplace gate, объявляя себя standalone. Guard с бюджетом 500 ms только наблюдает
ограниченное current state: без migration, backup или history scan. Acceptance
400000 history с zero-terminal reads относится к SQL-ready operation; legacy
projects сохраняют прежний bounded observer. File-only operation не требует
bootstrap Runtime/MCP, network или LLM.

## Миграция журнала событий одного проекта при работающем Runtime

Для существующего SQLite-журнала событий зарегистрированного проекта
используйте `--project-events` и передайте корни проекта и его Workplace.
Runtime должен объявлять возможность `project_event_maintenance`. Перед
переносом остановите внешних писателей, которые обращаются к выбранному
журналу напрямую.

```text
python -B tools/migrate-storage.py --project-root PROJECT --workplace-root WORKPLACE --project-events --inspect --json
python -B tools/migrate-storage.py --project-root PROJECT --workplace-root WORKPLACE --project-events --apply --json
python -B tools/migrate-storage.py --project-root PROJECT --workplace-root WORKPLACE --project-events --resume --json
```

В отчёте указан выбранный журнал. Мигратор ждёт окончания начатых операций с
хранилищами этого проекта, сохраняет проверенную резервную копию и точный план.
Пока журнал занят, операции проекта могут получить
`storage_project_event_maintenance_busy` или `storage_resume_required`.
Конкурирующий мигратор получает временный отказ. Остальные проекты продолжают
записывать события, доставлять хуки и выполнять Work через тот же Runtime.

После прерывания вызовите `--resume` с теми же корнями и конфигурацией при
работающем совместимом Runtime. Запись о незавершённом переносе закрывает
обычный доступ к журналу до окончания проверки. Проверьте `ready` через
`--inspect`, затем обновите контекст проекта.

Импортируйте старые записи NDJSON до начала миграции выбранного журнала. Если
неимпортированный NDJSON появился после публикации плана со статусом `pending`,
команда продолжения вернёт `storage_project_event_import_required`, а штатный
импортёр отклонит операцию с `storage_resume_required`. Сохраните файл NDJSON,
журнал SQLite и материалы миграции для восстановления.

Для общих хранилищ, базы исполнения и импорта старых NDJSON действует офлайн-процедура ниже.

## Явная миграция и ответственность за обновление

Новые проекты сразу используют SQL. Старые проекты с legacy-журналами блокируют
обычную запись Work/worker с `storage_migration_required`, пока оператор не
выполнит поддерживаемую миграцию. Чтение status/config/doctor её не запускает.
Обновление файлов Core не мигрирует все проекты автоматически.

В Гараже человек останавливает PF и всех писателей перед обслуживанием.
В Кузне updater останавливает единственный исполнитель PF, обновляет его и
запускает после обслуживания. PF не заявляет техническое исключение произвольных
исторических процессов. Исторический менеджер, enrollment, cold controller и
передача власти между конкретными версиями продукта не требуются.

После остановки PF проверьте и импортируйте event/raw-журналы, затем выполните
привязку существующих хранилищ и импорт execution snapshots:

```text
python -B bin/pf.py journal-maintenance inspect --project-root PROJECT --workplace WORKPLACE --json
python -B bin/pf.py journal-maintenance import --project-root PROJECT --workplace WORKPLACE --apply --json
python -B tools/migrate-storage.py --project-root PROJECT --workplace-root WORKPLACE --apply --offline-confirmed --json
```

`--offline-confirmed` фиксирует ответственность оператора/updater. Дополнительно
host требует реальный admission lock проекта/Workplace, отклоняет известный
работающий Runtime, закрепляет текущую конфигурацию, roots, owners и targets и
проверяет их перед изменениями. Подтверждение не отменяет проверок источников,
identity, схемы, backups и checkpoints. Неизвестные или изменённые данные
сохраняют блокировку.

Pending binding публикуется до изменения БД. Ready access проверяет UUID,
владельца, путь, схему и готовность. Отсутствующее или частично записанное bound
хранилище не получает новую identity и не переключается обратно на JSON.
Execution import сохраняет наблюдаемые snapshots и allocation floors, не
выдумывая перезаписанную историю. Batch и checkpoint фиксируются вместе.
Execution cutover — SQL CAS из importing/legacy в ready/sql; добавление UUID
metadata само по себе этим commit не является.

Миграция сохраняет frozen sources, transform hashes, проверенные WAL-aware
backups, журналы и checkpoints. Продолжение запускается явно для тех же roots
через `--resume --offline-confirmed`: проверяются исходный план, источники и
backup, UUID не заменяются, recovery evidence не перезаписывается. Сбой другого
target не откатывает уже готовое хранилище. После SQL-записей откат Core не
означает откат данных; JSON нельзя снова импортировать как новую истину.

Fresh authority подтверждается исключительным созданием flow root и receipt
`maintenance/project-initialization.json`; возможность запуска native worker
для этого не нужна. Main SQL и events готовы до первого onboarding event.
Project raw/search сохраняют planned UUIDs и создаются при первом использовании.
Восстановление использует прежние receipt, физический root, owner, routing и UUID.
Чужое, повреждённое или исчезнувшее ready-хранилище не пересоздаётся.

Native ownership workers и короткие OS leases сохраняются для их собственного
lifecycle. Они не доказывают отсутствие неизвестных старых процессов и не выдают
права на миграцию. Обычное чтение или запись не превращает старый проект в новый.
См. [обслуживание журналов и восстановление](sqlite-journal-maintenance.md).
