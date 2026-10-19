Статус: `ready_for_review`.

Реализован `tools/pf_runtime/linux_console.py` с API `minimize_console() -> str` и предусмотренными результатами: `minimized`, `unsupported`, `not_owned`, `unavailable`, `failed`.

Адаптер поддерживает только локальный X11 и прямой запуск через `xterm -e`. Проверяются WINDOWID, PID окна, класс XTerm, UID, исполняемый файл, родительский процесс, единственный дочерний процесс и foreground TTY. Ограниченный просмотр `/proc` отклоняет другие процессы той же сессии или TTY.

Wayland/XWayland, SSH, multiplexers, headless, удалённый DISPLAY, промежуточная оболочка и неподтверждённое владение отклоняются. Используются заранее установленные `xprop` и `xdotool`, без shell и с таймаутами. `minimized` возвращается только при наблюдении одновременно `WM_STATE: Iconic` и `_NET_WM_STATE_HIDDEN`. Импорт не выполняет GUI-действий.

Проверка:

```text
python -B .pf/artifacts/pf-app-server-window-impl-20261019/linux/check_linux_console.py
Ran 26 tests in 0.299s
OK
```

Покрыты отказы без GUI-запроса, смена владельца/PID, общая сессия/TTY, таймауты, отсутствие подтверждения и побочные действия при импорте. Доказательства находятся в `linux/checks.md` рядом с проверочным скриптом; журнал обновлён.

Все Linux `/proc` и X11-взаимодействия проверялись через mocks на Windows. Реальное сворачивание Linux-окна **не подтверждено**; необходимы независимая интеграционная проверка и реальная X11-приёмка.

Общий PF chat прочитан, READ_ACK и результат переданы. Ledger check-in, heartbeat и checkout выполнены под собственной worker identity. Другие продуктовые файлы не изменялись; коммитов, push, запуска служб и subagents не было. Интеграция и task commit остаются за primary.