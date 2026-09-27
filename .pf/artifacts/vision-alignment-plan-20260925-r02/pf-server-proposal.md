# Предложение T10: pf-server и окно рабочего места

- status: proposed_for_discussion
- source: дополнительные сообщения оператора в ходе ревизии плана 02
- candidate_id: T10
- not_implemented: true
- scope: развитие существующего Runtime, не новый обязательный центр ядра
- priority: P2 для операторского окна; надёжность доставки событий — часть P1 runtime/MCP приёмки
- complexity: M–L, уточнить после выбора интерфейса и способа поставки
- dependencies: T01, T08, T09 для полной реализации; обсуждение не блокирует текущую r02
- approval: pending; вне утверждённого графа T00–T09

## Рекомендация

Назвать долгоживущий workplace Runtime «ProcessForge Server», кратко pf-server.
Для постоянно используемого Garage сделать его штатным рекомендованным
сопутствующим сервисом: приём событий, наблюдение за сессиями, актуализация
производной статистики и обслуживание транспортных адаптеров. Полный live-режим
объявляет service readiness явно. Работа с процессными файлами/капсулами,
базовый CLI и сохранение событий не должны безусловно зависеть от daemon.

Это предложение уточняет эксплуатационный режим, а не переносит центр
архитектуры из файлового ядра в оркестратор/модель. Несколько Work и моделей
используют один соответствующий workplace instance; разные workplace/users
не объединяются неявно. MCP stdio-процессы конкретных клиентов — адаптеры,
а не обязательные отдельные копии центрального сервера.

## Что уже есть в коде

- tools/pf_runtime/service.py:RuntimeProcess (347), serve (636), command_start (676)
  — существующий постоянный процесс, singleton и lifecycle. Start на Windows
  создаёт detached child с перенаправлением stdout/stderr в журналы.
- tools/pf_runtime/codex_hooks.py:dispatch (148–182) сначала вызывает Runtime /event,
  при недоступности — локальный host.ingest_event; возвращается ledger-fallback.
  Поэтому отсутствие постоянного сервера не делает запись хуков невозможной.
  Это source-backed наблюдение, не новый fault-injection тест.
- service.py:status_payload (400) уже выдаёт состояние scheduler,
  known_projects, active_agent_sessions и active_workers. Их точную семантику,
  устаревание и стоимость следует проверить, не просто вывести raw counters.
- windows_autostart.py содержит Windows Task Scheduler integration.
  Новый установщик/автозапуск не нужен только ради брендинга.

## С чем стоит поспорить

1. Украшать «окно, которое нельзя закрывать» недостаточно. Лучше отделить
   viewer от daemon: закрытие viewer ничего не ломает; остановка сервера —
   отдельное явное действие. Не пытаться блокировать крестик окна вместо
   правильного жизненного цикла.
2. Зелёный process alive не означает исправный PF. Runtime, scheduler,
   hook ingress, MCP, ресурсный контекст и свежесть метрик показываются отдельно.
3. Сервер не видит действия агента, не переданные adapter/hooks/wrapper.
   Отсутствие событий — unknown/нет покрытия, не доказательство отсутствия работы.
4. Без daemon допустим локальный durable ingress; после восстановления нужна
   сверка/replay/idempotency. Очередь/spool — вариант для проектирования,
   не утверждение, что она уже полностью реализована для каждого адаптера.
5. Не заводить второй процессный журнал или обязательный model orchestrator
   ради окна статистики. Сервер публикует производные представления ядра.

## Имя процесса в Windows

Имя скрипта/команды и заголовок терминала — не имя executable image.
ProcessName отражает имя исполняемого файла:
[Microsoft](https://learn.microsoft.com/en-us/dotnet/api/system.diagnostics.process.processname?view=net-10.0).
При обычном запуске интерпретатора ожидается python.exe; переименование
скрипта этого не меняет. Заголовок можно задать отдельно, предпочтительно
terminal sequences с fallback:
[Windows console title](https://learn.microsoft.com/en-us/windows/console/setconsoletitle).

Для настоящего pf-server.exe возможен собственный executable/упакованный
Python runtime, например PyInstaller с именем приложения:
[PyInstaller usage](https://pyinstaller.org/en/stable/usage.html).
Это отдельная задача упаковки, обновлений и квалификации; одна launcher-обёртка
сама по себе не гарантирует переименование дочернего Python. Не переименовывать
общесистемный python.exe. На первом этапе достаточно имени команды,
заголовка окна, PID/build/workplace в статусе.

## Предлагаемый интерфейс

Имена ниже — варианты, пока не существующие новые команды:

- pf-server start/run/stop/status — управление существующим Runtime с сохранением
  совместимости pf runtime ...; точную CLI поверхность выбрать в архитектуре.
- pf monitor — отдельно открываемое read-only окно; выход/крестик/Ctrl+C
  закрывает монитор, не сервер. Не стартует сервер скрыто при запросе статуса.
- pf-server run --console — явный foreground/debug вариант: короткий pixel/ASCII
  splash и предупреждение, что закрытие именно этого окна остановит сервер.
- pf logs / pf diagnose — просмотр фильтрованных логов и сбор безопасного
  пакета по T09. Команды сейчас являются предложением, не инструкцией запуска.

Рекомендуемый первый этап: знакомое имя и компактный TUI-monitor.
Tray icon со статусом/открытием/явной остановкой — следующий Windows-адаптер.
Локальная web-панель полезна для нескольких проектов, но требует дополнительной
аутентификации/защиты и поддержки frontend; не обязательна для первой версии.

## Что показать в окне

- Небольшой логотип PF, ProcessForge Server, версия/build, workplace и PID.
- Runtime/scheduler/MCP/hooks отдельно: ready/degraded/offline/unknown,
  причина, timestamp последней проверки, возраст данных.
- Сессии: active/idle/stale и покрытие наблюдения; отдельно running workers,
  выполняемые Work и работы, ожидающие пользователя.
- Проекты: зарегистрированные и реально активные. «Занято» означает активную
  lease на конкретный scope: владелец, Work, TTL, конфликт/ожидание. Не путать
  это с открытым каталогом. x/y слотов показывать только если задана capacity.
- События: скорость/счётчики за явный интервал, последняя доставка, backlog,
  rejected/quarantined/retry, потерянные diagnostic records, объём логов.
- Краткие последние warning/error с correlation ID, переключение профиля/фильтра
  по явному действию; prompt/raw chat/secrets не выводить.

## Эскиз: символика и компоновка

Это макет, не реальные измерения и не реализованный интерфейс.

    █▀█ █▀▀   ProcessForge Server
    █▀▀ █▀    pf-server | <version> | <workplace>

    Runtime: READY      Scheduler: READY
    MCP:     DEGRADED   Hooks:     READY
    Updated: <time>     Last event: <age>

    Sessions: <active> / <idle> / <stale>
    Workers:  <running>   Work waiting: <count>
    Projects: <active>    Leases: <held> / <conflicts>
    Events:   <rate>      Backlog: <pending>

    ! MCP: <reason code>; request <correlation id>
    [L] logs  [D] diagnostics  [Q] close monitor

Splash показывать кратко, без искусственной задержки. В узком терминале —
простая компактная таблица; ASCII fallback, --no-color и non-TTY режим.
В JSON/MCP/hook protocol output нет splash, ANSI или обычного текста.

## Приёмка будущей T10

- Подтверждена изоляция monitor lifecycle: закрытие/сбой монитора не останавливает
  daemon; остановка сервера явная, учитывает активные workers и даёт диагностику.
- Нет двух серверов на одну идентичность workplace/user; чужие процессы/порты
  и установки не затронуты. Адреса локальные, IPC сохраняет авторизацию.
- Сбой daemon не теряет уже подтверждённые события; durable fallback/replay,
  bounded timeout hooks, deduplication и recovery проверены fault injection.
- Счётчики имеют определения, источники и freshness; нет ложного healthy или
  active из исторической регистрации. Polling bounded, нет тяжёлого rescan
  всей .pf каждую перерисовку и незаявленных write side effects.
- Экран проверен на разных ширинах/resize/Unicode/ASCII/no-color/non-TTY:
  screen-state regression, отсутствие мерцания и наложений, а не лишь поиск текста.
- Splash/статистика не ломают stdio протокол, перенаправление и privacy.
- Переключение log profile использует T09, а не отдельный UI-only механизм.
- Смена имени/CLI оставляет описанную совместимость автозапуска и старых команд;
  бинарная поставка, если выбрана, проходит отдельные source/archive/extracted checks.

## Артефакты

Domain/architecture decision об эксплуатационных режимах и lifecycle;
контракт status/metrics, CLI compatibility, TUI wireframe, протокол safe stop,
screen-state и outage tests, EN/RU operator runbook, handoff.
Новый T10 включать в очередную ревизию общего плана после обсуждения
границ и выбора первого этапа; технические предложения выше не утверждены.
