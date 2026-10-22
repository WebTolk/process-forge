"""Bounded advisory observations for newly submitted artifacts, never gate decisions."""

from __future__ import annotations

import copy
import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
from urllib.parse import unquote, urlsplit

MAX_BYTES = 1024 * 1024
MAX_FINDINGS = 32
MAX_LINKS = 64
_GENERIC_NA = {
    "n/a",
    "na",
    "not_applicable",
    "not applicable",
    "не применимо",
    "неприменимо",
}
_MARKERS = (
    "<id>",
    "<artifact-type>",
    "<title>",
    "<process-id>",
    "<version>",
    "<role>",
    "<assignment-id>",
    "<path>",
    "<summary>",
    "<artifact content>",
)
_FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
_HEADING = re.compile(r"^ {0,3}(#{1,6})[ \t]+(.+)$")
_LINK = re.compile(r"(?<!!)\[[^\[\]\n]{0,256}\]\(([^()\n]{0,2048})\)")
_MESSAGES = {
    "invalid_utf8": "The submitted text is not valid UTF-8; save a readable revision.",
    "replacement_character": "Prose contains a Unicode replacement character; check the original encoding.",
    "unfilled_placeholder": "A known or explicitly declared template marker remains in prose.",
    "required_section_missing": "An explicitly required Markdown section is missing.",
    "required_section_empty": "An explicitly required section has no content beyond template markers.",
    "authoring_declaration_invalid": "Authoring options must contain only required_sections/placeholders, each a list of at most 32 nonempty strings of at most 200 characters.",
    "generic_not_applicable": "Give a concrete reason for non-applicability and relate the supporting evidence to it.",
    "local_link_empty": "A local Markdown link has no destination.",
    "local_link_missing": "A local link target does not exist inside the project.",
    "local_link_unresolved": "A local link could not be resolved within the authorized project boundary.",
    "local_link_unreadable": "A local link target could not be checked.",
    "authoring_file_too_large": "Text inspection was skipped because the file exceeds the 1 MiB authoring limit.",
    "authoring_file_unreadable": "Text inspection could not read the submitted file.",
    "authoring_file_changed": "The inspected bytes differ from the evidence digest; review and resubmit the file.",
    "authoring_links_limited": "Only the first 64 simple inline links were checked.",
    "authoring_findings_limited": "Additional authoring findings were omitted after the bounded limit.",
}


def _finding(code: str, **details: Any) -> dict[str, Any]:
    return {"code": code, "severity": "warning", "message": _MESSAGES[code], **details}


def _prose_lines(text: str) -> list[str]:
    """Mask common Markdown code forms while preserving line numbers."""
    result = []
    fence = ""
    for line in text.splitlines():
        match = _FENCE.match(line)
        if fence:
            if (
                match
                and match[1][0] == fence[0]
                and len(match[1]) >= len(fence)
                and not match[2].strip()
            ):
                fence = ""
            result.append("")
        elif match:
            fence = match[1]
            result.append("")
        elif line.startswith(("    ", "\t")):
            result.append("")
        else:
            result.append(_mask_inline_code(line))
    return result


def _mask_inline_code(line: str) -> str:
    """Scan backtick runs once, including unmatched and very long delimiters."""
    chunks = []
    cursor = 0
    while cursor < len(line):
        opening = line.find("`", cursor)
        if opening < 0:
            chunks.append(line[cursor:])
            break
        chunks.append(line[cursor:opening])
        after = opening
        while after < len(line) and line[after] == "`":
            after += 1
        scan = after
        while True:
            closing = line.find("`", scan)
            if closing < 0:
                chunks.append(line[opening:])
                return "".join(chunks)
            end = closing
            while end < len(line) and line[end] == "`":
                end += 1
            if end - closing == after - opening:
                chunks.append(" " * (end - opening))
                cursor = end
                break
            scan = end
    return "".join(chunks)


def _heading_name(match: re.Match[str]) -> str:
    name = match[2].strip()
    without_closing = name.rstrip("#")
    if without_closing != name and without_closing.endswith((" ", "\t")):
        return without_closing.rstrip()
    return name


def _declarations(value: Any) -> tuple[list[str], list[str], list[dict[str, Any]]]:
    if value is None:
        return [], [], []
    if not isinstance(value, dict) or any(
        key not in {"required_sections", "placeholders"} for key in value
    ):
        return [], [], [_finding("authoring_declaration_invalid")]
    lists: list[list[str]] = []
    findings = []
    for key in ("required_sections", "placeholders"):
        items = value.get(key, [])
        if (
            not isinstance(items, list)
            or len(items) > 32
            or any(
                not isinstance(item, str) or not item.strip() or len(item) > 200
                for item in items
            )
        ):
            findings.append(_finding("authoring_declaration_invalid", field=key))
            lists.append([])
        else:
            lists.append(list(dict.fromkeys(items)))
    return lists[0], lists[1], findings


def _text_findings(
    text: str, sections: list[str], markers: list[str]
) -> tuple[list[dict[str, Any]], list[tuple[int, str]]]:
    prose = _prose_lines(text)
    findings: list[dict[str, Any]] = []
    links: list[tuple[int, str]] = []
    placeholders = tuple(dict.fromkeys((*_MARKERS, *markers)))
    for number, line in enumerate(prose, 1):
        if len(findings) <= MAX_FINDINGS:
            for marker in placeholders:
                if marker in line:
                    # Raw HTML with a closing tag is content, while a bare
                    # template value is unresolved. Explicit declarations win.
                    if (
                        marker in _MARKERS
                        and marker not in markers
                        and f"</{marker[1:-1]}>" in line
                    ):
                        continue
                    findings.append(
                        _finding("unfilled_placeholder", line=number, field=marker)
                    )
                    if len(findings) > MAX_FINDINGS:
                        break
            if "\ufffd" in line:
                findings.append(_finding("replacement_character", line=number))
        if len(links) <= MAX_LINKS:
            for match in _LINK.finditer(line):
                links.append((number, match[1]))
                if len(links) > MAX_LINKS:
                    break
    headings: list[tuple[int, re.Match[str]]] = []
    for index, line in enumerate(prose):
        heading_match = _HEADING.match(line)
        if heading_match is not None:
            headings.append((index, heading_match))
    body_lines = [
        (index + 1, line.strip())
        for index, line in enumerate(prose)
        if line.strip() and not _HEADING.match(line)
    ]
    if body_lines and all(
        line.casefold().rstrip(".!;:") in _GENERIC_NA for _, line in body_lines
    ):
        findings.append(_finding("generic_not_applicable", line=body_lines[0][0]))
    original = text.splitlines()
    ends: dict[int, int] = {}
    stack: list[tuple[int, int]] = []
    for index, heading in headings:
        level = len(heading[1])
        while stack and stack[-1][1] >= level:
            previous, _ = stack.pop()
            ends[previous] = index
        stack.append((index, level))
    for index, _ in stack:
        ends[index] = len(original)
    for section in sections:
        matched = [
            (index, match)
            for index, match in headings
            if _heading_name(match).casefold() == section.strip().casefold()
        ]
        if not matched:
            findings.append(_finding("required_section_missing", field=section))
            continue
        filled = False
        for index, heading in matched:
            end = ends[index]
            body = "\n".join(original[index + 1 : end])
            for marker in placeholders:
                body = body.replace(marker, "")
            filled = filled or bool(body.strip())
            if filled:
                break
        if not filled:
            findings.append(_finding("required_section_empty", field=section))
    return findings, links


@dataclass(frozen=True)
class ArtifactAuthoringService:
    project_root: Path
    resolve_path: Callable[[str], Path | None]

    def _link_finding(self, path: Path, raw: str, line: int) -> dict[str, Any] | None:
        raw = raw.strip()
        if not raw:
            return _finding("local_link_empty", line=line)
        # Deliberately limited to simple inline destinations; no network or
        # attempt to interpret nested-parenthesis Markdown syntax.
        if "(" in raw:
            return None
        target = (
            raw[1 : raw.find(">")]
            if raw.startswith("<") and ">" in raw
            else raw.split()[0]
        )
        if not target:
            return _finding("local_link_empty", line=line)
        try:
            parts = urlsplit(target)
            if parts.scheme and parts.scheme.casefold() != "file":
                return None
            if parts.netloc:
                return None
            if parts.scheme.casefold() == "file":
                return _finding("local_link_unresolved", line=line)
            if not parts.path:
                return None  # Anchor in the current document, not a file probe.
            decoded = unquote(parts.path, errors="strict")
            relative = (path.parent / decoded).relative_to(self.project_root).as_posix()
            resolved = self.resolve_path(relative)
            if resolved is None:
                return _finding("local_link_unresolved", line=line)
            resolved.resolve().relative_to(self.project_root.resolve())
            if not resolved.exists():
                return _finding("local_link_missing", line=line)
        except (ValueError, UnicodeError, RuntimeError):
            return _finding("local_link_unresolved", line=line)
        except OSError:
            return _finding("local_link_unreadable", line=line)
        return None

    def review(
        self, evidence: dict[str, Any], path: Path | None
    ) -> dict[str, Any] | None:
        applicable = str(evidence.get("status") or "") == "not_applicable"
        if path is None and not applicable and "authoring" not in evidence:
            return None
        sections, markers, findings = _declarations(evidence.get("authoring"))
        report: dict[str, Any] = {
            "schema_version": 1,
            "producer": "pf.artifact-authoring",
            "advisory": True,
            "status": "reviewed",
            "coverage": "justification_only",
            "findings": findings,
            "limits_reached": [],
        }
        if applicable:
            reason = str(evidence.get("reason") or "").strip()
            if reason.casefold().rstrip(".!;:") in _GENERIC_NA:
                findings.append(_finding("generic_not_applicable"))
            if reason in {
                "<actual justification>",
                "<actual reason>",
                "<reason>",
                "{{reason}}",
            } or any(marker in reason for marker in markers):
                findings.append(_finding("unfilled_placeholder", field="reason"))
            if any(
                value in {"<supporting evidence>", "<supporting-evidence-id>"}
                for value in evidence.get("evidence", [])
                if isinstance(value, str)
            ):
                findings.append(_finding("unfilled_placeholder", field="evidence"))
        if path is None:
            if not applicable:
                report.update(
                    status="skipped", coverage="not_inspected", reason="no_file"
                )
        elif path.suffix.casefold() not in {".md", ".txt", ".rst"}:
            report.update(
                status="skipped", coverage="not_inspected", reason="unsupported_format"
            )
        else:
            try:
                path.resolve().relative_to(self.project_root.resolve())
                with path.open("rb") as stream:
                    content = stream.read(MAX_BYTES + 1)
                if len(content) > MAX_BYTES:
                    report["limits_reached"].append("file_bytes")
                    report.update(
                        status="skipped", coverage="not_inspected", reason="size_limit"
                    )
                    findings.append(_finding("authoring_file_too_large"))
                else:
                    digest = "sha256:" + hashlib.sha256(content).hexdigest()
                    report["reviewed_sha256"] = digest
                    if (
                        digest.casefold()
                        != str(evidence.get("sha256") or "").casefold()
                    ):
                        report.update(
                            status="skipped",
                            coverage="not_inspected",
                            reason="file_changed",
                        )
                        findings.append(_finding("authoring_file_changed"))
                    else:
                        try:
                            text = content.decode("utf-8-sig")
                        except UnicodeDecodeError as exc:
                            report["coverage"] = "encoding_only"
                            findings.append(
                                _finding(
                                    "invalid_utf8",
                                    line=exc.object[: exc.start].count(b"\n") + 1,
                                )
                            )
                        else:
                            report["coverage"] = "text_and_simple_inline_links"
                            text_findings, links = _text_findings(
                                text, sections, markers
                            )
                            findings.extend(text_findings)
                            for line, target in links[:MAX_LINKS]:
                                finding = self._link_finding(path, target, line)
                                if finding is not None:
                                    findings.append(finding)
                            if len(links) > MAX_LINKS:
                                report["limits_reached"].append("links")
                                findings.append(_finding("authoring_links_limited"))
            except (OSError, ValueError, RuntimeError):
                report.update(
                    status="skipped",
                    coverage="not_inspected",
                    reason="unreadable_or_outside_project",
                )
                findings.append(_finding("authoring_file_unreadable"))
        if len(findings) > MAX_FINDINGS:
            report["limits_reached"].append("findings")
            findings[:] = findings[: MAX_FINDINGS - 1] + [
                _finding("authoring_findings_limited")
            ]
        if findings and report["status"] == "reviewed":
            report["status"] = "warnings"
        return report


def project_authoring_reviews(
    assignment: dict[str, Any], current: list[dict[str, Any]]
) -> dict[str, Any]:
    """Project stored observations only; legacy records are never rescanned."""

    def group(stage_id: str, records: Any) -> dict[str, Any]:
        entries = [
            {"evidence_index": index, "review": copy.deepcopy(item["authoring_review"])}
            for index, item in enumerate(records if isinstance(records, list) else [])
            if isinstance(item, dict) and isinstance(item.get("authoring_review"), dict)
        ]
        return {
            "stage_id": stage_id,
            "status": "recorded" if entries else "not_recorded",
            "entries": entries,
        }

    history = assignment.get("stage_history")
    previous = next(
        (
            item
            for item in reversed(history if isinstance(history, list) else [])
            if isinstance(item, dict) and item.get("status") == "completed"
        ),
        {},
    )
    return {
        "schema_version": 1,
        "advisory": True,
        "current_stage": group(str(assignment.get("stage") or ""), current),
        "last_completed_stage": group(
            str(previous.get("stage_id") or ""), previous.get("evidence")
        ),
    }
