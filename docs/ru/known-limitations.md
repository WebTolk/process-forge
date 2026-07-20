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

## Requirements boundary

- Для runtime рекомендуется Python 3.11+.
- Python 3.10+ допустим только когда текущие тесты подтверждают совместимость.
- PowerShell для runtime не нужен.
- Runtime usage из release archive не требует Git, если не нужна version-control integration.
- Development и release checks требуют Python 3.11+, Git, subprocess execution, temporary directories и ZIP support из стандартной библиотеки Python.
