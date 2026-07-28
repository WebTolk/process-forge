# Подключение проекта

Project onboarding создает в проекте папку `.pf/`, связывает проект с
workplace, добавляет runtime launcher и формирует стартовые инструкции для
агента.

Запускайте project onboarding только после того, как workplace существует и
нужные shared resources уже созданы, зарегистрированы или явно признаны
необязательными для текущего scope. Проектный `.pf/` выбирает ресурсы из
workplace, а не создаёт их вместо workplace setup.

Из distribution root:

Для dry-run сначала создайте или выберите `../my-project`. Apply mode может
создать отсутствующий greenfield project root.

```bash
python bin/pf.py project-onboard --project-root ../my-project --workplace ../pf-workplace --type generic-software-project --apply
python bin/pf.py agent-start-prompt --project-root ../my-project
```

Внутри подключенного проекта:

```bash
cd ../my-project
python .pf/runtime/bin/pf.py doctor-project --project-root .
python .pf/runtime/bin/pf.py project-context-refresh --project-root .
```

Агент должен начинать с `.pf/START_AGENT_HERE.md`. Этот файл объясняет, какие
локальные правила и snapshot нужно читать перед работой.

## Coordination mode

Project mode задаётся отдельно от workplace capability:

```bash
python bin/pf.py project-onboard --project-root ../my-project --workplace ../pf-workplace --type generic-software-project --coordination-mode inherit --apply
python bin/pf.py project-mode status --project-root ../my-project --workplace ../pf-workplace --json
python bin/pf.py project-mode set --project-root ../my-project --mode simple
python bin/pf.py project-mode set --project-root ../my-project --mode organized --init-office
```

`simple` сохраняет обычный 1-1-1-1 flow. `organized` нужен только проектам,
которые должны использовать workplace Director Office, Director inbox, cases,
leases, handoffs или error routes.
# Project context lock

Onboarding записывает `context_requirements` и `context_policy` в публичный
`.pf/process-forge.yaml`, затем `project-context-refresh` создаёт resolved lock
snapshot. Существующие capsules остаются закреплены за прежним snapshot
id/checksum; новые capsules используют текущий snapshot generation.
