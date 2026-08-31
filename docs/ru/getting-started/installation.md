# Установка

Установите ProcessForge один раз как Python-инструмент: склонируйте repository
или распакуйте release archive.

```bash
git clone <processforge-repo> process-forge
cd process-forge
python -m pip install -r requirements.txt

python bin/pf.py version
python bin/pf.py release-test --root .
```

Из корня дистрибутива используйте `python bin/pf.py`.

Храните изменяемые workplace и projects за пределами заменяемого каталога
дистрибутива. После `cd process-forge` указывайте соседние или другие внешние
пути, например `../pf-workplace` и `../my-project`.

Для production software-development profile сначала явно инициализируйте
workplace, затем подключите project:

```bash
python bin/pf.py workplace-init --workplace ../pf-workplace --profile software-development --apply
python bin/pf.py project-onboard --project-root ../my-project --workplace ../pf-workplace --type generic-software-project --apply
```

Команда `first-run` не принимает `--profile`; когда нужен bundled workplace
profile, используйте двухкомандный flow выше.

После подключения проекта используйте project runtime launcher внутри проекта:

```bash
cd ../my-project
python .pf/runtime/bin/pf.py doctor-project --project-root .
```

Не копируйте весь ProcessForge в `.codex`, `.claude`, `.agents` или похожие
папки конфигурации агентов. Конфигурации агента достаточно короткой инструкции:
где установлен ProcessForge и что project instructions находятся в
`.pf/START_AGENT_HERE.md`.

## Проверка

```bash
python tools/validate-public-cleanliness.py --root .
python tools/validate-process-forge-checksums.py --root . --check
python bin/pf.py release-test --root .
python bin/pf.py release-test --root . --trace-smokes
```

`--trace-smokes` пишет `.pf/runtime/release-test/latest-trace.ndjson` с current
smoke name, elapsed time, timeout budget и timeout reason.

## Требования

Runtime requirements:

- Рекомендуется Python 3.11+.
- Python 3.10+ допустим только если текущие tests подтверждают compatibility.
- Python package dependencies описаны в `requirements.txt`, сейчас это `PyYAML`.
- Нужна UTF-8 capable filesystem.
- Нужен read/write access к ProcessForge distribution, workplace и project folders.
- PowerShell для обычного runtime usage не требуется.
- Default ProcessForge CLI usage не требует daemon или background process.
  Optional PF Runtime lifecycle и Windows autostart описаны в
  [Автозапуск Runtime и запуск Codex MCP](runtime-autostart.md).

## Windows PowerShell UTF-8

PowerShell может неверно отображать русский UTF-8 text, если console encoding не
UTF-8. Файлы остаются UTF-8; это проблема отображения консоли.

```powershell
chcp 65001
$OutputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::InputEncoding = [System.Text.UTF8Encoding]::new()
```

Identifiers и YAML остаются ASCII-safe; docs используют UTF-8.

Development и release-check requirements:

- Python 3.11+.
- Python package dependencies из `requirements.txt`.
- Git для source installation и release checks, например `git diff --check`.
- Возможность запускать subprocesses и создавать temporary directories.
- ZIP support из Python standard library.

Git рекомендуется для установки из исходников и нужен для development/release
checks. Normal runtime usage из release archive не требует Git, если
version-control integration не нужна.
