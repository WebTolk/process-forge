# Автозапуск Runtime и запуск Codex MCP

У ProcessForge есть две разные модели запуска:

- **PF Runtime** — workplace-scoped loopback HTTP-сервис. Он может работать в
  foreground, запускаться вручную как detached background process или, на
  Windows, стартовать через opt-in задачу Task Scheduler.
- **PF MCP** — stdio-сервер для Codex. Процессом владеет Codex: он запускает
  сервер из своей MCP-конфигурации, когда host session нужен этот сервер.

Garage не требует PF Runtime. Устанавливайте Runtime autostart только для Forge
workplace, где long-lived service нужен выбранной coordination model. На Linux
Runtime можно запускать вручную или operator-managed background tooling;
managed установка `systemd --user` в 1.1.0 не предоставляется.

Не регистрируйте `tools/pf_runtime/mcp_server.py` в Windows autostart.
Отсоединенный stdio MCP-процесс не имеет подключенного MCP-клиента и не может
обслуживать полезный JSON-RPC трафик.

## Ручной lifecycle Runtime

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

## Windows autostart Runtime

Autostart на Windows является opt-in и использует Task Scheduler. Scheduled
action запускает `runtime serve` в foreground, поэтому Task Scheduler владеет
process lifecycle. Задача работает от текущего интерактивного пользователя, с
least privilege, logon trigger, ограниченной restart-on-failure политикой и
детерминированным именем, вычисленным от пути workplace.

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

Перемещение Python или установленного ProcessForge меняет scheduled command и
требует переустановки задачи.

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
