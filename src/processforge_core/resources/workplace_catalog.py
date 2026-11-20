"""Live root-independent workplace resource catalog rules."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .identity import ResourceIdentityPolicy
from .registries import WorkplaceRegistryReader


class WorkplaceCatalogReader(WorkplaceRegistryReader, ResourceIdentityPolicy):
    """Share the existing registry reads and resource rules without bound roots."""

    def workspace_registry_specs(self) -> dict[str, tuple[str, str, str]]:
        return {'knowledge_roots': ('knowledge_roots', 'knowledge-roots.yaml', 'knowledge_roots'), 'template_roots': ('template_roots', 'templates.yaml', 'template_roots'), 'templates': ('templates', 'templates.yaml', 'templates'), 'package_roots': ('package_roots', 'package-roots.yaml', 'package_roots'), 'tools': ('tools', 'tools.yaml', 'tools'), 'mcp': ('mcp', 'mcp.yaml', 'mcp_servers'), 'private_resource_paths': ('private_resource_paths', 'private-resource-paths.yaml', 'private_resource_paths')}

    def workplace_registry_entry(self, workplace_manifest: Path | None, registry: str, ref_id: str) -> dict[str, Any] | None:
        spec = self.workspace_registry_specs().get(registry)
        if not spec or not workplace_manifest:
            return None
        registry_key, default_name, collection_key = spec
        data = self.load_workplace_registry(workplace_manifest, registry_key, default_name)
        entries = data.get(collection_key) if isinstance(data, dict) else None
        if not isinstance(entries, list):
            return None
        for entry in entries:
            if isinstance(entry, dict) and str(entry.get('id') or '') == ref_id:
                return entry
        return None
