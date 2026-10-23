RESULT: реализация разрешённой области готова к интеграции primary. Независимое review и зарегистрированные QA остаются обязательными.

Assignment: `alpha4-revised-maintenance-native-contribution-in-1-1-4-implement-the-si`, attempt 1. READ_ACK выполнен до реализации; checksum собственной capsule совпал с prepared input. Прочитаны frozen R2/R3/R4, revision-handoff-r3 и фактические Python excerpts/provenance. Анализ существующих owners выполнен через Serena.

Изменены:

- `src/processforge_core/resources/index_backend.py`
- `src/processforge_core/resources/index_maintenance.py`
- `tools/pf_cli/commands/search_index.py`
- `tools/pf_cli/commands/search_maintenance.py`
- `tools/pf_cli/parsers/search_maintenance.py`
- `tests/context_index_separation/test_backend.py`
- `tests/context_index_separation/test_maintenance.py`

Общий owner переиспользует существующий SQLite `ResourceSearchIndex`. `ResourceIndexBackend` — фактически используемый structural Protocol с методами `refresh()`, `rebuild()` и `maintenance_tick(*, verify_files=True)`. Второй engine/DAL не добавлен.

Точные API:

```python
WorkplaceIndexMaintenanceService(
    workplace_root: Path,
    *,
    distribution_root: Path | None = None,
    backend_factory: ResourceIndexBackendFactory = ResourceSearchIndex,
)

service.run(*, reason="manual", verify_files=True) -> dict[str, Any]

service.run_scoped(
    project_root,
    snapshot,
    *,
    operation: Literal["refresh", "rebuild", "tick"],
    verify_files=True,
) -> dict[str, Any]
```

Factory получает `(project_root, snapshot, workplace_root)`. `.run()` возвращает прежнюю schema1 `pf.search_index.maintenance` со `scope="workplace"`, `project_count=0`, `results` и относительным `report`.

Refresh/rebuild/tick CLI теперь вызывают `.run_scoped()`. Их constructor parameters, freshness guards, verification flags, backend payload/exception и stdout/exit mapping сохранены. Scoped-операция не читает workplace catalogue и отклоняет workplace snapshot.

Все операции используют общий nonblocking OS-lock. До backend фиксируется `running`; required report предшествует `complete`. JSON state и отдельные running/terminal receipts публикуются через fsync/atomic replace. Завершение процесса освобождает lock; следующий authorized workplace pass повторяет обслуживание. Project pass не снимает незавершённое workplace-состояние. Новые диагностики исключают raw exceptions и private roots.

Для Main integration:

```python
command = WorkplaceIndexMaintenanceCommand(
    maintenance_factory=lambda workplace: WorkplaceIndexMaintenanceService(
        workplace, distribution_root=ROOT
    )
)
register_search_index_maintenance(sub.add_parser, execute=command.execute)
```

Импорты adapters: `pf_cli.commands.search_maintenance` и `pf_cli.parsers.search_maintenance`. Команда: `search-index-maintain --workplace <workplace> --apply [--json]`. Без apply — exit 1 без создания service; без workplace — parser exit 2; успех — 0; отказ/failure — 1. Подключение регистратора и Main delegation принадлежат primary.

Фактическая проверка:

```text
python -B .pf/tmp/context-index-alpha4-maintenance-r3-20261023/run-stdlib.py
exit 0
24 unittest; 0 failures; 0 errors
AST/compile: 7 Python-файлов
Python 3.14.3; SQLite 3.50.4
```

Проверены реальные SQLite fixtures, snapshot isolation, alternate backend, cold construction, обновление каталога, legacy CLI parity, required write failures, atomic replacement failure, безопасные диагностики, внутрипроцессная и межпроцессная блокировка, kill/retry. Исправлена выявленная регрессия generator-context-manager с frozen `LocalSearchError`; исходное исключение сохраняется.

Evidence и SHA256 текущих bytes: `.pf/artifacts/context-index-separation-alpha4-20261023/maintenance-r3/stdlib-checks.json`; вывод — `stdlib-output.txt`. Рядом находятся `changed-files.md`, `change-summary.md`, `integration-api.md` и `trigger-map.md`.

Это source/fixture evidence. POSIX branch, registered pytest/Ruff/format/mypy и дополнительная QA, archive/installed/connected acceptance не проверялись. Existing engine по-прежнему удаляет derived DB при rebuild и пропускает некоторые ошибки чтения файлов. Компонент отображает возвращённые/raised failures; полнота чтения каждого файла не доказана и требует решения primary/reviewer. Main, Runtime, lifecycle, Git, installs, внешние workplace roots, live indexing и subagents не затрагивались.

Автоматическая проверка отклонила очистку начальных scratch fixtures с причиной «blocked by policy». Удаление не выполнено; каталоги оставлены как evidence.