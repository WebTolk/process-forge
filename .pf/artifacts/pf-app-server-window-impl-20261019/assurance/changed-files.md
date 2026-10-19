# Изменённые файлы assurance

- `tools/smoke_server_console.py` — новый набор из 27 тестовых методов с дополнительными subTest: общая presentation policy, вызов foreground serve, parser aliases, Windows и Linux adapters.
- `tools/smoke_server_operator.py` — автоматический TTY-заголовок без обязательного `--console`, версия переданного Core; запуск нового suite из существующего smoke entrypoint. Тело существующих HTTP/guarded-stop проверок сохранено.
- `tools/smoke_runtime_mcp_autostart.py` — фикстура прямого CLI, foreground `--minimized`, точный Python, native Windows argv round trip, XML settings, action drift, отказ перезаписи и previews, CLI forwarding, отсутствие direct entrypoint. Весь smoke запрещает случайный запуск внешнего scheduler/Codex процесса.

Продуктовые runtime/parser/launcher файлы и `src/**` не изменялись worker. Существующий `tools/smoke_runtime_singleton_orphan.py` только прочитан и проверен, изменения отсутствуют. Коммит, push, установка и перезапуск служб не выполнялись.

Собственные служебные материалы: `assurance/change-summary.md`, результаты команд, хеши/верификация, sanitized liveness diagnostic и `.pf/logs/pf-app-server-window-impl-20261019-assurance.md`. Helper-скрипты и два пустых каталога неудачной временной подготовки в назначенном scratch удержаны как evidence; чужой scratch не открывался.
