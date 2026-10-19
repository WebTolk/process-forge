"""Existing project configuration path resolution with its shared Core resolver."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ..configuration.resolution import ConfigurationResolver
from ..work.context_documents import ContextContractInputs
from .metadata import ProjectMetadataReader


@dataclass(frozen=True)
class ProjectConfigurationReader:
    resolver: ConfigurationResolver = field(default_factory=ConfigurationResolver)
    inputs: ContextContractInputs = field(default_factory=ContextContractInputs)

    def project_configuration(self, project_root: Path, workplace_root: Path | None = None):
        if workplace_root is None:
            manifest = ProjectMetadataReader(project_root).workplace_manifest()
            workplace_root = manifest.parent.resolve() if manifest else None
        device_path = workplace_root / "configuration.yaml" if workplace_root is not None else None
        return self.resolver.resolve(device_path, self.inputs.locate_flow_root(project_root) / "configuration.yaml")


project_configuration_reader = ProjectConfigurationReader()
