# Реализация cold job R3

Assignment: `alpha4-revised-schedule-native-contribution-in-1-1-4-implement-only-a-co`.
Stage: `implementation`. Status: `ready_for_review`, stdlib checks пройдены.

Закреплённая последовательность: прочитать собственные assignment/capsule и Python excerpts; реализовать только job и тесты; выполнить stdlib checks в собственной изолированной области; оформить changed-files/change-summary и передать отчёт primary. Lifecycle assignment не меняется исполнителем.

Применены `architecture-r2.md`, `storage-decision-r3.md`, `trigger-policy-r4.md`, `revision-handoff-r3.md`: периодическое выполнение отложено. Старый `IndexMaintenanceSchedule.run_due()` и Runtime loop из R1 не реализуются.

API: `processforge_core.resources.index_schedule.IndexMaintenanceJob(workplace_root: Path, *, distribution_root: Path | None = None, maintenance_service: _MaintenanceService | None = None).execute() -> dict[str, Any]`. Узкий private Protocol требует только `run(*, reason: str, verify_files: bool) -> dict[str, Any]`.

Default composition импортирует `processforge_core.resources.index_maintenance.WorkplaceIndexMaintenanceService` только внутри `execute()` и создаёт service для каждого явного вызова. Передаются исходные Path и distribution_root, без resolve/IO/глобального current context. Вызов один: `run(reason="scheduler", verify_files=True)`. Результат, включая unknown fields/отказы, и исключения передаются без копии, печати или изменения. Индексация, блокировки, durable state, recovery и retry policy принадлежат каноническому service.

Архитектурное соответствие: D01/D02 — один application owner; D03 — холодные import/construction; D04 — явная небольшая композиция и constructor injection; D05 — operation-local default service, отсутствие захвата Work/grants; D06/R01–R06 — новые разрешения и project routing не добавляются; D07/R07/R11 — ошибки не маскируются, собственной persistence/retry нет; D09 — обычный Python module/Protocol; D11/R03/R10 — immutable входы и ownership сохранены; R08/R09 — transport/host/Ledger не затрагиваются; R12 — нет вывода exception details/private roots. D08/D10 не изменены.

Проверки: Python 3.14.3, `python -B -S .pf/tmp/context-index-alpha4-schedule-r3-20261023/run_stdlib_checks.py`; 10 unittest checks без failures/errors/skips, AST parsing и compile в памяти обоих файлов. `-B` исключает bytecode writes, `-S` исключает site initialization. Все тестовые корни — символические Path собственной scratch-области; реальные registry/source documents не читаются.

При первом анализе `index_maintenance.py` отсутствовал, затем появился в checkout. Прочитаны его dataclass constructor fields и `run`; фактическая сигнатура соответствует frozen API. Отдельный тест импортирует и создаёт настоящий `WorkplaceIndexMaintenanceService`, подменяя только `run` autospec mock: проверены переданные корни/kwargs и результат, тело обслуживания не выполняется. Остальные default-boundary тесты подменяют canonical module, а injected tests используют узкий fake. Это не проверка настоящей индексации, блокировок или durable recovery. Полная default integration, registered QA и независимое review остаются за primary. Scratch runner сохранён как воспроизводимое evidence.
