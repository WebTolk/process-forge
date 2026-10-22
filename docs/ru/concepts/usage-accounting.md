# Учёт usage

PF хранит счётчики токенов и наблюдаемые интервалы исполнения в одной локальной
базе workplace: `data/accounting/accounting.sqlite3`. Рабочее окружение находится
через существующую локальную ссылку проекта на его manifest. Подстановка checkout,
каталога установки или cache не применяется. Нужен явный `project.id` из PF
manifest. Общий `AccountingService` обслуживает все проекты и будущие клиенты;
устойчивый origin и явные project mappings сохраняются рядом с базой. Имя папки
не заменяет id. Явный импорт сохраняет исходные origin/source identity.

```sh
python bin/pf.py usage summary --project-root <project> --json
python bin/pf.py usage projects --project-root <project> --scope workplace --json
python bin/pf.py usage project --project-root <project> --json
python bin/pf.py usage task --project-root <project> --task <assignment> --json
python bin/pf.py usage run --project-root <project> --run <run> --json
python bin/pf.py usage attempt --project-root <project> --run <run> --task <assignment> --attempt 1 --json
python bin/pf.py usage details --project-root <project> --kind activity --json
```

Все команды возвращают JSON. По умолчанию разрешён только выбранный проект.
Локальный оператор может явно выбрать `--scope workplace`; управляемые workers
не могут так расширять scope. Будущие транспорты обязаны передавать собственный
разрешённый набор project ids в сервис; параметр CLI не заменяет аутентификацию.
Доступны `--project-id`, `--task`, `--run`, `--attempt`, `--source-id`, `--model`,
`--start`, `--end`, `--limit`, `--offset`. Окно UTC полуоткрытое `[start,end)`;
limit 1–500, offset 0–1000000. Pagination не ограничивает totals сводки.

Чтение использует read-only snapshot Core, не создаёт базу или origin. Если базы
нет, ответ содержит `status: unavailable`, `totals: null` и причину в coverage.
Неизвестный счётчик остаётся null, измеренный ноль — нулём. Cache входит во
входные токены, не прибавляется повторно. Неподтверждённый reasoning неизвестен.
Публичные DTO не содержат приватные пути receipts и provenance hashes. Полнота
и свежесть относятся только к объявленным/наблюдаемым источникам; вся активность
устройства не объявляется известной.

## Codex managed capture

Драйвер включает `codex exec --json`, сохраняя отдельный финальный отчёт `-o`,
heartbeat и exit code процесса. В native каталоге запуска каждая попытка получает
`usage-attempt-N` с `codex.jsonl`, `binding.json`, `timing.json` и результатом либо
ошибкой collection. Старые каталоги не перезаписываются. JSON stdout идёт сразу
на диск. Сбор выполняется и после ненулевого exit. Ошибка учёта не меняет exit
worker: receipts и ограниченная безопасная диагностика остаются для replay.

Из `turn.completed.usage` читаются `input_tokens`, `output_tokens`,
`cached_input_tokens`, `cache_write_input_tokens`, `reasoning_output_tokens`.
Кэш и reasoning являются подкатегориями, а не добавочными токенами.
Физические occurrences выделенного потока имеют разные
ordered ids даже при одинаковом payload. Без native timestamp используется
неизменяемое время наблюдения источника с partial quality; это не доказанная
граница конкретного запроса.

Измеряется один monotonic interval попытки; UTC start/finish остаются в raw
timing. Нормализованный интервал сохраняет оба наблюдаемых UTC-конца и независимую
монотонную длительность; качество часов и расхождение доступны в ответе. Для
расходящихся часов календарная доля длительности неизвестна, занятое время проекта
считается только по наблюдаемым прямым UTC-интервалам. При
обрыве может остаться открытая timing receipt; хвост не продолжается до времени
запроса. Ledger presence и дочерние интервалы не прибавляются к этой попытке.

## Явный импорт и replay

`collect`, `import`, `replay` выполняют одну ограниченную операцию:

```sh
python bin/pf.py usage import --project-root <project> --file <receipt.jsonl> --binding <binding.json> --json
python bin/pf.py usage replay --project-root <project> --file <codex.jsonl> --binding <binding.json> --timing <timing.json> --json
```

Импортёр должен иметь права на конкретные файлы и заранее доказать привязку.
Manifest — явное утверждение оператора/драйвера, не автоматически полученное
доказательство из произвольного payload. Истории сессий не обнаруживаются и не
сканируются. Файл ограничен 64 MiB, строка 1 MiB, metadata 64 KiB. Более крупные
источники требуют явно квалифицированных сегментов со стабильными source ids.
Пакет максимум из 100 строк и его cursor фиксируются одной транзакцией. Cursor
закрепляет принятый префикс и binding. Replay не удваивает факты; изменённый или
усечённый префикс отклоняется. Torn/malformed tail явно возвращает ошибку,
сохраняя валидный префикс; после дописывания хвоста сбор продолжается. Нельзя
переиспользовать source id для другого/переписанного потока или менять
`observed_at` при replay. Семантические revisions выполняются через Core ingest,
не изменением импортированного потока.

Синтетический пример binding; каждую identity необходимо заменить проверенной:

```json
{
  "schema_version": 1,
  "primary_records": true,
  "origin_id": "explicit-stable-origin",
  "source_id": "explicit-stable-primary-stream",
  "profile": "kimi-code-2.3.0-v1",
  "observed_at": "2026-10-22T12:00:00Z",
  "attribution": {
    "project_id": "example",
    "agent_instance_id": "agent-1",
    "session_id": "session-1",
    "provider": "kimi",
    "model": "qualified-model"
  }
}
```

Work binding необязателен. Если он доказан, одновременно передаются `run_id`,
`assignment_id`, положительный `attempt`. Project/session usage без такой связи
остаётся непривязанным к задаче. Неизвестную модель можно не указывать.

## Kimi и ограничения квалификации

Профиль современного TypeScript `kimi-code` 2.3.0 принимает **квалифицированную
PF-проекцию** primary wire occurrences, а не произвольный native wire layout.
Импортёр предварительно проверяет occurrence/session identity, primary provenance
и привязку проекта/Work. Синтетический пример строки:

```json
{"type":"usage.record","primary":true,"occurrence_id":"native-request-1","session_id":"session-1","agentId":"agent-1","model":"qualified-model","usageScope":"session","timestamp":"2026-10-22T12:00:00Z","usage":{"inputOther":40,"inputCacheRead":20,"inputCacheCreation":10,"output":3}}
```

Вход — сумма трёх входных компонентов только при наличии каждого.
`usageScope=session` не исключает запись и не доказывает cumulative snapshot.
Primary deltas учитываются по устойчивому occurrence id; summary/status mirrors
и родительские копии дочернего расхода не должны проецироваться как новые факты.
Повтор одинакового occurrence дедуплицируется; конфликт payload отклоняет пакет
атомарно. PreCompact `token_count`/`estimated_token_count` не являются usage.
Профиль `kimi-cli-legacy-unsupported` явно записывает unsupported coverage без
чтения/нормализации legacy history.

Тесты включают синтетические пограничные случаи и обезличенный реальный terminal
receipt управляемого Codex. Схема современного Kimi проверена по исходникам и
синтетическим данным; native capture Kimi и общая полнота провайдеров и дочерних
агентов ещё не квалифицированы. Collection консервативно остаётся
partial, даже конец корректного файла возвращает `complete: false`.

Exit codes: 0 — успешный запрос/импорт; 1 — неверный ввод/scope/недоступная база;
2 — явная ошибка частичного ввода или unsupported source; 3 — конфликт replay.
Запрос отсутствующей базы успешен с unavailable envelope. MCP, TUI, плагины и
REST остаются будущими клиентами общего scoped query service.
