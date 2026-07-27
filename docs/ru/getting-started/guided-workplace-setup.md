# Guided Workplace Setup

Guided workplace setup - это агентский сценарий настройки новой рабочей машины. Агент задаёт вопросы блоками, обновляет `answers.yaml`, до применения создаёт proposal, применяет workplace через существующую механику initialization, запускает `doctor-workplace` и записывает следующие шаги для `project-onboard`.

CLI поддерживает файловый workflow, но не является terminal-only wizard.

## Команды

```bash
python bin/pf.py workplace-setup start --workplace <workplace-root> --session-id first-machine --apply
python bin/pf.py workplace-setup review --workplace <workplace-root> --session-id first-machine
python bin/pf.py workplace-setup apply --workplace <workplace-root> --session-id first-machine --apply
python bin/pf.py workplace-setup status --workplace <workplace-root> --session-id first-machine
```

Артефакты session хранятся здесь:

```text
<workplace-root>/.pf-workplace/setup-sessions/<session-id>/
```

Создаются `answers.yaml`, `proposal.yaml`, `proposal.md`, `review.md`, `apply-report.md`, `agent-instructions.md` и `next-steps.md`.

## Блоки диалога

1. Размещение на машине: ProcessForge root, путь workplace, путь локальной документации, корни проектов.
2. Среда агентов: agent tools, instruction targets, global AGENTS policy.
3. Приватность и безопасность: локальные пути, public `path_ref`, secrets, update trust.
4. Ресурсы: knowledge roots, package roots, tools, MCP servers, templates.
5. Platform contracts: нейтральные по умолчанию; реальные platforms только при явном описании.
6. Coordination: Director capability, default project mode и нужно ли сразу создать Director Office.
7. Первый проект: необязательный план немедленного `project-onboard`, включая project coordination mode.

## Инструкция для агента

`apply` создаёт короткий фрагмент:

```text
ProcessForge установлен в <processforge-root>.
Workplace находится в <workplace-root>.

Не копируйте ProcessForge в папки конфигурации агентов или проекты.

Внутри подключённых проектов:
1. Сначала прочитайте .pf/START_AGENT_HERE.md.
2. Из корня проекта используйте python .pf/runtime/bin/pf.py.

Вне проектов используйте python <processforge-root>/bin/pf.py.
```
