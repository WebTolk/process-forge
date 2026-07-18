# Инициализация Workplace

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
