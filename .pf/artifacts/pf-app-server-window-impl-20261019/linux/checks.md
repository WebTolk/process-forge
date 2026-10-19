# Проверки Linux-адаптера

Статус: pass для scoped mock-проверок; реальная Linux/X11 GUI-приёмка не выполнена.

## Команда и результат

```text
python -B .pf/artifacts/pf-app-server-window-impl-20261019/linux/check_linux_console.py
Ran 26 tests in 0.299s
OK
```

Код продукта: `tools/pf_runtime/linux_console.py`.
SHA-256: `9e64c96a2c98b3e21c921e923b1c922c7e6cad01a1e01d8e90be037bbef4dd98`.

## Проверенное поведение

- Отказ для другой платформы, Wayland/XWayland, SSH, удалённого/отсутствующего DISPLAY, multiplexers, None/redirected/closed streams и некорректного WINDOWID до GUI-запроса.
- Прямой xterm -e, UID, executable, единственный дочерний процесс, session/process-group leader, foreground TTY и одинаковые stdin/stdout устройства.
- Ограниченный просмотр /proc: чужая сессия/TTY, reparented background jobs, несовпадение controlling device, исчезновение процесса, запрет чтения и лимиты времени/числа записей.
- Несовпадение PID окна или XTerm class, смена родителя и повторное использование PID отклоняются.
- Отсутствующие xprop/xdotool и неуправляемое/нераспознанное начальное WM_STATE не вызывают запрос сворачивания.
- Только одновременные WM_STATE Iconic и _NET_WM_STATE_HIDDEN дают minimized; успешный запрос, частичное состояние или отсутствие подтверждения дают failed.
- Повторная проверка владения до изменения окна и при наблюдении результата; уже свёрнутое собственное окно не получает второй запрос.
- subprocess без shell, с timeout=1s; до четырёх опросов состояния. Импорт без GUI, subprocess и проверки процессов.

## Граница доказательств

Тесты используют stdlib unittest/mock на Windows. Linux /proc, xterm, свойства X11, xprop и xdotool подменены fixture-данными. Эти результаты не доказывают фактическое сворачивание окна на Linux.

Остаются независимая интеграционная assurance и реальная проверка прямого xterm -e в локальном X11 с читаемым /proc и заранее установленными xprop/xdotool. Утилиты, Linux/WSL, Runtime и службы для проверки не устанавливались и не запускались.
