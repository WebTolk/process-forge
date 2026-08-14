# runtime-lifecycle-clean-smoke-worker

- Дата отчёта: 2026-08-14
- Задача: запуск неизменного `tools/smoke_long_lived_runtime.py` в чистом временном workplace
- Режим: только чтение, прав на модификацию файлов нет

## Выполненные команды (с evidence)

- `python tools/smoke_long_lived_runtime.py`
- `$env:TEMP='C:\Windows\Temp\pf-runtime-smoke'; $env:TMP='C:\Windows\Temp\pf-runtime-smoke'; $env:TMPDIR='C:\Windows\Temp\pf-runtime-smoke'; python tools/smoke_long_lived_runtime.py`

## Первая lifecycle-исходная точка (FAIL)

- Код выхода: `1` в обоих запусках
- Ключевая точка падения: `workplace-init --workplace D:\temp\pf-long-lived-runtime-... --apply` (до `runtime start`)
- Ошибка:
  - `AssertionError: expected 0, got 1: workplace-init ...`
  - `PermissionError: [WinError 5] Отказано в доступе: 'D:\Temp\pf-long-lived-runtime-...\\workplace'`
  - `PermissionError` возникает в `tools/processforge.py` на `append_workplace_event`: `events_path.parent.mkdir(parents=True, exist_ok=True)`
- Признак стадии lifecycle:
  - `runtime` не запускался
  - `active status` не был получен
  - перехват состояний (`started/ready/stale/stop`) не выполнялся из-за раннего файлового blocker

## Наблюдение о среде

- Внутри Python `tempfile.gettempdir()` стабильно возвращает `D:\temp`, даже при попытке перезаписи `TEMP/TMP/TMPDIR`
- Вероятная причина: ограничения среды выполнения на операции с временным деревом (cleanup/создание подкаталогов) в sandbox

## Итог по задаче

- Первый lifecycle outcome: **`FAIL` на подготовке clean workplace (ACL/permission blocker)**, smoke не дошёл до запуска long-lived runtime.
- Дополнительно: без изменения скрипта и без расширения прав среда не позволяет выполнить полноценный smoke-run в новом temp workplace.