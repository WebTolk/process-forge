# Явные пути required outputs

Дата: 2026-08-21

В трёх заданиях текущего run, созданных до строгой валидации, добавлены явные
repository-relative `path` для каждого required output. Также `task-create`
теперь отклоняет `--required-output` без пути и сообщает формат
`id=<id>,path=<repository-relative-path>`.

Проверка: `python tools/validate-process-forge-schemas.py --root .` — PASS.
