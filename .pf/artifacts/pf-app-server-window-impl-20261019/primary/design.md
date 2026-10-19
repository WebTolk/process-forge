# Серверное окно: исследование, домен и контракт реализации

Дата: 2026-10-19. Статус: принято primary для ограниченной реализации.

## Investigation report / impact analysis

Проверены service.command_serve, RuntimeCommandParser, windows_autostart,
bin/pf-server.py, действующие smoke_server_operator и smoke_runtime_mcp_autostart,
docs/getting-started/runtime-autostart.md и план revision 2. Сейчас banner выводится
только с --console и без Core version. Task Scheduler выполняет serve напрямую;
Hidden относится к отображению задачи, не окна. Консольный launcher сохраняет
владение PID. runtime start уже detached и ведёт stdout/stderr в журналы.

В этом изменении не меняем singleton, HTTP/auth, остановку сервера, MCP stdio,
конфигурацию PFConfig, installers Linux или установленный экземпляр устройства.
Новая человекочитаемая информация ограничена TTY foreground serve/run.
Публичные JSON payloads и их версии сохраняются. Новых Python зависимостей нет.

## Domain model / launch invariants

- Server и monitor — отдельные процессы. Здесь monitor не запускается.
- Заголовок интерактивного serve/run включён автоматически, в том числе без
  исторического --console; прежний флаг сохраняется как явный совместимый вход.
- Заголовок: существующий PF banner, PROCESSFORGE_VERSION переданного core,
  os.getpid(), назначение и честное предупреждение о закрытии окна. Не объявляет
  готовность до singleton/bind. Никаких token, endpoint credentials/private paths.
- --minimized на serve/run — общий запрос минимизации только отдельного
  принадлежащего PF окна. По умолчанию команда, введённая в существующий терминал,
  не сворачивает терминал пользователя. Autostart-профиль добавляет --minimized.
- Без TTY/со stdout None нет заголовка и GUI-действий. SSH/headless и multiplexers
  не получают попытку сворачивания. Неподдерживаемый backend не останавливает
  сервер; диагностическая строка сообщает отсутствие подтверждённой минимизации.
- Windows: только доказанно отдельная классическая видимая console с единственным
  клиентом (текущим процессом). Windows Terminal/ConPTY не принимается за такую
  console; нельзя сворачивать окно с чужими tabs.
- Linux: X11 только при доказанном отдельном терминале/окне; разрешён узкий backend
  xterm -e с проверкой WINDOWID, _NET_WM_PID и родителя. Wayland не имеет общего
  server-side API для чужого terminal window: ограничение обозначается явно,
  настройка запуска самого терминала/рабочего стола остаётся у оператора.

## Architecture plan / interface contract

tools/pf_runtime/console.py — общая presentation policy. Вызывается из
command_serve после успешного создания RuntimeProcess и до runtime.serve;
не владеет lifecycle и не меняет state. Рендер использует monitor.banner.
OS адаптеры импортируются лениво только при --minimized и доступном TTY.

Оба адаптера: minimize_console() -> str. Значения: minimized, unsupported,
not_owned, unavailable, failed. minimized означает подтверждённое наблюдение
состояния; неподтверждённый запрос не считается успехом. Ограниченные системные
вызовы; без shell=True, установки утилит, поиска окон по title, управления чужими
PID, переподчинения процесса или создания monitor. Вспомогательные функции могут
быть узкими и проверяемыми через mock; import-time GUI IO запрещён.

Windows worker владеет windows_console.py и windows_autostart.py. Профиль
выполняет тот же foreground serve с --minimized, без detached wrapper и без
молчаливой замены явно указанного Python. Никаких изменений реальных tasks.
Linux worker владеет linux_console.py; не вводит systemd installer.
Primary владеет service.py, console.py, parser; добавляет общий --minimized.
Docs worker уточняет существующие EN/RU runtime-autostart и runtime-monitor docs,
может уточнить EN/RU installation.md в части этой задачи. Assurance worker после
кода владеет smoke_server_operator.py, smoke_runtime_mcp_autostart.py и новым
smoke_server_console.py. Reviewer только читает продукт и пишет свой отчёт.

## Python guidance selected by PF

Разрешены и разрешены через pf.work.resolve docs.python:root (generation
sha256:0d5e255d8c7bf06e6f259954d5ba7960e0aeaa09c0a9b1b8ede7d57b9c794801)
и docs.python-practices:root (generation
sha256:a79ec68220e1b953af3364cd20d4d80a5fb31de2b3226f04e046592283ec22fe).
Из локальных subprocess.md и pep20.md: явная простая композиция, отсутствие
shell interpolation, ограничение subprocess timeout, CREATE_NEW_CONSOLE и
DETACHED_PROCESS взаимоисключающие; STARTF_USESHOWWINDOW не универсальная
минимизация, SW_HIDE скрывает. None streams допустимы у pythonw. Локальные
архитектурные ADR требуют узкие adapters и отсутствие import-time IO.
Эта выдержка — разрешённый вход работников, не разрешение произвольного чтения
внешних docs; собственное разрешение PF resource требуется для их полного текста.

Планирование уже проверило первичные спецификации Microsoft ShowWindow,
GetConsoleWindow/TaskSettings.Hidden и Freedesktop EWMH. При уточнении X11/Wayland
использовать первичные спецификации. Подтверждения реальной GUI-минимизации
отделять от mocked checks; не объявлять Windows/Linux acceptance без наблюдения.
