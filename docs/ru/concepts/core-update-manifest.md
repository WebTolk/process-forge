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

### Остановка, обновление, проверка и запуск

В Garage человек останавливает PF и остальных писателей перед заменой файлов.
В Forge единственным исполнителем PF и его остановкой, обновлением и запуском
управляет updater. Файловая операция требует остановленной установки; она не
обнаруживает и не исключает все исторические процессы. Известный работающий
App Server выбранного Workplace блокирует apply.

Распакуйте проверенный релиз вне установленного Core. Запускайте из него
`bin/pf.py core-update plan|apply`, явно указывая установленный Core, исходный ZIP
и обслуживаемый Workplace. Для его сервера используется существующая команда
`server stop --workplace <workplace>`; до замены убедитесь в успешной остановке.

Сохраняются backups, журнал операции, частные данные и запись manifest после
проверки файлов. Корни installer и target не должны пересекаться. Исторические
маркеры native enrollment сохраняются, но не требуются и не служат допуском.
Файловый mutex исключает одновременные операции updater, а не произвольные
независимые процессы.

Старый installed manifest может владеть startup templates
`.pf/AGENTS.md`, `.pf/hooks.yaml` и `.pf/process-forge.yaml`.
Перед удалением old-only paths updater сохраняет реальные preimages либо
отсутствие. Это правило совместимости опирается на владение в manifest,
а не номер продукта. Новый архив не может объявлять private `.pf` data.

Замена Core не мигрирует журналы проектов. Старые проекты остаются
заблокированы до явной [миграции журналов](sqlite-journal-maintenance.md);
новые сразу используют SQL. После apply выполните
`doctor-workplace --root <workplace>` перед запуском нужного PF.
См. [проверку public upgrade](../audits/issue-19-public-upgrade.md).

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
к резервным копиям. После успешного apply явно выполните
`doctor-workplace --root <workplace>`; updater не запускает другой Core
для автоматической maintenance.

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
Сохраняются cooperating file mutex, проверки physical target, nonoverlap и offline.
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
архив или binding и любые after-manifest состояния
отказывают. Обычный apply по-прежнему отказывает при incomplete update. Команда
не выполняет rollback файлов, переключение SQL binding или
downgrade Core после SQL commits: для них нужен собственный supported maintenance.
