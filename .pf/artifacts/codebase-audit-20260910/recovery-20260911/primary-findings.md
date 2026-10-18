# Независимая проверка результатов аудита

Дата: 2026-09-11. Проверенный commit: `901d0551773fe7a5b382b89ebe95b212b0747e83`.
Область: завершение существующего аудита и диагностики. Исправления продукта,
публикация и изменение установленной инфраструктуры в эту работу не входят.

## Подтверждённые проблемы

| ID | Приоритет | Проблема | Точки реализации | Доказательство |
|---|---|---|---|---|
| A01 | P1 | Источник поиска выходит за границы файлового ресурса | `src/processforge_core/local_resource_search.py:352` | `file-root-primary.txt` |
| A02 | P1 | Сбор отчёта читает файл за пределами проекта | `tools/processforge.py:18404`, `:19065`, `:19093`; `tools/pf_runtime/host.py:850` | `collection-primary-results.json`, case `external_report` |
| A03 | P1 | Отсутствующее задание останавливает поток планировщика | `tools/pf_runtime/service.py:349`, `:368` | `runtime_health.stdout.json`, case `missing_assignment` |
| A04 | P2 | Ответ Runtime скрывает ухудшение состояния | `tools/pf_runtime/service.py:304`, `:309` | `runtime_health.stdout.json`, case `invalid_task_order` |
| A05 | P2 | Отсутствующий источник миграции оставляет update в `applying` | `src/processforge_core/core_update.py:236`, `:321`, `:611` | `migration-source-primary.txt` |
| A06 | P2 | Авторизованный отчёт с путями не проходит сбор | `tools/pf_runtime/host.py:923`; `tools/processforge.py:19128` | `collection-primary-results.json`, case `path_content` |
| A07 | P2 | MCP не находит успешно зарегистрированную сессию с заглавными буквами | `tools/processforge.py:17084`, `:17137`, `:17263`; `tools/pf_runtime/session_read.py:43` | `mcp-primary-results.json`, `Case-Session` и контроль `lower-session` |
| A08 | P2 | Нарушены проверки запросов и уведомлений JSON-RPC | `tools/pf_runtime/mcp_server.py:290`, `:301`, `:311` | `mcp-primary-results.json`, `protocol` |
| A09 | P2 | Представление пути классификатора даёт ложный `stale` | `tools/processforge.py:3673`, `:10269` | `classification_origin.stdout.json`; текущие ответы MCP и source CLI |
| A10 | P1 | Захват singleton-lock у живого orphaned владельца | `tools/pf_runtime/service.py:181`, `:255` | `hooks-primary-results.json`, `orphan_takeover` |
| A11 | P2 | Startup и resume имеют одинаковый normalized event id | `tools/pf_runtime/codex_hooks.py:48`, `:71`; `tools/pf_runtime/host.py:591` | `hooks-primary-results.json`, `session_start_resume` |

P1 означает высокий приоритет исправления; P2 — следующий приоритет.
Оценка не утверждает эксплуатацию без прав на настройку ресурсов/заданий.

## Триггеры, результат и границы

### A01 — граница файлового ресурса

Ресурс разрешает единственный файл `allowed.md`, но источник `../secret.txt`
проверяется относительно родительской папки файла. Реальные `_iter_source_files`,
`build_index` и `search` индексируют соседний файл и возвращают его маркер:
`SEARCH_TOTAL 1`, `RESULT_PATHS ['secret.txt']`.

Проба использует явно заданный ресурс/источник, а не подмену результатов поиска.
Это нарушение ограничения источника при ошибочной или недоверенной конфигурации;
не доказательство чтения произвольного проекта обычным поисковым запросом.
Для файлового корня допустим только сам файл. Для каталога нужно сохранить
каноническую проверку вложенности и действующие include/exclude.

### A02 — граница expected report

В отдельном тестовом PF-проекте назначен `expected_report.artifact: ../outside.md`.
Настоящий collector принимает внешний безвредный маркер, создаёт один assistant
message и ставит задачу в `done`. Обе попытки завершаются с кодом 0.
Ожидается отказ до чтения и до записи содержимого в raw/chat.

Общий resolver должен отклонять абсолютные пути, переходы `..` и выход через
symlink. Его должны применять и collector, и авторизация входящего отчёта.
Реальный Windows symlink-сценарий в этой проверке не выполнялся.

### A03 / A04 — живучесть и состояние Runtime

Изолированный RuntimeProcess с настоящим Core обрабатывает повреждённый run.
Отсутствующее assignment вызывает `SystemExit`, который не перехватывается
`except Exception`. Поток перестаёт работать, но статус и health равны `ready`.
Отдельная ошибка `order: invalid` ловится: внутренняя health становится
`degraded`, а `status_payload()` всё равно выдаёт `ready`.

Дополнительно реальный повреждённый JSON host cache вызывает JSONDecodeError
из `known_project_roots()` до блока try и тоже завершает поток без записи
last_scheduler_error (`hooks-primary-results.json`, `cache_read_failure`).
Это второй воспроизведённый триггер задачи A03, а не отдельная дублирующая задача.

Нужно изолировать ошибки одной работы от планировщика и отражать фактическую
health/liveness. Нельзя просто перехватить все BaseException без различения
штатной остановки и ошибок исполнения. Установленный Runtime не изменялся.

### A05 — журнал обновления

ZIP содержит миграцию `copy_if_missing` со ссылкой на отсутствующий member.
`build_plan` возвращает `planned`, затем настоящий `apply_update` бросает сырой
KeyError. `runtime/core-update/in-progress.json` остаётся `applying`.

Проверить migration source до записи и оформить структурированную ошибку.
Проверка повторена в одноразовом Core/Workplace; установленная копия не затронута.

### A06 — содержимое авторизованного отчёта

Положительный контроль: обычный отчёт после двух collect даёт ровно одно сообщение.
Отчёт с абсолютным Windows-путём после двух collect даёт коды `[1, 1]`, ноль
сообщений и `unsafe_automatic_content`. Сохранение raw успешно в обеих попытках.

Нужна отдельная политика для аутентифицированного PF-owned output после всех
проверок задания, попытки, пути, точных байтов, native id и hash. Проверки
секретов и отказ для чужого происхождения сохраняются.

Исправление прежнего заключения: дедупликация сама по себе не останавливает
повторную derivation. Она снова отклоняется из-за содержимого. Старое объяснение
из `context-collection-20260910/report-capture/report.md` не принимается.

### A07 — идентичность сессии

Настоящие `agent-checkin` и native stdio MCP выполнены в одноразовом workplace.
Оба check-in успешны. Для `lower-session` чтение проходит, для `Case-Session`
ответ содержит `unknown_session`. Историческая расширенная проба также описывает
коллизию двух идентификаторов, различающихся регистром; в этом проходе первичный
контроль повторял одиночный mixed-case lookup, а не отдельную collision matrix.

Сохранить точную opaque identity; для имени файла использовать безопасное
кодирование или digest с защитой от коллизий. Простое приведение всех id к
нижнему регистру неприемлемо без изменения контракта и миграции.

### A08 — протокол MCP

Настоящий subprocess сервера отвечает на notification `tools/list`; принимает
`jsonrpc: 1.0` для initialize; массивы вместо `params`/`arguments` превращает
в пустой словарь и выдаёт прикладную ошибку. Нужна валидация envelope и параметров
до dispatch, правильные ошибки запроса/параметров и подавление ответов на
корректные notifications. Схема инструмента не заменяет проверки на сервере.

### A09 — ложное устаревание классификации

Байты classifier-файлов source и установленной копии имеют одинаковый SHA-256.
Но `matched_rules[].source` содержит полный относительный путь в первом случае
и только basename во втором. Сравнивается весь объект классификации.

Это воспроизведённая зависимость от расположения distribution, а не доказательство
устаревшего процесса MCP. Нужно отделить семантическую identity/fingerprint
классификатора от отображаемого пути, сохранив stale при настоящих изменениях.
Перезапуск или очередное обновление snapshot не исправляет этот контракт.

### A10 — живой владелец orphaned Runtime

Настоящие service/lock JSON содержат живой OS PID и несовпадающие instance id.
`inspect_lifecycle()` честно возвращает orphaned, но `acquire_singleton()`
удаляет lock и записывает new-owner. Проверка использует настоящие файлы,
PID-проверку и os.open, без заглушек этих операций. Второй daemon не запускался:
подтверждён именно ошибочный захват ownership при живом владельце.

Нужно блокировать orphaned при acquire и согласовать проверку отсутствующего
lock с service state. Отдельно проверить конкурентный старт и разрешённую
операторскую recovery-процедуру после завершения старого процесса.

### A11 — потеря resume

В настоящем одноразовом workplace через native envelope/host ingest доставлены
SessionStart startup и resume с одинаковой сессией. Raw ids различаются, но
normalized ids совпадают; resume получает duplicate=true. В project journal
остаётся только agent.session.started. При формировании event id не учтён source.

В identity включить различимые lifecycle facts, сохранив идемпотентность
повторной доставки одного факта. Отдельно проверить repeated resumes, clear и
compact с учётом реально доступных provider identifiers; одного source может
быть недостаточно для различения нескольких возобновлений.

### Отклонённый вывод H-01

Воркер показал mock-счётчик двух dispatch при одной записи event. Это верно
как наблюдение, но не доказывает контракт ровно одной delivery или вредный
downstream эффект. Документация различает факт события и delivery attempt.
Предложение просто убрать повторный dispatch может сломать восстановление
после записи event и до dispatch. В подтверждённые дефекты/задачи H-01 не включён.

## Воспроизведение

Из корня репозитория:

```powershell
python .pf/artifacts/codebase-audit-20260910/recovery-20260911/verify_primary.py
python .pf/artifacts/codebase-audit-20260910/recovery-20260911/verify_collection.py
python .pf/artifacts/codebase-audit-20260910/recovery-20260911/verify_hooks.py
python .pf/artifacts/codebase-audit-20260910/native-core/audit_core_update_missing_migration_source.py
python .pf/artifacts/codebase-audit-20260910/native-core/audit_search_file_root_escape.py
```

Сборщик проверяется через настоящие PF fixtures и Core command. Обёртка
`host.ingest_event` лишь сохраняет ответ; авторизация, raw ingress, dedup,
транскрипт и завершение задачи не подменены. Подробные JSON сохраняются рядом.

## Контроль качества и ограничения

- Выводы shell-воркеров принимаются после независимого воспроизведения первичным агентом.
- Ошибки создания временных папок внутри worker sandbox не объявлены дефектами PF.
- Прежние отчёты и attempt1 логи сохранены; первичная ошибочная инвентаризация
  native-папок исправлена в журнале погружения.
- Полный release-test не выполнялся: это аудит, а не релизная квалификация.
- Новых изменений продуктового кода, установки, коммитов и публикаций нет.
