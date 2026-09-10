# Рабочий сценарий task batch

Используйте task batch execution, когда одна рабочая сессия содержит несколько
связанных задач и каждой задаче может понадобиться несколько циклов
work/debug/fix. Для обычного управляемого цикла работы предпочитайте
[Garage Core (EN)](../../concepts/garage-core.md) и
[Declarative process execution](../concepts/declarative-process-execution.md);
нижеприведённый CLI нужен как совместимый сценарий явного управления run/task.

Предусловие: оператор уже активировал официальные пакеты
`processforge.official.software-development` и `processforge.official.verification`
в Workplace. Пример использует их процессы `software-feature-development` и
`testing` соответственно. Проверьте их наличие
через `process-list`; если они недоступны, сначала запросите настройку у
оператора. Обычная проектная работа не должна неявно активировать пакеты для
устранения такого отказа.

Создайте run:

```bash
python .pf/runtime/bin/pf.py run-create --project-root . --id release-prep --title "Release preparation" --process task-batch-execution --apply
```

Создайте задачи:

```bash
python .pf/runtime/bin/pf.py task-create --project-root . --run release-prep --id task-001-docs --title "Update docs" --process software-feature-development --apply
python .pf/runtime/bin/pf.py task-create --project-root . --run release-prep --id task-002-tests --title "Run tests" --process testing --apply
```

Зафиксируйте итерации:

```bash
python .pf/runtime/bin/pf.py iteration-add --project-root . --task task-001-docs --kind work --summary "Updated run docs." --apply
python .pf/runtime/bin/pf.py iteration-add --project-root . --task task-001-docs --kind debug --status passed --summary "Docs links checked." --apply
python .pf/runtime/bin/pf.py iteration-add --project-root . --task task-002-tests --kind work --summary "Ran the test batch." --apply
python .pf/runtime/bin/pf.py iteration-add --project-root . --task task-002-tests --kind debug --status passed --summary "Tests and logs reviewed." --apply
```

Завершите задачи и только затем run:

```bash
python .pf/runtime/bin/pf.py task-complete --project-root . --task task-001-docs --summary "Docs updated and checked." --apply
python .pf/runtime/bin/pf.py task-complete --project-root . --task task-002-tests --summary "Tests completed and reviewed." --apply
python .pf/runtime/bin/pf.py run-summary --project-root . --run release-prep --apply
python .pf/runtime/bin/pf.py run-doctor --project-root . --run release-prep
python .pf/runtime/bin/pf.py run-complete --project-root . --run release-prep --apply
```

`run-complete` отклоняется, пока открыта хотя бы одна блокирующая задача, так
что все blocking tasks нужно закрыть до завершения run.

Внутри подключённого проекта предпочитайте связанный runtime launcher:

```bash
python .pf/runtime/bin/pf.py run-status --project-root . --run release-prep
```
