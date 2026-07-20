# Первый запуск

Первый запуск разделен на два шага: workplace создается один раз на машине, а
каждый проект подключается отдельно.

## 1. Создать workplace

```bash
python bin/pf.py workplace-init --workplace ../pf-workplace --apply
python bin/pf.py doctor-workplace --root ../pf-workplace
```

Workplace хранит общие registries, templates, knowledge packages и platform
contracts.

## 2. Подключить проект

```bash
python bin/pf.py project-onboard --project-root ../my-project --workplace ../pf-workplace --type generic-software-project --apply
python bin/pf.py agent-start-prompt --project-root ../my-project
```

После onboarding в проекте появится `.pf/` и стартовый файл
`.pf/START_AGENT_HERE.md`.

## 3. Проверить проект

```bash
cd ../my-project
python .pf/runtime/bin/pf.py doctor-project --project-root .
python .pf/runtime/bin/pf.py project-context-check --project-root .
```

Полный порядок см. в [Порядке инициализации](initialization-order.md): install and verify ProcessForge, initialize workplace, configure roots включая `knowledge_roots.local-docs`, register tools и MCP servers, create/import knowledge packages и templates, затем create platform contracts и onboard projects.

Не начинайте с platform contract, если его обязательные packages, templates или tools ещё не существуют. Сначала создайте или зарегистрируйте зависимости.
