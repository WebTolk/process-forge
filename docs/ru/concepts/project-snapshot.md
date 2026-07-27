# Project Snapshot

Project snapshot — машинно-читаемое описание текущего состояния проекта:
manifest, linked workplace, найденные процессы, resources и freshness.

Обновить snapshot:

```bash
python .pf/runtime/bin/pf.py project-context-refresh --project-root .
```

Проверить freshness:

```bash
python .pf/runtime/bin/pf.py project-context-check --project-root .
```

Snapshot нужен для handoff, старта агента, release checks и принятия решения,
нужно ли обновлять контекст перед новой задачей.

Snapshot также содержит `workplace_coordination`. Worker должен использовать
этот блок, чтобы отличать effective `simple` project, где Director не нужен,
от effective `organized` project, где может применяться Director inbox
metadata.
# Project Context Lock

Текущий project context snapshot является lock-файлом: он хранит snapshot id,
resolved resources, generations, fingerprints и checksum. Подробнее:
`docs/ru/concepts/project-context-lock-model.md`.
