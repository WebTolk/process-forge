"""Thin JSON CLI adapter for the single shared accounting application service."""

from __future__ import annotations

import argparse
import json
import os
from collections.abc import Callable
from pathlib import Path

from processforge_core.accounting.binding import CollectionBinding, timestamp
from processforge_core.accounting.collectors import ProviderCollector, import_timing
from processforge_core.accounting.composition import WorkplaceAccounting, read_json
from processforge_core.accounting.model import QueryFilter
from processforge_core.accounting.storage import (
    AccountingStorageError,
    RevisionConflict,
)


class UsageCommand:
    """Adapt explicit CLI scope; private errors and references never enter DTOs."""

    def __init__(
        self,
        *,
        discover: Callable[..., WorkplaceAccounting] = WorkplaceAccounting.discover,
    ) -> None:
        self._discover = discover

    def execute(self, args: argparse.Namespace) -> int:
        """Run one query/import using the selected existing workplace."""
        try:
            project_root = Path(args.project_root).expanduser().resolve()
            managed = any(
                os.environ.get(name)
                for name in (
                    "PF_PREPARED_INPUT_FILE",
                    "PF_AGENT_RUN_DIR",
                    "PF_TASK_ID",
                    "PF_WORKER_TASK_ID",
                )
            )
            if managed:
                bound_project = os.environ.get("PF_PROJECT_ROOT")
                if not bound_project or Path(bound_project).resolve() != project_root:
                    raise PermissionError("managed_project_scope_mismatch")
            workplace = Path(args.workplace).expanduser() if args.workplace else None
            composition = self._discover(project_root, workplace)
            if managed and workplace is not None:
                configured = self._discover(project_root)
                if composition.workplace != configured.workplace:
                    raise PermissionError("managed_workplace_scope_mismatch")
            if args.usage_command in ("collect", "import", "replay"):
                binding = CollectionBinding.from_dict(
                    read_json(Path(args.binding)), project_id=composition.project_id
                )
                # Validate before creating a store. Imported origin ids remain
                # explicit so foreign receipts can replay without identity loss.
                service = composition.service(create=True)
                assert service is not None
                result = ProviderCollector().collect(Path(args.file), binding, service)
                data = result.to_dict()
                if args.timing:
                    data["activity_stored"] = import_timing(
                        Path(args.timing), binding, service
                    )
                print(
                    json.dumps(
                        {"schema_version": 1, "collection": data}, sort_keys=True
                    )
                )
                return 2 if result.error else 0
            wider = args.scope == "workplace"
            if wider and managed:
                raise PermissionError("managed_scope_cannot_expand")
            allowed = composition.allowed_projects(workplace_scope=wider)
            filters = QueryFilter(
                project_id=args.project_id,
                assignment_id=args.assignment_id,
                run_id=args.run_id,
                attempt=args.attempt,
                source_id=args.source_id,
                model=args.model,
                start=timestamp(args.start) if args.start else None,
                end=timestamp(args.end) if args.end else None,
                limit=args.limit,
                offset=args.offset,
            )
            if filters.project_id is not None and filters.project_id not in allowed:
                raise PermissionError("project_outside_scope")
            service = composition.service()
            if service is None:
                print(
                    json.dumps(
                        {
                            "schema_version": 1,
                            "status": "unavailable",
                            "totals": None,
                            "coverage": {"complete": False, "reason": "store_missing"},
                        }
                    )
                )
                return 0
            if args.usage_command == "projects":
                data = service.projects(allowed, filters).to_dict()
            elif args.usage_command in ("summary", "project"):
                data = service.summary(allowed, filters).to_dict()
            else:
                data = service.details(allowed, filters, kind=args.kind).to_dict()
            print(json.dumps(data, sort_keys=True))
            return 0
        except PermissionError:
            code, error = 1, "usage_scope_denied"
        except RevisionConflict:
            code, error = 3, "usage_replay_conflict"
        except AccountingStorageError:
            code, error = 1, "usage_store_unavailable"
        except (OSError, ValueError, TypeError, KeyError, OverflowError):
            code, error = 1, "usage_input_invalid"
        print(json.dumps({"schema_version": 1, "error": error}))
        return code
