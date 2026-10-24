"""Existing project configuration path resolution with its shared Core resolver."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from pathlib import Path

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


@contextmanager
def configuration_operation(
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
    if current is not None and current[0] == key:
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
    token = _OPERATION.set((key, pinned))
    try:
        yield pinned
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
        if current is not None and current[0] == (
            project_root,
            workplace_root,
            device_config_path,
            context_overrides,
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
