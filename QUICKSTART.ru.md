# Быстрый старт ProcessForge

Этот guide предполагает, что вы находитесь в distribution root ProcessForge.

```bash
git clone <processforge-repo> process-forge
cd process-forge

python bin/pf.py version
python bin/pf.py release-test --root .
```

## 1. Инициализировать workplace

```bash
python bin/pf.py workplace-init --workplace ../pf-workplace --apply
python bin/pf.py doctor-workplace --root ../pf-workplace
```

## 2. Подключить проект

```bash
python bin/pf.py project-onboard --project-root ../my-project --workplace ../pf-workplace --type generic-software-project --apply
python bin/pf.py agent-start-prompt --project-root ../my-project
```

## 3. Работать внутри подключенного проекта

```bash
cd ../my-project
python .pf/runtime/bin/pf.py doctor-project --project-root .
python .pf/runtime/bin/pf.py run-create --project-root . --id first-run --title "First ProcessForge run" --process task-batch-execution --apply
```

## 4. Создать tasks и iterations

```bash
python .pf/runtime/bin/pf.py task-create --project-root . --run first-run --id task-001-example --title "Example task" --process software-feature-development --apply
python .pf/runtime/bin/pf.py iteration-add --project-root . --task task-001-example --kind work --summary "Initial work done." --apply
python .pf/runtime/bin/pf.py iteration-add --project-root . --task task-001-example --kind review --summary "Reviewed the result." --apply
python .pf/runtime/bin/pf.py task-complete --project-root . --task task-001-example --summary "Task completed." --apply
python .pf/runtime/bin/pf.py run-summary --project-root . --run first-run --apply
python .pf/runtime/bin/pf.py run-doctor --project-root . --run first-run
```

## 5. Создать собственный процесс

```bash
python .pf/runtime/bin/pf.py process-authoring-start --project-root . --id seo-audit --title "SEO Audit" --scope project --kind operational --apply
python .pf/runtime/bin/pf.py process-authoring-review --project-root . --id seo-audit
python .pf/runtime/bin/pf.py process-authoring-apply --project-root . --id seo-audit --apply
python .pf/runtime/bin/pf.py process-doctor --project-root . --process seo-audit
python .pf/runtime/bin/pf.py process-list --project-root .
python .pf/runtime/bin/pf.py process-describe --project-root . --process seo-audit
```

## 6. Создать общие ресурсы workplace

Из distribution root ProcessForge:

```bash
python bin/pf.py template-create --workplace ../pf-workplace --id release-note --title "Release Note" --apply
python bin/pf.py template-doctor --workplace ../pf-workplace --template release-note

python bin/pf.py knowledge-package-create --workplace ../pf-workplace --id project-docs --title "Project Docs" --package-root global --apply
python bin/pf.py knowledge-package-doctor --workplace ../pf-workplace --package project-docs

python bin/pf.py platform-create --workplace ../pf-workplace --id generic-platform --title "Generic Platform" --apply
python bin/pf.py platform-contract-doctor --workplace ../pf-workplace --platform generic-platform
```

## 7. Дать агенту правильный prompt

В подключенном проекте прочитайте `.pf/START_AGENT_HERE.md`. Готовые prompts
для типовых задач находятся в
[docs/ru/getting-started/agent-prompts.md](docs/ru/getting-started/agent-prompts.md).

Не копируйте весь репозиторий ProcessForge в `.codex`, `.claude`, `.agents`
или похожие папки конфигурации агентов. Установите ProcessForge один раз как
инструмент и укажите агенту на проектный `.pf/START_AGENT_HERE.md`.

## 8. Проверить релиз

Из distribution root ProcessForge:

```bash
python tools/validate-public-cleanliness.py --root .
python tools/validate-process-forge-checksums.py --root . --check
python bin/pf.py release-test --root .
python bin/pf.py release-pack --root . --output dist/processforge-v0.1.0.zip
python bin/pf.py release-archive-test --archive dist/processforge-v0.1.0.zip
```
