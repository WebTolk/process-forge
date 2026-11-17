# Manifest обновления ядра

Обновления ядра ProcessForge используют явный ownership manifest:

```text
processforge-core.manifest.json
```

Release archive содержит manifest новой версии. Установленный core root хранит текущий manifest в корне distribution directory. Manifest задаёт границу PF-owned файлов.

## Контракт manifest

Минимальные поля:

- `schema_version: 1`
- `kind: processforge.core_manifest`
- `version`
- `generated_at`
- `source`
- `files[]`
  - `relative_path`
  - `size`
  - `sha256`

Пути должны быть относительными к core root. Absolute paths, backslashes, пустые сегменты, `.`, `..` и выход за core root отклоняются.

`runtime/`, workplace data, project `.pf` data, caches, SQLite indexes и update journals являются derived/local state и не должны моделироваться как core-owned payload files.

## Flow обновления

CLI:

```bash
python bin/pf.py core-update status --core-root <core>
python bin/pf.py core-update plan --core-root <core> --archive <processforge.zip>
python bin/pf.py core-update apply --core-root <core> --archive <processforge.zip> --confirm
python bin/pf.py core-update repair --core-root <core>
```

`plan` работает read-only. `apply` требует `--confirm`.

Публичная 1.2.0 включала три Core-owned startup template в собственной .pf/:
AGENTS.md, hooks.yaml и process-forge.yaml. Внешний file updater сохраняет их
реальные preimages либо отсутствие перед удалением old-only paths. Исключение
действует только для установленного manifest точной версии 1.2.0; новые архивы
по-прежнему исключают private .pf data. Замена Core не даёт authority для миграции
проекта. См. [границы проверки public upgrade](../audits/issue-19-public-upgrade.md).

## Совместимая миграция Workplace

Архив может содержать декларативную миграцию Workplace в `updates/migrations/`.
Чтобы включить её в обновление существующего рабочего места, передайте его
корень при планировании и применении:

```bash
python bin/pf.py core-update plan --core-root <core> --archive <processforge.zip> --workplace-root <workplace>
python bin/pf.py core-update apply --core-root <core> --archive <processforge.zip> --workplace-root <workplace> --confirm
```

План включает только операции, объявленные в архиве. Применение выполняется
последовательно: сначала заменяются файлы Core и записывается manifest Core,
затем выполняется совместимая миграция Workplace. Изменения проектной `.pf`
оцениваются и применяются позднее, в отдельной работе каждого проекта.
Независимые параллельные применения Core или Workplace не поддерживаются.

Миграция 1.0.2 → 1.1.0
добавляет встроенный драйвер `codex-exec` и запись в его реестре только при
их отсутствии. Существующие файлы и записи сохраняются. Команда
`workplace-init` предназначена для первичной инициализации и не вызывается
при обновлении.

Перед записью updater сохраняет затронутые файлы Workplace в каталоге резервных
копий обновления Core и регистрирует операцию в журнале. Если миграция
Workplace после обновления Core не завершилась, Core остаётся на новом manifest,
а `core-update repair` показывает состояние, требующее ручного решения, и путь
к резервным копиям. После успешного apply с `--workplace-root` автоматически
выполняется короткая проверка `doctor-workplace`; её результат записывается в
`<core>/runtime/core-update/last-apply.json`.

Updater вычисляет:

```text
removed = old_manifest.files - new_manifest.files
added   = new_manifest.files - old_manifest.files
changed = common paths with different sha256
```

Удаляются только paths, которые были в старом manifest и отсутствуют в новом manifest. Unknown files сохраняются. Directories удаляются только когда становятся пустыми.

PF отвечает за принадлежащие релизу файлы Core. Подтверждённое обновление должно
привести все такие файлы к байтам проверенного целевого релиза, заменяя локальные
правки Core даже тогда, когда официальные байты между релизами не изменились.
Поэтому различия manifest выше не ограничивают набор файлов Core для замены.

Существующие публичные флаги продолжают приниматься. Force не требуется только
из-за локальных правок Core и не обходит проверки полномочий, владения, выбора,
путей, коллизий и безопасности. Неизвестные файлы вне владения PF, конфигурация,
данные проектов и Workplace, состояние runtime сохраняют прежние правила
обработки. Эта политика замены не разрешает удалять пользовательские данные.

Новый installed manifest записывается последним, после успешных file changes.

## Recovery

Apply пишет runtime update state в:

```text
<core>/runtime/core-update/
```

До замены или удаления старых PF-owned файлов существующий recovery backup
сохраняет их фактические байты до обновления, включая локальные правки, и
фиксирует отсутствие недостающих файлов. Если update прерван или файловая
операция завершилась ошибкой, `core-update status` показывает `incomplete_update`,
а `core-update repair` возвращает состояние для оператора.

File operation failures, включая locked-file style ошибки от ОС, возвращаются как явный `file_operation_failed` и оставляют `runtime/core-update/in-progress.json` со `status: failed`.

Incomplete update journal записывает:

- `installed_version`
- `target_version`
- `archive`
- `backup_dir`
- `counts`
- `completed_operations`
- `pending_operations`
- `backed_up`
- `error`

`core-update repair` классифицирует incomplete states:

- `safe_to_rollback`, если update упал до записи manifest и backup старого manifest существует;
- `manual_repair_required`, если manifest уже записан, journal неполный или безопасность нельзя доказать;
- `nothing_to_repair`, если incomplete update отсутствует.

По умолчанию repair и Python API `repair_status` остаются read-only.
Одна классификация не разрешает восстановление. Новый file-only apply до первой
мутации payload закрепляет SHA256 исходного архива, old/new manifests и плана,
хеши и длины фактических preimages, а также исходное отсутствие added paths.

Для failed/interrupted **before-manifest file-only** update, созданного этим
updater, остановите выбранный Workplace App Server, устраните файловый сбой и
запустите тот же внешний sealed installer с исходным архивом:

```sh
python installer/bin/pf.py core-update repair --core-root CORE --resume --archive ORIGINAL.zip --workplace-root WORKPLACE --confirm
```

Повторите исходный явный выбор Workplace; пропускайте его только если исходный
apply также его пропустил. Без confirmation recovery не изменяет файлы.
Сохраняются cooperating file mutex, unmanaged target, nonoverlap и offline guards.
Проверяются identity Core/Workplace, все закреплённые control/backup bytes и
затронутые файлы: допустимы только доказанное исходное либо точное целевое
состояние. Прерывание после atomic replacement, но до публикации journal,
обрабатывается идемпотентно по bytes; progress counters разрешением не служат.

Recovery продолжает исходный план, не обходя incomplete-update blocker новым
планированием. Сохраняются исходные backups, update identity и failure history;
перед каждой допущенной попыткой удерживается точный предыдущий journal.
Все target-owned bytes проверяются, manifest публикуется последним. Повторный
сбой сохраняет incomplete journal и evidence. Unknown files остаются нетронутыми.

Старые журналы без versioned proof, неполные/повреждённые backups, drift, чужой
архив или binding, native/partial enrollment и любые after-manifest состояния
отказывают. Обычный apply по-прежнему отказывает при incomplete update. Команда
не выполняет rollback файлов, native adoption, переключение SQL binding или
downgrade Core после SQL commits: для них нужен собственный supported maintenance.

## Граница квалификации original-manager bridge

Исходный Windows bridge ограничен настоящей публичной 1.2.0, которая находилась
под первоначальным доверенным launcher до первого writer. Core service
`OriginalManagerUpdateService` строит план; native adapter сохраняет исходные
gate, sentinel и полный набор Jobs. Конечный issuer-bound profile закрепляет
неизменённые ZIP/sidecar, физические roots, защищённое runtime closure, environment
и точные argv всех шести классов ingress. Публичного флага для утверждения либо
восстановления этого profile нет. Сам по себе hash не создаёт authority.

Фиксированный маршрут manager вызывает существующие plan/apply/confirmed repair
из отдельной accepted current installation. Используются штатный owned-file delta,
фактические preimages и absence facts. Пересечение действующей конфигурации или
данных с Core отклоняется. Только три точных historical entry templates 1.2.0
допускаются к backup/removal; новый payload не получает private ownership.
File-only update продолжает отказывать при любом полном или частичном managed marker.

До copy manager публикует постоянный replacement intent. Native adapter сохраняет
owned preimages, заменяет файлы атомарно и публикует manifest последним. Затем
используется существующий handoff legacy-manager → pending/guard/epoch/bound/head.
Свежий child захватывает новую accepted publication под собственным lease,
вызывает storage coordinator и проверяет реальный SQL execution repository.
Старый parent после overwrite не импортирует Core и не изменяет storage.

Recovery требует точных operation/archive/selection/preimages, физических bindings
и журнала в том же живом manager. Если публикация intent/control files прервалась
до первого журнала, manager повторно проверяет исходные bytes и продолжает только
свои control files и созданный им физический backup directory. Чужие либо
изменённые control bytes и подмена directory отклоняются. Receipt не восстанавливает
утраченные handles. Потеря manager до bound, uncertain child outcome, подмена
root/guard, повреждённый backup или чужой selection запрещают автоматический replay.
Сохраните историю и backups. После SQL commits используется поддерживаемое
forward recovery; bridge не разрешает downgrade.

Это граница реализации и проверки, а не подтверждённый полный public upgrade.
Положительные public-archive migration/worker, реальный copy failure/recovery,
независимый review и применимая OS qualification остаются обязательными.
Новый manager не квалифицирует неизвестную историю установки. Этот Windows slice
не добавляет Linux controller или historical cold route.
