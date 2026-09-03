# runtime-lifecycle-isolated-repro

- **Задача:** `verification-runtime-lifecycle-isolated-repro`
- **Режим:** изолированный запуск без параллельных воркеров (последовательно).
- **Дата:** 2026-08-14
- **Изменения в коде:** не выполнялись (только чтение + запуск скриптов).
- **Статус артефакта:** `FAIL`

## Результаты запуска (по порядку)

1. `python tools/smoke_long_lived_runtime.py`
   - Итог: `FAIL` (exit code `1`)
   - Точка падения: `workplace-init` внутри скрипта на этапе `with tempfile.TemporaryDirectory(...)`
   - Ошибка: `PermissionError: [WinError 5] Отказано в доступе` при создании `D:\Temp\pf-long-lived-runtime-*\\workplace`
   - Трасс: попытка `processforge.py workplace-init ...` падает до каких-либо runtime-команд (`runtime start` и далее).

2. `python tools/smoke_runtime_ledger_hooks_mcp.py`
   - Итог: `FAIL` (exit code `1`)
   - Точка падения: та же стадия `workplace-init` с `PermissionError` на `D:\Temp\pf-ledger-hooks-mcp-*\\workplace`
   - Трасс: скрипт не дошёл до проверок Ledger/Codex adapter/MCP.

## Причина блокера (общая для обоих скриптов)

- В текущей среде разрешённый доступ не позволяет создавать временные runtime-workplace-деревья в `D:\temp`/`D:\Temp`.
- Оба скрипта используют `tempfile.TemporaryDirectory(prefix=...)` и ожидают корректную запись в temp-директории; это происходит на этапе инициализации окружения, поэтому runtime-цикл не запускается.

## Первый воспроизводимый lifecycle-переход

- **Не воспроизведён.**
- Первый переход в рантайм-жизненном цикле (`not_running -> starting/ready` или `stale -> ...`) не случился, потому что запуск прерывается до старта `runtime` уже на этапе `workplace-init`.

## Последовательность соблюдена?

- Да. Скрипты запускались строго последовательно, в одном изолированном потоке, без параллелизма.