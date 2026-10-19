# Исследование окна App Server

Status: ready_for_review
Date: 2026-10-19
Scope: planning_only; продукт не изменяется

## Подтверждённый сценарий

Пользователь уточнил: пустое окно появляется **при входе в Windows**.
Визуальное воспроизведение и принадлежность конкретного окна PID сервера
в этой Work не установлены. Вход в Windows, сервер и монитор не запускались
для воспроизведения.

## Факты по исходникам

| Участок | Наблюдение | Значение для плана |
| --- | --- | --- |
| `tools/pf_cli/parsers/runtime.py:50` | `server` — alias `runtime`; `run` — alias `serve`; уже есть `--console` | Полная замена argparse не нужна для оформления окна |
| `tools/processforge.py:14062` | `command_runtime_serve` делегирует `service.command_serve` | Фасад не должен получать логику UI |
| `tools/pf_runtime/service.py:878` | Заставка выводится только при `--console` и `sys.stdout.isatty()` | Обычный foreground serve без флага может быть пустым |
| `tools/pf_runtime/service.py:884` | Используется существующий `monitor.banner`, затем предупреждение о закрытии окна | Брендинг уже есть; версия/PID/подробности в этой ветке не выводятся |
| `tools/pf_runtime/service.py:843` | Singleton, HTTP bind и публикация ready находятся внутри `RuntimeProcess.serve` | Нельзя объявить сервер готовым при выводе ранней заставки |
| `tools/pf_runtime/service.py:133` | State содержит версию Core, runtime/protocol version, PID, instance_id, endpoint, started_at | Источники идентичности существуют; новый параллельный state не нужен |
| `tools/pf_runtime/service.py:894` | `runtime start` запускает дочерний `runtime serve`, перенаправляет stdout/stderr в журналы; Windows использует DETACHED_PROCESS и CREATE_NEW_PROCESS_GROUP | Это иной маршрут, чем foreground action Task Scheduler |
| `tools/pf_runtime/windows_autostart.py:44` | Scheduled action прямо вызывает `bin/pf.py runtime serve`; `--console` не добавляется | Нельзя автоматически заменить его на detached `runtime start`, потеряв владение процессом планировщиком |
| `tools/pf_runtime/windows_autostart.py:77` | LogonTrigger, InteractiveToken, LeastPrivilege, IgnoreNew и ограниченный restart-on-failure | Новый интерфейс обязан сохранить одно серверное исполнение и прежний lifecycle |
| `tools/pf_runtime/service.py:950` | `server stop` без `--force` требует проверенного владельца, capability guarded_shutdown и безопасной проверки занятости | Кнопка остановки должна использовать этот контракт; прямой kill или legacy unguarded stop не подходят |
| `docs/ru/concepts/runtime-monitor.md:3` | `pf monitor` — чтение; Q/Esc/Ctrl+C закрывают монитор, сервер остаётся работать | Существующий monitor нельзя незаметно превратить в управляющую панель |

`tools/smoke_server_operator.py:151` уже проверяет разбор `server run
--console`; строки 166–173 проверяют вывод только при console+TTY, ASCII
fallback и отсутствие ANSI. В том же smoke есть проверки busy/unknown,
owner/auth и guarded shutdown. Они изучены, но **не запускались**: текущая
Work проверяет план и не запускает серверные fixtures.

## Наблюдение на устройстве

Полное приватное наблюдение: [device-observation.json](device-observation.json).

У зарегистрированной задачи Task Scheduler — `pythonw.exe`, прямой
`runtime serve`, без `--console`; состояние задачи `Ready`. Последний
зафиксированный запуск задачи — утром 17 октября, результат 0.

Наблюдавшийся сервер — PID 6052 под `python.exe`, `runtime serve`, без
`--console`, создан вечером 17 октября. Родитель с записанным PID уже
недоступен. `MainWindowHandle` у Python равен 0; это само по себе не доказывает
ни наличия, ни отсутствия связанной консоли. Найденная задача и этот процесс
не образуют подтверждённую единую цепочку запуска.

Это ограничение доказательств, а не установленная неисправность Task Scheduler.
Результат задачи 0 не доказывает текущее здоровье сервера. В доступных
`Win32_StartupCommand` не обнаружено дополнительной записи PF; это не полный
аудит всех механизмов автозапуска Windows.

Проверка по [документации Python](https://docs.python.org/3.14/using/windows.html)
подтверждает назначение windowed launcher: он не создаёт консоль. Следовательно,
источник видимого окна нужно связать с процессом при следующем естественном
входе пользователя. Нельзя без этой связи считать смену `pythonw` на `python`
или добавление `--console` исправлением наблюдаемого окна.

Параметр Task Scheduler `Hidden` относится к видимости самой задачи в интерфейсе
планировщика, а не является средством скрытия консоли приложения.
Основание: [Microsoft TaskSettings.Hidden](https://learn.microsoft.com/en-us/windows/win32/taskschd/tasksettings-hidden).

## Исходники и установленная копия

Обе версии обозначены 1.2.0. Хеши `windows_autostart.py`, parser runtime,
`monitor.py` и `smoke_server_operator.py` совпадают. `service.py` различается:
на уровне верхних символов различаются `RuntimeProcess` и `runtime_request`.
Однако исходный текст `command_serve` в обеих копиях одинаков, включая
существующую заставку под `--console`.

Хеши и ограниченные выдержки: [source-evidence.json](source-evidence.json).
Сравнение файлов на диске не подтверждает байты, загруженные работающим
сервером или MCP. Установленная среда не обновлялась.

## Архитектурные основания

Прочитаны базовые `python-architecture-20261005/architecture.md`,
`pf-framework-architecture-20261005/{adr,domain,direction}.md`, актуальные
решения `pf121-architecture-cycle-20261018/decision-log.md` и текущая
`docs/ru/concepts/python-core-structure.md`.

Сохраняются: тонкие CLI/MCP/GUI адаптеры; общие прикладные правила;
явное владение ресурсами; отдельные lifetime серверного процесса и клиента;
отсутствие загрузки UI в Core/MCP; неизменность публичных wire/exit/error
контрактов. Выбор библиотеки UI не разрешает новый DI framework, перенос
общего логирования или переписывание монолита. Старые OOP slices не открываются.

## Вопрос пользователя о библиотеках

В локальных выбранных материалах поиск Textual/Typer/Click/Rich не дал
подходящей документации; затем проверены официальные источники.

| Средство | Предназначение | Применение к PF |
| --- | --- | --- |
| [Click](https://click.palletsprojects.com/en/stable/) | Дерево команд, параметры, help, prompts | Аналог роли Symfony Console; не нужен для исправления существующего argparse |
| [Typer](https://typer.tiangolo.com/) | CLI по аннотациям типов, команды и автосправка | Кандидат отдельной будущей CLI-миграции; не готовая интерактивная панель |
| [Rich](https://rich.readthedocs.io/en/stable/introduction.html) | Оформление текста и таблиц; поддержка Windows | Кандидат оформления консоли; добавление зависимости не обязательно для простого статуса |
| [Textual](https://textual.textualize.io/widget_gallery/) | TUI с кнопками, таблицами, вкладками и формами в терминале | Кандидат отдельной интерактивной панели App Server |
| [PySide6 / QSystemTrayIcon](https://doc.qt.io/qtforpython-6/PySide6/QtWidgets/QSystemTrayIcon.html) | GUI и значок с меню в системном трее | Кандидат полноценного desktop-варианта; отдельный packaging и lifecycle |

Ни одна библиотека не установлена и не проверена в исполнении. Выбор
совместимых версий, dependencies и состава архива относится к будущей
реализации. Textual не добавляет системный трей и не отделяет lifecycle
сервера от своего процесса автоматически.

## Влияние и открытые вопросы

Главные затрагиваемые границы: Windows launch adapter; human-readable
foreground presentation; существующий read-only monitor; операторский
guarded stop. Core workflow, MCP stdio, JSON-команды, scheduler, journals и
публичные команды не должны получать новые правила ради окна.

Открыты: точный владелец видимого окна при logon; основной UI-вариант;
нужны ли управляющие кнопки; должны ли окно/панель автоматически появляться
при входе; нужны ли пользователю смена статуса в реальном времени и доступ
к журналам. Автоматический запуск monitor по-прежнему не согласован.

Дальнейший handoff: зафиксировать доменные правила и основной вариант;
план реализации должен начинаться с идентификации окна, содержать отдельный
допуск к зависимостям/UI и не запускать работы с продуктом в этой Work.
