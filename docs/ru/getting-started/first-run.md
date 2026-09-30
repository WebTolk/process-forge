# Первый запуск

Первый запуск разделен на два шага: workplace создается один раз на машине, а
каждый проект подключается отдельно.

Если нужна диалоговая настройка новой машины, сначала используйте
[пошаговую настройку workplace](guided-workplace-setup.md): агент соберёт
ответы, подготовит предложение, проверку, отчёт о применении, фрагмент
инструкции для агента и следующие шаги.

Команда `first-run` выполняет `workplace-initialization` и
`project-onboarding` по порядку. Это удобная команда запуска, а не отдельное
описание процесса.

Для обычной настройки новой машины с человеком не начинайте с `first-run`.
Сначала проведите пошаговую настройку workplace, затем создайте или
зарегистрируйте ресурсы workplace, и только после этого подключайте проект.
Используйте `first-run` как полностью автоматический shortcut, когда уже
известны workplace path, project root и project type, а ресурсная часть либо
готова, либо явно не входит в область работ.

```bash
python bin/pf.py first-run --workplace ../pf-workplace --project-root ../my-project --type generic-software-project --apply
```

Пути намеренно находятся за пределами каталога дистрибутива: тогда изменяемые
workplace и проект сохранятся при замене или обновлении установки ProcessForge.
У `first-run` нет параметра `--profile`; эта команда не выбирает поставляемый
профиль workplace.

## 1. Создать workplace

Для рабочего профиля разработки ПО укажите `software-development` явно:

```bash
python bin/pf.py workplace-init --workplace ../pf-workplace --profile software-development --apply
python bin/pf.py doctor-workplace --root ../pf-workplace
```

Workplace хранит общие реестры, шаблоны, пакеты знаний и platform contracts.

## 2. Подключить проект

```bash
python bin/pf.py project-onboard --project-root ../my-project --workplace ../pf-workplace --type generic-software-project --apply
python bin/pf.py agent-start-prompt --project-root ../my-project
```

После подключения появятся корневой `AGENTS.md`, состояние `.pf/`, скрытая
проекция `.pf/AGENTS.md` и `.pf/agent-entry.json`. START больше не нужен и не
создаётся; существующие файлы остаются нетронутыми. `agent-start-prompt` только
печатает актуальную подсказку без записи файлов. Старый проект без корневого входа явно использует `.pf/AGENTS.md`.
Обычная работа идёт через `pf.context`, `pf.work.start`, `pf.work.state` и
`pf.work.transition` до `run_completed`, с возвращёнными идентификаторами
Run/assignment/capsule. См. [политику входа](../concepts/agent-entry.md).

## 3. Проверить проект

```bash
cd ../my-project
python .pf/runtime/bin/pf.py doctor-project --project-root .
python .pf/runtime/bin/pf.py project-context-check --project-root .
```

Полный порядок см. в [Порядке инициализации](initialization-order.md): установите
и проверьте ProcessForge, инициализируйте workplace, настройте корневые
каталоги, включая `knowledge_roots.local-docs`, зарегистрируйте инструменты и
MCP servers, создайте или импортируйте пакеты знаний и шаблоны, затем создайте
platform contracts и подключите проекты.

Не начинайте с platform contract, если его обязательные packages, templates или
tools ещё не существуют. Сначала создайте или зарегистрируйте зависимости.
