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
