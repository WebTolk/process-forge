# Первый запуск

Первый запуск разделен на два шага: workplace создается один раз на машине, а
каждый проект подключается отдельно.

Если нужна диалоговая настройка новой машины, сначала используйте
[Guided workplace setup](guided-workplace-setup.md): агент соберёт answers,
proposal, review, apply report, agent snippet и next steps.

Команда `first-run` выполняет `workplace-initialization` и
`project-onboarding` по порядку. Это удобная команда запуска, а не отдельное
process definition.

Для обычной настройки новой машины с человеком не начинайте с `first-run`.
Сначала проведите guided workplace setup, затем создайте или зарегистрируйте
resources workplace, и только после этого подключайте проект. Используйте
`first-run` как полностью автоматический shortcut, когда уже известны
workplace path, project root и project type, а ресурсная часть либо готова,
либо явно не входит в scope.

```bash
python bin/pf.py first-run --workplace ../pf-workplace --project-root ../my-project --type generic-software-project --apply
```

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
