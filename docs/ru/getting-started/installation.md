# Установка

Установите ProcessForge один раз как инструмент: склонируйте репозиторий или
распакуйте release archive.

```bash
git clone <processforge-repo> process-forge
cd process-forge

python bin/pf.py version
python bin/pf.py release-test --root .
```

Из distribution root используйте `python bin/pf.py`.

Внутри подключенного проекта используйте runtime launcher проекта:

```bash
python .pf/runtime/bin/pf.py doctor-project --project-root .
```

Не копируйте весь ProcessForge в `.codex`, `.claude`, `.agents` или похожие
папки конфигурации агентов. В конфигурации агента достаточно короткой
инструкции: где установлен ProcessForge и что проектные инструкции находятся в
`.pf/START_AGENT_HERE.md`.

## Проверка

```bash
python tools/validate-public-cleanliness.py --root .
python tools/validate-process-forge-checksums.py --root . --check
python bin/pf.py release-test --root .
```

## Требования

Runtime requirements:

- Рекомендуется Python 3.11+.
- Python 3.10+ допустим только если текущие тесты подтверждают совместимость.
- Нужна файловая система с UTF-8.
- Нужен read/write access к ProcessForge distribution, workplace и папкам проекта.
- PowerShell для runtime не требуется.
- ProcessForge v0.1 не требует daemon или фонового процесса.

Development / release-check requirements:

- Python 3.11+.
- Git для установки из исходников и release checks, например `git diff --check`.
- Возможность запускать subprocesses и создавать temporary directories.
- ZIP support из стандартной библиотеки Python.

Git recommended для установки из source и required для development/release checks. Обычное runtime usage из release archive не требует Git, если пользователь не включает version-control integration.
