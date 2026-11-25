#!/usr/bin/env python3
"""Regression smoke for the workplace-wide local resource search index."""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import tempfile
from contextlib import closing
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
for entry in (ROOT / "src", ROOT / "tools"):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

import processforge as core  # noqa: E402 - trusted entry before Core
from garage_search_smoke_support import run_cli  # noqa: E402 - source bootstrap

from processforge_core.composition import build_resource_resolve_service  # noqa: E402
from processforge_core.resources.catalog_read import WorkplaceSearchCatalogReader  # noqa: E402
from processforge_core.resources.identity import search_root_id  # noqa: E402
from processforge_core.resources.local_search import ResourceSearchIndex, search  # noqa: E402


def snapshot(resource_id: str, content_root: Path) -> dict:
    return {
        "snapshot": {"id": f"project-{resource_id}", "checksum": f"project-{resource_id}"},
        "local_search_resources": [{"id": resource_id, "content_roots": [str(content_root)]}],
    }


def call_search_tools(
    workplace: Path, calls: list[tuple[str, Path, dict[str, Any]]]
) -> list[dict[str, Any]]:
    requests = [{"jsonrpc": "2.0", "id": 0, "method": "initialize"}]
    for call_id, (name, project, arguments) in enumerate(calls, start=1):
        requests.append(
            {
                "jsonrpc": "2.0",
                "id": call_id,
                "method": "tools/call",
                "params": {
                    "name": name,
                    "arguments": {"project_root": str(project), **arguments},
                },
            }
        )
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools/pf_runtime/mcp_server.py"),
            "--workplace",
            str(workplace),
        ],
        cwd=ROOT,
        input="".join(json.dumps(request) + "\n" for request in requests),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
    )
    assert result.returncode == 0, result.stderr
    replies = {
        reply["id"]: reply for reply in map(json.loads, result.stdout.splitlines())
    }
    assert set(replies) == set(range(len(requests))), replies
    payloads = []
    for call_id in range(1, len(requests)):
        response = replies[call_id]["result"]
        assert not response.get("isError"), response
        payloads.append(
            response.get("structuredContent")
            or json.loads(response["content"][0]["text"])
        )
    return payloads


def select_version(
    project: Path, workplace: Path, package_id: str, resource_id: str, version: str
) -> None:
    project.mkdir()
    run_cli(
        "project-onboard",
        "--project-root",
        str(project),
        "--workplace",
        str(workplace),
        "--type",
        "generic",
        "--apply",
    )
    manifest_path = project / ".pf/process-forge.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    manifest["knowledge_stack"].append(
        {"id": package_id, "version": "1.0.0", "source": "workplace"}
    )
    requirements = manifest["context_requirements"]
    requirements["knowledge_packages"].append(
        {"id": package_id, "constraint": "*", "required": True}
    )
    requirements["knowledge_resources"] = [
        {"id": resource_id, "preferred_version": version, "required": True}
    ]
    manifest_path.write_text(yaml.safe_dump(manifest), encoding="utf-8")
    run_cli(
        "project-context-refresh",
        "--project-root",
        str(project),
        "--workplace",
        str(workplace),
        "--apply",
    )


def maintain_workplace(workplace: Path) -> None:
    result = run_cli(
        "search-index-maintain", "--workplace", str(workplace), "--apply", "--json"
    )
    report = json.loads(result.stdout)
    assert report["scope"] == "workplace" and report["results"][0]["status"] == "ok", (
        report
    )


def check_version_search(
    workplace: Path, projects: list[tuple[Path, Path]], resource_id: str
) -> None:
    calls: list[tuple[str, Path, dict[str, Any]]] = []
    for number, (project, _) in enumerate(projects, start=1):
        calls.extend(
            [
                ("pf.search", project, {"query": "sharedmatch", "limit": 1}),
                (
                    "pf.search",
                    project,
                    {"query": "sharedmatch", "limit": 1, "offset": 1},
                ),
                ("pf.search", project, {"query": f"uniquematch{number}"}),
                ("pf.search", project, {"query": f"uniquematch{3 - number}"}),
                ("pf.resolve", project, {"resource_id": resource_id}),
            ]
        )
    replies = call_search_tools(workplace, calls)
    for number, (_, root) in enumerate(projects, start=1):
        first, second, own, other, resolution = replies[(number - 1) * 5 : number * 5]
        assert first["page"]["next_limitstart"] == 1, first
        assert second["page"]["next_limitstart"] is None, second
        assert own["total"] == 2 and other["total"] == 0, (own, other)
        assert other["results"] == [], other
        assert Path(resolution["resource"]["local_root"]) == root.resolve(), resolution
        for page, name in ((first, "one.md"), (second, "two.md")):
            assert page["search_status"] == "fresh" and page["total"] == 2, page
            assert page["page"]["total"] == 2 and page["page"]["returned"] == 1, page
            assert page["authorized_coverage"]["document_count"] == (
                2 if number == 1 else 3
            ), page
            (match,) = page["results"]
            assert (
                match["resource_id"] == resource_id and match["canonical_path"] == name
            ), match
            assert match["metadata"]["version"] == root.name, match
            assert match["metadata"]["instance_id"] == f"{resource_id}@{root.name}", (
                match
            )
            assert match["metadata"]["root_id"] == search_root_id(root.resolve()), match
            path = Path(match["local_path"])
            assert path == (root / name).resolve(), match
            assert (
                path.read_text(encoding="utf-8") == f"sharedmatch uniquematch{number}"
            ), match


def check_project_search_grants(
    workplace: Path, project: Path, selected_root: Path, resource_id: str
) -> None:
    calls: list[tuple[str, Path, dict[str, Any]]] = [
        ("pf.search", project, {"query": "sharedmatch"}),
    ]
    unavailable = selected_root.with_name("unavailable")
    selected_root.rename(unavailable)
    try:
        (missing,) = call_search_tools(workplace, calls)
        assert missing["search_status"] == "stale", missing
        assert missing["results"] == [] and missing["total"] == 0, missing
        assert missing["degraded_reason"] == "resource_not_indexed", missing
        assert missing["authorized_coverage"]["unavailable_resource_ids"] == [
            resource_id
        ], missing
    finally:
        unavailable.rename(selected_root)

    path = project / ".pf/contexts/project-context.snapshot.yaml"
    original = path.read_bytes()
    snapshot = yaml.safe_load(original)
    del snapshot["local_search_resources"]
    try:
        path.write_text(yaml.safe_dump(snapshot), encoding="utf-8")
        (legacy,) = call_search_tools(workplace, calls)
        assert legacy["search_status"] == "fresh" and legacy["total"] == 2, legacy
        assert all(
            Path(match["local_path"]).parent == selected_root.resolve()
            for match in legacy["results"]
        ), legacy

        snapshot["local_search_resources"] = []
        path.write_text(yaml.safe_dump(snapshot), encoding="utf-8")
        (denied,) = call_search_tools(workplace, calls)
        assert denied["search_status"] == "fresh" and denied["total"] == 0, denied
        assert denied["authorized_coverage"]["authorized_resource_count"] == 0, denied
    finally:
        path.write_bytes(original)


def check_rank_isolation(workplace: Path, project: Path, other_document: Path) -> None:
    calls: list[tuple[str, Path, dict[str, Any]]] = [
        ("pf.search", project, {"query": "sharedmatch", "limit": 1, "offset": offset})
        for offset in (0, 1)
    ]

    def rank_pages() -> list[tuple[str, float]]:
        pages = call_search_tools(workplace, calls)
        assert all(
            page["search_status"] == "fresh" and page["total"] == 2 for page in pages
        ), pages
        return [
            (page["results"][0]["canonical_path"], page["results"][0]["match"]["rank"])
            for page in pages
        ]

    before = rank_pages()
    other_document.write_text("unselectedfiller " * 10_000, encoding="utf-8")
    maintain_workplace(workplace)
    assert rank_pages() == before


def smoke_selected_versions(scratch_root: Path) -> None:
    with tempfile.TemporaryDirectory(
        prefix="pf-search-versions-", dir=scratch_root
    ) as raw:
        root = Path(raw)
        workplace = root / "workplace"
        run_cli("workplace-init", "--workplace", str(workplace), "--apply")
        package_id = "fixture.search-versions"
        resource_id = f"{package_id}:guide"
        package = workplace / "packages" / package_id
        projects = []
        resources = []
        for number in (1, 2):
            version = f"{number}.0.0"
            version_root = package / version
            version_root.mkdir(parents=True)
            for name in ("one.md", "two.md"):
                (version_root / name).write_text(
                    f"sharedmatch uniquematch{number}", encoding="utf-8"
                )
            resources.append(
                {
                    "id": "guide",
                    "kind": "documentation",
                    "title": "Versioned Guide",
                    "version": version,
                    "path": version,
                    "indexing": {
                        "mode": "fulltext",
                        "sources": [
                            {"path": ".", "mode": "fulltext", "include": ["**/*.md"]}
                        ],
                    },
                }
            )
            projects.append((root / f"project-{number}", version_root))
        other_document = projects[1][1] / "filler.md"
        other_document.write_text("unselectedfiller", encoding="utf-8")
        (package / "package.yaml").write_text(
            yaml.safe_dump(
                {
                    "schema_version": 1,
                    "id": package_id,
                    "version": "1.0.0",
                    "kind": "documentation",
                    "resources": resources,
                }
            ),
            encoding="utf-8",
        )
        for project, version_root in projects:
            select_version(
                project, workplace, package_id, resource_id, version_root.name
            )
        maintain_workplace(workplace)
        check_version_search(workplace, projects, resource_id)
        project = projects[0][0]
        check_project_search_grants(workplace, project, projects[0][1], resource_id)
        check_rank_isolation(workplace, project, other_document)
        run_cli(
            "search-index",
            "refresh",
            "--project-root",
            str(project),
            "--workplace",
            str(workplace),
        )
        check_version_search(workplace, projects, resource_id)

        database = workplace / "runtime/search/local-resource-search.sqlite"
        calls: list[tuple[str, Path, dict[str, Any]]] = [
            ("pf.search", project, {"query": "sharedmatch"})
        ]
        with closing(sqlite3.connect(database)) as db, db:
            store_id = db.execute("SELECT store_id FROM pf_store_meta").fetchone()
            fingerprint = db.execute(
                "SELECT fingerprint FROM resources WHERE resource_id=?", (resource_id,)
            ).fetchone()[0]
            instance_inventory = json.loads(fingerprint)
            selected_key = next(
                key
                for key, metadata in db.execute(
                    "SELECT root_id, metadata FROM documents WHERE resource_id=?",
                    (resource_id,),
                )
                if json.loads(metadata)["version"] == "1.0.0"
            )
            del instance_inventory[selected_key]
            db.execute(
                "UPDATE resources SET fingerprint=? WHERE resource_id=?",
                (json.dumps(instance_inventory), resource_id),
            )
        (stale,) = call_search_tools(workplace, calls)
        assert (
            stale["search_status"] == "stale"
            and stale["degraded_reason"] == "resource_not_indexed"
        ), stale
        assert stale["results"] == [] and stale["total"] == 0, stale
        assert stale["authorized_coverage"]["missing_instance_count"] == 1, stale
        maintain_workplace(workplace)
        check_version_search(workplace, projects, resource_id)

        with closing(sqlite3.connect(database)) as db, db:
            db.execute("DELETE FROM meta WHERE key='resource_identity_format'")
        (previous,) = call_search_tools(workplace, calls)
        assert previous["search_status"] == "degraded" and previous["results"] == [], (
            previous
        )
        assert previous["degraded_reason"] == "index_schema_mismatch", previous
        maintain_workplace(workplace)
        check_version_search(workplace, projects, resource_id)
        with closing(sqlite3.connect(database)) as db:
            assert (
                db.execute("SELECT store_id FROM pf_store_meta").fetchone() == store_id
            )


def main() -> int:
    scratch_root = Path(
        os.environ.get("PF_TEST_SCRATCH_ROOT") or tempfile.gettempdir()
    ).resolve(strict=True)
    with tempfile.TemporaryDirectory(
        prefix="pf-workplace-search-", dir=scratch_root
    ) as raw:
        root = Path(raw)
        workplace = root / "workplace"
        packages = workplace / "packages" / "docs.a"
        project_a = root / "project-a"
        project_b = root / "project-b"
        for path in (packages / "guide", packages / "tree", project_a / ".pf" / "contexts", project_b / ".pf" / "contexts"):
            path.mkdir(parents=True, exist_ok=True)
        (packages / "guide" / "guide.md").write_text("workplace-fulltext-marker", encoding="utf-8")
        (packages / "tree" / "large.txt").write_text("workplace-metadata-marker", encoding="utf-8")
        (packages / "ignored.md").write_text("workplace-forbidden-marker", encoding="utf-8")
        (workplace / "registries").mkdir(parents=True)
        (workplace / "workplace.yaml").write_text(yaml.safe_dump({"schema_version": 1, "id": "smoke-workplace"}, sort_keys=False), encoding="utf-8")
        (workplace / "registries" / "package-roots.yaml").write_text(
            yaml.safe_dump({"schema_version": 1, "package_roots": [{"id": "local", "path": "packages", "status": "available"}]}, sort_keys=False),
            encoding="utf-8",
        )
        (packages / "package.yaml").write_text(
            yaml.safe_dump(
                {
                    "schema_version": 1,
                    "id": "docs.a",
                    "resources": [
                        {"id": "guide", "kind": "documentation", "path": "guide", "indexing": {"mode": "fulltext", "sources": [{"path": ".", "mode": "fulltext", "include": ["**/*.md"]}]}},
                        {"id": "tree", "kind": "source_tree", "path": "tree", "indexing": {"mode": "metadata"}},
                        {"id": "ignored", "kind": "documentation", "path": "ignored.md", "indexing": {"mode": "none"}},
                    ],
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )
        guide_id, tree_id = "docs.a:guide", "docs.a:tree"
        # Core Workplace maintenance needs no project context, Runtime, Ledger,
        # or session to create the one physical index.
        catalog = WorkplaceSearchCatalogReader(workplace)
        assert catalog.runtime_snapshot() == core.workplace_search_runtime_snapshot(workplace)
        index = ResourceSearchIndex(workplace, catalog.runtime_snapshot(), workplace)
        rebuilt = index.rebuild()
        assert rebuilt["status"] == "fresh" and rebuilt["resources"] == 2, rebuilt
        status = index.status()
        assert status["status"] == "fresh", status
        assert status["sqlite"]["fts5_available"], status
        database = workplace / "runtime" / "search" / "local-resource-search.sqlite"
        assert database.is_file()
        db = sqlite3.connect(database)
        try:
            assert db.execute("SELECT count(*) FROM resources").fetchone()[0] == 2
            assert db.execute("SELECT count(*) FROM resources WHERE resource_id=?", (guide_id,)).fetchone()[0] == 1
        finally:
            db.close()
        # Both projects query the same DB but receive only their snapshot grant.
        result_a = search(project_a, snapshot(guide_id, packages / "guide"), query="workplace-fulltext-marker", workplace_root=workplace)
        result_b = search(project_b, snapshot(tree_id, packages / "tree"), query="workplace-fulltext-marker", workplace_root=workplace)
        assert result_a["results"] and result_a["results"][0]["resource_id"] == guide_id, result_a
        assert result_b["results"] == [], result_b
        metadata = search(project_b, snapshot(tree_id, packages / "tree"), query="tree", workplace_root=workplace)
        assert metadata["results"] and metadata["results"][0]["resource_id"] == tree_id, metadata
        assert search(project_a, snapshot(guide_id, packages / "guide"), query="workplace-forbidden-marker", workplace_root=workplace)["results"] == []
        # pf.resolve receives the canonical package root for an authorized
        # resource and remains a project-snapshot authorization operation.
        project_snapshot = {"local_search_resources": [{"id": guide_id, "package_id": "docs.a", "kind": "documentation", "path_ref": {"registry": "package_roots", "id": "local", "relative_path": "docs.a/guide"}}]}
        (project_a / ".pf" / "contexts" / "project-context.snapshot.yaml").write_text(yaml.safe_dump(project_snapshot, sort_keys=False), encoding="utf-8")
        resolved = build_resource_resolve_service(project_a, workplace).resolve(resource_id=guide_id)
        assert Path(resolved["resource"]["local_root"]) == (packages / "guide").resolve(), resolved
    smoke_selected_versions(scratch_root)
    print(
        "PASS: Workplace FTS legacy grants, versioned MCP pages and ranking, "
        "scoped refresh and explicit recovery"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
