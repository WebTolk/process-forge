# Чтение контекста без изменения файлов проекта

`context-resolve` читает контекст. Без селекторов ресурсов команда возвращает
существующий canonical project snapshot и текущую проверку его актуальности
и готовности:

```sh
python bin/pf.py context-resolve --project-root <project-root> --json
```

Вывод — один JSON-объект с полями `snapshot` и `check`. Без `--json` тот же
объект печатается в YAML. Canonical reader сохраняет неизвестные поля snapshot.
Проверка использует текущую политику и проверки ресурсов из
`project-context-check`; чтение не запускает refresh или обслуживание индекса.

Для отсутствующего или повреждённого snapshot возвращаются `snapshot: {}`
и существующий broken check, включая `recommended_action`. Код возврата — 1
при broken-контексте или блокирующей политике, иначе 0. Устаревший snapshot
остаётся устаревшим до явного refresh. Отсутствующий корень проекта или PF
manifest вызывает прежнюю CLI-ошибку.

`--platform`, `--process` или `--specialization` выбирает существующую ветку
разрешения ресурсов с прежним объектом `resolved_context`. Код возврата — 1,
если список `conflicts` непуст, иначе 0. Один `--workplace` сохраняет ветку
snapshot/check и передаёт явный workplace штатной проверке.

## Явная запись и старые скрипты

Обновляйте современный project snapshot отдельной командой:

```sh
python bin/pf.py project-context-refresh --project-root <project-root>
python bin/pf.py project-context-check --project-root <project-root> --json
```

Для новой современной assignment capsule используйте `assignment-capsule`.
Существующие capsules сохраняют закреплённые входы. `context-compile` остаётся
явной legacy writer-командой с прежними предпосылками, включая наличие legacy
context index; исправление не переводит её на современную snapshot-модель.

Раньше `context-resolve` без селекторов безусловно перезаписывал
`context-index.yaml`, `resolved-rules.yaml`, `context-conflict-report.md` и
приватный `context-cache.yaml`, игнорируя `--json`. Это поведение исправлено.
Скрипты, полагавшиеся на такие побочные эффекты, должны перейти на явные
современные snapshot/capsule workflows; неявной генерации legacy-файлов больше
нет. Существующая библиотечная writer-функция `write_context_outputs` не изменена.
