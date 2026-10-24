# R02 — согласованный контракт реализации

Дата: 2026-10-24. Статус: `ready_for_review`, не `approved`.
Run: `pf-r02-contract-20261024`; assignment: `pf-r02-w1-contract-20261024`; context: `pf-r02-w1-contract-20261024-capsule`; попытка 1.

Прочитаны закреплённый brief, orchestration plan и все четыре отчёта/карты попытки 2 из immutable prepared input. SHA256 capsule совпал. Результат — спецификация следующей реализации; продукт, тесты и живые данные не изменялись.

**Принятые решения**

- Публичный пакет: `processforge_core.database`. Первый SQL dialect — SQLite с bound parameters. Сменяемость обеспечивают доменные порты и backend adapters; универсального SQL, ORM, codec/driver registry и серверных драйверов в срезе нет.
- Основная проектная БД: `data/pf.sqlite3` относительно фактического flow root. Envelope: `application_id=0x50464D31`, `user_version=1`; отдельно `pf_store_meta` и `pf_schema_versions`. Простого перенаправления прежних SQLite owners нет.
- Новые namespaces: `execution@1` и `execution_migration@1`. Таблицы execution: state, attempts, heads, current и bounded receipt admissions. History — завершённые попытки с индексированным монотонным sequence; current содержит только неосвобождённое физическое владение.
- Identity: `project_id/run_id/task_id/attempt`; прежний `task_id` равен assignment ID. Отдельные launch token, revision и writer generation защищают поздние receipts. Дополнительный execution-instance ID не нужен. Для миграции требуется явно сохранённый `project.id`: фактический metadata reader иначе использует имя корневого каталога, что непригодно для устойчивого переноса.
- Work YAML, capsules, prepared inputs, содержательные артефакты и Ledger сохраняют своих владельцев. Accounting/events/hooks продолжают работать в прежних хранилищах. Workplace main DB этим срезом не активируется. Это переходная топология, не завершённая консолидация.

**API и оперативные гарантии**

В `implementation-contract.json` закреплены модули, DTO, точные сигнатуры Database/SqlSession/SchemaManager/DatabaseFactory, минимальные профили, ExecutionRepository, импорт и migration API.

Конструкторы и factory не выполняют I/O. Read — noncreating read-only snapshot; write — явный `BEGIN IMMEDIATE`, без скрытых retries и commits. DDL только через SchemaManager. Доменные ошибки не раскрывают SQL, параметры или приватные пути. Deadline guard ограничивает также ожидание SQLite.

Reservation фиксируется до `Popen`. Все lifecycle writers используют общий task lock и CAS по attempt/token/revision/generation. Сигнал stop и выход wrapper сами по себе не доказывают отсутствие дерева процессов. Неопределённость остаётся в current; TTL её не снимает. Доказанное отсутствие при неизвестном exit даёт `unknown_exit`, не успешный результат.

Collection учитывается отдельно. Его ошибка может сохранять прежний публичный `failed`, не возвращая физическую активность. После cutover CLI/MCP/continuation читают SQL; `status.json` сохраняет прежнюю форму как проекция. Dirty head и CAS позволяют повторить публикацию после сбоя без обхода истории. Время heartbeat берётся из принятого evidence, не из наличия файла.

**Минимальный admission fence**

Переиспользуется `registry_file_lock` с существующим OS guard. Порядок: workplace admission → project admission → task lock → короткая SQL transaction. Core получает lock callable через composition, не импортирует CLI.

Независимые start, регистрация проектов и guarded shutdown используют один workplace gate. Start публикует reservation до освобождения допуска. Shutdown проверяет покрытие и current, затем долговечно публикует instance-bound `stopping` до освобождения допуска. In-process state locks не удерживаются при ожидании межпроцессного gate.

Read-only guard не сигналит и не выполняет lifecycle reconciliation. Недоступный gate, неполное покрытие, неизвестная активность или превышение бюджета сохраняют `running=null` и существующий отказ `runtime_busy_or_activity_unknown`. `owner_changed` сохраняется. Старые неперенесённые проекты продолжают прежний bounded observer; гарантия независимости от 400000 history относится к SQL-ready проектам.

**Миграция и совместимость**

`ExecutionMigrationService.inspect/plan/apply/resume` использует descriptor, canonical SHA256, frozen manifest, ограниченные batches и checkpoint в той же transaction, что импорт. Переиспользуется `BackupPort/SQLiteBackupService`; backup на resume проверяется и повторно используется, не заменяется произвольной новой копией.

Переносятся наблюдаемые snapshots, точные исходные bytes, неизвестные поля и provenance. Отсутствующие старые попытки не реконструируются. Имена attempt directories учитываются только для безопасного следующего номера. Неизвестный attempt, конфликт identity и неизвестная текущая активность блокируют переход. Пропуск допускается лишь явно для доказанной исторической порчи.

Binding `data/execution-storage.json` закрепляет маршрут/store identity; SQL marker остаётся единственным владельцем readiness. Pending binding блокирует обычные исполнения. Cutover — одна transaction с CAS generation, `authority=sql`, `ready` и полным active coverage. Сбой последующего отчёта или проекции не отменяет commit.

До opt-in старые проекты используют прежний путь. Чтения, doctor и config ничего не создают. Fresh initialization разрешена только явному apply, действительно создающему новый flow root; существующий проект, включая `--force`, не становится fresh по отсутствию history. После cutover отсутствующая/повреждённая связанная БД даёт отказ, не JSON fallback.

**Конкретная граница безопасности:** старые бинарные клиенты не читают новый marker и не берут новый admission gate. Поэтому онлайн-переход со смешанными писателями не поддержан. Apply требует исключения старых entrypoints, подтверждённого offline maintenance и доказуемой quiescence; неизвестное владение блокирует cutover. Флаг подтверждения не выдаётся за техническое обнаружение всех старых процессов.

После новых SQL commits возврат старого Core без квалифицированного reverse export не поддержан. Предпочтительны resume/roll-forward; restore — в новое назначение при остановленных писателях. Конкретные номера старых релизов источниками не квалифицированы: контракт задаёт матрицу legacy/capable/future clients; перед rollout нужны доказательства для точных исходных и целевых байтов.

**Владение и последовательность**

| Владелец | Закреплённая ответственность |
| --- | --- |
| W1 | Execution DTO/ports, пакетный `__init__.py`, domain tests/docs |
| W2 | Database API/SQLite/envelope, configuration profiles/schemas, database tests/docs |
| W3 | Execution schema/repository/service/projection, admission/OS identity, все общие integration files, runtime tests/docs |
| W4 | Migration descriptor/scanner/checkpoints/binding, maintenance adapter/parser, migration tests/docs |

Точные непересекающиеся списки, включая `__init__.py`, находятся в контракте. Единственный владелец `tools/processforge.py`, composition/bootstrap, Runtime/host и fresh-init integration — W3. Прежние accounting/journal owners в этот объём не включены.

Порядок: W1/W2 → W3 repository/admission → W4 migration → W3 integration → адресная assurance итоговых байтов → независимый review после реализации. Новые файлы или смена сигнатур требуют governed handoff, не расширения scope исполнителем.

**Приёмка и ограничения**

Зафиксированы девять ограниченных групп acceptance: SQL/config; масштаб; гонки/сбои; identity/receipts/collection; migration/recovery; матрица клиентов; CLI/MCP/file-only/fresh-init; обязательные Python QA.

Матрица масштаба: 0/510/400000 terminal × 0/1/3 current. Нужны SQL trace, EXPLAIN, инструментированные чтения строк и запрет старого glob/terminal-file opens: ноль чтений terminal history, а не только хорошее время. Оба runtime consumers используют один current reader. Фиксируются latency, память, объём работы и поведение при исчерпании существующего бюджета 500 ms.

Структурная проверка завершилась с exit 0: JSON корректен; 69 файлов, четыре владельца, пересечений 0; девять acceptance-групп, пять dependency edges и точные DDL. SHA256 восьми входных отчётов/карт и шести проверенных исходников совпали; capsule также проверена. Это проверка артефактов и адресных стыков, не функциональная приёмка.

Product pytest/Ruff/mypy, benchmark, backup/restore и миграции не запускались по brief. Prepared MCP grants пусты; использован bounded shell fallback, без Serena/IDE. Совместимость выполнения ещё не доказана.

Native READ_ACK принят: `msg_50e5b8e9212a4448bf73a6d80d0ecfdf`; RESULT_READY принят: `msg_2b840638391f427fb965925aaebdb798`; heartbeat собственной identity выполнен и обновлён с exit 0. Новая Work, bootstrap/context rebuild, lifecycle transitions, коммиты, push и инфраструктурные действия не выполнялись.