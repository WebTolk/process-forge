# Manifest обновления ядра

Обновления ядра ProcessForge используют явный ownership manifest:

```text
processforge-core.manifest.json
```

Release archive содержит manifest новой версии. Установленный core root хранит текущий manifest в корне distribution directory. Manifest задаёт границу PF-owned файлов.

## Контракт manifest

Минимальные поля:

- `schema_version: 1`
- `kind: processforge.core_manifest`
- `version`
- `generated_at`
- `source`
- `files[]`
  - `relative_path`
  - `size`
  - `sha256`

Пути должны быть относительными к core root. Absolute paths, backslashes, пустые сегменты, `.`, `..` и выход за core root отклоняются.

`runtime/`, workplace data, project `.pf` data, caches, SQLite indexes и update journals являются derived/local state и не должны моделироваться как core-owned payload files.

## Flow обновления

CLI:

```bash
python bin/pf.py core-update status --core-root <core>
python bin/pf.py core-update plan --core-root <core> --archive <processforge.zip>
python bin/pf.py core-update apply --core-root <core> --archive <processforge.zip> --confirm
python bin/pf.py core-update repair --core-root <core>
```

`plan` работает read-only. `apply` требует `--confirm`.

## Совместимая миграция Workplace

Архив может содержать декларативную миграцию Workplace в `updates/migrations/`.
Чтобы включить её в обновление существующего рабочего места, передайте его
корень при планировании и применении:

```bash
python bin/pf.py core-update plan --core-root <core> --archive <processforge.zip> --workplace-root <workplace>
python bin/pf.py core-update apply --core-root <core> --archive <processforge.zip> --workplace-root <workplace> --confirm
```

План включает только операции, объявленные в архиве. Миграция 1.0.2 → 1.1.0
добавляет встроенный драйвер `codex-exec` и запись в его реестре только при
их отсутствии. Существующие файлы и записи сохраняются. Команда
`workplace-init` предназначена для первичной инициализации и не вызывается
при обновлении.

Перед записью updater сохраняет затронутые файлы Workplace в каталоге резервных
копий обновления Core и регистрирует операцию в журнале. Если миграция не
завершилась, `core-update repair` показывает состояние восстановления и путь
к резервным копиям. После успешного apply с `--workplace-root` автоматически
выполняется короткая проверка `doctor-workplace`; её результат записывается в
`<core>/runtime/core-update/last-apply.json`.

Updater вычисляет:

```text
removed = old_manifest.files - new_manifest.files
added   = new_manifest.files - old_manifest.files
changed = common paths with different sha256
```

Удаляются только paths, которые были в старом manifest и отсутствуют в новом manifest. Unknown files сохраняются. Directories удаляются только когда становятся пустыми.

Locally modified PF-owned files определяются сравнением текущего file hash со старым installed manifest. Они блокируют apply, если оператор явно не использовал force option.

Новый installed manifest записывается последним, после успешных file changes.

## Recovery

Apply пишет runtime update state в:

```text
<core>/runtime/core-update/
```

Backups создаются до замены или удаления старых PF-owned файлов. Если update прерван или файловая операция завершилась ошибкой, `core-update status` показывает `incomplete_update`, а `core-update repair` возвращает состояние для оператора.

File operation failures, включая locked-file style ошибки от ОС, возвращаются как явный `file_operation_failed` и оставляют `runtime/core-update/in-progress.json` со `status: failed`.

Incomplete update journal записывает:

- `installed_version`
- `target_version`
- `archive`
- `backup_dir`
- `counts`
- `completed_operations`
- `pending_operations`
- `backed_up`
- `error`

`core-update repair` классифицирует incomplete states:

- `safe_to_rollback`, если update упал до записи manifest и backup старого manifest существует;
- `manual_repair_required`, если manifest уже записан, journal неполный или безопасность нельзя доказать;
- `nothing_to_repair`, если incomplete update отсутствует.

Автоматическое выполнение continue/rollback намеренно уже, чем classification contract, и должно добавляться только для состояний, которые journal доказывает безопасными.
