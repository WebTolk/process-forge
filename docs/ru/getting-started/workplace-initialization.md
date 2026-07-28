# Инициализация workplace

Workplace — машинный слой ProcessForge. Он хранит общие ресурсы, которые могут
использовать разные проекты: templates, knowledge packages, platform contracts
и registries.

Создайте workplace из distribution root:

```bash
python bin/pf.py workplace-init --workplace ../pf-workplace --apply
python bin/pf.py doctor-workplace --root ../pf-workplace
```

Не создавайте `.pf/` внутри проекта на этом шаге. Проект подключается отдельно
через `project-onboard`.

После инициализации сохраните путь к workplace в инструкции для агентов или в
локальной документации команды.

## Coordination mode

Workplace хранит capability, а не обязательный режим всех проектов:

```yaml
coordination:
  director_enabled: true
  director_office_enabled: true
  default_project_mode: simple
```

Даже если Director capability включена, отдельный проект может оставаться
`simple`. Для смешанной работы обычно удобно держать
`default_project_mode: simple`, а сложные проекты переводить в `organized`
локально.

```bash
python bin/pf.py workplace-mode status --workplace ../pf-workplace
python bin/pf.py workplace-mode set --workplace ../pf-workplace --director-enabled true --director-office-enabled true
python bin/pf.py workplace-mode set-default-project-mode --workplace ../pf-workplace --mode simple
python bin/pf.py workplace-mode doctor --workplace ../pf-workplace
```
