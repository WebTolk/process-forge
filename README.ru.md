# ProcessForge

**English documentation:** [README.md](README.md)

ProcessForge — file-first framework для работы человека и ИИ-агентов над
проектами. Он хранит определения процессов, runs, tasks, iterations, artifacts,
reviews, handoffs, пакеты знаний, шаблоны и platform contracts в файлах,
которые можно версионировать и проверять.

ProcessForge не требует backend, базы данных, web UI, сетевого транспорта или
обязательного постоянно работающего runner. Текущий релиз ориентирован на
Python CLI и короткие команды.

Текущий release candidate: `0.1.0-rc.1`.

![Архитектура ProcessForge](docs/assets/processforge-architecture.svg)

## Что такое ProcessForge

ProcessForge добавляет в проект явный операционный слой. Правила работы,
процессы, задачи, артефакты и handoff-материалы не остаются только в чате или
в разрозненных заметках. Они записываются в проектные файлы и могут проходить
проверки вместе с кодом и документацией.

Это полезно, когда проекту нужны повторяемые workflow, понятные инструкции для
агентов, локальная история выполнения задач и проверяемый pre-release процесс.

## Основные понятия

- Distribution root: checkout или распакованный релиз ProcessForge как
  инструмента.
- Workplace: машинный уровень для общих пакетов знаний, шаблонов, platform
  contracts, registries и defaults.
- Project: обычный репозиторий, подключенный к workplace через папку `.pf/`.
- `.pf/START_AGENT_HERE.md`: проектная точка входа, которую агент читает после
  onboarding.
- Process definition: YAML-файл со стадиями, ролями, артефактами, gates,
  событиями, tools и evolution policy.
- Run, task, iteration: запись рабочей сессии, ее задач и повторных попыток
  work/debug/fix/review.
- Authoring parity: проверка, что существующий процесс можно backfill-нуть в
  answers и семантически воспроизвести.

ProcessForge отличается от обычного README или `AGENTS.md`: он не только
описывает договоренности, но и создает файловый слой процессов, runtime-записей,
проверок и артефактов.

## Установка

Склонируйте или распакуйте ProcessForge один раз как инструмент:

```bash
git clone <processforge-repo> process-forge
cd process-forge

python bin/pf.py version
python bin/pf.py release-test --root .
```

Из distribution root используйте `python bin/pf.py`. Внутри подключенного
проекта используйте `python .pf/runtime/bin/pf.py`.

## Быстрый старт

Инициализируйте workplace:

```bash
python bin/pf.py workplace-init --workplace ../pf-workplace --apply
python bin/pf.py doctor-workplace --root ../pf-workplace
```

Подключите проект:

```bash
python bin/pf.py project-onboard --project-root ../my-project --workplace ../pf-workplace --type generic-software-project --apply
python bin/pf.py agent-start-prompt --project-root ../my-project
```

Внутри подключенного проекта:

```bash
cd ../my-project
python .pf/runtime/bin/pf.py doctor-project --project-root .
python .pf/runtime/bin/pf.py run-create --project-root . --id first-run --title "First ProcessForge run" --process task-batch-execution --apply
```

Полный короткий путь описан в [QUICKSTART.ru.md](QUICKSTART.ru.md).

## Использование ProcessForge с агентскими окружениями

Не копируйте весь репозиторий ProcessForge в `.codex`, `.claude`, `.agents`
или похожие папки конфигурации агентов.

Установите ProcessForge один раз как инструмент, инициализируйте workplace,
подключите проект и добавьте в конфигурацию агента короткую инструкцию: где
установлен ProcessForge и что проектные инструкции находятся в
`.pf/START_AGENT_HERE.md`.

Сгенерируйте стартовый prompt для проекта:

```bash
python bin/pf.py agent-start-prompt --project-root ../my-project
```

Готовые prompt snippets находятся в
[docs/ru/getting-started/agent-prompts.md](docs/ru/getting-started/agent-prompts.md).

## First-run команды

```bash
python bin/pf.py workplace-init --workplace <workplace-path> --apply
python bin/pf.py doctor-workplace --root <workplace-path>
python bin/pf.py project-onboard --project-root <project-root> --workplace <workplace-path> --type generic-software-project --apply
python bin/pf.py agent-start-prompt --project-root <project-root>
```

Для новых проектов используйте `workplace-init` и `project-onboard`.

## Создание ресурсов workplace

Переиспользуемый шаблон:

```bash
python bin/pf.py template-create --workplace <workplace-path> --id <template-id> --title "<title>" --apply
python bin/pf.py template-doctor --workplace <workplace-path> --template <template-id>
```

Пакет знаний:

```bash
python bin/pf.py knowledge-package-create --workplace <workplace-path> --id <package-id> --title "<title>" --package-root global --apply
python bin/pf.py knowledge-package-doctor --workplace <workplace-path> --package <package-id>
```

Platform contract:

```bash
python bin/pf.py platform-create --workplace <workplace-path> --id <platform-id> --title "<title>" --apply
python bin/pf.py platform-contract-doctor --workplace <workplace-path> --platform <platform-id>
```

## Создание собственных процессов

Внутри подключенного проекта используйте runtime launcher проекта:

```bash
python .pf/runtime/bin/pf.py process-authoring-start --project-root . --id <process-id> --title "<title>" --scope project --kind operational --apply
python .pf/runtime/bin/pf.py process-authoring-review --project-root . --id <process-id>
python .pf/runtime/bin/pf.py process-authoring-apply --project-root . --id <process-id> --apply
python .pf/runtime/bin/pf.py process-doctor --project-root . --process <process-id>
```

## Работа с run/task/iteration

Внутри подключенного проекта:

```bash
python .pf/runtime/bin/pf.py run-create --project-root . --id <run-id> --title "<title>" --process task-batch-execution --apply
python .pf/runtime/bin/pf.py task-create --project-root . --run <run-id> --id <task-id> --title "<task title>" --process <process-id> --apply
python .pf/runtime/bin/pf.py iteration-add --project-root . --task <task-id> --kind work --summary "..." --apply
python .pf/runtime/bin/pf.py task-complete --project-root . --task <task-id> --summary "..." --apply
python .pf/runtime/bin/pf.py run-summary --project-root . --run <run-id> --apply
python .pf/runtime/bin/pf.py run-doctor --project-root . --run <run-id>
```

## Release checks

Из distribution root:

```bash
python tools/validate-public-cleanliness.py --root .
python tools/validate-process-forge-checksums.py --root . --check
python bin/pf.py release-test --root .
python bin/pf.py release-pack --root . --output dist/processforge-v0.1.0.zip
python bin/pf.py release-archive-test --archive dist/processforge-v0.1.0.zip
```

## Карта документации

- [Quickstart](QUICKSTART.ru.md)
- [Индекс документации](docs/ru/index.md)
- [Установка](docs/ru/getting-started/installation.md)
- [Первый запуск](docs/ru/getting-started/first-run.md)
- [Agent prompts](docs/ru/getting-started/agent-prompts.md)
- [Workplace vs project](docs/ru/concepts/workplace-vs-project.md)
- [Runs, tasks и iterations](docs/ru/concepts/runs-tasks-iterations.md)
- [Authoring parity](docs/ru/authoring/authoring-parity.md)
- [Ограничения](docs/ru/known-limitations.md)

## Ограничения

Версия `0.1` — файловый MVP. Watcher, runner/orchestrator service, GUI,
marketplace, remote sync и database-backed control plane не входят в этот
релиз. Resource parity для templates, knowledge packages и platform contracts
пока поверхностный и честно сообщает WARN до появления полного authoring
round-trip.

## Лицензия

См. [LICENSE](LICENSE).
