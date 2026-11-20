"""Regressions for deferred advisory root access and material-check ordering."""

from __future__ import annotations

import hashlib
import importlib
from pathlib import Path

import pytest


@pytest.fixture
def owners(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2] / "src"))
    validation = importlib.import_module("processforge_core.evidence.validation")
    authoring = importlib.import_module("processforge_core.evidence.authoring")
    return validation.EvidenceValidationService, authoring.ArtifactAuthoringService


@pytest.mark.parametrize(
    "evidence",
    [
        "note",
        {"kind": "gate", "id": "example", "status": "passed"},
        {
            "status": "not_applicable",
            "reason": "This evidence-only contribution has no separate deployment.",
            "evidence": ["review-receipt"],
        },
        {"authoring": {}},
    ],
)
def test_pathless_evidence_never_reads_project_root(owners, evidence):
    validation, _ = owners

    def forbidden_root():
        raise AssertionError("Pathless evidence must not resolve a project root")

    validator = validation(forbidden_root, lambda: "fixed", str, lambda _: "unused")
    normalized, blockers = validator.normalize(evidence)
    assert blockers == []
    assert len(normalized) == 1
    assert normalized[0]["recorded_at"] == "fixed"
    if isinstance(evidence, dict) and evidence.get("status") == "not_applicable":
        assert normalized[0]["authoring_review"]["coverage"] == "justification_only"
    elif isinstance(evidence, dict) and "authoring" in evidence:
        assert normalized[0]["authoring_review"]["reason"] == "no_file"
    else:
        assert "authoring_review" not in normalized[0]


def test_actual_authoring_follows_material_callbacks(owners, tmp_path):
    validation, _ = owners
    text = tmp_path / "evidence.md"
    text.write_text(
        "# Evidence\n\nCompleted checks have actual receipts.\n", encoding="utf-8"
    )
    digest = hashlib.sha256(text.read_bytes()).hexdigest()
    trace = []

    def root():
        trace.append("root")
        return tmp_path

    def relative(path):
        trace.append("relative")
        return path.relative_to(tmp_path).as_posix()

    def hash_file(path):
        trace.append("hash")
        return hashlib.sha256(path.read_bytes()).hexdigest()

    validator = validation(
        root, lambda: trace.append("clock") or "fixed", relative, hash_file
    )
    assert trace == []
    normalized, blockers = validator.normalize({"path": "evidence.md"})
    assert blockers == []
    assert trace == ["clock", "root", "root", "relative", "hash", "root"]
    assert normalized[0]["sha256"] == "sha256:" + digest
    review = normalized[0]["authoring_review"]
    assert review["status"] == "reviewed"
    assert review["reviewed_sha256"] == "sha256:" + digest
    assert review["coverage"] == "text_and_simple_inline_links"


def test_authoring_construction_and_unsupported_file_do_not_read_root(owners, tmp_path):
    _, authoring = owners

    def forbidden_root():
        raise AssertionError("No text-file operation needs a project root here")

    reviewer = authoring(forbidden_root, lambda _: None)
    assert reviewer.review({}, None) is None
    result = reviewer.review({}, tmp_path / "receipt.json")
    assert result["status"] == "skipped"
    assert result["reason"] == "unsupported_format"


def test_lazy_root_preserves_containment_before_file_open(
    owners, tmp_path, monkeypatch
):
    _, authoring = owners
    root = tmp_path / "project"
    root.mkdir()
    outside = tmp_path / "outside.md"
    outside.write_text("# Outside\n", encoding="utf-8")
    digest = hashlib.sha256(outside.read_bytes()).hexdigest()
    original_open = Path.open

    def guarded_open(path, *args, **kwargs):
        assert path != outside, "Outside file must be refused before reading"
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", guarded_open)
    reviewer = authoring(lambda: root, lambda _: None)
    result = reviewer.review({"sha256": "sha256:" + digest}, outside)
    assert result["status"] == "skipped"
    assert result["reason"] == "unreadable_or_outside_project"
    assert [item["code"] for item in result["findings"]] == [
        "authoring_file_unreadable"
    ]
