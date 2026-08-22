# Manifest обновления ядра

Обновление ядра ProcessForge использует явный manifest владения:

```text
processforge-core.manifest.json
```

Release archive содержит manifest новой версии. Установленное ядро хранит текущий manifest в корне distribution directory. Этот manifest задаёт границу PF-owned файлов.

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

`runtime/`, workplace data, project `.pf` data, caches, SQLite indexes и update journals являются derived/local state и не должны считаться core-owned payload files.

## Flow обновления

CLI:

```bash
python bin/pf.py core-update status --core-root <core>
python bin/pf.py core-update plan --core-root <core> --archive <processforge.zip>
python bin/pf.py core-update apply --core-root <core> --archive <processforge.zip> --confirm
python bin/pf.py core-update repair --core-root <core>
```

`plan` работает read-only. `apply` требует `--confirm`.

Updater вычисляет:

```text
removed = old_manifest.files - new_manifest.files
added   = new_manifest.files - old_manifest.files
changed = общие пути с другим sha256
```

Удаляются только пути, которые были в старом manifest и отсутствуют в новом. Неизвестные файлы сохраняются. Каталоги удаляются только если стали пустыми.

Локально изменённые PF-owned файлы определяются сравнением текущего hash со старым установленным manifest. По умолчанию они блокируют apply.

Новый installed manifest записывается последним, после успешных файловых изменений.

## Recovery

Apply пишет runtime state в:

```text
<core>/runtime/core-update/
```

Backups создаются до замены или удаления старых PF-owned файлов. Если update прерван или файловая операция завершилась ошибкой, `core-update status` показывает `incomplete_update`, а `core-update repair` возвращает состояние для оператора.

File operation failures, включая locked-file style ошибки от ОС, возвращаются как явный `file_operation_failed` и оставляют `runtime/core-update/in-progress.json` со `status: failed`.

В этом первом slice repair консервативно сообщает incomplete state. Автоматический continue/rollback можно добавить отдельным slice.
