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

## Блоки Диалога

1. Machine layout: ProcessForge root, workplace path, local docs path, project roots.
2. Agent environment: agent tools, instruction targets, global AGENTS policy.
3. Privacy and safety: local paths, public `path_ref`, secrets, update trust.
4. Resources: knowledge roots, package roots, tools, MCP servers, templates.
5. Platform contracts: neutral by default, real platforms only when explicitly defined.
6. First project: optional immediate project onboarding plan.

## Инструкция Для Агента

`apply` создаёт короткий фрагмент:

```text
ProcessForge is installed at <processforge-root>.
Workplace is <workplace-root>.

Do not copy ProcessForge into agent config folders or projects.

Inside onboarded projects:
1. Read .pf/START_AGENT_HERE.md first.
2. Use python .pf/runtime/bin/pf.py from the project root.

Outside projects:
use python <processforge-root>/bin/pf.py.
```
