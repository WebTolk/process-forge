# Отчёт `smoke-retry` (assignment `python-core-phase-c-smoke-retry`)

## Режим запуска
- Дата/время: 2026-08-14
- Команда 1: `python tools/smoke_process_resolver_multiple_roots.py`
- Команда 2: `python tools/smoke_builtin_process_catalog.py`
- Допуски: редактирование продукта не выполнялось.

## 1) `smoke_process_resolver_multiple_roots.py`

**Запуск с явным `TEMP/TMP` в `.pf/tmp`**
```powershell
$env:TEMP = (Resolve-Path .pf/tmp).Path
$env:TMP  = (Resolve-Path .pf/tmp).Path
python tools/smoke_process_resolver_multiple_roots.py
```

**Результат:** `FAILED` (код возврата `1`)

**Диагностический фрагмент:**
```text
PermissionError: [WinError 5] Отказано в доступе: 'D:\Dev\process-forge\.pf\tmp\pf-process-roots-...'
...
PermissionError: [WinError 5] Отказано в доступе: 'D:\Dev\process-forge\.pf\tmp\pf-process-roots-...'
```

**Ключевая причина:**
- Подготовка временного каталога создаётся в `.pf/tmp/...`, но внутри него `tempfile` не может создать/удалить вложенную структуру `.pf` из-за ограничений прав на доступ (или ACL в этом дереве), а не из-за логики резолва процессов.

---

## 2) `smoke_builtin_process_catalog.py` (без изменений)

**Запуск:**
```powershell
python tools/smoke_builtin_process_catalog.py
```

**Результат:** `FAILED` (код возврата `1`)

**Диагностический вывод (верхняя часть):**
```text
PROCESS CATALOG: FAIL
public_stable: 27 pass, 2 fail
experimental: 1 warn
internal: 1 skipped
warnings: 133
...
FAIL: context-resolution.ecp-capsule-generation required_inputs valid: assignment
...
FAIL: processforge-update-check.discover required_inputs valid: .pf/process-forge.local.yaml or explicit no-local mode, .pf/process-forge.yaml, updates/processforge-update-index.yaml
```

**Сырые данные JSON (`--json`) подтверждают два падения процесса:**
- `context-resolution` — `context-resolution.ecp-capsule-generation` (`required_inputs` → `assignment`).
- `processforge-update-check` — `processforge-update-check.discover` (`required_inputs` → `.pf/process-forge.local.yaml` / `.pf/process-forge.yaml` / `updates/processforge-update-index.yaml`).

---

## Классификация с точки зрения назначения
- **Каталогный seam-регрессии (новая поломка в контракте smoke) не подтверждено.**
- `smoke_builtin_process_catalog.py` падает из-за уже имеющихся/контекстных несоответствий входных требований (неполные `required_inputs` в двух проверках), поэтому это нужно трактовать как **контекстно-предварительная/окружная ошибка**, а не регрессия самой проверки каталога.
- `smoke_process_resolver_multiple_roots.py` падает из-за **ограничений файловой системы в `.pf/tmp`** при запуске с заданными переменными, не из-за бизнес-логики резолва.