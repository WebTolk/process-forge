"""First creation of the derived index by an explicit Workplace search build."""

from __future__ import annotations

from uuid import uuid4

from ..project.metadata import declared_workplace_id
from ..resources.local_search import index_path
from .backup import _sidecars
from .contracts import MaintenanceError, StoreTarget
from .execution_migration import _hash
from .fresh_project import _physical, initialize_pinned_domain
from .storage_migration import (
    StorageMigrationHost,
    _safe,
    _slot,
    validate_storage_context,
)


def initialize_workplace_search(
    host: StorageMigrationHost, target: StoreTarget, *, resume_only: bool = False
) -> bool:
    """Publish or recover the index's UUID under the existing owner gate."""
    context = host.context
    root = context.workplace_root
    if root is None or target.scope != "workplace" or target.kind != "search":
        return False
    with host.service._admitted_gate(context, root, None):
        if (
            target.target != index_path(root, root)
            or target not in validate_storage_context(context)
            or declared_workplace_id(_safe(root / "workplace.yaml")) != target.owner_id
        ):
            raise MaintenanceError("storage_fresh_target_conflict")
        if host.service._selector(root, target).exists():
            return False
        slot = _slot(root, target)
        if slot is None:
            if resume_only or target.target.exists():
                return False
            store_id = uuid4().hex
        else:
            store_id = str(slot["store_id"])
        checksum = _hash(
            {
                "initializer": "workplace-search",
                "root_identity": _physical(root),
                "owner_id": target.owner_id,
                "target_relative_path": target.target_relative_path,
                "store_id": store_id,
            }
        )
        if slot is not None:
            if slot["plan_checksum"] != checksum:
                return False
            if slot["state"] == "ready" and target.target.is_file():
                return True
        if not target.target.exists():
            _sidecars(target.target, absent=True)
        initialize_pinned_domain(host, root, target, store_id, checksum)
        return True
