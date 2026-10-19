# Автозапуск Runtime и запуск Codex MCP

У ProcessForge есть две разные модели запуска:

- **PF App Server (PF Runtime)** — workplace-scoped loopback HTTP-сервис.
  Он может работать в текущем окне, запускаться фоном по явной команде или,
  в Windows, стартовать через включённую оператором задачу Task Scheduler.
- **PF MCP** — stdio-сервер для Codex. Процессом владеет Codex: он запускает
  сервер из своей MCP-конфигурации, когда host session нужен этот сервер.

Garage не требует PF Runtime. Устанавливайте Runtime autostart только для Forge
workplace, где long-lived service нужен выбранной coordination model. На Linux
Runtime можно запускать вручную или operator-managed background tooling;
Текущий CLI не устанавливает `systemd --user`; вне Windows механизм
автозапуска сообщает `unsupported`.

Не регистрируйте `tools/pf_runtime/mcp_server.py` в Windows autostart.
Отсоединенный stdio MCP-процесс не имеет подключенного MCP-клиента и не может
обслуживать полезный JSON-RPC трафик.

Команды ниже предназначены оператору для настройки и обслуживания. Агент
обычного проекта не должен устанавливать, запускать, перезапускать или чинить
Runtime, MCP и хуки. Используйте Python-окружение из [инструкции установки](installation.md);
память дополнительных процессов учитывайте отдельно по [требованиям](../requirements.md).

## Управление Runtime вручную

Из корня установленного дистрибутива ProcessForge:

```bash
python bin/pf.py runtime start --workplace <workplace>
python bin/pf.py runtime status --workplace <workplace>
python bin/pf.py runtime doctor --workplace <workplace>
python bin/pf.py runtime stop --workplace <workplace>
```

`runtime start` запускает `runtime serve` как detached background process.
Сервис пишет singleton-состояние в `<workplace>/runtime/pf-runtime/`, поднимает
loopback HTTP endpoint на `127.0.0.1` и защищает запросы локальным bearer token.

## Окно сервера

Для запуска сервера в текущем терминале используйте команду:

```bash
python bin/pf-server.py run --workplace <workplace>
```

При выводе в TTY команды `run`/`serve` автоматически показывают
логотип PF, версию работающего Core, PID и назначение процесса. Флаг `--console`
сохранён, но для этого заголовка больше не нужен. Заголовок появляется до
привязки сетевого адреса; готовность проверяйте через `runtime status` или
`runtime doctor`. Закрытие этого серверного окна останавливает сервер.

Для запроса сворачивания отдельного серверного окна добавьте `--minimized`:

```bash
python tools/processforge.py server run --workplace <workplace> --minimized
```

Команды `python bin/pf.py server run ...`, `server serve ...`, `runtime run ...`
и `runtime serve ...` используют ту же политику работы в текущем окне. Без
`--minimized` PF не сворачивает терминал, в котором введена команда. Флаг не
создаёт отдельный терминал и не отсоединяет процесс: оператор должен запустить
сервер в отдельном графическом окне, принадлежность которого PF может проверить.

| Рабочая среда | Граница поддержки сворачивания |
| --- | --- |
| Классическая консоль Windows | Только видимая отдельная консоль, единственный консольный клиент которой — текущий сервер. Общие консоли отклоняются. |
| Windows Terminal / ConPTY | Не поддерживаются: PF не сворачивает окно хоста с другими вкладками. |
| Linux X11 | Только отдельное окно `xterm -e` на локальном дисплее с проверками ID окна, PID окна и родительского процесса. Другие эмуляторы терминала не поддерживаются. |
| Wayland / XWayland | Не поддерживаются. При необходимости настройте запуск терминала или рабочего стола отдельно. |

В Windows после `bin/pf.py` и `bin/pf-server.py` в консоли остаётся дополнительный
Python-процесс запуска, поэтому проверка единственного клиента отклоняет
сворачивание. Программа, создающая отдельное окно, должна выполнять показанную
выше команду с `tools/processforge.py` напрямую, без другой присоединённой
оболочки или промежуточного процесса запуска. Новая вкладка оболочки сама по
себе не подтверждает принадлежность окна. Задача Task Scheduler ниже использует
прямой запуск.

В Linux для сворачивания нужны уже установленные `xprop` и `xdotool`; PF их не
устанавливает. Запускайте Python непосредственно через `xterm -e`, без
промежуточной оболочки, например:

```bash
xterm -e python tools/processforge.py server run --workplace "../pf-workplace" --minimized
```

До запроса PF проверяет родительский терминал, `WINDOWID` и `_NET_WM_PID`, затем
проверяет состояние свёрнутого окна. Удалённые дисплеи и неоднозначная
принадлежность отклоняются. При отсутствии вспомогательных утилит сворачивание
недоступно.

Без TTY, включая перенаправленный или отсутствующий стандартный вывод, PF не
показывает серверный заголовок и не выполняет действий с окном. В SSH-сеансах,
при работе без графической среды и внутри `tmux`/`screen` попыток сворачивания
нет. При наличии TTY неподдерживаемый механизм, неподтверждённая принадлежность
окна или неподтверждённое сворачивание дают диагностическое сообщение, а запуск
сервера продолжается. Сам запрос
сворачивания не доказывает, что рабочий стол свернул окно.

Для видимого серверного окна используйте консольный Python (`python.exe` в
Windows). `pythonw.exe` работает без окна, а не в свёрнутом окне; стандартные
потоки могут быть `None`. `runtime start` запускает сервер фоном и не создаёт
свёрнутое окно.

Существующий [монитор только для чтения](../concepts/runtime-monitor.md)
запускается отдельно; команды запуска сервера и `--minimized` его не открывают.
Закрытие монитора оставляет сервер работающим. Монитор на Textual и предложенное
поле конфигурации `autostart_pf_app_server_monitor` — будущая работа; текущие
CLI и конфигурация их не предоставляют.

## Windows autostart Runtime

Автозапуск Windows включается оператором и использует Task Scheduler. Задача
запускает указанный Python напрямую с
`tools/processforge.py runtime serve --minimized`. Сервер остаётся в этом
процессе, жизненным циклом которого управляет планировщик.
Задача работает от текущего интерактивного пользователя, с
least privilege, logon trigger, ограниченной restart-on-failure политикой и
детерминированным именем, вычисленным от пути workplace.

Созданный профиль запрашивает сворачивание собственного отдельного серверного
окна с проверками, описанными выше. Он не запускает монитор и не отсоединяет
сервер в фоновый процесс. Настройка `Hidden` в Task Scheduler управляет видимостью
задачи, а не сворачиванием консоли. Исполняемый файл, явно указанный через
`--python`, сохраняется;
выбор `pythonw.exe` означает процесс без окна, а не свёрнутую консоль.

Проверить задачу:

```powershell
python bin/pf.py runtime autostart status --workplace <workplace>
```

Запланировать или установить:

```powershell
python bin/pf.py runtime autostart install --workplace <workplace>
python bin/pf.py runtime autostart install --workplace <workplace> --apply
```

Запланировать или удалить:

```powershell
python bin/pf.py runtime autostart remove --workplace <workplace>
python bin/pf.py runtime autostart remove --workplace <workplace> --apply
```

Если status показывает drift, используйте `--replace` при install, чтобы
перезаписать детерминированное определение задачи ProcessForge. Используйте
`--force` при remove только когда нужно удалить drifted task с детерминированным
именем ProcessForge.

Прежние профили использовали `bin/pf.py` без `--minimized`; после обновления Core
их команда запуска намеренно определяется как drift. Обновление файлов не перезаписывает
зарегистрированную задачу. Оператор может явно проверить и применить замену:

```powershell
python bin/pf.py runtime autostart install --workplace <workplace> --replace
python bin/pf.py runtime autostart install --workplace <workplace> --replace --apply
```

Дополнительные настройки scheduled action:

```powershell
python bin/pf.py runtime autostart install --workplace <workplace> --distribution-root <processforge-install> --python <python> --port 0 --interval 2.0 --delay-seconds 10 --apply
```

После установки проверяйте:

```powershell
python bin/pf.py runtime autostart status --workplace <workplace>
python bin/pf.py runtime status --workplace <workplace>
python bin/pf.py runtime doctor --workplace <workplace>
```

При перемещении Python, виртуального окружения или ProcessForge задачу нужно
переустановить: изменится путь в команде. Планировщик не наследует активацию
окружения из оболочки; в указанном интерпретаторе должен быть установлен PyYAML.

## Регистрация Codex MCP

Регистрация Codex MCP отделена от Runtime autostart. ProcessForge управляет
конфигурацией Codex host только по явной команде:

```powershell
python bin/pf.py codex-mcp status --workplace <workplace>
python bin/pf.py codex-mcp install --workplace <workplace>
python bin/pf.py codex-mcp install --workplace <workplace> --apply
python bin/pf.py codex-mcp remove --workplace <workplace>
python bin/pf.py codex-mcp remove --workplace <workplace> --apply
```

Имя сервера по умолчанию — `processforge`. Используйте `--name`, `--python`,
`--codex` или `--distribution-root`, если host должен использовать нестандартный
executable или путь установки. Явное значение `--python` является точным pin
исполняемого файла; `status` сообщает drift, если сохраненная команда отличается.
`--replace` заменяет drifted Codex registration,
а `--force` удаляет drifted registration по имени.

После изменения регистрации Codex нужно перезапустить или reload. Каждая новая
host session запускает собственный подключенный Python stdio MCP-процесс. MCP
registration не создает Windows service, scheduled task, idle daemon или
always-on network endpoint.
