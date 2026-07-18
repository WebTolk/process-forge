# ProcessForge

**English documentation:** [README.md](README.md)

ProcessForge — файловый framework для управляемой работы человека и ИИ-агентов
над проектами. Он хранит определения процессов, runs, tasks, iterations,
artifacts, reviews, handoffs, пакеты знаний, шаблоны и platform contracts в
файлах, которые можно версионировать и проверять.

Этот README написан для человека. Здесь намеренно даны prompts, а не списки
команд. Передайте prompt своему ИИ-агенту, а полный набор команд агент должен
брать из [docs/ru/getting-started/agent-prompts.md](docs/ru/getting-started/agent-prompts.md).

![Архитектура ProcessForge](docs/assets/processforge-architecture.svg)

## Что попросить у агента

### Настроить ProcessForge

```text
Настрой ProcessForge для моих локальных проектов.

Используй ProcessForge как файловый инструмент workflow. Сначала прочитай
документацию репозитория, затем используй агентский command runbook в
docs/ru/getting-started/agent-prompts.md.

Создай или проверь workplace, запусти нужные doctor-проверки и сообщи:
- где находится workplace;
- готов ли он к работе;
- какой prompt использовать для подключения проекта.

Не копируй весь репозиторий ProcessForge в .codex, .claude, .agents или другие
папки конфигурации агентов.
```

### Подключить проект

```text
Подключи этот проект к существующему ProcessForge workplace.

Сначала изучи структуру проекта. Используй агентский command runbook
ProcessForge, создай проектный .pf слой, прочитай .pf/START_AGENT_HERE.md,
запусти doctor-проверки и предложи первый полезный run/task план.

ProcessForge должен оставаться установленным как инструмент. Не копируй весь
репозиторий ProcessForge внутрь проекта или в папки конфигурации агентов.
```

### Начать рабочую сессию

```text
Начни ProcessForge run для этой работы.

Сначала прочитай .pf/START_AGENT_HERE.md. Создай run, разбей работу на явные
tasks, фиксируй iterations типов work/debug/fix/review, сохраняй artifacts и
handoffs в проектной .pf папке, а в конце сделай run summary и doctor-проверку.
```

### Создать процесс

```text
Создай новый ProcessForge process для этого проекта.

Используй process authoring workflow. Спрашивай недостающие решения, поддерживай
answers и draft process в актуальном состоянии, проверь semantic parity,
применяй процесс только после review и докажи, что его можно использовать для run.
```

### Создать общие ресурсы

```text
Создай общие ProcessForge resources, которые нужны этому проекту.

Спроси, нужен ли reusable template, knowledge package, platform contract или всё
сразу. Машинные ресурсы держи в workplace, ссылайся на них стабильными ids, не
записывай приватные абсолютные пути в публичные файлы и запусти соответствующие
doctor-проверки.
```

### Проверить релиз

```text
Проверь репозиторий ProcessForge для релиза.

Используй агентский command runbook и release checklist репозитория. Запусти
public cleanliness, checksum, release-test, release-pack, release-archive-test и
whitespace checks. В документации и отчётах используй нейтральное имя архива, не
вшивай туда номер релиза ProcessForge.
```

## Карта документации

- [Prompts быстрого старта](QUICKSTART.ru.md)
- [Индекс документации](docs/ru/index.md)
- [Агентский command runbook](docs/ru/getting-started/agent-prompts.md)
- [Workplace vs project](docs/ru/concepts/workplace-vs-project.md)
- [Runtime model](docs/ru/concepts/runtime-model.md)
- [Runs, tasks и iterations](docs/ru/concepts/runs-tasks-iterations.md)
- [Authoring parity](docs/ru/authoring/authoring-parity.md)
- [Ограничения](docs/ru/known-limitations.md)

## Лицензия

См. [LICENSE](LICENSE).
