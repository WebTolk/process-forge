"""Existing project configuration path resolution with its shared Core resolver."""

from __future__ import annotations

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
