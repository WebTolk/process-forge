# Целевые проверки primary

Дата: 2026-10-19. Код adapters и common console завершён; четвёртый worker
добавил постоянные проверки только в собственной области smoke файлов.

Команды выполнены без изменения test source или подмены assertions. Единственная
настройка окружения: TEMP/TMP указывают на собственный primary task scratch.
Это устраняет ограничение sandbox дочернего worker на новые TemporaryDirectory.

```text
python -B tools/smoke_server_operator.py
.........................
Ran 25 tests in 0.248s
OK
PASS: 25 server-console checks (desktop APIs mocked; native GUI acceptance excluded).
PASS: actual HTTP busy/unknown/inflight/owner/auth guards, force, old capability refusal, launcher and readonly JSON
exit: 0

python -B tools/smoke_runtime_mcp_autostart.py
PASS: Runtime Task Scheduler minimized/exact-interpreter/refusal previews and Codex MCP contracts (no real scheduler changes).
exit: 0
```

smoke_server_operator вызывает smoke_server_console, поэтому новая проверка
включена в существующий canonical release entrypoint без изменения монолита.
Сервисы устройства и настоящая Task Scheduler task не изменялись. HTTP fixture
изолирован. GUI API проверены mocks; Windows native отказ подтверждён отдельно
в windows/verification.md; успешная реальная минимизация здесь не заявляется.
