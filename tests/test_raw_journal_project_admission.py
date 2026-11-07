"""Actual SQL admission isolates foreign history without bypassing migration."""

import json
from pathlib import Path

import pytest
from pf_runtime.raw_ingress_kernel import NativeAgentEvent, RawIngressKernel

from processforge_core.sqlite_storage import JournalMigrationRequired


def event(project: Path) -> NativeAgentEvent:
    return NativeAgentEvent(
        "generic", "test", "reply", {"text": "first"}, source_project_ref=str(project)
    )


def legacy(root: Path, content: str) -> Path:
    path = root / "runtime/agent-events/raw/v1/history.ndjson"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def test_foreign_history_allows_first_sql_receipt(tmp_path: Path) -> None:
    workplace, project = tmp_path / "workplace", tmp_path / "fresh"
    old = legacy(
        workplace, json.dumps({"source_project_ref": str(tmp_path / "foreign")}) + "\n"
    )
    before = old.read_bytes()
    kernel = RawIngressKernel(workplace, flow_root=project / ".pf")
    assert kernel.ingest(event(project)).accepted
    assert kernel.database.is_file()
    assert kernel.ingest(event(project)).deduplicated
    assert old.read_bytes() == before
    with kernel.storage.connection(kernel.database) as connection:
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


@pytest.mark.parametrize(
    "kind",
    [
        "own",
        "mixed",
        "unknown",
        "relative",
        "bad_json",
        "duplicate",
        "nonfinite",
        "non_object",
        "local",
        "workplace",
    ],
)
def test_relevant_or_uncertain_history_requires_migration(
    tmp_path: Path, kind: str
) -> None:
    workplace, project = tmp_path / "workplace", tmp_path / "fresh"
    own = json.dumps({"source_project_ref": str(project)})
    foreign = json.dumps({"source_project_ref": str(tmp_path / "foreign")})
    content = {
        "own": own,
        "mixed": foreign + "\n" + own,
        "unknown": "{}",
        "relative": '{"source_project_ref":"relative"}',
        "bad_json": "{",
        "duplicate": '{"source_project_ref":'
        + json.dumps(str(project))
        + ',"source_project_ref":'
        + json.dumps(str(tmp_path / "foreign"))
        + "}",
        "nonfinite": foreign[:-1] + ',"value":NaN}',
        "non_object": "[]",
        "local": foreign,
        "workplace": foreign,
    }[kind]
    old = legacy(project / ".pf" if kind == "local" else workplace, content + "\n")
    before = old.read_bytes()
    kernel = RawIngressKernel(
        workplace, flow_root=None if kind == "workplace" else project / ".pf"
    )
    with pytest.raises(
        JournalMigrationRequired, match="raw_journal_migration_required"
    ):
        kernel.ingest(event(project))
    assert not kernel.database.exists()
    assert old.read_bytes() == before
