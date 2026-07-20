# Агентский command runbook и prompts

Эта страница написана для ИИ-агентов. Документация для человека должна ссылаться
сюда, а не дублировать длинные списки команд. Не вшивайте номера релизов в текст,
примеры, имена архивов и отчёты.

## Правила работы

- Рассматривайте ProcessForge как установленный инструмент, а не как содержимое
  для копирования в `.codex`, `.claude`, `.agents` или похожие папки.
- Из distribution root ProcessForge используйте `python bin/pf.py`.
- Внутри подключенного проекта используйте `python .pf/runtime/bin/pf.py`.
- Перед проектной работой читайте `.pf/START_AGENT_HERE.md`.
- Общие ресурсы держите на уровне workplace, а execution records проекта — в
  проектной `.pf/` папке.
- Process definitions держите platform-agnostic. Process описывает механику:
  stages, roles, gates, artifacts, capabilities, tools, hooks и task loops.
- Platform contracts рассматривайте как workplace composition manifests. Они
  собирают knowledge packages, templates, tools, MCP providers, capabilities,
  processes, coding standards, project type hints, policies и optional
  parent/child platform inheritance.
- В публичных примерах и отчётах используйте нейтральные имена release archives,
  например `dist/processforge-release.zip`.
- `--interactive` принимается first-run initialization commands для UX
  compatibility; текущие commands остаются file-first и не требуют terminal
  prompting.

## Проверки distribution root

```bash
python bin/pf.py version
python tools/validate-process-forge-schemas.py --root .
python tools/validate-public-cleanliness.py --root .
python tools/validate-process-forge-checksums.py --root . --check
python bin/pf.py release-test --root .
python bin/pf.py release-pack --root . --output dist/processforge-release.zip
python bin/pf.py release-archive-test --archive dist/processforge-release.zip
git diff --check
```

## Настройка workplace

```bash
python <processforge-root>/bin/pf.py workplace-init --workplace <workplace-path> --apply
python <processforge-root>/bin/pf.py doctor-workplace --root <workplace-path>
```

## Подключение проекта

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
python .pf/runtime/bin/pf.py run-create --project-root . --id <run-id> --title "<title>" --process task-batch-execution --apply
python .pf/runtime/bin/pf.py task-create --project-root . --run <run-id> --id <task-id> --title "<task title>" --process <process-id> --apply
python .pf/runtime/bin/pf.py iteration-add --project-root . --task <task-id> --kind work --summary "..." --apply
python .pf/runtime/bin/pf.py iteration-add --project-root . --task <task-id> --kind debug --summary "..." --apply
python .pf/runtime/bin/pf.py iteration-add --project-root . --task <task-id> --kind fix --summary "..." --apply
python .pf/runtime/bin/pf.py iteration-add --project-root . --task <task-id> --kind review --summary "..." --apply
python .pf/runtime/bin/pf.py task-complete --project-root . --task <task-id> --summary "..." --apply
python .pf/runtime/bin/pf.py run-summary --project-root . --run <run-id> --apply
python .pf/runtime/bin/pf.py run-doctor --project-root . --run <run-id>
```

## Authoring ресурсов workplace

Register tools и MCP providers:

```bash
python <processforge-root>/bin/pf.py tool-register --workplace <workplace-path> --id <tool-id> --capability <capability> --command "<command without secrets>" --apply
python <processforge-root>/bin/pf.py mcp-register --workplace <workplace-path> --id <mcp-id> --capability <capability> --command "<command without secrets>" --apply
```

Reusable template:

```bash
python <processforge-root>/bin/pf.py template-create --workplace <workplace-path> --id <template-id> --title "<title>" --apply
python <processforge-root>/bin/pf.py template-doctor --workplace <workplace-path> --template <template-id>
```

Knowledge package:

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

Knowledge resources:

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
Настрой ProcessForge на этой машине. Используй агентский command runbook в
документации репозитория, создай или проверь workplace, запусти doctor-проверки
и сообщи точные пути и следующий шаг подключения проекта.
```

## Prompt для человека: работа над проектом

```text
Используй ProcessForge для этой задачи. Сначала прочитай .pf/START_AGENT_HERE.md,
создай или переиспользуй run, разбей запрос на tasks, фиксируй iterations,
сохраняй artifacts в .pf, запусти нужные проверки и заверши кратким handoff с
фактическими evidence.
```

## Subagent prompt: documentation specialist

```text
Ты ProcessForge documentation subagent.

Scope: только документация. Не меняй source code, package manifests, release
artifacts или generated checksums, если main agent явно не назначил это тебе.

Tasks:
- прочитай релевантные docs и assignment;
- обновляй только назначенные documentation files;
- держи human docs в формате prompt-only, где это требуется;
- держи agent docs command-complete;
- не вшивай номера релизов в prose или archive examples;
- верни file list, summary и residual risks.
```

## Subagent prompt: implementation specialist

```text
Ты ProcessForge implementation subagent.

Scope: только code или schema files, явно назначенные main agent. Не пиши в
documentation files, закреплённые за другим subagent.

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
- rebuild release archives делай с нейтральными filenames для documentation-facing
  evidence;
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
