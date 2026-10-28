"""Existing project configuration path resolution with its shared Core resolver."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import AbstractContextManager, contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from ..maintenance.storage_migration import StorageMigrationHost

from ..configuration import (
    ConfigurationProvider,
    ConfigurationResolver,
    ProjectPFConfig,
    ResolvedConfig,
)
from ..work.context_documents import ContextContractInputs
from .metadata import ProjectMetadataReader

_OperationKey = tuple[Path | None, Path | None, Path | None, ProjectPFConfig | None]
_OPERATION: ContextVar[tuple[_OperationKey, ConfigurationProvider] | None] = ContextVar(
    "pf_configuration_operation", default=None
)
_STORAGE_OPERATION: ContextVar[StorageMigrationHost | None] = ContextVar(
    "pf_storage_operation", default=None
)


def _matches_operation(current: _OperationKey, requested: _OperationKey) -> bool:
    return (
        current[:2] == requested[:2]
        and (requested[2] is None or requested[2] == current[2])
        and (requested[3] is None or requested[3] == current[3])
    )


def operation_configuration(
    project: Path | None, workplace: Path | None
) -> ConfigurationProvider | None:
    """Return only an already pinned exact-root value, without discovery or I/O."""
    current = _OPERATION.get()
    return (
        current[1]
        if current is not None and current[0][:2] == (project, workplace)
        else None
    )


def operation_device_path(
    project: Path | None, workplace: Path | None, fallback: Path | None = None
) -> Path | None:
    """Carry selectors separately from the immutable value; never rediscover."""
    current = _OPERATION.get()
    if current is not None and current[0][:2] == (project, workplace):
        return current[0][2]
    return fallback


def _identityless_legacy(
    project: Path | None,
    workplace: Path | None,
    configuration: ConfigurationProvider,
) -> None:
    """Permit only unbound, pre-pending legacy; never synthesize an owner."""
    from ..database import DatabaseFactory
    from ..executions.composition import _fresh_initialization, select_execution_storage
    from ..maintenance.contracts import MaintenanceError, StoreTarget
    from ..maintenance.storage_migration import (
        _descriptor,
        _inspect_target,
        _pins,
        _safe,
    )

    if project is None:
        raise MaintenanceError("project_identity_required")
    metadata = ProjectMetadataReader(project)
    flow = _safe(metadata.flow_root())
    manifest = _safe(flow / "process-forge.yaml")
    owner = metadata.manifest().get("project") if manifest.is_file() else None
    if not isinstance(owner, dict) or "id" in owner:
        raise MaintenanceError("project_identity_required")
    if _fresh_initialization(flow) is not None:
        raise MaintenanceError("project_identity_required")
    # Execution composition owns the binding/profile/domain eligibility policy.
    if (
        select_execution_storage(
            project, workplace, configuration=configuration
        ).repository
        is not None
    ):
        raise MaintenanceError("project_identity_required")
    roots: list[tuple[Path, Literal["project", "workplace"]]] = [(flow, "project")]
    if workplace is not None:
        roots.append((_safe(workplace), "workplace"))
    descriptor = _descriptor(verify_transforms=False)
    driver = DatabaseFactory.resolve_driver(configuration.current().database)
    for root, scope in roots:
        if (
            _pins(root)["slots"]
            or _safe(root / "maintenance/storage-migrations").exists()
        ):
            raise MaintenanceError("project_identity_required")
        paths: list[
            tuple[Literal["events", "raw", "search", "accounting", "main"], str]
        ] = [
            ("events", "runtime/events/events.sqlite3"),
            ("raw", "runtime/agent-events/hooks.sqlite3"),
            ("search", "runtime/local-resource-search/search.sqlite")
            if scope == "project"
            else ("search", "runtime/search/local-resource-search.sqlite"),
        ]
        if scope == "workplace":
            paths = [
                ("raw", "runtime/agent-events/hooks.sqlite3"),
                ("search", "runtime/search/local-resource-search.sqlite"),
                ("accounting", "data/accounting/accounting.sqlite3"),
            ]
        for kind, relative in paths:
            # An empty owner carries no adoption authority. Core rejects adopted
            # or foreign envelopes and validates each existing legacy schema.
            target = StoreTarget(kind, root / relative, relative, scope, "")
            facts = _inspect_target(target, descriptor, driver)
            if facts.get("store_id") is not None:
                raise MaintenanceError("project_identity_required")


def _first_write_storage_host(
    project: Path,
    workplace: Path | None,
    device: Path | None,
    configuration: ConfigurationProvider,
) -> StorageMigrationHost | None:
    """Return deliberate legacy deferral separately from an unselected host."""
    from .. import composition
    from ..maintenance.contracts import MaintenanceError
    from ..maintenance.storage_migration import StorageMigrationHost

    host = _STORAGE_OPERATION.get()
    current = _OPERATION.get()
    if host is None or current is None or current[0][:2] != (project, workplace):
        factory = getattr(composition, "build_storage_migration_host", None)
        if factory is None:
            raise MaintenanceError("storage_host_factory_unavailable")
        host = factory(
            project_root=project,
            workplace_root=workplace,
            device_config_path=device,
            configuration=configuration,
        )
    if not isinstance(host, StorageMigrationHost):
        raise MaintenanceError("storage_host_factory_invalid")
    try:
        host.context
    except MaintenanceError as error:
        if error.code != "project_identity_required":
            raise
        _identityless_legacy(project, workplace, configuration)
        return None
    return host


def operation_storage_host(path: Path) -> StorageMigrationHost | None:
    """Route a selected adapter within this operation; no process-global cache."""
    from ..maintenance.contracts import MaintenanceError

    host = _STORAGE_OPERATION.get()
    if host is None:
        return None
    try:
        context = host.context
    except MaintenanceError as error:
        current = _OPERATION.get()
        if error.code == "project_identity_required" and current is not None:
            _identityless_legacy(current[0][0], current[0][1], current[1])
            return None
        raise
    return (
        host
        if any(t.target == path for t in context.targets)
        or any(selected == path for _kind, selected in context.unqualified_targets)
        else None
    )


class _ConfigurationOperation:
    def __init__(self, scope: AbstractContextManager[ConfigurationProvider]) -> None:
        self._scope = scope

    def __enter__(self) -> ConfigurationProvider:
        return self._scope.__enter__()

    def __exit__(self, *_exception: object) -> None:
        # As in request_scope, complete cleanup without injecting the original
        # exception: generator context managers rewrite frozen tracebacks.
        self._scope.__exit__(None, None, None)


def configuration_operation(
    project_root: Path | None,
    workplace_root: Path | None,
    *,
    device_config_path: Path | None = None,
    context_overrides: ProjectPFConfig | None = None,
    configuration: ConfigurationProvider | None = None,
) -> _ConfigurationOperation:
    """Pin configuration without rewriting exceptions on operation exit."""
    return _ConfigurationOperation(
        _configuration_scope(
            project_root,
            workplace_root,
            device_config_path=device_config_path,
            context_overrides=context_overrides,
            configuration=configuration,
        )
    )


@contextmanager
def _configuration_scope(
    project_root: Path | None,
    workplace_root: Path | None,
    *,
    device_config_path: Path | None = None,
    context_overrides: ProjectPFConfig | None = None,
    configuration: ConfigurationProvider | None = None,
) -> Iterator[ConfigurationProvider]:
    """Pin one full native value for an exact operation, without project leakage."""
    key = (project_root, workplace_root, device_config_path, context_overrides)
    current = _OPERATION.get()
    if current is not None and _matches_operation(current[0], key):
        yield current[1]
        return
    provider = configuration or ProjectConfigurationReader().configuration_provider(
        project_root,
        workplace_root,
        device_config_path=device_config_path,
        context_overrides=context_overrides,
    )
    snapshot = provider.snapshot()
    pinned = ConfigurationProvider.pinned(snapshot.config, errors=snapshot.errors)
    from ..configuration import DeviceConfigurationSource

    selected_device = device_config_path or provider.device_path
    if selected_device is None:
        selected_device = DeviceConfigurationSource.default_path()
    key = (project_root, workplace_root, selected_device, context_overrides)
    token = _OPERATION.set((key, pinned))
    from ..composition import build_storage_migration_host

    try:
        host = build_storage_migration_host(
            project_root=project_root,
            workplace_root=workplace_root,
            device_config_path=selected_device,
            configuration=pinned,
        )
        storage_token = _STORAGE_OPERATION.set(host)
        try:
            yield pinned
        finally:
            _STORAGE_OPERATION.reset(storage_token)
    finally:
        _OPERATION.reset(token)


@dataclass(frozen=True)
class ProjectConfigurationReader:
    resolver: ConfigurationResolver = field(default_factory=ConfigurationResolver)
    inputs: ContextContractInputs = field(default_factory=ContextContractInputs)

    def configuration_provider(
        self,
        project_root: Path | None = None,
        workplace_root: Path | None = None,
        *,
        device_config_path: Path | None = None,
        context_overrides: ProjectPFConfig | None = None,
    ) -> ConfigurationProvider:
        """Bind already selected roots without discovery or reading any source."""
        current = _OPERATION.get()
        if current is not None and _matches_operation(
            current[0],
            (
                project_root,
                workplace_root,
                device_config_path,
                context_overrides,
            ),
        ):
            return current[1]
        return ConfigurationProvider(
            device_path=device_config_path,
            workplace_path=workplace_root / "configuration.yaml"
            if workplace_root is not None
            else None,
            project_path=self.inputs.locate_flow_root(project_root)
            / "configuration.yaml"
            if project_root is not None
            else None,
            context_overrides=context_overrides,
            resolver=self.resolver,
        )

    def project_configuration(
        self,
        project_root: Path,
        workplace_root: Path | None = None,
        *,
        device_config_path: Path | None = None,
        context_overrides: ProjectPFConfig | None = None,
    ) -> ResolvedConfig:
        """Keep legacy enrollment discovery at this explicit read boundary."""
        if workplace_root is None:
            manifest = ProjectMetadataReader(project_root).workplace_manifest()
            workplace_root = manifest.parent.resolve() if manifest else None
        return self.configuration_provider(
            project_root,
            workplace_root,
            device_config_path=device_config_path,
            context_overrides=context_overrides,
        ).snapshot()


project_configuration_reader = ProjectConfigurationReader()
