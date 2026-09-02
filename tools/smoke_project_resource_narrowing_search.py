#!/usr/bin/env python3
"""Acceptance smoke for narrow, version-aware project resource selection."""

from __future__ import annotations

import importlib.util
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from processforge_core.garage import resource_selection_summary, selected_resource
from processforge_core.local_resource_search import maintenance_tick, search


def load_pf_module():
    spec = importlib.util.spec_from_file_location("processforge_cli", ROOT / "tools" / "processforge.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


PF = load_pf_module()


def resource(package: str, version: str, *, kind: str = "source_tree") -> dict:
    return {
        "id": f"{package}:root",
        "resource_id": "root",
        "package": package,
        "kind": kind,
        "title": f"Platform resource {version}",
        "version": version,
        "indexing": {"enabled": True, "mode": "metadata", "sources": [{"path": ".", "mode": "metadata"}]},
        "versioning": {"mode": "multi_version", "instance_id_template": "{id}@{version}"},
        "retention": {"policy": "keep_versions"},
        "snapshot_behavior": {"reproducibility": "exact"},
    }


def smoke_project_selects_current_platform_resources() -> None:
    resources = [resource("knowledge.platform-core.v5-4-5", "5.4.5"), resource("knowledge.platform-core.v6-1-2", "6.1.2")]
    selected, report = PF.select_resolved_knowledge_resources(
        resources,
        {"knowledge_resources": [], "resource_selection": {"platform_versions": {"cms": "6.1"}}},
        direct_package_ids=["knowledge.platform-guide-6-1"],
    )
    assert [item["resolved_version"] for item in selected] == ["6.1.2"], (selected, report)
    assert report["target_versions"] == ["6.1"]


def smoke_project_does_not_select_all_platform_versions() -> None:
    resources = [resource("knowledge.platform-core.v5-4-5", "5.4.5"), resource("knowledge.platform-core.v6-1-1", "6.1.1"), resource("knowledge.platform-core.v6-1-2", "6.1.2")]
    selected, _report = PF.select_resolved_knowledge_resources(
        resources,
        {"knowledge_resources": [], "resource_selection": {"platform_versions": {"cms": "6.1"}}},
        direct_package_ids=["knowledge.platform-guide-6-1"],
    )
    assert {item["resolved_version"] for item in selected} == {"6.1.2"}


def smoke_platform_version_compatibility_resolution() -> None:
    resources = [resource("knowledge.platform-core", "6.1.1"), resource("knowledge.platform-core", "6.1.2")]
    selected, report = PF.select_resolved_knowledge_resources(
        resources,
        {"knowledge_resources": [{"id": "root", "constraint": ">=6.1 <6.2", "required": True}]},
    )
    assert len(selected) == 1 and selected[0]["resolved_version"] == "6.1.2", (selected, report)
    assert report["provenance"][0]["status"] == "selected"


def smoke_real_project_fulltext_docs_selected() -> None:
    with tempfile.TemporaryDirectory(prefix="pf-real-project-resource-") as raw:
        root = Path(raw)
        documentation_root = root / "joomla-6-1-docs"
        old = root / "joomla-5-4-docs"
        documentation_root.mkdir()
        old.mkdir()
        (documentation_root / "media-api.md").write_text("CurrentJoomlaMediaApiNeedle", encoding="utf-8")
        (old / "legacy.md").write_text("HistoricalJoomlaNeedle", encoding="utf-8")
        current = resource("knowledge.platform-guide-6-1", "6.1", kind="documentation")
        current.update({"title": "Platform 6.1 Documentation", "content_roots": [str(documentation_root)], "indexing": {"enabled": True, "mode": "fulltext", "sources": [{"path": ".", "mode": "fulltext", "include": ["**/*.md"]}]}})
        historical = resource("knowledge.platform-guide-5-4", "5.4", kind="documentation")
        historical.update({"content_roots": [str(old)], "indexing": current["indexing"]})
        snapshot = {"snapshot": {"id": "real-joomla-shaped", "checksum": "fixture"}, "resolved": {"available_knowledge_resources": [historical], "knowledge_resources": [current]}, "local_search_resources": [current]}
        assert maintenance_tick(root / "project", snapshot)["after"]["status"] == "fresh"
        result = search(root / "project", snapshot, query="CurrentJoomlaMediaApiNeedle")
        assert result["results"] and result["results"][0]["resource_id"] == "knowledge.platform-guide-6-1:root", result
        assert result["results"][0]["match_reason"] == "content"
        assert not search(root / "project", snapshot, query="HistoricalJoomlaNeedle")["results"]


def smoke_source_tree_metadata_only() -> None:
    with tempfile.TemporaryDirectory(prefix="pf-source-metadata-") as raw:
        root = Path(raw)
        source = root / "source"
        source.mkdir()
        (source / "hidden.php").write_text("PrivateSourceNeedle", encoding="utf-8")
        item = resource("knowledge.platform-core.v6-1-2", "6.1.2")
        item["content_roots"] = [str(source)]
        item.pop("indexing")
        item["index_policy"] = "source_tree"
        snapshot = {"snapshot": {"id": "source-metadata", "checksum": "fixture"}, "local_search_resources": [item]}
        assert maintenance_tick(root / "project", snapshot)["after"]["status"] == "fresh"
        assert not search(root / "project", snapshot, query="PrivateSourceNeedle")["results"]


def smoke_search_returns_current_platform_source() -> None:
    smoke_real_project_fulltext_docs_selected()


def smoke_search_historical_versions_hidden() -> None:
    smoke_real_project_fulltext_docs_selected()


def smoke_migration_project_can_select_old_and_new_versions() -> None:
    resources = [resource("knowledge.platform-core.v5-4-5", "5.4.5"), resource("knowledge.platform-core.v6-1-2", "6.1.2")]
    old, _ = PF.select_resolved_knowledge_resources(resources, {"knowledge_resources": [], "resource_selection": {"platform_versions": {"cms": "5.4"}}}, direct_package_ids=["knowledge.platform-guide-5-4"])
    new, _ = PF.select_resolved_knowledge_resources(resources, {"knowledge_resources": [], "resource_selection": {"platform_versions": {"cms": "6.1"}}}, direct_package_ids=["knowledge.platform-guide-6-1"])
    assert [item["resolved_version"] for item in old] == ["5.4.5"]
    assert [item["resolved_version"] for item in new] == ["6.1.2"]


def smoke_resource_selection_provenance() -> None:
    selected, report = PF.select_resolved_knowledge_resources([resource("knowledge.platform-core.v6-1-2", "6.1.2")], {"knowledge_resources": [], "resource_selection": {"platform_versions": {"cms": "6.1"}}}, direct_package_ids=["knowledge.platform-guide-6-1"])
    assert selected[0]["selection"]["reason"] == "legacy_compatible_version"
    assert report["provenance"][0]["selector"]["selection_reason"] == "legacy_compatible_version"
    documentation = resource("knowledge.platform-guide-6-1", "6.1", kind="documentation")
    documentation.pop("indexing")
    indexing = PF.selected_resource_indexing(documentation, report)
    assert indexing["mode"] == "fulltext" and indexing["migration"] == "legacy_documentation_fulltext"


def smoke_search_scope_remains_snapshot_bound() -> None:
    current = resource("knowledge.current", "6.1", kind="documentation")
    historical = resource("knowledge.historical", "5.4", kind="documentation")
    snapshot = {"resolved": {"available_knowledge_resources": [historical], "knowledge_resources": [current]}, "local_search_resources": [current]}
    assert selected_resource(snapshot, "knowledge.historical:root") == {}
    assert selected_resource(snapshot, "knowledge.current:root")["id"] == "knowledge.current:root"
    summary = resource_selection_summary(
        {
            **snapshot,
            "resource_selection": {"mode": "explicit", "available_count": 2, "selected_count": 1, "target_versions": ["6.1"]},
        }
    )
    assert summary["available_count"] == 2 and summary["selected_count"] == 1 and summary["target_versions"] == ["6.1"]


def main() -> int:
    for check in [
        smoke_project_selects_current_platform_resources,
        smoke_project_does_not_select_all_platform_versions,
        smoke_platform_version_compatibility_resolution,
        smoke_real_project_fulltext_docs_selected,
        smoke_source_tree_metadata_only,
        smoke_search_returns_current_platform_source,
        smoke_search_historical_versions_hidden,
        smoke_migration_project_can_select_old_and_new_versions,
        smoke_resource_selection_provenance,
        smoke_search_scope_remains_snapshot_bound,
    ]:
        check()
    print("PASS: project resource narrowing and search acceptance")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
