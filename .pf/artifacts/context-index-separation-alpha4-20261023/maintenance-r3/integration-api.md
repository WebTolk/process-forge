# API для primary

Canonical imports:

```python
from processforge_core.resources.index_backend import (
    ResourceIndexBackend,
    ResourceIndexBackendFactory,
)
from processforge_core.resources.index_maintenance import (
    IndexMaintenanceError,
    WorkplaceIndexMaintenanceService,
)
from pf_cli.commands.search_maintenance import WorkplaceIndexMaintenanceCommand
from pf_cli.parsers.search_maintenance import register_search_index_maintenance
```

Точные сигнатуры:

```python
ResourceIndexBackendFactory = Callable[
    [Path, dict[str, Any], Path], ResourceIndexBackend
]

WorkplaceIndexMaintenanceService(
    workplace_root: Path,
    *,
    distribution_root: Path | None = None,
    backend_factory: ResourceIndexBackendFactory = ResourceSearchIndex,
)

service.run(
    *, reason: str = "manual", verify_files: bool = True
) -> dict[str, Any]

service.run_scoped(
    project_root: Path,
    snapshot: dict[str, Any],
    *,
    operation: Literal["refresh", "rebuild", "tick"],
    verify_files: bool = True,
) -> dict[str, Any]

WorkplaceIndexMaintenanceCommand(
    *,
    maintenance_factory: Callable[
        [Path], WorkplaceIndexMaintenanceService
    ] = WorkplaceIndexMaintenanceService,
)

register_search_index_maintenance(
    add_parser: Callable[..., argparse.ArgumentParser],
    *, execute: Callable[[argparse.Namespace], int],
) -> None
```

Backend Protocol требует только `.refresh()`, `.rebuild()` и `.maintenance_tick(*, verify_files=True)`, все возвращают `dict[str, Any]`. Существующий ResourceSearchIndex удовлетворяет ему структурно; wrapper/fake engine не требуется. Factory вызывается внутри операции с `(project_root, supplied_snapshot, workplace_root)`; construction холодный.

Минимальная явная сборка в Main, только primary:

```python
command = WorkplaceIndexMaintenanceCommand(
    maintenance_factory=lambda workplace: WorkplaceIndexMaintenanceService(
        workplace, distribution_root=ROOT
    )
)
register_search_index_maintenance(sub.add_parser, execute=command.execute)
```

`sub` здесь означает существующий объект top-level subparsers, а не новый container. Registrar принимает его public `add_parser` callback. Команда: `search-index-maintain --workplace <workplace> --apply [--json]`. Missing apply — exit 1 до создания service/I/O; missing workplace — parser exit 2; successful maintenance — 0; busy/degraded/failed/persistence refusal — 1. Никаких новых MCP schemas.

Future cold job вызывает тот же `.run(reason=..., verify_files=...)`. Primary может делегировать бывший Main workplace maintenance helper напрямую этому `.run()` с существующим distribution root. Project refresh/init/repair/query должны только observe, не вызывать owner. `run_scoped` предназначен для уже явных выпущенных project CLI, не для автоматического lifecycle.

У старых `SearchIndexRefreshCommand`, `SearchIndexRebuildCommand`, `SearchIndexTickCommand` параметры constructors не изменены: keyword-only `index_factory` и `snapshot_reader`. Первая factory по-прежнему получает три positional аргумента; snapshot_reader — `(project_root, workplace_root)`. Обновлять их Main callers для этой миграции не требуется.

Derived storage относителен explicit workplace: `runtime/search/local-resource-search.sqlite` остаётся прежним; coordination `runtime/search/maintenance.lock`; state `runtime/search/maintenance-state.json`; running/terminal receipts `runtime/search/maintenance-history/<attempt>-<status>.json`; report `runtime/search/latest-maintenance.yaml`. Lock file не удаляется, PID/возраст не являются основанием разблокировки; OS handle освобождается при закрытии/смерти процесса. После interrupted running нужен authorized workplace `.run()`; project pass не объявляет весь workplace восстановленным.

`.run()` возвращает bounded error row и `report=None`, если обязательная фиксация не удалась или writer занят. Успешный physical pass не считается complete при отказе terminal state write. `.run_scoped()` сохраняет legacy backend result/exception; coordination/persistence failures поднимают `IndexMaintenanceError` с safe `.code`. Construction/Protocol/registration не выдают grants.
