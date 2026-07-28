# Командный справочник агента и промпты

Эта страница написана для ИИ-агентов. Документация для человека должна ссылаться
сюда, а не дублировать длинные списки команд. Не вшивайте номера релизов в текст,
примеры, имена архивов и отчёты.

## Правила работы

- Рассматривайте ProcessForge как установленный инструмент, а не как содержимое
  для копирования в `.codex`, `.claude`, `.agents` или похожие папки.
- Из корня дистрибутива ProcessForge используйте `python bin/pf.py`.
- Внутри подключенного проекта используйте `python .pf/runtime/bin/pf.py`.
- Перед проектной работой читайте `.pf/START_AGENT_HERE.md`.
- Для новой настройки машины с участием человека по умолчанию используйте
  пошаговую настройку workplace: `workplace-setup start`,
  `workplace-setup review`, `workplace-setup apply` и
  `workplace-setup status`.
- Полностью автоматический путь используйте только когда оператор явно просит
  автоматизацию и дал нужные пути и решения.
- Держите строгий порядок инициализации: сначала workplace, затем ресурсы
  workplace, затем подключение проекта.
- Общие ресурсы держите на уровне workplace, а записи выполнения проекта — в
  проектной `.pf/` папке.
- Process definitions держите независимыми от платформы. Process описывает
  механику: стадии, роли, gates, артефакты, capabilities, инструменты, hooks и
  task loops.
- Platform contracts рассматривайте как композиционные манифесты workplace.
  Они собирают пакеты знаний, шаблоны, инструменты, MCP providers,
  capabilities, процессы, стандарты кода, project type hints, политики и
  необязательное наследование parent/child platform.
- Имена архивов конкретного релиза держите в release checklist. В повторно
  используемых примерах промптов применяйте нейтральные имена архивов.
- `--interactive` принимается first-run initialization commands ради
  совместимости пользовательского опыта; текущие команды остаются файловыми и
  не требуют вопросов в терминале.
- Для обычной проектной работы начинайте с single-agent `1-1-1-1` model: один
  оператор, одна primary agent session, один проект и один active process/run.
  Сделайте check-in через `session-start` или `agent-checkin`, выполняйте
  процесс последовательно, используйте CLI checks и gates как проверку, затем
  сделайте checkout через `session-end` или `agent-checkout`.
- Не предполагайте Agent Director, explicit leases или Supervisor / Execution
  Inspector для простой работы. Используйте их только когда выбранный process
  требует multi-agent coordination, process handoffs или external runtime
  workers.
- Для bounded worker orchestration используйте `orchestrator-plan create`,
  `orchestrator-plan validate`, `orchestrator-plan apply`,
  `orchestrator-plan status` и `worker-launch-prompt create`.

## Проверки корня дистрибутива

```bash
python bin/pf.py version
python tools/validate-process-forge-schemas.py --root .
python tools/validate-public-cleanliness.py --root .
python tools/validate-process-forge-checksums.py --root . --check
python bin/pf.py release-test --root .
python bin/pf.py release-test --root . --public --fail-fast
python bin/pf.py release-pack --root . --output dist/processforge.zip
python bin/pf.py release-archive-test --archive dist/processforge.zip --root . --extracted-test full
git diff --check
```

## Настройка workplace по умолчанию

Используйте этот путь для новой машины, если оператор явно не попросил
полностью автоматическую настройку.

```bash
python <processforge-root>/bin/pf.py workplace-setup start --workplace <workplace-path> --session-id <session-id> --answers <answers-yaml> --apply
python <processforge-root>/bin/pf.py workplace-setup review --workplace <workplace-path> --session-id <session-id>
python <processforge-root>/bin/pf.py workplace-setup apply --workplace <workplace-path> --session-id <session-id> --apply
python <processforge-root>/bin/pf.py workplace-setup status --workplace <workplace-path> --session-id <session-id>
python <processforge-root>/bin/pf.py doctor-workplace --root <workplace-path>
```

Во время пошаговой настройки задавайте вопросы блоками, обновляйте
`answers.yaml`, пересоздавайте предложение, показывайте `proposal.md` перед
apply и не подключайте проект, пока выбор ресурсов не согласован.

## Полностью автоматическая настройка workplace

Используйте этот путь только когда нужные пути и решения уже известны.

```bash
python <processforge-root>/bin/pf.py workplace-init --workplace <workplace-path> --apply
python <processforge-root>/bin/pf.py doctor-workplace --root <workplace-path>
```

## Удобная команда first-run

Используйте `first-run` только когда нужно выполнить workplace initialization и
project onboarding последовательно, без пошагового диалога. Это не путь по
умолчанию для настройки с участием человека. Используйте его, когда оператор
передал `workplace`, `project-root` и `type`, а подготовка общих ресурсов уже
завершена или явно не входит в область работ. Для dry-run на новом проекте
сначала создайте или выберите целевой каталог проекта.

```bash
python <processforge-root>/bin/pf.py first-run --workplace <workplace-path> --project-root <project-root> --type <project-type> --apply
```

## Подключение проекта

Project onboarding допустим только после того, как workplace существует, а
нужные общие ресурсы уже есть, проверены или явно не входят в область работ.

Для dry-run `<project-root>` должен уже существовать. Режим apply может создать
отсутствующий greenfield project root.

```bash
python <processforge-root>/bin/pf.py project-onboard --project-root <project-root> --workplace <workplace-path> --type <project-type> --apply
python <processforge-root>/bin/pf.py agent-start-prompt --project-root <project-root>
```

После подключения:

```bash
cd <project-root>
python .pf/runtime/bin/pf.py doctor-project --project-root .
python .pf/runtime/bin/pf.py project-context-refresh --project-root .
python .pf/runtime/bin/pf.py project-context-check --project-root .
```

## Process authoring

```bash
python .pf/runtime/bin/pf.py process-authoring-start --project-root . --id <process-id> --title "<title>" --scope project --kind operational --apply
python .pf/runtime/bin/pf.py process-authoring-review --project-root . --id <process-id>
python .pf/runtime/bin/pf.py process-authoring-apply --project-root . --id <process-id> --apply
python .pf/runtime/bin/pf.py process-doctor --project-root . --process <process-id>
python .pf/runtime/bin/pf.py process-list --project-root .
python .pf/runtime/bin/pf.py process-describe --project-root . --process <process-id>
```

## Task batch run

```bash
python .pf/runtime/bin/pf.py session-start --project-root . --agent primary-agent --process task-batch-execution
python .pf/runtime/bin/pf.py run-create --project-root . --id <run-id> --title "<title>" --process task-batch-execution --apply
python .pf/runtime/bin/pf.py task-create --project-root . --run <run-id> --id <task-id> --title "<task title>" --process <process-id> --apply
python .pf/runtime/bin/pf.py iteration-add --project-root . --task <task-id> --kind work --summary "..." --apply
python .pf/runtime/bin/pf.py iteration-add --project-root . --task <task-id> --kind debug --summary "..." --apply
python .pf/runtime/bin/pf.py iteration-add --project-root . --task <task-id> --kind fix --summary "..." --apply
python .pf/runtime/bin/pf.py iteration-add --project-root . --task <task-id> --kind review --summary "..." --apply
python .pf/runtime/bin/pf.py task-complete --project-root . --task <task-id> --summary "..." --apply
python .pf/runtime/bin/pf.py run-summary --project-root . --run <run-id> --apply
python .pf/runtime/bin/pf.py run-doctor --project-root . --run <run-id>
python .pf/runtime/bin/pf.py session-end --project-root .
```

## Создание ресурсов workplace

Регистрация инструментов и MCP providers:

```bash
python <processforge-root>/bin/pf.py tool-register --workplace <workplace-path> --id <tool-id> --capability <capability> --command "<command without secrets>" --apply
python <processforge-root>/bin/pf.py mcp-register --workplace <workplace-path> --id <mcp-id> --capability <capability> --command "<command without secrets>" --apply
```

Повторно используемый шаблон:

```bash
python <processforge-root>/bin/pf.py template-create --workplace <workplace-path> --id <template-id> --title "<title>" --apply
python <processforge-root>/bin/pf.py template-doctor --workplace <workplace-path> --template <template-id>
```

Пакет знаний:

```bash
python <processforge-root>/bin/pf.py knowledge-package-create --workplace <workplace-path> --id <package-id> --title "<title>" --package-root global --apply
python <processforge-root>/bin/pf.py knowledge-package-doctor --workplace <workplace-path> --package <package-id>
```

Platform contract:

```bash
python <processforge-root>/bin/pf.py platform-create --workplace <workplace-path> --id <platform-id> --title "<title>" --apply
python <processforge-root>/bin/pf.py platform-contract-install --workplace <workplace-path> --id <platform-id> --required-packages <package-id> --required-tools <tool-id> --required-mcp <mcp-id> --required-templates <template-id> --apply
python <processforge-root>/bin/pf.py platform-contract-doctor --workplace <workplace-path> --platform <platform-id>
```

Ресурсы знаний:

```bash
python <processforge-root>/bin/pf.py knowledge-add-url --workplace <workplace-path> --package <package-id> --url <url> --apply
python <processforge-root>/bin/pf.py knowledge-add-resource --workplace <workplace-path> --package <package-id> --resource-file <resource-yaml> --apply
python <processforge-root>/bin/pf.py knowledge-index-refresh --workplace <workplace-path> --package <package-id> --apply
```

Platform contracts создавайте после того, как их required packages, templates,
tools, MCP providers, processes, coding standards и capabilities уже
существуют.

## Prompt для человека: настройка

```text
Настрой ProcessForge на этой машине в режиме пошаговой настройки. Используй
командный справочник агента в документации репозитория, задавай вопросы блоками,
создай или проверь workplace, настрой ресурсы workplace перед подключением
проекта, запусти doctor-проверки и сообщи точные пути и следующий шаг.
```

## Prompt для человека: полностью автоматическая настройка

```text
Настрой ProcessForge автоматически. Используй явно переданные мной пути и
решения, пропусти пошаговый диалог, если не отсутствует обязательный ответ,
инициализируй или проверь workplace, настрой или зарегистрируй общие ресурсы,
создай platform contracts после их зависимостей, затем подключи проект только
если передан project path. Запусти doctor checks и сообщи допущения и
пропущенные области.
```

## Prompt для человека: работа над проектом

```text
Используй ProcessForge для этой задачи. Сначала прочитай
.pf/START_AGENT_HERE.md, создай или переиспользуй run, разбей запрос на задачи,
фиксируй итерации, сохраняй артефакты в .pf, запусти нужные проверки и заверши
кратким handoff с фактическими свидетельствами.
```

## Subagent prompt: documentation specialist

```text
Ты ProcessForge documentation subagent.

Scope: только документация. Не меняй исходный код, package manifests, release
artifacts или generated checksums, если main agent явно не назначил это тебе.

Tasks:
- прочитай релевантные документы и assignment;
- обновляй только назначенные файлы документации;
- держи human docs в формате prompt-only, где это требуется;
- держи agent docs command-complete;
- не вшивай номера релизов в prose или archive examples;
- верни список файлов, краткое содержание и остаточные риски.
```

## Subagent prompt: implementation specialist

```text
Ты ProcessForge implementation subagent.

Scope: только code или schema files, явно назначенные main agent. Не пиши в
файлы документации, закреплённые за другим subagent.

Tasks:
- изучи существующие command и schema patterns перед правками;
- сделай минимальное совместимое изменение;
- запусти focused compile/schema checks, если они доступны;
- сообщи точные commands, outputs, changed files и follow-up risks.
```

## Subagent prompt: test and release specialist

```text
Ты ProcessForge test and release subagent.

Scope: только validation, если тебя явно не попросили исправить failing gate.

Tasks:
- запусти назначенные validation commands;
- пересобирай релизные архивы с нейтральными filenames для свидетельств,
  предназначенных для документации;
- проверь archive после упаковки;
- сообщи pass/fail status с command names и первой actionable failure.
```

## Subagent prompt: review specialist

```text
Ты ProcessForge review subagent.

Scope: review changed files и evidence. Не меняй файлы, если main agent не
попросил repair.

Tasks:
- ищи behavioral regressions, stale commands, current-version references в docs,
  смешивание human/agent instructions и missing validation;
- цитируй files и lines для findings;
- отделяй blocking findings от non-blocking follow-up.
```
# Lock-модель project context

На старте сессии агент должен показать результат
`project-context-check --session-start --json`. `fresh` продолжает работу,
`fresh_with_updates` требует уведомления, `stale` обрабатывается по
`context_policy`, `broken` блокирует выполнение. Capsules закрепляют snapshot
id/checksum и не используют `latest`.

Для `software-feature-development` агент проходит полный lifecycle:
orchestration, intake, investigation, domain, architecture, implementation,
assurance, release-delivery и evolve. Release/evolve можно отметить
`not_applicable`, но только с причиной и свидетельствами. Package/build/install - это
`execution_profile.delivery_profile`, а не отдельный process id.
