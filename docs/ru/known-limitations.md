# Ограничения

ProcessForge сейчас работает как файловый инструмент.

Текущие ограничения:

- нет GUI;
- нет marketplace;
- нет remote sync;
- нет database-backed control plane;
- long-running watcher/runner не обязателен и не входит в основной runtime;
- resource parity для templates, knowledge packages и platform contracts пока
  поверхностный и сообщает WARN;
- agent prompts помогают стартовать работу, но не заменяют project-specific
  review и `doctor-project`.

Для обычного linked-проекта используйте:

```bash
python .pf/runtime/bin/pf.py doctor-project --project-root .
```

Для distribution root используйте:

```bash
python bin/pf.py release-test --root .
```
