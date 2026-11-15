"""CLI bootstrap preflight regression tests; native capability is stubbed."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pf_native_control as native
import pytest

from processforge_core.configuration import ConfigurationProvider, PFConfig
from processforge_core.database import SchemaManager
from processforge_core.executions.composition import select_execution_storage
from processforge_core.maintenance import fresh_project as fresh
from processforge_core.maintenance.contracts import MaintenanceError
from processforge_core.project.metadata import ProjectMetadataReader


@pytest.fixture
def cli(monkeypatch):
    source = Path(__file__).resolve().parents[2]
    name = "bootstrap_preflight_cli_fixture"
    spec = importlib.util.spec_from_file_location(
        name, source / "tools/processforge.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, name, module)
    spec.loader.exec_module(module)
    monkeypatch.setattr(native, "supports_owned_execution", lambda: True)
    monkeypatch.setattr(
        module, "build_configuration_provider", lambda **kwargs: provider()
    )

    def apply_entry(project, plan):
        # Exercise ordering and byte preservation without native entry ownership.
        (project / "AGENTS.md").write_text("PF:ENTRY:BEGIN\n")
        return {"status": "complete", "agent_entry": {}}

    monkeypatch.setattr(module.project_initialization, "apply_agent_entry", apply_entry)

    def first_event(project, event, **kwargs):
        assert event == "project.onboarding.started"
        assert fresh._receipt(project)["state"] == "ready"
        manifest = ProjectMetadataReader(project).workplace_manifest()
        workplace = manifest.parent if manifest else None
        assert select_execution_storage(
            project, workplace, configuration=provider()
        ).repository
        raise RuntimeError("ready before first event")

    monkeypatch.setattr(
        module._process_event_recorder, "emit_process_event", first_event
    )
    return module


def provider():
    return ConfigurationProvider.pinned(PFConfig())


def files_for(root, workplace=None):
    return {
        root / ".pf/process-forge.yaml": "project:\n  id: fresh-owner\n",
        root / ".pf/process-forge.local.yaml": json.dumps(
            {"workplace": {"manifest": str(workplace / "workplace.yaml")}}
            if workplace
            else {}
        )
        + "\n",
    }


def request_for(cli, root, **kwargs):
    return {
        "project_root": root,
        "force": True,
        "agent_entry_plan": cli.project_initialization.plan_agent_entry(root),
        **kwargs,
    }


def bytes_before(root):
    return {
        path.relative_to(root): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


def make_project(root, *, state="ready", workplace=None):
    root.mkdir()
    (root / "AGENTS.md").write_bytes(b"# Existing user instructions\r\n")
    assert fresh.create_project_storage_root(root)
    if state == "unbound":
        return
    for path, content in files_for(root, workplace).items():
        path.write_text(content, encoding="utf-8")
    if state == "authored":
        return
    if state == "pending":
        with patch.object(
            SchemaManager, "initialize", side_effect=RuntimeError("stop")
        ):
            with pytest.raises(RuntimeError, match="stop"):
                fresh.initialize_project_storage(
                    root, workplace, configuration=provider()
                )
    else:
        fresh.initialize_project_storage(root, workplace, configuration=provider())


@pytest.mark.parametrize(
    "fault",
    [
        "proposed_owner",
        "current_owner",
        "proposed_route",
        "current_route",
        "requested_route",
        "corrupt_json",
        "physical_root",
        "domains_missing",
        "domain_duplicate",
        "domain_owner",
        "domain_uuid",
        "receipt_state_type",
        "proposed_yaml",
        "current_yaml",
    ],
)
def test_force_conflict_refuses_before_any_authoring(tmp_path, cli, fault):
    root = tmp_path / "project"
    make_project(root)
    files = files_for(root)
    request = request_for(cli, root)
    receipt_path = root / ".pf" / fresh.RECEIPT
    receipt = json.loads(receipt_path.read_bytes())
    other = tmp_path / "other" / "workplace.yaml"
    if fault == "proposed_owner":
        files[root / ".pf/process-forge.yaml"] = "project:\n  id: changed-owner\n"
    elif fault == "current_owner":
        (root / ".pf/process-forge.yaml").write_text("project:\n  id: changed-owner\n")
    elif fault in {"proposed_route", "current_route"}:
        content = json.dumps({"workplace": {"manifest": str(other)}})
        if fault == "proposed_route":
            files[root / ".pf/process-forge.local.yaml"] = content
        else:
            (root / ".pf/process-forge.local.yaml").write_text(content)
    elif fault == "requested_route":
        request["workplace"] = other
    elif fault == "corrupt_json":
        receipt_path.write_bytes(b"{corrupt")
    elif fault == "proposed_yaml":
        files[root / ".pf/process-forge.yaml"] = "project: [invalid"
    elif fault == "current_yaml":
        (root / ".pf/process-forge.yaml").write_text("project: [invalid")
    else:
        if fault == "physical_root":
            receipt["root_identity"][1] += 1
        elif fault == "domains_missing":
            receipt["domains"] = None
        elif fault == "domain_duplicate":
            receipt["domains"][1] = receipt["domains"][0]
        elif fault == "domain_owner":
            receipt["domains"][0]["owner_id"] = "other"
        elif fault == "domain_uuid":
            receipt["domains"][0]["store_id"] = "invalid"
        elif fault == "receipt_state_type":
            receipt["state"] = []
        receipt_path.write_text(json.dumps(receipt))
    before = bytes_before(root)
    with pytest.raises(MaintenanceError):
        cli.execute_project_initialization(request, files)
    assert bytes_before(root) == before


@pytest.mark.parametrize("state", ["new", "unbound", "authored", "pending", "ready"])
@pytest.mark.parametrize("enrolled", [False, True])
def test_legitimate_initialization_and_recovery(tmp_path, cli, state, enrolled):
    root = tmp_path / "project"
    workplace = tmp_path / "workplace" if enrolled else None
    if workplace:
        workplace.mkdir()
        (workplace / "workplace.yaml").write_text("workplace:\n  id: workplace-owner\n")
    if state == "new":
        root.mkdir()
    else:
        make_project(root, state=state, workplace=workplace)
    receipt = fresh._receipt(root) if state != "new" else None
    binding = root / ".pf/data/execution-storage.json"
    original_binding = binding.read_bytes() if binding.exists() else None
    with pytest.raises(RuntimeError, match="ready before first event"):
        cli.execute_project_initialization(
            request_for(
                cli, root, workplace=workplace / "workplace.yaml" if workplace else None
            ),
            files_for(root, workplace),
        )
    after = fresh._receipt(root)
    assert after["state"] == "ready"
    assert after["project_id"] == "fresh-owner"
    if receipt:
        assert after["creation_id"] == receipt["creation_id"]
        if receipt["domains"] is not None:
            assert after["domains"] == receipt["domains"]
    if original_binding is not None:
        assert binding.read_bytes() == original_binding
    assert "PF:ENTRY:BEGIN" in (root / "AGENTS.md").read_text()


def test_unbound_receipt_with_conflicting_route_is_not_recovery(tmp_path, cli):
    root = tmp_path / "project"
    make_project(root, state="unbound")
    receipt_path = root / ".pf" / fresh.RECEIPT
    receipt = json.loads(receipt_path.read_bytes())
    receipt["workplace"] = "already-bound"
    receipt_path.write_text(json.dumps(receipt))
    before = bytes_before(root)
    with pytest.raises(MaintenanceError):
        cli.execute_project_initialization(request_for(cli, root), files_for(root))
    assert bytes_before(root) == before


def test_unknown_existing_root_requires_migration_before_authoring(
    tmp_path, cli, monkeypatch
):
    root = tmp_path / "project"
    (root / ".pf").mkdir(parents=True)
    (root / "AGENTS.md").write_bytes(b"preserve")
    before = bytes_before(root)

    def migration_required(*args):
        raise MaintenanceError("migration_required")

    monkeypatch.setattr(cli, "_storage_first_write", migration_required)
    with pytest.raises(MaintenanceError, match="migration_required"):
        cli.execute_project_initialization(request_for(cli, root), files_for(root))
    assert bytes_before(root) == before


def test_force_cannot_remove_existing_enrollment(tmp_path, cli):
    workplace = tmp_path / "workplace"
    workplace.mkdir()
    (workplace / "workplace.yaml").write_text("workplace:\n  id: workplace-owner\n")
    root = tmp_path / "project"
    make_project(root, workplace=workplace)
    before = bytes_before(root)
    with pytest.raises(MaintenanceError, match="storage_enrollment_conflict"):
        cli.execute_project_initialization(
            request_for(cli, root, workplace=workplace / "workplace.yaml"),
            files_for(root),
        )
    assert bytes_before(root) == before


def test_nonforce_candidate_does_not_change_effective_owner(tmp_path, cli):
    root = tmp_path / "project"
    make_project(root)
    files = files_for(root)
    manifest = root / ".pf/process-forge.yaml"
    original = manifest.read_bytes()
    files[manifest] = "project:\n  id: candidate-owner\n"
    with pytest.raises(RuntimeError, match="ready before first event"):
        cli.execute_project_initialization(request_for(cli, root, force=False), files)
    assert manifest.read_bytes() == original
    assert fresh._receipt(root)["project_id"] == "fresh-owner"
    assert manifest.with_suffix(".yaml.candidate").read_text() == files[manifest]


@pytest.mark.parametrize(
    "state,fault", [("ready", "missing"), ("ready", "binding"), ("pending", "binding")]
)
def test_main_storage_conflict_refuses_before_authoring(tmp_path, cli, state, fault):
    from processforge_core.executions.model import ExecutionError

    root = tmp_path / "project"
    make_project(root, state=state)
    if fault == "missing":
        (root / ".pf/data/pf.sqlite3").unlink()
    else:
        binding = root / ".pf/data/execution-storage.json"
        value = json.loads(binding.read_bytes())
        value["profile_id"] = "changed-profile"
        binding.write_text(json.dumps(value))
    request = request_for(cli, root)
    before = bytes_before(root)
    with pytest.raises((MaintenanceError, ExecutionError)):
        cli.execute_project_initialization(request, files_for(root))
    assert bytes_before(root) == before
