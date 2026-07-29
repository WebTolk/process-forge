# Workplace Init

Workplace Init создает machine-local слой ProcessForge.

Он отвечает на вопрос:

```text
What is available on this machine and where is it?
```

Workplace layer не является проектом. Он записывает local capabilities, roots,
registries, cache, runtime state, logs и policies, которые проект может
использовать через explicit resolution.

Эти capabilities являются данными, объявленными в workplace, project, package,
platform, tool, MCP, template, specialization или override files. PF core не
устанавливает domain capability catalog во время workplace init и не активирует
example domain resources как defaults.

Создаваемый `registries/project-classifiers.yaml` пуст. Workplace Init не
определяет технологии по именам файлов и не импортирует classifiers из example
packages.

Команды:

```bash
python bin/pf.py workplace-init --workplace <workplace-root> --dry-run
python bin/pf.py workplace-init --workplace <workplace-root> --apply
python bin/pf.py doctor-workplace --root <workplace-root>
```

Для agent-led machine setup используйте `workplace-setup
start/review/apply/status`, чтобы собрать answers и review proposal перед
запуском механики workplace initialization.

Workplace Init создает `AGENTS.md`, `workplace.yaml`, registry files, terms
aliases, bootstrap artifacts и workplace init report под `logs/`.
