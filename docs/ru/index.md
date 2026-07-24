# Документация ProcessForge

**English documentation:** [../index.md](../index.md)

![Схема рабочего места ProcessForge](../assets/processforge-architecture.svg)

ProcessForge — файловый framework для управляемой работы человека и ИИ-агентов
над проектами. Начните с установки, затем создайте workplace, подключите проект
и передайте агенту `.pf/START_AGENT_HERE.md`.

Верхний уровень модели: workplace - это машина, где работают человек и агенты;
ProcessForge установлен один раз как инструмент; глобальные resources живут в
workplace; каждый repository хранит только проектный слой `.pf/`.

## Начало работы

- [Установка](getting-started/installation.md)
- [Первый запуск](getting-started/first-run.md)
- [Порядок инициализации](getting-started/initialization-order.md)
- [Инициализация workplace](getting-started/workplace-initialization.md)
- [Guided workplace setup](getting-started/guided-workplace-setup.md)
- [Подключение проекта](getting-started/project-onboarding.md)
- [Агентский command runbook и prompts](getting-started/agent-prompts.md)
- [Первый собственный процесс](getting-started/create-your-first-process.md)
- [Task batch workflow](getting-started/task-batch-workflow.md)
- [Multi-agent orchestration](getting-started/multi-agent-orchestration.md)

## Authoring

- [Reusable templates](authoring/reusable-template-authoring.md)
- [Knowledge packages](authoring/knowledge-package-authoring.md)
- [Platform contracts](authoring/platform-contract-authoring.md)
- [Process authoring](authoring/process-authoring.md)
- [Authoring parity](authoring/authoring-parity.md)
- [Backfill existing processes](authoring/backfill-existing-processes.md)

## Concepts

- [Workplace vs project](concepts/workplace-vs-project.md)
- [Runtime model](concepts/runtime-model.md)
- [Path constants](concepts/path-constants.md)
- [Package roots](concepts/package-roots.md)
- [Project snapshot](concepts/project-snapshot.md)
- [Runs, tasks и iterations](concepts/runs-tasks-iterations.md)
- [Process definition, run, task, iteration](concepts/process-definition-run-task-iteration.md)
- [Multi-agent orchestration](concepts/multi-agent-orchestration.md)
- [Platform contracts](concepts/platform-contracts.md)
- [Platform inheritance](concepts/platform-inheritance.md)
- [Навигация knowledge resources](concepts/knowledge-resource-navigation.md)
- [Hooks и events](concepts/hooks-events.md)
- [Semantic parity](concepts/semantic-parity.md)

## Порядок Слоёв

1. Workplace device: computer, laptop, server или runner host.
2. ProcessForge tool root: CLI, schemas, processes, docs, templates, checks.
3. Global workplace resources: knowledge packages, reusable templates, tools,
   MCP providers, platform contracts, roots, registries, runtime data.
4. Project `.pf/` layer: selected resources, project context, assignments,
   runs, tasks, iterations, artifacts, reviews, handoffs, hooks.

Platform contracts являются composition manifests. Они могут описывать single
platform или parent/child stack и подключать resources, нужные конкретному
проекту. Process definitions остаются platform-agnostic process mechanics.

## Релизы

- [Initial release notes](releases/initial-release.md)
- [Ограничения](known-limitations.md)
