# Первый запуск

Сначала выполните [установку](installation.md) и
[предварительную проверку требований](../requirements.md). Команды ниже и
проектный launcher должны использовать одно Python-окружение. Для обычной
работы Garage не нужны Runtime, MCP, хуки или ручная сессия Agent Ledger.

Первый запуск состоит из двух отдельных процессов:

- `workplace-initialization` готовит рабочее место, реестры и общие ресурсы.
- `project-onboarding` подключает выбранный проект к готовому workplace.

Если новую машину настраивают вместе с человеком, начните с
[пошаговой настройки workplace](guided-workplace-setup.md): агент соберёт
ответы, подготовит предложение, затем применит согласованные настройки.
Общие ресурсы должны быть подготовлены до подключения проекта.

## Автоматический сокращённый путь

`first-run` выполняет инициализацию workplace и подключение проекта по очереди.
Используйте его, когда уже известны пути и тип проекта, а настройка ресурсов
завершена или явно не входит в задачу. Это команда удобства, а не третий процесс:

```bash
python bin/pf.py first-run --workplace ../pf-workplace --project-root ../my-project --type generic-software-project --apply
```

Workplace и проект намеренно находятся вне заменяемого дистрибутива. Команда
`first-run` не принимает `--profile`. Для встроенного профиля разработки ПО
используйте два отдельных шага ниже.

## Создайте workplace

Из корня дистрибутива, с нужными путями и подготовленными ответами:

```bash
python bin/pf.py workplace-init --workplace ../pf-workplace --profile software-development --apply
python bin/pf.py doctor-workplace --root ../pf-workplace
```

Подготовьте нужные пакеты знаний, шаблоны, инструменты и контракты платформ.
Не создавайте контракт платформы, если его обязательные зависимости отсутствуют.

## Подключите проект

```bash
python bin/pf.py project-onboard --project-root ../my-project --workplace ../pf-workplace --type generic-software-project --apply
python bin/pf.py agent-start-prompt --project-root ../my-project
```

Создаются корневой `AGENTS.md`, скрытая `.pf/` с `.pf/AGENTS.md` и
`.pf/agent-entry.json`, а также связь с workplace. START больше не нужен и не
создаётся; существующие файлы сохраняются. `agent-start-prompt` только печатает
актуальную подсказку без записи. В старом проекте без корневого файла явно
используется `.pf/AGENTS.md`. См. [политику входа](../concepts/agent-entry.md).

Обычная работа проходит через `pf.context`, `pf.work.start`, `pf.work.state`
и `pf.work.transition` до `run_completed`. Используйте возвращённые
идентификаторы Run, assignment и context capsule. Если требуется выбор
процесса (`process_choice_required`), выбирайте только из предложенных вариантов.

## Проверьте подключение

```bash
cd ../my-project
python .pf/runtime/bin/pf.py doctor-project --project-root .
python .pf/runtime/bin/pf.py project-context-check --project-root .
```

Из обычного проекта не вызывайте `python bin/pf.py`. Используйте проектный
launcher и тот же интерпретатор Python, в котором установлен PyYAML.
Полный порядок описан в [инициализации](initialization-order.md).
