# runtime-lifecycle-temp-rerun

## Условия запуска
- `TEMP` и `TMP` устанавливались в `D:\Dev\process-forge\.pf\runtime\verification-temp` перед каждым smoke-запуском.
- Исходники не менялись, удаление существующих директорий не выполнялось.

## Команды (выполнены последовательно)

1) Длинноживущий Runtime smoke:

```powershell
$tempDir = Resolve-Path '.\.pf\runtime\verification-temp' -ErrorAction SilentlyContinue
if (-not $tempDir) { $tempDir = (New-Item -ItemType Directory -Path '.\.pf\runtime\verification-temp' -Force).FullName } else { $tempDir = $tempDir.Path }
$env:TEMP = $tempDir
$env:TMP = $tempDir
python tools/smoke_long_lived_runtime.py
```

2) Runtime ledger + MCP smoke:

```powershell
$tempDir = Resolve-Path '.\.pf\runtime\verification-temp' -ErrorAction SilentlyContinue
if (-not $tempDir) { $tempDir = (New-Item -ItemType Directory -Path '.\.pf\runtime\verification-temp' -Force).FullName } else { $tempDir = $tempDir.Path }
$env:TEMP = $tempDir
$env:TMP = $tempDir
python tools/smoke_runtime_ledger_hooks_mcp.py
```

3) Доп. мини-проверка окружения `tempfile` (показала тот же паттерн):

```powershell
$env:TEMP = 'D:\Dev\process-forge\.pf\runtime\verification-temp'
$env:TMP = 'D:\Dev\process-forge\.pf\runtime\verification-temp'
python -c "import tempfile, os; d=tempfile.TemporaryDirectory(prefix='pf-long-lived-runtime-', dir=os.environ['TEMP']); print(d.name); p=os.path.join(d.name,'workplace','runtime','events'); os.makedirs(p,exist_ok=True)"
```

## Результаты

- Шаг 1 (`smoke_long_lived_runtime.py`): **неуспешно**, `exit code 1`.
  - Ключевая ошибка: `PermissionError: [WinError 5] Отказано в доступе: 'D:\Dev\process-forge\.pf\runtime\verification-temp\pf-long-lived-runtime-...\\workplace'`
  - Предшествующий шаг: `FileNotFoundError` на `...\workplace\runtime\events`, затем отказ в доступе к `...\workplace`.
- Шаг 2 (`smoke_runtime_ledger_hooks_mcp.py`): **неуспешно**, `exit code 1`.
  - Тот же шаблон ошибки: `PermissionError: [WinError 5] Отказано в доступе: '...\\verification-temp\\pf-ledger-hooks-mcp-...\\workplace'`.
- Шаг 3 (`tempfile` + `os.makedirs`): воспроизвел тот же `PermissionError` при создании `...\\workplace`.

## Вывод
- Требуемый rerun с `TEMP`/`TMP = .pf/runtime/verification-temp` не выполнен успешно в текущем окружении из-за системного/FS ограничения на подкаталоги, создаваемые `tempfile.TemporaryDirectory(...)` внутри этого пути.
- Непосредственная причина — **недоступность для записи/просмотра созданного временного корня `...verification-temp\pf-*-*` на уровне Python**, при том что сам `.pf/runtime/verification-temp` создаётся и доступен для ручного создания `New-Item`.
- Без изменения окружения/ACL для этого пути оба скрипта блокируются до старта runtime-процесса.
