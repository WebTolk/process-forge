# Release Src Packaging Audit

## Итог
Причина сбоя высокая по уверенности и статически однозначна: `release-archive-test` распаковывает ZIP и запускает извлечённый `tools/processforge.py`, а этот CLI сразу бутстрэпит `repo_root/src` и делает top-level import `processforge_core`. При этом release pack сейчас не включает `src`, поэтому после распаковки импорт ломается ещё до выполнения самих release-check/smoke-команд.

## Доказательства
- `tools/processforge.py:32-45`:
  - `_bootstrap_repo_src()` добавляет `repo_root / "src"` в `sys.path`.
  - сразу после этого идёт `from processforge_core.process_catalog import ...`.
- `tools/processforge.py:5972-5974`:
  - release surface собирается из `RELEASE_DIRS`, `RELEASE_ROOT_FILES`, `RELEASE_PF_PUBLIC_FILES`.
  - в `RELEASE_DIRS` нет `src`.
- `tools/processforge.py:6063-6085`:
  - `release_source_files()` реально архивирует только root files, public `.pf` files и каталоги из `RELEASE_DIRS`.
  - отдельного special-case для `src/processforge_core` нет.
- `.processforge-releaseignore:1-25`:
  - `src` не исключается правилами ignore.
  - значит проблема не в ignore-паттерне, а в том, что `src` вообще не попадает в набор release sources.
- `tools/processforge.py:7324-7347`:
  - `release-archive-test` делает `extractall(...)`,
  - затем запускает `python <extract_root>/tools/processforge.py release-test --root <extract_root>`.
  - следовательно failure возникает именно на старте извлечённого CLI.
- `src/processforge_core/bootstrap.py:70-76`:
  - packaged runtime seam тоже ожидает `repo_root / "src"` в `sys.path`.
- `tools/smoke_processforge_core_package_bootstrap.py:46-68`:
  - существующий smoke явно грузит `src/processforge_core/bootstrap.py` и проверяет packaged bootstrap seam.
  - это подтверждает контракт: release должен содержать `src/processforge_core/**` в исходном пути `src/...`.

## Наименьшая корректная правка
Минимальная корректная правка release surface: включать в публичный архив `src/processforge_core/**` с сохранением пути `src/...`.

Практически самый маленький change в текущем packer, если не усложнять спец-логикой: добавить `src` в перечисление release sources. По текущему разрешённому дереву `src` содержит только `processforge_core`, так что это совпадает с требуемой поверхностью.

Полезное дополнительное ужесточение, но уже не сама причина: добавить в release checks обязательный путь вида `src/processforge_core/bootstrap.py` или `src/processforge_core`, чтобы omission падал на `release-pack/release-check`, а не только на `release-archive-test`.

## Обязательные регрессионные доказательства
1. ZIP/manifest после сборки содержит `src/processforge_core/__init__.py`, `src/processforge_core/bootstrap.py` и файлы `src/processforge_core/process_catalog/*`.
2. `release-archive-test` проходит на извлечённом архиве минимум в режиме `--extracted-test quick`; предпочтительно также `full`.
3. Отдельно должен быть подтверждён packaged bootstrap seam:
   - либо явным прогоном `tools/smoke_processforge_core_package_bootstrap.py` внутри extracted archive,
   - либо включением этого smoke в `release_test_commands()` и затем прохождением extracted `release-test`.
4. До этого отдельного доказательства coverage остаётся неполным: текущий репозиторный smoke для package bootstrap существует, но статический поиск по `tools/processforge.py` не показывает его регистрации в `release_test_commands()`.

## Статус аудита
Вывод основан на статическом трассировании только разрешённых файлов. Live-прогон архива в рамках этого read-only assignment не выполнялся.
