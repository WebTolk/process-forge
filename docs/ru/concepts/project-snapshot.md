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
