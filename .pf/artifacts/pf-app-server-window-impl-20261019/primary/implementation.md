# PF App Server: реализация серверного окна

Дата: 2026-10-19. Статус: implementation complete, assurance pending.

## Изменения primary

В .pf/AGENTS.md сохранено определение 1-1-4: основной агент совмещает
оркестрацию и исполнение, один независимый ревьювер проверяет все вклады,
четыре воркера работают в отдельных областях. Число воркеров можно увеличить.
Поручения и READ_ACK идут через PF, каждый участник имеет Agent Ledger identity.

tools/pf_runtime/console.py отделяет человекочитаемую консоль от lifecycle
сервера. command_serve после успешной загрузки конфигурации вызывает её с
PROCESSFORGE_VERSION фактически переданного Core. Заголовок автоматически
появляется только на TTY, содержит существующий логотип PF, Core version, PID,
назначение и последствия закрытия окна. Заголовок не объявляет готовность
сервера. С None/non-TTY stdout нет вывода и GUI-действий. ASCII fallback без ANSI.

RuntimeCommandParser принимает --minimized у serve/run и прежних runtime/server
aliases. --console сохранён; для обычного TTY заголовка больше не обязателен.
Минимизация запрашивается явно для отдельного окна; в существующем терминале
без флага окно не сворачивается. OS adapters загружаются лениво. Ошибка рабочего
стола не останавливает сервер и даёт ограниченную понятную строку на TTY.

## Вклады воркеров

- Windows: windows_console.py проверяет видимую классическую console, её класс,
  список клиентов с единственным текущим PID и наблюдённое IsIconic. Shared
  console и ConPTY не затрагиваются. windows_autostart.py запускает напрямую
  tools/processforge.py runtime serve --minimized, сохраняя явный interpreter
  и foreground владение Task Scheduler. bin/pf.py не менялся.
- Linux: linux_console.py допускает только подтверждённый отдельный xterm -e
  с локальным X11, WINDOWID, PID окна/родителя, процессом/TTY и проверкой состояния.
  Нужны уже установленные xprop/xdotool. Wayland/XWayland, SSH, multiplexer,
  общий терминал и неоднозначность дают безопасный отказ. PF утилиты не устанавливает.
- Docs: EN/RU installation.md, runtime-autostart.md, runtime-monitor.md описывают
  единый запрос, поддерживаемые механизмы, прямой вход для Windows, ограничения
  и явную миграцию прежней scheduled action через операторский --replace.
- Assurance: отдельный четвёртый worker проверяет три smoke файла после кода;
  его итог и независимый reviewer report фиксируются отдельно.

## Границы результата

Textual, PFConfig.autostart_pf_app_server_monitor, список проектов и системные
установщики Linux не добавлены. HTTP, singleton, shutdown guard и MCP stdout
не менялись. Реальные Runtime/MCP/Task Scheduler не устанавливались и не
перезапускались. Исходная рабочая копия не означает обновление установленного Core.

## Проверки и исходное состояние

Компиляция общей части и parser help прошли. Windows worker сообщил 25 checks;
Linux worker — 25 mocked checks. Итоговые команды/результаты сохраняются в
worker reports и отдельном quality report; эти предварительные counts не
подменяют независимую проверку. Real Linux GUI на этом устройстве недоступен
(WSL не установлен), эта платформенная приёмка не заявляется.

Полный source schema scan нашёл историческую assignment
analyze-project-evolve-records-against-current-code-and-create-evidence с
execution_mode строкой вместо object. Source public-cleanliness нашёл 15
старых docs.python* ids в локальной .pf/process-forge.yaml; конфигурация вне
scope и не менялась. Один новый scanner false-positive platform.startswith
в общей части устранён эквивалентным точным сравнением sys.platform.
Чужое dirty/staged состояние сохраняется. Коммит/push ещё не выполнялись.
