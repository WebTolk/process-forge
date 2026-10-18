# Новые задачи и уточнения — ревизия 02

Статус T08/T09: proposed. Ниже — требования будущей реализации, не уже
существующие настройки/команды PF. Обе задачи выполняются через отдельные
Works процесса software-feature-development, с domain/architecture до кода.

## T08 — Работоспособность MCP в реальном окружении

- Приоритет: P1, обязательный результат. Сложность: M–L, уточнить после воспроизведения.
- Зависимости: T00. Полный T09 не является предварительным условием ремонта.
- Основание: подключённый pf.context видит актуальный snapshot ID, но сообщает
  stale и блокирует поиск; source CLI для него возвращает fresh/ready.
- Область исследования: tools/pf_runtime/mcp_server.py, codex_mcp.py, host.py;
  src/processforge_core/garage.py, process_execution.py; tools/processforge.py
  (source resolution, classification, freshness, stdio entry point);
  docs/concepts/runtime-mcp.md; конфигурация реально подключённого сервера —
  только по результатам диагностики и в отдельном точном file scope.
- Работа:
  1. Воспроизвести расхождение; зафиксировать request ID, snapshot identity,
     исполняемый entry point, фактически загруженный Core/build, effective
     project/workplace roots, параметры запуска, классификацию и причину stale.
     Сравнить source и установленную копии. Старый provenance defect —
     гипотеза, а не установленный диагноз текущего случая.
  2. Различить транспорт, версию/путь кода, контекст, session binding и права.
     Проверить существующие регрессии до добавления новых. Не лечить симптом
     отключением freshness, подменой session ID или безусловным refresh/restart.
  3. Внести минимальный ремонт в ответственный слой, добавить регрессию.
     Если требуется изменение установки/конфигурации или restart конкретного
     сервера, сначала описать цель, воздействие, сохранение логов и rollback;
     согласовать необходимые операции, не трогать другие интеграции.
  4. Снять доказательства через тот клиент/сервер, которым пользуется оператор,
     затем проверить повторное подключение и продолжение Work.
- Приёмка:
  - MCP context и source CLI совпадают по смыслу freshness/readiness, process,
    snapshot identity и разрешённым ресурсам; не требовать побайтного совпадения
    динамических полей разных ответов.
  - pf.search/pf.resolve находят разрешённый ресурс; запрещённый остаётся запрещённым.
  - Через реальный клиент в изолированном согласованном fixture проходят
    work.start → work.state → work.transition → run_completed; новое подключение
    продолжает именно эту Work, без выбора старых исторических назначений.
  - Sessionless Garage работает; session-bound методы сохраняют проверку
    реальной авторизации и понятные ошибки отсутствующей/чужой сессии.
  - Реально stale/broken контекст по-прежнему диагностируется; нет ложного fresh.
  - Stdio содержит только протокольные сообщения; невалидный запрос, notification,
    сбой инструмента и завершение клиента не портят поток и не скрывают ошибки.
  - Source test PASS и installed/live acceptance фиксируются отдельно;
    CLI workaround, initialize или отдельный healthcheck не закрывают задачу.
- Проверки: tools/smoke_classifier_distribution_parity.py,
  tools/smoke_mcp_jsonrpc_validation.py, tools/smoke_mcp_missing_session_diagnostics.py,
  tools/smoke_project_init_local_search_mcp.py; новая регрессия текущей причины
  только после воспроизведения. Эти тесты перечислены для будущего запуска.
- Артефакты: reproduction + before/after, root-cause, минимальный change-summary,
  test-report, live MCP acceptance, применимость установки/rollback, handoff.
- Ограничение: не менять ядро под особенности Codex; общий контракт и адаптер
  конкретного хоста остаются разными слоями. Логи до ремонта сохранить.

## T09 — Общий контракт диагностического логирования и уровни детализации

- Приоритет: P1, обязательный результат. Сложность: L.
- Зависимости: T01.
- Область: tools/processforge.py:append_telemetry_event/redact_telemetry_value,
  tools/pf_runtime/mcp_server.py, host.py, codex_hooks.py и worker adapters;
  src/processforge_core/garage.py, process_execution.py;
  docs/concepts/session-telemetry.md, runtime-mcp.md и соответствующие RU docs.
  Новый общий logger/config/export module — путь выбирается на architecture-plan.
- Работа: ввести provider-neutral logger contract по аналогии с
  [PSR-3](https://www.php-fig.org/psr/psr-3/): log(level, message, context),
  удобные методы уровней, placeholders, безопасная обработка context/exception,
  подключаемые приёмники и no-op вариант. Для Python определить явное
  соответствие стандартному logging; не тянуть PHP-пакет и не плодить второй
  независимый журнал процессных фактов.

### Severity: серьёзность события

В порядке возрастания: debug, info, notice, warning, error, critical, alert,
emergency. Порог включает выбранный уровень и более серьёзные события.
Определить таблицу сопоставления уровней Python и экспортируемых значений,
валидацию неизвестных уровней и одинаковый результат log() и методов уровней.
Это аналогия интерфейса PSR-3, не заявление формальной PHP-совместимости PF.

### Verbosity: диагностические профили

| Профиль | Предлагаемый порог | Состав |
|---|---|---|
| quiet | warning | Предупреждения и ошибки, краткие причины |
| normal | info | Основные операции, результат, длительность, идентификаторы |
| diagnostic | debug | Ограниченные детали выбора контекста, источников и конфигурации |
| trace | debug + трассировки | Ограниченные spans/шаги, причины ветвления и безопасные stack traces |

Имена/пороги — предложение для проектирования, не существующие флаги CLI.
Trace не добавляет девятый стандартный уровень. Режим off/no-op допустим
только для необязательного диагностического приёмника, не для обязательного
process journal, audit/evidence или явной ошибки в ответе вызывающей стороне.

### Конфигурация, корреляция, безопасность

- Единая версионированная схема: severity threshold, diagnostic profile,
  фильтры компонентов (context/MCP/runtime/search/worker), output sink и лимиты.
  Предлагаемый порядок: defaults → project → Work/session → invocation override.
  Закреплённые security/storage ограничения не ослабляются override.
  Эффективные значения и источник каждого значения видны; подробный сбор
  включается на ограниченный срок/объём, затем возвращается к обычному режиму.
- Структурированная запись: timestamp UTC, severity, component, event/error code,
  message/template, bounded context; request/correlation ID, project/run/Work,
  session (если есть), snapshot, duration, build/source identity. Не выдумывать
  session ID для sessionless работы; отсутствующие поля имеют явную семантику.
- JSONL private sink, human-readable CLI/stderr и диагностический экспорт —
  представления одного контракта. При stdio MCP stdout остаётся протоколом;
  обычные логи идут в stderr/private sink, не примешиваются к JSON-RPC.
- Redaction до записи во все sinks: credentials, tokens, headers, чувствительные
  context/exception/stack значения; prompt, raw payload, environment dump и
  содержимое файлов по умолчанию не собирать, в trace тоже не включать автоматически.
  Private local logs могут содержать необходимые локальные пути; экспорт наружу
  должен санитизировать пути и пройти проверку. Это защита логов, не замена T07.
- Ротация, retention, общий quota, max record/depth/string size, ограничение
  stack/spans, sampling только необязательного debug/trace, счётчики пропусков.
  Важные ошибки не терять молча; пределы и поведение при переполнении явные.
  Не формировать дорогой diagnostic context при выключенном уровне.
- Ошибка sink/сериализации не маскирует исходный результат или исключение:
  безопасный fallback/health indication без рекурсии, учёт потерянных записей.
  Ошибки обязательной записи process evidence обрабатываются его контрактом,
  а не игнорируются под видом best-effort logging.
- Сбор диагностического пакета по request/Work и временному интервалу:
  версии и происхождение Core/adapter, эффективная конфигурация без секретов,
  snapshot IDs/hashes, причины freshness, связанные логи, результаты read-only
  проверок, manifest и отметки redaction/truncation. Экспорт не чинит систему
  и не перезапускает службы; доступ и публикация пакета контролируются явно.

### Приёмка T09

- Матрица всех восьми уровней: пороги, методы и log(), неизвестный уровень,
  корректная interpolation, arbitrary/non-serializable context и exception.
- Один сценарий при quiet/normal/diagnostic/trace/off даёт тот же процессный
  результат, обязательные события и evidence, но ожидаемую подробность диагностики.
- Профиль/компонент/порог задаются без изменения кода; precedence/locked policy,
  срок действия и эффективные значения проверены.
- Ошибка context freshness прослеживается от CLI/MCP request до причины/источника;
  две параллельные сессии/Work не смешиваются, sessionless сценарий не сломан.
- Synthetic secrets отсутствуют в каждом sink, exception, trace и export;
  stdout MCP и protocol stdout хуков разбираются клиентом при любом уровне,
  включая failure path. Проверить текущую debug-ветку except в codex_hooks.main:
  она печатает диагностический JSON обычным print без file=sys.stderr;
  сначала воспроизвести эффект тестом протокола, затем исправить в T09.
- Проверены disk-full/read-only sink, broken serializer, rotation/quota,
  truncation/drop counters, длительная нагрузка и overhead выключенного debug.
  Числовые budgets закрепить в архитектуре до реализации и измерить.
- Диагностический пакет позволяет воспроизвести сравнение CLI/MCP без ручного
  сбора десятка файлов, содержит manifest и безопасен для заявленного адресата.
- Артефакты: logger/domain contract, severity/profile/config matrix,
  compatibility notes, regression/performance/privacy reports, пример
  санитизированного diagnostic bundle, EN/RU runbook, handoff.

## Уточнение T01 — общий контракт

Добавить терминологию severity/profile/threshold/sink/correlation и отделить
обязательный process journal от необязательных diagnostics. Задать границы
core logger и adapters, mapping Python, config precedence, privacy/retention,
контракт эффективной диагностики, MCP/CLI эквивалентность.
Остальные приёмка и область T01 из ревизии 01 сохраняются.

## Уточнение T06 — сквозная приёмка

Актуальные зависимости: T02, T03, T04, T05, T08, T09.
Дополнить финальную матрицу реальным MCP-клиентом, повторным подключением,
sessionless/session-bound отрицательными сценариями и каждым профилем логов.
Повторить T08 acceptance после интеграции T09. Проверить сохранность stdout,
корреляцию, секреты, overhead/retention и диагностический экспорт.
Без подтверждённых T08/T09 основная последовательность не считается принятой.
Локальный исполнитель без MCP из T05 по-прежнему допустим: необязательность
транспорта для модели не отменяет качества поддерживаемого MCP-адаптера.
