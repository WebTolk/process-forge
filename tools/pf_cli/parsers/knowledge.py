"""Register existing CLI commands for knowledge."""

from __future__ import annotations

import argparse
from collections.abc import Callable


class KnowledgeCommandParser:
    """Register the existing knowledge command family."""

    def __init__(
        self,
        *,
        docs_import_plan: Callable[[argparse.Namespace], int],
        knowledge_add_resource: Callable[[argparse.Namespace], int],
        knowledge_add_url: Callable[[argparse.Namespace], int],
        knowledge_hub_import: Callable[[argparse.Namespace], int],
        knowledge_hub_init: Callable[[argparse.Namespace], int],
        knowledge_index_refresh: Callable[[argparse.Namespace], int],
        knowledge_package_build_from_candidates: Callable[[argparse.Namespace], int],
        knowledge_package_create: Callable[[argparse.Namespace], int],
        knowledge_package_doctor: Callable[[argparse.Namespace], int],
        knowledge_package_release: Callable[[argparse.Namespace], int],
    ) -> None:
        self._docs_import_plan = docs_import_plan
        self._knowledge_add_resource = knowledge_add_resource
        self._knowledge_add_url = knowledge_add_url
        self._knowledge_hub_import = knowledge_hub_import
        self._knowledge_hub_init = knowledge_hub_init
        self._knowledge_index_refresh = knowledge_index_refresh
        self._knowledge_package_build_from_candidates = knowledge_package_build_from_candidates
        self._knowledge_package_create = knowledge_package_create
        self._knowledge_package_doctor = knowledge_package_doctor
        self._knowledge_package_release = knowledge_package_release

    def register_resources(
        self, add_parser: Callable[..., argparse.ArgumentParser]
    ) -> None:
        knowledge_add_url = add_parser("knowledge-add-url", help="Create or apply a proposal to add a URL-backed knowledge resource.")
        knowledge_add_url.add_argument("--workplace", required=True, help="Workplace root path.")
        knowledge_add_url.add_argument("--package", required=True, help="Knowledge package id.")
        knowledge_add_url.add_argument("--package-root", dest="package_root", help="Package root id from registries/package-roots.yaml.")
        knowledge_add_url.add_argument("--url", required=True, help="External source URL.")
        knowledge_add_url.add_argument("--kind", default="article", help="Resource kind.")
        knowledge_add_url.add_argument("--id", help="Resource id override.")
        knowledge_add_url.add_argument("--title", help="Resource title.")
        knowledge_add_url.add_argument("--description", help="Resource description.")
        knowledge_add_url.add_argument("--license", help="License note.")
        knowledge_add_url.add_argument("--load-policy", dest="load_policy", help="Load policy override.")
        knowledge_add_url.add_argument("--index-policy", dest="index_policy", help="Index policy override.")
        knowledge_add_url.add_argument("--dry-run", action="store_true", help="Show the complete transaction plan without writing.")
        knowledge_add_url.add_argument("--apply", action="store_true", help="Update package manifest and resource index.")
        knowledge_add_url.set_defaults(func=self._knowledge_add_url)

        knowledge_add_resource = add_parser("knowledge-add-resource", help="Create or apply a proposal to add a YAML resource record.")
        knowledge_add_resource.add_argument("--workplace", required=True, help="Workplace root path.")
        knowledge_add_resource.add_argument("--package", required=True, help="Knowledge package id.")
        knowledge_add_resource.add_argument("--package-root", dest="package_root", help="Package root id from registries/package-roots.yaml.")
        knowledge_add_resource.add_argument("--resource-file", required=True, help="YAML knowledge resource record.")
        knowledge_add_resource.add_argument("--dry-run", action="store_true", help="Show the complete transaction plan without writing.")
        knowledge_add_resource.add_argument("--apply", action="store_true", help="Update package manifest and resource index.")
        knowledge_add_resource.set_defaults(func=self._knowledge_add_resource)

        knowledge_package_doctor = add_parser("knowledge-package-doctor", help="Validate a knowledge package manifest and resource index.")
        knowledge_package_doctor.add_argument("--workplace", required=True, help="Workplace root path.")
        knowledge_package_doctor.add_argument("--package", required=True, help="Knowledge package id.")
        knowledge_package_doctor.add_argument("--package-root", dest="package_root", help="Package root id from registries/package-roots.yaml.")
        knowledge_package_doctor.set_defaults(func=self._knowledge_package_doctor)

        knowledge_index_refresh = add_parser("knowledge-index-refresh", help="Refresh a package resource index without loading heavy resources.")
        knowledge_index_refresh.add_argument("--workplace", required=True, help="Workplace root path.")
        knowledge_index_refresh.add_argument("--package", required=True, help="Knowledge package id.")
        knowledge_index_refresh.add_argument("--package-root", dest="package_root", help="Package root id from registries/package-roots.yaml.")
        knowledge_index_refresh.add_argument("--dry-run", action="store_true", help="Write proposal only.")
        knowledge_index_refresh.add_argument("--apply", action="store_true", help="Write resource index.")
        knowledge_index_refresh.set_defaults(func=self._knowledge_index_refresh)

        docs_import_plan = add_parser("docs-import-plan", help="Create a documentation mirror import plan without downloading content.")
        docs_import_plan.add_argument("--workplace", required=True, help="Workplace root path.")
        docs_import_plan.add_argument("--source", required=True, help="Documentation source id, for example mdn.")
        docs_import_plan.add_argument("--topics", required=True, help="Comma-separated topics.")
        docs_import_plan.add_argument("--package", help="Target documentation package id.")
        docs_import_plan.add_argument("--id", help="Plan id override.")
        docs_import_plan.add_argument("--license", help="License note.")
        docs_import_plan.set_defaults(func=self._docs_import_plan)

    def register_create(
        self, add_parser: Callable[..., argparse.ArgumentParser]
    ) -> None:
        knowledge_package_create = add_parser("knowledge-package-create", help="Author a workplace knowledge package.")
        knowledge_package_create.add_argument("--workplace", required=True, help="Workplace root path.")
        knowledge_package_create.add_argument("--id", required=True, help="Package id.")
        knowledge_package_create.add_argument("--title", required=True, help="Package title.")
        knowledge_package_create.add_argument("--description", help="Package description.")
        knowledge_package_create.add_argument("--package-root", dest="package_root", required=True, help="Package root id from registries/package-roots.yaml.")
        knowledge_package_create.add_argument("--kind", default="documentation", choices=["documentation", "rules", "source", "project", "platform", "mixed"], help="Package kind.")
        knowledge_package_create.add_argument("--dry-run", action="store_true", help="Show planned files without writing.")
        knowledge_package_create.add_argument("--apply", action="store_true", help="Write package files.")
        knowledge_package_create.add_argument("--force", action="store_true", help="Overwrite an existing package.")
        knowledge_package_create.set_defaults(func=self._knowledge_package_create)

    def register_hub_release(
        self, add_parser: Callable[..., argparse.ArgumentParser]
    ) -> None:
        knowledge_hub_init = add_parser("knowledge-hub-init", help="Initialize a file-first knowledge hub.")
        knowledge_hub_init.add_argument("--hub", required=True, help="Hub root path.")
        knowledge_hub_init.add_argument("--apply", action="store_true", help="Write hub files.")
        knowledge_hub_init.set_defaults(func=self._knowledge_hub_init)

        knowledge_hub_import = add_parser("knowledge-hub-import", help="Import a learning export bundle into a knowledge hub.")
        knowledge_hub_import.add_argument("--hub", required=True, help="Hub root path.")
        knowledge_hub_import.add_argument("--bundle", required=True, help="Learning export zip path.")
        knowledge_hub_import.add_argument("--apply", action="store_true", help="Import bundle files.")
        knowledge_hub_import.set_defaults(func=self._knowledge_hub_import)

        knowledge_package_build_from_candidates = add_parser("knowledge-package-build-from-candidates", help="Build package candidate notes from imported learning candidates.")
        knowledge_package_build_from_candidates.add_argument("--hub", required=True, help="Hub root path.")
        knowledge_package_build_from_candidates.add_argument("--package", required=True, help="Package id, for example docs.example.")
        knowledge_package_build_from_candidates.add_argument("--version", required=True, help="Package version.")
        knowledge_package_build_from_candidates.add_argument("--apply", action="store_true", help="Write package files.")
        knowledge_package_build_from_candidates.set_defaults(func=self._knowledge_package_build_from_candidates)

        knowledge_package_release = add_parser("knowledge-package-release", help="Create a package release artifact and local update manifest.")
        knowledge_package_release.add_argument("--hub", required=True, help="Hub root path.")
        knowledge_package_release.add_argument("--package", required=True, help="Package id, for example docs.example.")
        knowledge_package_release.add_argument("--version", required=True, help="Package version.")
        knowledge_package_release.add_argument("--output", required=True, help="Release zip output path.")
        knowledge_package_release.set_defaults(func=self._knowledge_package_release)
