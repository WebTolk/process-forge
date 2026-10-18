# Подключение проекта

Project onboarding создаёт корневой `AGENTS.md`, скрытые `.pf/AGENTS.md`
и `.pf/agent-entry.json`, состояние процесса в `.pf/`, связь с workplace и
проектный launcher. Созданный `first-assignment.yaml` — заготовка совместимости,
а не обязательная стадия работы. START больше не нужен и не создаётся.
Существующие файлы сохраняются без изменений, в том числе при `--force`;
статус, doctor и repair не требуют и не воссоздают START.

Запускайте project onboarding только после того, как workplace существует и
нужные общие ресурсы уже созданы, зарегистрированы или явно признаны
необязательными для текущей области работ. Проектный `.pf/` выбирает ресурсы из
workplace, а не создаёт их вместо настройки workplace.

Корень проекта должен быть выбран явно. Не считайте текущую рабочую папку,
корень дистрибутива ProcessForge или глобальную папку конфигурации агента
проектом, пока оператор не подтвердил этот точный каталог как target project.

Из корня дистрибутива:

Для dry-run сначала создайте или выберите `../my-project`. Режим apply может
создать отсутствующий greenfield project root.

```bash
python bin/pf.py project-onboard --project-root ../my-project --workplace ../pf-workplace --type generic-software-project --apply
python bin/pf.py agent-start-prompt --project-root ../my-project
```

Внутри подключенного проекта:

Агент читает корневой `AGENTS.md` (в старом проекте без него — `.pf/AGENTS.md`), затем использует `pf.context`, при необходимости
`pf.search`/`pf.resolve` и `pf.work.start`. Возвращённые Run/assignment/capsule
используются в `pf.work.state` и `pf.work.transition` до `run_completed`;
при `process_choice_required` выбирается предложенный процесс.
`agent-start-prompt` только печатает подсказку, не меняя файлы. См.
[политику входа](../concepts/agent-entry.md). Generic onboarding не устанавливает host-specific Codex hooks и не
требует Runtime, MCP или manual Ledger session. Doctor и context refresh
остаются operator/advanced diagnostics.

## Coordination mode

Project mode задаётся отдельно от capability workplace:

```bash
python bin/pf.py project-onboard --project-root ../my-project --workplace ../pf-workplace --type generic-software-project --coordination-mode inherit --apply
python bin/pf.py project-mode status --project-root ../my-project --workplace ../pf-workplace --json
python bin/pf.py project-mode set --project-root ../my-project --mode simple
python bin/pf.py project-mode set --project-root ../my-project --mode organized --init-office
```

`simple` сохраняет обычный режим 1-1-1-1. `organized` нужен только проектам,
которые должны использовать Director Office рабочего места, Director inbox,
cases, leases, handoffs или error routes.

# Lock-модель project context

Onboarding записывает `context_requirements` и `context_policy` в публичный
`.pf/process-forge.yaml`, затем `project-context-refresh` создаёт разрешённый
lock snapshot. Существующие capsules остаются закреплены за прежним snapshot
id/checksum; новые capsules используют текущее поколение snapshot.
