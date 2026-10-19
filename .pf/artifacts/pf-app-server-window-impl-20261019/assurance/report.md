# Отчёт assurance: серверное окно PF App Server

Дата: 2026-10-19. Исполнитель: `pf-app-server-window-assurance`.

**Статус: `pass_with_conditions`.** Целевые регрессионные проверки пройдены. Реальная GUI-приёмка остаётся открытой.

## Изменения

Изменены только назначенные тестовые файлы:

- `tools/smoke_server_console.py` — новый suite из 27 тестовых методов с дополнительными сценариями `subTest`.
- `tools/smoke_server_operator.py` — автоматический TTY-заголовок, версия Core и подключение нового suite.
- `tools/smoke_runtime_mcp_autostart.py` — проверки прямого foreground-запуска с `--minimized`, точного интерпретатора и отказов автозапуска.

Продуктовые модули не изменялись. Существующие HTTP/guarded-stop assertions сохранены; singleton-тест не изменялся.

## Покрытие

Проверены автоматический логотип, версия переданного Core, PID, ASCII fallback, nonTTY/None и ошибки потоков; совместимость `--console` и aliases `runtime/server`, `serve/run`; продолжение запуска Runtime после ошибки адаптера.

Windows-проверки охватывают собственную и общую консоль, чужой PID, Windows Terminal/ConPTY, смену владения, ошибки API и обязательное подтверждение `IsIconic`.

Linux-проверки охватывают отдельный xterm/X11, владение процессом и окном, Wayland/XWayland, SSH, headless, multiplexers, недоступные инструменты, ограничения `/proc`, timeout и отсутствие подтверждения минимизации.

Autostart проверяет точный Python без подмены на соседний `pythonw.exe`, Windows argv с пробелами/Unicode, XML, несовпадение прежнего действия, требование `--replace` и previews. Случайный запуск настоящего scheduler/Codex subprocess запрещён тестом.

## Результаты команд

| Команда / окружение | Результат |
| --- | --- |
| `python -B tools/smoke_server_console.py`, worker | exit 0; 27/27 |
| Operator через scoped fixture harness, worker | exit 0; 27 тестов и реальные loopback HTTP guards |
| Autostart через scoped fixture harness, worker | exit 0 |
| Неизменённый singleton через harness, worker | exit 1; живой владелец не распознан |
| `python -B tools/smoke_server_operator.py`, primary | exit 0; финальные 27 тестов и HTTP guards |
| `python -B tools/smoke_runtime_mcp_autostart.py`, primary | exit 0 |
| `python -B tools/smoke_runtime_singleton_orphan.py`, primary | exit 0 |

Прямые worker-запуски operator/autostart остановились до assertions из-за ACL `TemporaryDirectory`. Harness заменял только создание временных каталогов. Отдельная диагностика singleton показала живой готовый child при `tasklist: ERROR: Access denied`. В родительском окружении проблема не повторилась.

Результаты primary подтверждены прочитанным `primary/focused-checks-final.md` и сообщением `msg_3b5323a1f0b54db3a49ffcdf22ad8c7e`. Синтаксис, whitespace и неизменность финальных SHA256 трёх файлов проверены.

## Артефакты и ограничения

В области `assurance/`: `changed-files.md`, `change-summary.md`, `verification.json`, результаты команд `.txt`, `liveness-diagnostic.json`. Append-only журнал: `.pf/logs/pf-app-server-window-impl-20261019-assurance.md`. Scoped helpers и два пустых недоступных каталога удержаны как evidence; ACL не менялись.

Успешная минимизация настоящего Windows classic/Linux X11 окна и реальные GUI-сценарии общей консоли **не подтверждены mocks**.

PF chat прочитан, READ_ACK и RESULT записаны. Agent Ledger check-in/heartbeat/checkout выполнены. Службы, установленные Runtime/MCP и реальные scheduled tasks не изменялись; commits, push и subagents отсутствуют. Независимый review, интеграция и task commit принадлежат primary.