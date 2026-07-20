# Runtime Model

![Lifecycle run/task/iteration](../../assets/processforge-run-lifecycle.svg)

ProcessForge работает через короткие CLI-команды. Команда читает файлы workplace
и project, записывает нужный artifact или runtime record, emits events и
завершается.

Основные runtime files:

- `.pf/process-forge.yaml`;
- `.pf/contexts/`;
- `.pf/runs/`;
- `.pf/assignments/`;
- `.pf/artifacts/`;
- `.pf/reviews/`;
- `.pf/handoffs/`;
- `.pf/runtime/events/events.ndjson`.

Долгоживущий watcher или runner может появиться отдельным слоем позже, но core
runtime не требует daemon.

## Runtime requirements

Для runtime рекомендуется Python 3.11+. Python 3.10+ допустим только когда текущие тесты подтверждают совместимость. Также нужны Python package dependencies из `requirements.txt`, включая `PyYAML`, UTF-8 файловая система и read/write access к ProcessForge distribution, workplace и папкам проекта.

Runtime usage не требует PowerShell, Git, daemon или фонового процесса. Git нужен только для version-control integration или для development/release checks.
