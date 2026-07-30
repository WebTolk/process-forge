# Установка

Установите ProcessForge один раз как инструмент: склонируйте репозиторий или
распакуйте релизный архив.

```bash
git clone <processforge-repo> process-forge
cd process-forge
python -m pip install -r requirements.txt

python bin/pf.py version
python bin/pf.py release-test --root .
```

Из корня дистрибутива используйте `python bin/pf.py`.

Храните изменяемые workplace и проекты за пределами заменяемого каталога
дистрибутива. После `cd process-forge` указывайте соседние или другие внешние
пути, например `../pf-workplace` и `../my-project`.

Для рабочего профиля разработки ПО сначала явно инициализируйте workplace, а
затем подключите проект:

```bash
python bin/pf.py workplace-init --workplace ../pf-workplace --profile software-development --apply
python bin/pf.py project-onboard --project-root ../my-project --workplace ../pf-workplace --type generic-software-project --apply
```

У команды `first-run` нет параметра `--profile`. Если нужен поставляемый
профиль workplace, используйте две отдельные команды выше.

Внутри подключенного проекта используйте project-local launcher:

```bash
cd ../my-project
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

Требования к среде выполнения:

- Рекомендуется Python 3.11+.
- Python 3.10+ допустим только если текущие тесты подтверждают совместимость.
- Зависимости Python-пакетов описаны в `requirements.txt`, сейчас это `PyYAML`.
- Нужна файловая система с UTF-8.
- Нужен доступ на чтение и запись к дистрибутиву ProcessForge, workplace и
  папкам проекта.
- PowerShell для обычного использования не требуется.
- ProcessForge не требует демона или фонового процесса.

Требования к разработке и проверкам релиза:

- Python 3.11+.
- Зависимости Python-пакетов из `requirements.txt`.
- Git для установки из исходников и проверок релиза, например `git diff --check`.
- Возможность запускать дочерние процессы и создавать временные каталоги.
- Поддержка ZIP из стандартной библиотеки Python.

Git рекомендуется для установки из исходников и нужен для проверок разработки и
релиза. Обычное использование из релизного архива не требует Git, если
пользователь не включает интеграцию с системой контроля версий.
