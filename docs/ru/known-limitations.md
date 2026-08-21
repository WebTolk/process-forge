# Ограничения

ProcessForge сейчас работает как файловый инструмент.

Текущие ограничения:

- нет GUI;
- нет marketplace;
- нет remote sync;
- нет database-backed control plane;
- long-running watcher/runner не обязателен и не входит в основную среду выполнения;
- resource parity для templates, knowledge packages и platform contracts пока
  поверхностный и сообщает WARN;
- агентские промпты помогают стартовать работу, но не заменяют проектную
  проверку и `doctor-project`.
- регистрация Codex hooks принадлежит окружению: shipped adapter не доказывает,
  что все hooks реально зарегистрированы;
- automatic capture ограничен attributed `UserPromptSubmit` и PF-owned
  worker records; generic assistant/subagent responses пока не захватываются;
- session replay восстанавливает только поддержанные normalized derived events,
  а не полный transcript;
- raw ingress отклоняет payload больше 1 048 576 байт: blob spill и receipt
  для oversized payload пока отсутствуют;
- file-per-event raw indexes и сканирование shards при recovery требуют
  отдельного решения о масштабировании после измерения нагрузки.

Для обычного подключённого проекта используйте:

```bash
python .pf/runtime/bin/pf.py doctor-project --project-root .
```

Для корня дистрибутива используйте:

```bash
python bin/pf.py release-test --root .
```

## Граница требований

- Для среды выполнения рекомендуется Python 3.11+.
- Python 3.10+ допустим только когда текущие тесты подтверждают совместимость.
- PowerShell для обычного использования не нужен.
- Использование из релизного архива не требует Git, если не нужна интеграция с
  системой контроля версий.
- Проверки разработки и релиза требуют Python 3.11+, Git, запуска дочерних
  процессов, временных каталогов и поддержки ZIP из стандартной библиотеки
  Python.
