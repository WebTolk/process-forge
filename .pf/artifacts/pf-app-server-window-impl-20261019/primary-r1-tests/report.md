# Проверки исправления R1

Дата: 2026-10-19. Исполнитель: primary. Статус: ready_for_review.

Запись этой Work в продукт ограничена tools/smoke_server_console.py.
Предыдущий assurance writer завершён и передал область через immutable handoff;
новых native workers и параллельной записи нет.

Добавлены два test methods с 12 subcases: OSError/ValueError при write и flush
автоматического заголовка (с --minimized и без него) и диагностической строки.
Проверяется реальная цепочка service.command_serve с mocked RuntimeProcess:
serve вызывается, его return value сохраняется; ошибка header не инициирует GUI.
Существующие assertions не ослаблялись.

До исправления console.py точечный unittest завершился exit 1, Ran 2 tests,
FAILED (errors=12). Это подтвердило independent R1 и выявило тот же отказ
диагностики. После изменения только optional presentation в родительской Work:

```text
python -B -m unittest tools.smoke_server_console.PresentationChecks.test_tty_header_write_and_flush_failure_do_not_prevent_serve tools.smoke_server_console.PresentationChecks.test_minimization_diagnostic_write_and_flush_failure_do_not_prevent_serve
Ran 2 tests in 0.025s
OK
exit: 0

python -B tools/smoke_server_operator.py
Ran 29 tests in 0.377s
OK
PASS: 29 server-console checks (desktop APIs mocked; native GUI acceptance excluded).
PASS: actual HTTP busy/unknown/inflight/owner/auth guards, force, old capability refusal, launcher and readonly JSON
exit: 0

python -B tools/smoke_runtime_mcp_autostart.py
PASS: Runtime Task Scheduler minimized/exact-interpreter/refusal previews and Codex MCP contracts (no real scheduler changes).
exit: 0
```

git diff --check прошёл. Неизменённый singleton smoke уже прошёл в parent;
повтор не понадобился: singleton/lifecycle source не менялся. Настоящие службы,
Scheduler и графические окна этими проверками не менялись. Успешная реальная
GUI-минимизация по-прежнему не квалифицирована. Старые reports/hash revision
сохранены; отдельное независимое повторное ревью R1 обязательно до доставки.
