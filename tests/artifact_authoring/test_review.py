from __future__ import annotations

import copy
import hashlib
from pathlib import Path
from typing import Any

import pytest

from processforge_core.evidence.authoring import (
    MAX_BYTES,
    ArtifactAuthoringService,
    project_authoring_reviews,
)
from processforge_core.evidence.readiness import StageReadinessPolicy
from processforge_core.evidence.validation import EvidenceValidationService


def validator(root: Path) -> EvidenceValidationService:
    return EvidenceValidationService(
        root,
        lambda: "fixture-time",
        lambda path: path.relative_to(root).as_posix(),
        lambda path: hashlib.sha256(path.read_bytes()).hexdigest(),
    )


def submit(root: Path, content: bytes, **options: Any) -> tuple[dict[str, Any], Path]:
    path = root / "report.md"
    path.write_bytes(content)
    records, blockers = validator(root).normalize(
        {
            "kind": "artifact",
            "artifact_id": "report",
            "status": "ready",
            "path": path.name,
            **options,
        }
    )
    assert not blockers
    assert path.read_bytes() == content
    return records[0], path


def codes(record: dict[str, Any]) -> set[str]:
    return {item["code"] for item in record["authoring_review"]["findings"]}


@pytest.mark.parametrize(
    "text",
    [
        "# Report\nThe change and its limitations are documented.\n",
        "# Отчёт\nПроверено содержимое, зафиксированы ограничения.\n",
        "Résumé, Ελληνικά, 日本語 — valid UTF-8.\n",
        "```python\nvalue = '<summary>'\n# [sample](missing.md)\n```\n",
        "~~~~text\n<summary>\n~~~\n[example](missing.md)\n~~~~\n",
        "Use `<summary>` and `[example](missing.md)` in the code example.\n",
        "    <summary>\n    [example](missing.md)\n",
        "<div>Real HTML markup</div>\n",
        "<details><summary>Review results</summary>Verified text.</details>\n",
        "\ufeff# Report\nUTF-8 BOM is supported.\n",
    ],
)
def test_valid_languages_and_code_are_not_flagged(text: str, tmp_path: Path) -> None:
    record, _ = submit(tmp_path, text.encode("utf-8"))
    assert not codes(record)
    assert record["authoring_review"]["status"] == "reviewed"


@pytest.mark.parametrize(
    "data", [b"# Report\n\xffinvalid\n", b"\xef\xbb\xbf# Report\n\xffinvalid\n"]
)
def test_invalid_utf8_is_advisory_and_does_not_change_readiness(
    tmp_path: Path, data: bytes
) -> None:
    record, _ = submit(tmp_path, data)
    review = record["authoring_review"]
    assert codes(record) == {"invalid_utf8"}
    assert review["findings"][0]["line"] == 2
    assert review["reviewed_sha256"] == record["sha256"]
    policy = StageReadinessPolicy(
        validator(tmp_path).diagnostic,
        lambda value: value or [],
        lambda process: [],
        lambda code, key, requirement: {},
    )
    assert policy.requirement("artifact", "report", [record])["satisfied"]


def test_declared_sections_and_markers_are_detected_without_language_guessing(
    tmp_path: Path,
) -> None:
    record, _ = submit(
        tmp_path,
        b"## Summary\n<summary>\n## Example\n```\n<custom>\n```\n",
        authoring={
            "required_sections": ["Summary", "Missing", "Example"],
            "placeholders": ["<custom>"],
        },
    )
    assert codes(record) == {
        "unfilled_placeholder",
        "required_section_empty",
        "required_section_missing",
    }
    fields = {
        (item["code"], item.get("field"))
        for item in record["authoring_review"]["findings"]
    }
    assert ("required_section_empty", "Summary") in fields
    assert ("required_section_missing", "Missing") in fields
    assert not any(field == "Example" or field == "<custom>" for _, field in fields)
    record, _ = submit(
        tmp_path,
        "## Итог\nРабота проверена.\n".encode("utf-8"),
        authoring={"required_sections": ["Итог"], "placeholders": ["TODO"]},
    )
    assert not codes(record)


@pytest.mark.parametrize(
    "declaration",
    [
        [],
        {"unknown": True},
        {"required_sections": "Summary"},
        {"placeholders": [None]},
        {"placeholders": [""]},
        {"placeholders": ["x" * 201]},
        {"placeholders": [str(i) for i in range(33)]},
    ],
)
def test_invalid_authoring_declaration_warns_without_rejecting(
    declaration: Any, tmp_path: Path
) -> None:
    record, _ = submit(tmp_path, b"Useful report\n", authoring=declaration)
    assert "authoring_declaration_invalid" in codes(record)


@pytest.mark.parametrize(
    "reason,expected",
    [
        ("N/A", "generic_not_applicable"),
        ("не применимо.", "generic_not_applicable"),
        ("<actual justification>", "unfilled_placeholder"),
        ("No UI changed; the diff contains only server code.", None),
        ("Изменены только серверные файлы, интерфейс не затронут.", None),
    ],
)
def test_not_applicable_keeps_acceptance_but_explains_generic_reason(
    reason: str, expected: str | None, tmp_path: Path
) -> None:
    records, blockers = validator(tmp_path).normalize(
        {
            "kind": "gate",
            "gate_id": "ui-review",
            "status": "not_applicable",
            "reason": reason,
            "evidence": ["reviewed-diff"],
        }
    )
    assert not blockers and records
    assert codes(records[0]) == ({expected} if expected else set())
    changes: list[dict[str, Any]] = [{"reason": ""}, {"evidence": []}]
    for change in changes:
        rejected, errors = validator(tmp_path).normalize({**records[0], **change})
        assert (
            not rejected and errors[0]["code"] == "not_applicable_evidence_incomplete"
        )


def test_local_links_are_bounded_and_cannot_probe_outside_project(
    tmp_path: Path,
) -> None:
    (tmp_path / "exists.md").write_text("target", encoding="utf-8")
    record, _ = submit(
        tmp_path,
        b"[ok](exists.md)\n[remote](https://example.invalid/a)\n[anchor](#section)\n[bad](missing.md)\n[empty]()\n[out](../outside.md)\n[file](file:///outside.md)\n",
    )
    assert codes(record) == {
        "local_link_missing",
        "local_link_empty",
        "local_link_unresolved",
    }
    missing_lines = {item["line"] for item in record["authoring_review"]["findings"]}
    assert missing_lines == {4, 5, 6, 7}
    assert not any(
        "outside.md" in str(item) for item in record["authoring_review"]["findings"]
    )


def test_resolver_returning_external_target_is_not_probed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    record, path = submit(tmp_path, b"[target](anything.md)\n")
    outside = tmp_path.parent / "external.md"
    monkeypatch.setattr(
        Path, "exists", lambda path: pytest.fail("outside target was probed")
    )
    report = ArtifactAuthoringService(tmp_path, lambda relative: outside).review(
        record, path
    )
    assert report is not None
    assert report["findings"][0]["code"] == "local_link_unresolved"


def test_remote_links_and_code_do_not_resolve_or_fetch_targets(tmp_path: Path) -> None:
    record, path = submit(
        tmp_path,
        b"[web](https://example.invalid)\n`[literal](missing.md)`\n[anchor](#part)\n",
    )

    def forbidden(relative: str) -> Path | None:
        pytest.fail("remote or code link was resolved")

    report = ArtifactAuthoringService(tmp_path, forbidden).review(record, path)
    assert report is not None and not report["findings"]


def test_unsupported_large_and_changed_files_are_not_claimed_clean(
    tmp_path: Path,
) -> None:
    material = validator(tmp_path)
    binary = tmp_path / "binary.bin"
    binary.write_bytes(b"\xff\0")
    records, blockers = material.normalize(
        {"kind": "artifact", "id": "blob", "path": binary.name}
    )
    assert (
        not blockers
        and records[0]["authoring_review"]["reason"] == "unsupported_format"
    )
    record, path = submit(tmp_path, b"x" * (MAX_BYTES + 1))
    assert codes(record) == {"authoring_file_too_large"}
    assert record["authoring_review"]["status"] == "skipped"
    path.write_bytes(b"changed")
    report = ArtifactAuthoringService(tmp_path, material.safe_path).review(record, path)
    assert report is not None and report["reason"] == "file_changed"


def test_findings_and_reference_probes_have_limits(tmp_path: Path) -> None:
    record, path = submit(tmp_path, ("<summary>\n" * 100).encode())
    assert len(record["authoring_review"]["findings"]) <= 32
    assert "findings" in record["authoring_review"]["limits_reached"]
    calls = []
    record, path = submit(tmp_path, ("[ref](missing.md)\n" * 100).encode())

    def counted(relative: str) -> Path | None:
        calls.append(relative)
        return tmp_path / "missing.md"

    report = ArtifactAuthoringService(tmp_path, counted).review(record, path)
    assert report is not None and len(calls) == 64
    assert len(report["findings"]) <= 32
    assert {"findings", "links"} <= set(report["limits_reached"])


def test_file_read_limit_is_enforced_at_the_stream(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    record, path = submit(tmp_path, b"x" * (MAX_BYTES * 2))
    original_open = Path.open
    requests: list[int] = []

    class LimitedReader:
        def __enter__(self) -> LimitedReader:
            return self

        def __exit__(self, *args: Any) -> None:
            stream.close()

        def read(self, size: int = -1) -> bytes:
            assert 0 <= size <= MAX_BYTES + 1
            requests.append(size)
            return stream.read(size)

    stream = original_open(path, "rb")
    monkeypatch.setattr(Path, "open", lambda *args, **kwargs: LimitedReader())
    report = ArtifactAuthoringService(tmp_path, validator(tmp_path).safe_path).review(
        record, path
    )
    assert requests == [MAX_BYTES + 1]
    assert report is not None and report["limits_reached"] == ["file_bytes"]


def test_empty_angled_link_and_unfilled_support_are_explained(tmp_path: Path) -> None:
    record, _ = submit(tmp_path, b"[empty](<>)\n")
    assert codes(record) == {"local_link_empty"}
    records, blockers = validator(tmp_path).normalize(
        {
            "kind": "gate",
            "id": "review",
            "status": "not_applicable",
            "reason": "No UI changes in this diff.",
            "evidence": ["<supporting evidence>"],
        }
    )
    assert not blockers and codes(records[0]) == {"unfilled_placeholder"}


@pytest.mark.parametrize(
    "text,expected",
    [
        ("# Applicability\nnot_applicable\n", {"generic_not_applicable"}),
        ("# Применимость\nне применимо.\n", {"generic_not_applicable"}),
        (
            "# Applicability\nnot_applicable\nReason: no UI changes; evidence: reviewed-diff.\n",
            set(),
        ),
    ],
)
def test_bare_exception_document_and_concrete_explanation(
    text: str, expected: set[str], tmp_path: Path
) -> None:
    record, _ = submit(tmp_path, text.encode("utf-8"))
    assert codes(record) == expected


def test_repeated_headings_and_long_whitespace_do_not_require_nested_scans(
    tmp_path: Path,
) -> None:
    text = "## Summary ##\n" * 20000 + "# " + " " * 100000 + "\n"
    record, _ = submit(
        tmp_path, text.encode(), authoring={"required_sections": ["Summary"]}
    )
    assert codes(record) == {"required_section_empty"}
    record, _ = submit(
        tmp_path, b"## C#\nVerified.\n", authoring={"required_sections": ["C#"]}
    )
    assert not codes(record)


def test_long_inline_delimiters_are_masked_without_regex_backtracking(
    tmp_path: Path,
) -> None:
    delimiter = "`" * 2000
    text = "Example: " + delimiter + "<summary> [x](missing.md)" + delimiter + ".\n"
    record, _ = submit(tmp_path, text.encode())
    assert not codes(record)


def test_caller_cannot_supply_clean_review_and_legacy_state_is_never_rescanned(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    claimed = {
        "producer": "pf.artifact-authoring",
        "status": "reviewed",
        "findings": [],
    }
    record, _ = submit(tmp_path, b"<summary>\n", authoring_review=claimed)
    assert codes(record) == {"unfilled_placeholder"} and claimed["findings"] == []
    old = {"kind": "artifact", "id": "old", "path": "legacy.md"}
    assignment = {
        "stage": "verify",
        "stage_history": [
            {"stage_id": "build", "status": "completed", "evidence": [old, record]}
        ],
    }
    before = copy.deepcopy(assignment)
    monkeypatch.setattr(
        Path,
        "open",
        lambda *args, **kwargs: pytest.fail("state projection performed I/O"),
    )
    projected = project_authoring_reviews(assignment, [])
    assert projected["current_stage"]["status"] == "not_recorded"
    entries = projected["last_completed_stage"]["entries"]
    assert entries[0]["evidence_index"] == 1
    entries[0]["review"]["findings"].clear()
    assert assignment == before
