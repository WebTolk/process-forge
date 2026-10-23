"""Reproduce independent-review failures through actual SQLite and event paths."""

from __future__ import annotations

import ast
import io
import json
import os
import sqlite3
import time
from contextlib import closing, redirect_stdout
from pathlib import Path
from typing import Any
from unittest.mock import Mock

import pytest
from pf_cli.commands.search_index import (
    SearchIndexDoctorCommand,
    SearchIndexStatusCommand,
)

from processforge_core.resources import access, index_maintenance, local_search
from processforge_core.resources.access import ResourceSearchService
from processforge_core.resources.index_maintenance import (
    WorkplaceIndexMaintenanceService,
)
from processforge_core.resources.index_observation import (
    IndexObservationService,
    invalidation_notifications_path,
    invalidation_token_path,
    maintenance_state_path,
    pending_invalidation_notifications,
)
from processforge_core.resources.workplace_events import WorkplaceResourceEventJournal


def main_function(name):
    """Load only the actual owned Main adapter, keeping host bootstrap out."""
    from processforge_core.common import clock
    from processforge_core.common.paths import rel

    repository = Path(__file__).resolve().parents[2]
    path = repository / "tools/processforge.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    node = next(
        item
        for item in tree.body
        if isinstance(item, ast.FunctionDef) and item.name == name
    )
    environment = {
        "Path": Path,
        "Any": Any,
        "ROOT": repository,
        "_core_common_clock": clock,
        "rel": rel,
        "__file__": str(path),
    }
    exec(
        compile(ast.Module(body=[node], type_ignores=[]), str(path), "exec"),
        environment,
    )
    return environment[name], environment


class Reads:
    """Inject already-validated context identity, retaining real query filtering."""

    def __init__(self, snapshot):
        self.snapshot = snapshot

    def read_snapshot(self, _snapshots):
        return self.snapshot

    def context_checker(self):
        return lambda *_args, **_kwargs: {"status": "fresh"}

    def search_roots_resolver(self):
        return lambda snapshot: snapshot


@pytest.fixture
def corpus(tmp_path, monkeypatch):
    resources = []
    files = []
    for number in range(3):
        root = tmp_path / f"docs-{number}"
        root.mkdir()
        source = root / "guide.md"
        source.write_text(f"commonneedle oldtoken{number}", encoding="utf-8")
        resources.append({"id": f"review:{number}", "content_roots": [str(root)]})
        files.append(source)
    snapshot = {
        "search_index_scope": "workplace",
        "snapshot": {"checksum": "review-regressions"},
        "local_search_resources": resources,
    }
    catalogue = Mock()
    catalogue.runtime_snapshot.return_value = snapshot
    monkeypatch.setattr(
        index_maintenance, "WorkplaceSearchCatalogReader", Mock(return_value=catalogue)
    )
    monkeypatch.setattr(
        "processforge_core.resources.index_observation.WorkplaceSearchCatalogReader",
        Mock(return_value=catalogue),
    )
    return tmp_path, snapshot, files


def selected(snapshot, count):
    return {
        **snapshot,
        "search_index_scope": "project",
        "local_search_resources": snapshot["local_search_resources"][:count],
    }


def resource_changed(workplace):
    journal = WorkplaceResourceEventJournal(Mock(), Mock())
    journal.mark_search_index_dirty_after_resource_event(
        workplace, {"event_type": "resource.changed", "result": {"status": "complete"}}
    )


def test_targeted_pass_reads_only_selection_and_retains_other_rows(corpus, monkeypatch):
    root, snapshot, files = corpus
    service = WorkplaceIndexMaintenanceService(root)
    assert service.run()["results"][0]["status"] == "ok"
    files[0].write_text("commonneedle replacement", encoding="utf-8")
    original = Path.read_text

    def refuse_unselected(path, *args, **kwargs):
        if path in files[1:]:
            raise AssertionError("unselected document body was opened")
        return original(path, *args, **kwargs)

    with monkeypatch.context() as scoped:
        scoped.setattr(Path, "read_text", refuse_unselected)
        result = service.run_resources(["review:0", "review:0"])
    assert result["status"] == "fresh"
    assert result["resource_ids"] == ["review:0"]
    assert result["workplace_reconciled"] is False
    with closing(sqlite3.connect(local_search.index_path(root, root))) as db:
        assert db.execute("SELECT count(*) FROM resources").fetchone()[0] == 3
        assert (
            db.execute(
                "SELECT content FROM documents_fts WHERE resource_id=?", ("review:0",)
            )
            .fetchone()[0]
            .endswith("replacement")
        )
        assert (
            db.execute(
                "SELECT content FROM documents_fts WHERE resource_id=?", ("review:1",)
            )
            .fetchone()[0]
            .endswith("oldtoken1")
        )
    assert snapshot["search_index_scope"] == "workplace"
    assert len(snapshot["local_search_resources"]) == 3


def test_targeted_pass_cannot_acknowledge_pending_global_invalidation(corpus):
    root, _snapshot, _files = corpus
    service = WorkplaceIndexMaintenanceService(root)
    assert service.run()["results"][0]["status"] == "ok"
    service.mark_dirty(reason="other-resource-changed")
    assert service.run_resources(["review:0"])["status"] == "fresh"
    assert IndexObservationService(root).observe()["status"] != "fresh"
    state = json.loads(maintenance_state_path(root).read_text(encoding="utf-8"))
    assert state["scope"] == "resources"
    assert state["status"] == "failed"
    assert service.run()["results"][0]["status"] == "ok"


@pytest.mark.parametrize("selection", [[], ["unknown:resource"], "review:0", [None]])
def test_targeted_invalid_selection_never_opens_document(
    corpus, monkeypatch, selection
):
    root, _snapshot, files = corpus
    original = Path.read_text

    def refused(path, *args, **kwargs):
        if path in files:
            raise AssertionError("invalid selection read document body")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", refused)
    with pytest.raises(index_maintenance.IndexMaintenanceError):
        WorkplaceIndexMaintenanceService(root).run_resources(selection)
    assert not local_search.index_path(root, root).exists()


def test_targeted_pass_uses_canonical_bounded_writer_lock(corpus):
    root, _snapshot, _files = corpus
    with index_maintenance._writer_lock(root):
        with pytest.raises(index_maintenance.IndexMaintenanceError) as caught:
            WorkplaceIndexMaintenanceService(root).run_resources(["review:0"])
        assert caught.value.code == "search_maintenance_busy"
    assert not local_search.index_path(root, root).exists()


def test_targeted_pass_does_not_claim_success_after_raced_invalidation(
    corpus, monkeypatch
):
    root, _snapshot, _files = corpus
    service = WorkplaceIndexMaintenanceService(root)
    original = local_search._documents

    def invalidated(resources):
        documents = original(resources)
        service.mark_dirty(reason="during-targeted-pass")
        return documents

    monkeypatch.setattr(local_search, "_documents", invalidated)
    result = service.run_resources(["review:0"])
    assert result["status"] == "stale"
    assert result["error"] == "search_maintenance_invalidated"
    assert IndexObservationService(root).observe()["status"] != "fresh"


@pytest.mark.parametrize("legacy", ["metadata", "full_text", ""])
def test_targeted_external_reference_indexes_metadata_without_document_walk(
    corpus, monkeypatch, legacy
):
    root, snapshot, _files = corpus
    snapshot["local_search_resources"].append(
        {
            "id": "docs.example:guide",
            "title": "ExternalMetadataNeedle",
            "path_ref": {
                "registry": "external_resources",
                "id": "guide",
                "url": "https://example.org/guide",
            },
            "index_policy": legacy,
        }
    )
    monkeypatch.setattr(
        local_search,
        "_iter_source_files",
        Mock(side_effect=AssertionError("metadata walked bodies")),
    )
    result = WorkplaceIndexMaintenanceService(root).run_resources(
        ["docs.example:guide"]
    )
    assert result["resources"] == 1
    assert result["indexed"] == 1
    with closing(sqlite3.connect(local_search.index_path(root, root))) as db:
        assert (
            db.execute(
                "SELECT title FROM documents WHERE resource_id='docs.example:guide'"
            ).fetchone()[0]
            == "ExternalMetadataNeedle"
        )


def test_targeted_missing_local_root_is_not_successfully_indexed(corpus):
    root, _snapshot, files = corpus
    files[0].unlink()
    files[0].parent.rmdir()
    with pytest.raises(index_maintenance.IndexMaintenanceError) as caught:
        WorkplaceIndexMaintenanceService(root).run_resources(["review:0"])
    assert caught.value.code == "search_maintenance_resource_missing"


def test_targeted_disabled_resource_retires_only_its_cached_rows(corpus):
    root, snapshot, _files = corpus
    service = WorkplaceIndexMaintenanceService(root)
    assert service.run()["results"][0]["status"] == "ok"
    snapshot["local_search_resources"][0]["indexing"] = {"mode": "none"}
    assert service.run_resources(["review:0"])["resources"] == 0
    with closing(sqlite3.connect(local_search.index_path(root, root))) as db:
        assert db.execute(
            "SELECT resource_id FROM resources ORDER BY resource_id"
        ).fetchall() == [("review:1",), ("review:2",)]


def test_actual_main_batch_adapter_qualifies_only_success_ids_once(tmp_path, capsys):
    import argparse

    from processforge_core.common.yaml_dump import dump_yaml

    command, environment = main_function("command_knowledge_add_batch")
    manifest = tmp_path / "manifest.yaml"
    manifest.write_text("existing package", encoding="utf-8")
    batch = tmp_path / "batch.yaml"
    batch.write_text(
        dump_yaml(
            {
                "schema_version": 1,
                "resources": [{"id": "one"}, {"id": "broken"}, {"id": "two"}],
            }
        ),
        encoding="utf-8",
    )

    def build(_args, command_name, record):
        assert command_name == "knowledge-add-batch"
        if record["id"] == "broken":
            raise ValueError("private invalid resource")
        return object(), record, "added", manifest, tmp_path / "index.yaml", None

    owner = Mock()
    owner.run_resources.return_value = {"status": "fresh"}
    factory = Mock(return_value=owner)
    environment.update(
        build_knowledge_resource_add_plan=build,
        preflight_authoring_plan=Mock(),
        execute_authoring_plan=Mock(return_value={"state": "committed_audit_complete"}),
        WorkplaceIndexMaintenanceService=factory,
    )
    args = argparse.Namespace(
        workplace=str(tmp_path),
        package="docs.example",
        batch_file=str(batch),
        apply=True,
        dry_run=False,
        json=True,
    )
    assert command(args) == 1
    report = json.loads(capsys.readouterr().out)
    assert report["successful_resource_ids"] == ["docs.example:one", "docs.example:two"]
    assert [row["status"] for row in report["results"]] == ["ok", "error", "ok"]
    factory.assert_called_once_with(tmp_path, distribution_root=environment["ROOT"])
    owner.run_resources.assert_called_once_with(
        ["docs.example:one", "docs.example:two"]
    )
    assert "private invalid resource" not in json.dumps(report)


def batch_resource_changed(root, resource_id="0"):
    """Use the actual new command event route, rather than a raw backend dirty call."""
    journal = WorkplaceResourceEventJournal(Mock(), Mock())
    event = journal.resource_management_event(
        scope="workplace",
        command="knowledge-add-batch",
        event_type="knowledge.resource.added",
        target={"package_id": "review", "resource_id": resource_id},
        status="added",
        message="added",
    )
    journal.mark_search_index_dirty_after_resource_event(root, event)


@pytest.mark.parametrize("failure", ["permission", "missing", "unresolved"])
def test_established_index_cannot_drop_a_refused_or_missing_declared_root(
    corpus, monkeypatch, failure
):
    root, snapshot, files = corpus
    service = WorkplaceIndexMaintenanceService(root)
    assert service.run()["results"][0]["document_count"] == 3
    original = Path.resolve
    if failure == "missing":
        snapshot["local_search_resources"][1]["content_roots"] = [
            str(root / "missing-root")
        ]
    elif failure == "unresolved":
        snapshot["local_search_resources"][1].pop("content_roots")
        snapshot["local_search_resources"][1]["path_ref"] = {
            "registry": "knowledge_roots",
            "id": "unresolved",
        }

    def refused(path, *args, **kwargs):
        if (
            failure == "permission"
            and path == files[1].parent
            and kwargs.get("strict") is True
        ):
            raise PermissionError("private root location")
        return original(path, *args, **kwargs)

    with monkeypatch.context() as scoped:
        scoped.setattr(Path, "resolve", refused)
        result = service.run()
    assert result["results"][0]["status"] != "ok"
    assert IndexObservationService(root).observe()["status"] != "fresh"
    with closing(sqlite3.connect(local_search.index_path(root, root))) as db:
        assert db.execute("SELECT count(*) FROM documents").fetchone()[0] == 3
    assert "private root location" not in json.dumps(result)


def test_strict_collection_retains_intentional_containment_exclusion(
    tmp_path, monkeypatch
):
    root = tmp_path / "project"
    root.mkdir()
    documents = root / "documents"
    documents.mkdir()
    (documents / "guide.md").write_text("AllowedRootNeedle", encoding="utf-8")
    outside = tmp_path / "outside.md"
    outside.write_text("ForbiddenOutsideNeedle", encoding="utf-8")
    snapshot = {
        "snapshot": {"checksum": "strict-containment"},
        "local_search_resources": [
            {"id": "allowed", "content_roots": [str(documents)]},
            {
                "id": "denied",
                "path_ref": {"package": "self", "relative_path": "../outside.md"},
            },
        ],
    }
    original = Path.read_text

    def refused(path, *args, **kwargs):
        if path == outside:
            raise AssertionError("denied document body was opened")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", refused)
    assert local_search.build_index(root, snapshot)["resources"] == 1
    assert local_search.search(root, snapshot, query="AllowedRootNeedle")["total"] == 1
    assert (
        local_search.search(root, snapshot, query="ForbiddenOutsideNeedle")["total"]
        == 0
    )


@pytest.mark.parametrize("operation", ["verified-workplace", "scoped-rebuild"])
def test_established_source_failure_preserves_last_database(
    corpus, monkeypatch, operation
):
    import hashlib

    root, snapshot, files = corpus
    service = WorkplaceIndexMaintenanceService(root)
    assert service.run()["results"][0]["document_count"] == 3
    database = local_search.index_path(root, root)
    before = hashlib.sha256(database.read_bytes()).hexdigest()
    original = Path.read_text

    def refused(path, *args, **kwargs):
        if path == files[1]:
            raise PermissionError("private read location")
        return original(path, *args, **kwargs)

    with monkeypatch.context() as scoped:
        scoped.setattr(Path, "read_text", refused)
        if operation == "verified-workplace":
            assert service.run()["results"][0]["status"] != "ok"
        else:
            with pytest.raises(index_maintenance.IndexMaintenanceError):
                service.run_scoped(root, selected(snapshot, 3), operation="rebuild")
    assert database.is_file()
    assert hashlib.sha256(database.read_bytes()).hexdigest() == before
    with closing(sqlite3.connect(database)) as db:
        assert db.execute("SELECT count(*) FROM documents").fetchone()[0] == 3
    assert IndexObservationService(root).observe()["status"] != "fresh"
    assert service.run()["results"][0]["status"] == "ok"


@pytest.mark.parametrize("operation", ["verified-workplace", "selected"])
def test_resolved_root_disappearing_during_collection_retains_database(
    corpus, monkeypatch, operation
):
    root, snapshot, files = corpus
    service = WorkplaceIndexMaintenanceService(root)
    assert service.run()["results"][0]["document_count"] == 3
    database = local_search.index_path(root, root)
    before = database.read_bytes()
    files[0].write_text("changed explicit refresh", encoding="utf-8")
    collect = local_search._documents
    calls = 0

    def unavailable(resources):
        nonlocal calls
        calls += 1
        # The global verified pass first collects for its status check.
        if operation == "verified-workplace" and calls == 1:
            return collect(resources)
        original = files[1].parent
        parked = root / "temporarily-unavailable"
        original.rename(parked)
        try:
            return collect(resources)
        finally:
            parked.rename(original)

    with monkeypatch.context() as scoped:
        scoped.setattr(local_search, "_documents", unavailable)
        if operation == "verified-workplace":
            assert service.run()["results"][0]["status"] != "ok"
        else:
            with pytest.raises(index_maintenance.IndexMaintenanceError):
                service.run_resources(["review:0", "review:1", "review:2"])
    assert all(path.is_file() for path in files)
    assert database.read_bytes() == before
    with closing(sqlite3.connect(database)) as db:
        assert db.execute("SELECT count(*) FROM documents").fetchone()[0] == 3
    assert IndexObservationService(root).observe()["status"] != "fresh"
    assert service.run()["results"][0]["document_count"] == 3


def test_actual_audit_replay_retries_required_notification_until_delivered(
    corpus, monkeypatch
):
    from processforge_core.common.ids import safe_id

    root, _snapshot, _files = corpus
    service = WorkplaceIndexMaintenanceService(root)
    assert service.run()["results"][0]["status"] == "ok"
    journal = WorkplaceResourceEventJournal(
        Mock(), Mock(redact_telemetry_value=lambda value: value)
    )
    execute, environment = main_function("execute_authoring_effect")
    replay, replay_environment = main_function("run_post_commit_effect_records")
    environment.update(
        AuthoringPlan=Any,
        safe_id=safe_id,
        _workplace_resource_events=journal,
        write_resource_proposal=lambda *args, **kwargs: (
            "owned-proposal",
            root / "proposal.json",
        ),
        write_resource_management_report=lambda *args, **kwargs: root / "report.md",
    )
    replay_environment.update(
        AuthoringPlan=Any,
        execute_authoring_effect=execute,
        _authoring_journal_store=Mock(),
    )
    receipt = {
        "state": "committed",
        "post_commit_effects": [
            {
                "kind": "knowledge_audit",
                "effect_id": "owned-native-audit",
                "label": "knowledge-audit-events",
                "executable": True,
                "payload": {
                    "workplace_root": str(root),
                    "command": "knowledge-add-batch",
                    "resource_id": "0",
                    "events": [
                        {
                            "event_type": event_type,
                            "status": "updated",
                            "message": "committed update",
                            "target": {"package_id": "review", "resource_id": "0"},
                        }
                        for event_type in (
                            "knowledge.resource.added",
                            "package.updated",
                            "knowledge.package.updated",
                        )
                    ],
                },
            }
        ],
    }
    atomic = index_maintenance._atomic_write

    def refused(path, content):
        if path.parent == invalidation_notifications_path(root):
            raise OSError("private notification destination")
        return atomic(path, content)

    with monkeypatch.context() as scoped, redirect_stdout(io.StringIO()):
        scoped.setattr(index_maintenance, "_atomic_write", refused)
        for _attempt in range(5):
            with pytest.raises(
                index_maintenance.IndexMaintenanceError,
                match="search_maintenance_state_write_failed",
            ):
                replay(receipt, root / "authoring.json", None)
            assert receipt["state"] == "committed_audit_pending"
    with redirect_stdout(io.StringIO()):
        replay(receipt, root / "authoring.json", None)
    assert receipt["state"] == "committed_audit_complete"
    event_file = root / "runtime/events/events.ndjson"
    rows = [
        json.loads(line) for line in event_file.read_text(encoding="utf-8").splitlines()
    ]
    assert len(rows) == len({row["event_id"] for row in rows}) == 3
    assert len(pending_invalidation_notifications(root)) == 3
    assert IndexObservationService(root).observe()["status"] != "fresh"
    assert service.run_resources(["review:0"])["status"] == "fresh"
    assert not pending_invalidation_notifications(root)


@pytest.mark.parametrize("change", ["empty-remap", "added-root"])
def test_partial_pass_keeps_unselected_actual_root_changes_stale(
    corpus, monkeypatch, change
):
    root, snapshot, files = corpus
    snapshot["local_search_resources"][1]["path_ref"] = {
        "registry": "fixture",
        "id": "stable",
    }
    if change == "empty-remap":
        files[1].unlink()
    service = WorkplaceIndexMaintenanceService(root)
    assert service.run()["results"][0]["status"] == "ok"
    mapped = root / "remapped-root"
    mapped.mkdir()
    extra = mapped / "extra.md"
    extra.write_text("NewUnselectedRootNeedle", encoding="utf-8")
    if change == "empty-remap":
        snapshot["local_search_resources"][1]["content_roots"] = [str(mapped)]
    else:
        snapshot["local_search_resources"][1]["content_roots"].append(str(mapped))
    batch_resource_changed(root)
    original = Path.read_text

    def no_unselected_body(path, *args, **kwargs):
        if path in files[1:] or path == extra:
            raise AssertionError("unselected body read")
        return original(path, *args, **kwargs)

    with monkeypatch.context() as scoped:
        scoped.setattr(Path, "read_text", no_unselected_body)
        assert service.run_resources(["review:0"])["status"] == "fresh"
        assert IndexObservationService(root).observe()["status"] != "fresh"
    assert service.run()["results"][0]["status"] == "ok"
    assert (
        ResourceSearchService(root, root, Reads(selected(snapshot, 3))).search(
            query="NewUnselectedRootNeedle"
        )["total"]
        == 1
    )


def test_main_lifecycle_projection_discards_generation_raced_during_coverage(
    corpus, monkeypatch
):
    root, snapshot, files = corpus
    service = WorkplaceIndexMaintenanceService(root)
    assert service.run()["results"][0]["status"] == "ok"
    command, _environment = main_function("observe_search_index_for_project")
    original_coverage = local_search.authorized_coverage
    atomic = index_maintenance._atomic_write

    def fail_terminal(path, content):
        if (
            path == maintenance_state_path(root)
            and json.loads(content)["status"] == "complete"
        ):
            raise OSError("private terminal location")
        return atomic(path, content)

    def interleaved(*args, **kwargs):
        (files[0].parent / "extra.md").write_text(
            "NewGenerationNeedle", encoding="utf-8"
        )
        with monkeypatch.context() as scoped:
            scoped.setattr(index_maintenance, "_atomic_write", fail_terminal)
            assert service.run()["results"][0]["status"] == "error"
        return original_coverage(*args, **kwargs)

    monkeypatch.setattr(
        "processforge_core.project.snapshot.load_snapshot",
        lambda _root: selected(snapshot, 1),
    )
    monkeypatch.setattr(local_search, "authorized_coverage", interleaved)
    row = command(root, reason="project-context-refresh", project_root=root)["results"][
        0
    ]
    assert row["status"] != "ok"
    assert row["search_status"] != "fresh"
    assert row["generation"] is None
    assert row["document_count"] == 0
    assert IndexObservationService(root).observe()["status"] == "building"


def test_known_batch_notification_restores_search_without_reading_other_bodies(
    corpus, monkeypatch
):
    root, snapshot, files = corpus
    service = WorkplaceIndexMaintenanceService(root)
    assert service.run()["results"][0]["status"] == "ok"
    before = IndexObservationService(root).observe()["last_full_reconciliation"]
    files[0].write_text("NewSelectedSearchNeedle", encoding="utf-8")
    files[1].write_text("UnselectedMustWaitForFullPass", encoding="utf-8")
    batch_resource_changed(root)
    assert IndexObservationService(root).observe()["status"] != "fresh"
    original = Path.read_text

    def refuse_unselected(path, *args, **kwargs):
        if path in files[1:]:
            raise AssertionError("unselected body opened")
        return original(path, *args, **kwargs)

    with monkeypatch.context() as scoped:
        scoped.setattr(Path, "read_text", refuse_unselected)
        assert service.run_resources(["review:0"])["status"] == "fresh"
        observed = IndexObservationService(root).observe()
    assert observed["status"] == "fresh"
    assert observed["last_full_reconciliation"] == before
    assert not pending_invalidation_notifications(root)
    result = local_search.search(
        root,
        selected(snapshot, 1),
        query="NewSelectedSearchNeedle",
        workplace_root=root,
    )
    assert result["total"] == 1
    assert "resource_metadata_hash" not in result["items"][0]["metadata"]
    with closing(sqlite3.connect(local_search.index_path(root, root))) as db:
        assert (
            "oldtoken1"
            in db.execute(
                "SELECT content FROM documents_fts WHERE resource_id='review:1'"
            ).fetchone()[0]
        )


@pytest.mark.parametrize("other", [None, ["review:1"]])
def test_known_selection_cannot_clear_unknown_or_unselected_notifications(
    corpus, other
):
    root, _snapshot, _files = corpus
    service = WorkplaceIndexMaintenanceService(root)
    assert service.run()["results"][0]["status"] == "ok"
    service.mark_dirty(resource_ids=other)
    batch_resource_changed(root)
    assert service.run_resources(["review:0"])["status"] == "fresh"
    assert pending_invalidation_notifications(root)
    assert IndexObservationService(root).observe()["status"] != "fresh"


def test_notification_is_visible_when_its_token_publication_fails(corpus, monkeypatch):
    root, _snapshot, _files = corpus
    service = WorkplaceIndexMaintenanceService(root)
    assert service.run()["results"][0]["status"] == "ok"
    observer = IndexObservationService(root)
    before = observer.checkpoint()
    original = index_maintenance._atomic_write

    def refused(path, text):
        if path == invalidation_token_path(root):
            raise OSError("private publication location")
        return original(path, text)

    with monkeypatch.context() as scoped:
        scoped.setattr(index_maintenance, "_atomic_write", refused)
        with pytest.raises(index_maintenance.IndexMaintenanceError):
            service.mark_dirty(resource_ids=["review:0"])
    assert observer.checkpoint() != before
    assert observer.observe()["status"] != "fresh"
    assert service.run()["results"][0]["status"] == "ok"
    assert observer.observe()["status"] == "fresh"


def test_notification_retirement_failure_requires_explicit_recovery(
    corpus, monkeypatch
):
    root, _snapshot, _files = corpus
    service = WorkplaceIndexMaintenanceService(root)
    assert service.run()["results"][0]["status"] == "ok"
    batch_resource_changed(root)
    original = Path.unlink

    def refused(path, *args, **kwargs):
        if (
            path.parent == invalidation_notifications_path(root)
            and path.suffix == ".json"
        ):
            raise OSError("private notification location")
        return original(path, *args, **kwargs)

    with monkeypatch.context() as scoped:
        scoped.setattr(Path, "unlink", refused)
        with pytest.raises(index_maintenance.IndexMaintenanceError):
            service.run_resources(["review:0"])
    assert IndexObservationService(root).observe()["status"] != "fresh"
    assert service.run_resources(["review:0"])["status"] == "fresh"
    assert IndexObservationService(root).observe()["status"] != "fresh"
    assert service.run()["results"][0]["status"] == "ok"
    assert IndexObservationService(root).observe()["status"] == "fresh"


def test_selected_metadata_publication_does_not_hide_unselected_metadata_change(corpus):
    root, snapshot, _files = corpus
    service = WorkplaceIndexMaintenanceService(root)
    assert service.run()["results"][0]["status"] == "ok"
    snapshot["local_search_resources"][1]["title"] = "ChangedUnselectedMetadata"
    batch_resource_changed(root)
    assert service.run_resources(["review:0"])["status"] == "fresh"
    assert IndexObservationService(root).observe()["status"] != "fresh"
    assert service.run_resources(["review:1"])["status"] == "fresh"
    assert IndexObservationService(root).observe()["status"] == "fresh"


def test_known_notification_during_capture_survives_selected_completion(
    corpus, monkeypatch
):
    root, _snapshot, _files = corpus
    service = WorkplaceIndexMaintenanceService(root)
    assert service.run()["results"][0]["status"] == "ok"
    batch_resource_changed(root)
    original = local_search._documents

    def raced(resources):
        result = original(resources)
        batch_resource_changed(root)
        return result

    monkeypatch.setattr(local_search, "_documents", raced)
    assert service.run_resources(["review:0"])["status"] == "stale"
    assert len(pending_invalidation_notifications(root)) == 2
    assert IndexObservationService(root).observe()["status"] != "fresh"


def test_explicit_fulltext_external_policy_is_not_silently_changed(corpus):
    root, snapshot, _files = corpus
    snapshot["local_search_resources"].append(
        {
            "id": "review:external",
            "path_ref": {"registry": "external_resources", "id": "external"},
            "indexing": {"enabled": True, "mode": "fulltext"},
        }
    )
    with pytest.raises(index_maintenance.IndexMaintenanceError):
        WorkplaceIndexMaintenanceService(root).run_resources(["review:external"])


def test_actual_document_read_failure_is_incomplete_until_recovered(
    corpus, monkeypatch
):
    root, _snapshot, files = corpus
    service = WorkplaceIndexMaintenanceService(root)
    original = Path.read_text

    def refused(path, *args, **kwargs):
        if path == files[1]:
            raise PermissionError("private-document-location")
        return original(path, *args, **kwargs)

    with monkeypatch.context() as scoped:
        scoped.setattr(Path, "read_text", refused)
        for _ in range(2):
            result = service.run()
            assert result["results"][0]["status"] != "ok"
            assert "private-document-location" not in json.dumps(result)
            assert (
                json.loads(maintenance_state_path(root).read_text(encoding="utf-8"))[
                    "status"
                ]
                == "failed"
            )
            assert IndexObservationService(root).observe()["status"] != "fresh"
    recovered = service.run()
    assert recovered["results"][0]["status"] == "ok"
    assert recovered["results"][0]["document_count"] == 3
    assert IndexObservationService(root).observe()["status"] == "fresh"


def test_real_directory_scan_failure_is_incomplete(corpus, monkeypatch):
    root, _snapshot, files = corpus
    original = os.scandir

    def refused(path):
        if not isinstance(path, int) and Path(path) == files[1].parent:
            raise PermissionError("private-directory-location")
        return original(path)

    with monkeypatch.context() as scoped:
        scoped.setattr(os, "scandir", refused)
        result = WorkplaceIndexMaintenanceService(root).run()
    assert result["results"][0]["status"] != "ok"
    assert "private-directory-location" not in json.dumps(result)
    assert IndexObservationService(root).observe()["status"] != "fresh"
    assert WorkplaceIndexMaintenanceService(root).run()["results"][0]["status"] == "ok"


@pytest.mark.parametrize("count", [0, 1])
def test_project_counts_exclude_unselected_corpus(corpus, count):
    root, snapshot, _files = corpus
    assert WorkplaceIndexMaintenanceService(root).run()["results"][0]["status"] == "ok"
    service = ResourceSearchService(root, root, Reads(selected(snapshot, count)))
    for view in (service.readiness(), service.search(query="commonneedle")["search"]):
        assert view["resource_count"] == count
        assert view["document_count"] == count
        assert view["status"] == ("ready" if count else "empty")
    assert IndexObservationService(root).observe()["document_count"] == 3


def test_query_discards_generation_with_unpublished_terminal_state(corpus, monkeypatch):
    root, snapshot, files = corpus
    writer = WorkplaceIndexMaintenanceService(root)
    assert writer.run()["results"][0]["status"] == "ok"
    original_coverage = access.authorized_coverage
    original_write = index_maintenance._atomic_write

    def fail_terminal(path, text):
        if (
            path.name == "maintenance-state.json"
            and json.loads(text)["status"] == "complete"
        ):
            raise OSError("private-terminal-location")
        return original_write(path, text)

    def interleave(*args, **kwargs):
        files[0].write_text("newgenerationneedle", encoding="utf-8")
        with monkeypatch.context() as scoped:
            scoped.setattr(index_maintenance, "_atomic_write", fail_terminal)
            failed = writer.run()
        assert failed["results"][0]["error"] == "search_maintenance_state_write_failed"
        return original_coverage(*args, **kwargs)

    monkeypatch.setattr(access, "authorized_coverage", interleave)
    result = ResourceSearchService(root, root, Reads(selected(snapshot, 1))).search(
        query="newgenerationneedle"
    )
    assert result["search_status"] != "fresh"
    assert result["search"]["status"] != "ready"
    assert result["total"] == 0
    assert result["results"] == []
    assert IndexObservationService(root).observe()["status"] == "building"


def test_resource_event_during_document_capture_survives_terminal_write(
    corpus, monkeypatch
):
    root, snapshot, files = corpus
    writer = WorkplaceIndexMaintenanceService(root)
    assert writer.run()["results"][0]["status"] == "ok"
    resource_changed(root)
    original_documents = local_search._documents
    calls = 0

    def interleave(resources):
        nonlocal calls
        calls += 1
        documents = original_documents(resources)
        if calls == 2:
            files[0].write_text("knownmutationneedle", encoding="utf-8")
            resource_changed(root)
        return documents

    with monkeypatch.context() as scoped:
        scoped.setattr(local_search, "_documents", interleave)
        result = writer.run()
    assert calls == 2
    assert result["results"][0]["status"] != "ok"
    assert IndexObservationService(root).observe()["status"] != "fresh"
    assert writer.run()["results"][0]["status"] == "ok"
    answer = ResourceSearchService(root, root, Reads(selected(snapshot, 1))).search(
        query="knownmutationneedle"
    )
    assert answer["total"] == 1


def test_resource_event_does_not_write_sqlite_outside_canonical_lock(
    corpus, monkeypatch
):
    root, _snapshot, _files = corpus
    assert WorkplaceIndexMaintenanceService(root).run()["results"][0]["status"] == "ok"
    connect = Mock(side_effect=AssertionError("invalidation must not write SQLite"))
    with index_maintenance._writer_lock(root):
        with monkeypatch.context() as scoped:
            scoped.setattr(local_search.sqlite3, "connect", connect)
            resource_changed(root)
    connect.assert_not_called()
    assert IndexObservationService(root).observe()["status"] != "fresh"


def test_project_pass_cannot_acknowledge_global_pending_invalidation(corpus):
    root, snapshot, files = corpus
    writer = WorkplaceIndexMaintenanceService(root)
    assert writer.run()["results"][0]["status"] == "ok"
    files[2].write_text("pendingoutsideproject", encoding="utf-8")
    resource_changed(root)
    writer.run_scoped(root, selected(snapshot, 1), operation="refresh")
    assert IndexObservationService(root).observe()["status"] != "fresh"
    recovered = writer.run(verify_files=False)
    assert recovered["results"][0]["status"] == "ok"
    answer = ResourceSearchService(root, root, Reads(selected(snapshot, 3))).search(
        query="pendingoutsideproject"
    )
    assert answer["total"] == 1


def test_late_notification_survives_terminal_publication(corpus, monkeypatch):
    root, snapshot, files = corpus
    writer = WorkplaceIndexMaintenanceService(root)
    assert writer.run()["results"][0]["status"] == "ok"
    original = index_maintenance._atomic_write
    notified = False

    def interleave(path, text):
        nonlocal notified
        if (
            not notified
            and path.name == "maintenance-state.json"
            and json.loads(text)["status"] == "complete"
        ):
            notified = True
            files[0].write_text("latemutationneedle", encoding="utf-8")
            resource_changed(root)
        return original(path, text)

    with monkeypatch.context() as scoped:
        scoped.setattr(index_maintenance, "_atomic_write", interleave)
        writer.run()
    assert notified
    assert IndexObservationService(root).observe()["status"] != "fresh"
    assert writer.run(verify_files=False)["results"][0]["status"] == "ok"
    assert (
        ResourceSearchService(root, root, Reads(selected(snapshot, 1))).search(
            query="latemutationneedle"
        )["total"]
        == 1
    )


def test_notification_publication_failure_preserves_previous_token(corpus, monkeypatch):
    root, _snapshot, _files = corpus
    writer = WorkplaceIndexMaintenanceService(root)
    writer.mark_dirty()
    token = root / "runtime/search/invalidation.token"
    before = token.read_bytes()
    original = os.replace

    def refused(source, destination):
        if Path(destination) == token:
            raise PermissionError("private-notification-location")
        return original(source, destination)

    with monkeypatch.context() as scoped:
        scoped.setattr(os, "replace", refused)
        with pytest.raises(index_maintenance.IndexMaintenanceError) as caught:
            resource_changed(root)
    assert str(caught.value) == "search_maintenance_state_write_failed"
    assert token.read_bytes() == before
    assert IndexObservationService(root).observe()["status"] != "fresh"


def test_completed_concurrent_generation_is_discarded_until_next_query(
    corpus, monkeypatch
):
    root, snapshot, files = corpus
    writer = WorkplaceIndexMaintenanceService(root)
    assert writer.run()["results"][0]["status"] == "ok"
    original = access.authorized_coverage

    def interleave(*args, **kwargs):
        files[0].write_text("completednewgeneration", encoding="utf-8")
        assert writer.run()["results"][0]["status"] == "ok"
        return original(*args, **kwargs)

    service = ResourceSearchService(root, root, Reads(selected(snapshot, 1)))
    with monkeypatch.context() as scoped:
        scoped.setattr(access, "authorized_coverage", interleave)
        answer = service.search(query="completednewgeneration")
    assert answer["total"] == 0
    assert answer["search_status"] == "stale"
    assert answer["degraded_reason"] == "search_maintenance_state_changed"
    assert service.search(query="completednewgeneration")["total"] == 1


def test_opaque_marker_bytes_require_explicit_reconciliation(corpus):
    root, _snapshot, _files = corpus
    writer = WorkplaceIndexMaintenanceService(root)
    assert writer.run()["results"][0]["status"] == "ok"
    marker = root / "runtime/search/invalidation.token"
    marker.write_bytes(b"\xff\x00opaque invalidation")
    assert IndexObservationService(root).observe()["status"] != "fresh"
    assert writer.run(verify_files=False)["results"][0]["status"] == "ok"
    assert IndexObservationService(root).observe()["status"] == "fresh"


def test_project_lifecycle_observation_hides_workplace_counts(corpus, monkeypatch):
    root, snapshot, _files = corpus
    assert WorkplaceIndexMaintenanceService(root).run()["results"][0]["status"] == "ok"
    observe, _environment = main_function("observe_search_index_for_project")
    monkeypatch.setattr(
        "processforge_core.project.snapshot.load_snapshot",
        Mock(return_value=selected(snapshot, 1)),
    )
    result = observe(
        root, reason="project-context-refresh", project_root=root / "project"
    )
    row = result["results"][0]
    assert row["document_count"] == 1
    assert row["stale_resource_count"] is None
    assert row["failed_file_count"] is None
    assert (
        observe(root, reason="explicit-workplace-observation")["results"][0][
            "document_count"
        ]
        == 3
    )


def test_main_maps_required_notification_failure_to_safe_nonzero(capsys):
    main, environment = main_function("main")
    application = Mock()
    application.run.side_effect = index_maintenance.IndexMaintenanceError(
        "search_maintenance_state_write_failed"
    )
    environment.update(
        {
            "CliApplication": Mock(return_value=application),
            "build_parser": Mock(),
            "project_id": Mock(),
        }
    )
    output = io.StringIO()
    with redirect_stdout(output):
        assert main([]) == 1
    assert output.getvalue() == "FAIL: search_maintenance_state_write_failed\n"
    assert capsys.readouterr().err == ""


@pytest.mark.parametrize("operation", ["status", "doctor"])
def test_read_only_cli_observes_pending_invalidation(corpus, operation):
    import argparse

    root, snapshot, _files = corpus
    writer = WorkplaceIndexMaintenanceService(root)
    assert writer.run()["results"][0]["status"] == "ok"
    project = selected(snapshot, 1)
    writer.run_scoped(root, project, operation="refresh")
    captured = []

    def doctor(status, _context):
        captured.append(status)
        return 0

    arguments = {
        "index_factory": local_search.ResourceSearchIndex,
        "snapshot_reader": lambda *_args: ({"status": "fresh"}, project),
    }
    command = (
        SearchIndexStatusCommand(**arguments)
        if operation == "status"
        else SearchIndexDoctorCommand(**arguments, doctor_formatter=doctor)
    )
    initial = io.StringIO()
    with redirect_stdout(initial):
        command.execute(argparse.Namespace(project_root=str(root), workplace=str(root)))
    expected_path = str(root / "runtime/search/local-resource-search.sqlite")
    if operation == "status":
        assert "STATUS: fresh" in initial.getvalue()
        assert "INDEX: " + expected_path in initial.getvalue()
    else:
        assert captured[0]["path"] == expected_path
    captured.clear()
    resource_changed(root)
    output = io.StringIO()
    with redirect_stdout(output):
        command.execute(argparse.Namespace(project_root=str(root), workplace=str(root)))
    if operation == "status":
        assert "STATUS: fresh" not in output.getvalue()
        assert "STATUS: stale" in output.getvalue()
    else:
        assert captured[0]["status"] == "stale"
    assert IndexObservationService(root).observe()["status"] == "stale"


def test_pending_invalidation_allows_explicit_schema_recovery(corpus):
    root, _snapshot, _files = corpus
    writer = WorkplaceIndexMaintenanceService(root)
    assert writer.run()["results"][0]["status"] == "ok"
    database = root / "runtime/search/local-resource-search.sqlite"
    with closing(sqlite3.connect(database)) as connection:
        connection.execute("UPDATE meta SET value='999' WHERE key='schema_version'")
        connection.commit()
    resource_changed(root)
    assert IndexObservationService(root).observe()["status"] != "fresh"
    recovered = writer.run()
    assert recovered["results"][0]["status"] == "ok"
    assert recovered["results"][0]["action"] == "rebuild"
    assert IndexObservationService(root).observe()["status"] == "fresh"


@pytest.mark.parametrize("layer", ["backend", "service"])
def test_query_handles_busy_between_status_and_sql_without_wait(
    corpus, monkeypatch, layer
):
    root, snapshot, _files = corpus
    assert WorkplaceIndexMaintenanceService(root).run()["results"][0]["status"] == "ok"
    database = root / "runtime/search/local-resource-search.sqlite"
    writer = sqlite3.connect(database)
    original_status = local_search.index_status
    locked = False

    def interleave(*args, **kwargs):
        nonlocal locked
        state = original_status(*args, **kwargs)
        if not locked:
            assert state["status"] == "fresh"
            writer.execute("BEGIN EXCLUSIVE")
            locked = True
        return state

    try:
        started = time.monotonic()
        if layer == "backend":
            with monkeypatch.context() as scoped:
                scoped.setattr(local_search, "index_status", interleave)
                result = local_search.search(
                    root,
                    selected(snapshot, 1),
                    query="commonneedle",
                    workplace_root=root,
                )
        else:
            original_search = local_search.ResourceSearchIndex.search

            def query(index, **kwargs):
                with monkeypatch.context() as scoped:
                    scoped.setattr(local_search, "index_status", interleave)
                    return original_search(index, **kwargs)

            with monkeypatch.context() as scoped:
                scoped.setattr(local_search.ResourceSearchIndex, "search", query)
                result = ResourceSearchService(
                    root, root, Reads(selected(snapshot, 1))
                ).search(query="commonneedle")
            assert result["search"]["status"] != "ready"
        assert locked
        assert time.monotonic() - started < 1.5
        assert result["search_status"] == "degraded"
        assert result["degraded_reason"] == "search_database_busy"
        assert result["results"] == [] and result["total"] == 0
    finally:
        writer.rollback()
        writer.close()
