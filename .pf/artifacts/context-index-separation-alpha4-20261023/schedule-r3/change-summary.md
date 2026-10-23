# Change summary — schedule R3

Status: `ready_for_review`.

Создан `processforge_core.resources.index_schedule.IndexMaintenanceJob` с API `IndexMaintenanceJob(workplace_root: Path, *, distribution_root: Path | None = None, maintenance_service: _MaintenanceService | None = None).execute() -> dict[str, Any]`.

Import/construction холодные: корни только сохраняются. Каждый явный `execute()` использует borrowed injected service либо лениво создаёт настоящий `processforge_core.resources.index_maintenance.WorkplaceIndexMaintenanceService(workplace_root, distribution_root=...)`. Вызывается ровно `run(reason="scheduler", verify_files=True)`, канонический результат возвращается без копирования/изменения, исключения распространяются без логирования текста и маскировки. Falsey injected service также сохраняется. Default service создаётся на операцию; job не удерживает Work/grants или предыдущий результат.

R2/R3/R4 и revision-handoff-r3 соблюдены. Фактический планировщик, периоды, циклы, потоки, timer/autostart и Runtime integration не реализованы. Индексация, engine/backend, persistence, serialization, lock/retry/recovery policy не дублируются. Зависимости не добавлены.

Локальная проверка: Python 3.14.3, `python -B -S .pf/tmp/context-index-alpha4-schedule-r3-20261023/run_stdlib_checks.py`, exit 0; 10 tests, failures/errors/skips = 0; AST parse и compile в памяти обоих Python-файлов. Проверены cold import/construction, точные roots/kwargs, сохранение opaque success/failure payloads, exception identity/cancellation без rendering/retry, явный повтор и отсутствие lifetime result/service cache. Проверка реальной default composition создаёт настоящий service с подменённым autospec `run`; его рабочее тело не запускается. Hashes и фактическое время проверки — `stdlib-checks.json`.

Handoff primary: выполнить зарегистрированные pytest/Ruff lint+format/mypy и требуемое независимое review, затем полную интеграционную проверку общего компонента в разрешённых fixtures. Проверка настоящей индексации/сериализации/recovery, archive/installed/connected-host proof, доставка и PF lifecycle остаются вне этого file-only вклада.
