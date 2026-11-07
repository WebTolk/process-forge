"""Internal canonical selection values; no store or routing side effects.

Domain import must preserve malformed legacy bodies in its own health/raw
relations. These typed summaries accept text, never SQL coercions of those
bodies. Identifier validation belongs to selectors; current rows may contain
empty or invalid legacy identifiers without becoming catalog members.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

__all__ = (
    "SelectionError",
    "SelectionRowKey",
    "SelectionCandidate",
    "CandidateSet",
    "normalize_objective",
    "preferred",
)

_SELECTOR = re.compile(r"(?:[a-z0-9]|[a-z0-9][a-z0-9-]*[a-z0-9])")


class SelectionError(ValueError):
    """Stable internal error without SQL, payloads or private diagnostics."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _text(value: object, *, nonempty: bool = False) -> str:
    if (
        type(value) is not str
        or "\x00" in value
        or any(0xD800 <= ord(char) <= 0xDFFF for char in value)
        or (nonempty and not value.strip())
    ):
        raise SelectionError("selection_input_invalid")
    return value


def _selector(value: object) -> str:
    text = _text(value)
    if _SELECTOR.fullmatch(text) is None:
        raise SelectionError("invalid_work_selector")
    return text


@dataclass(frozen=True)
class SelectionRowKey:
    """A membership occurrence, including synthetic empty-Run ordinal -1."""

    project_uuid: str
    run_id: str
    ordinal: int

    def __post_init__(self) -> None:
        _text(self.project_uuid, nonempty=True)
        _text(self.run_id, nonempty=True)
        if type(self.ordinal) is not int or not -1 <= self.ordinal < 2**63:
            raise SelectionError("selection_input_invalid")


@dataclass(frozen=True)
class SelectionCandidate:
    """Resolved summary; identity proof and body loading remain separate."""

    key: SelectionRowKey
    assignment_id: str
    source_order: str
    objective: str
    session_id: str
    updated_lex: str
    created_lex: str
    pending_completion: bool

    def __post_init__(self) -> None:
        if not isinstance(self.key, SelectionRowKey):
            raise SelectionError("selection_input_invalid")
        for value in (
            self.assignment_id,
            self.source_order,
            self.objective,
            self.session_id,
            self.updated_lex,
            self.created_lex,
        ):
            _text(value)
        if type(self.pending_completion) is not bool:
            raise SelectionError("selection_input_invalid")


@dataclass(frozen=True)
class CandidateSet:
    """Legacy-complete traversal-ordered results at one catalog revision."""

    catalog_revision: int
    rows: tuple[SelectionCandidate, ...]

    def __post_init__(self) -> None:
        if (
            type(self.catalog_revision) is not int
            or not 1 <= self.catalog_revision < 2**63
            or type(self.rows) is not tuple
            or any(not isinstance(row, SelectionCandidate) for row in self.rows)
        ):
            raise SelectionError("selection_input_invalid")


def normalize_objective(value: str) -> str:
    """Match the existing Unicode casefold and whitespace normalization."""
    return " ".join(_text(value).casefold().split())


def preferred(
    rows: tuple[SelectionCandidate, ...], *, session_id: str
) -> SelectionCandidate | None:
    """Prefer a session, then lexical timestamps/ID; preserve first tie."""
    _text(session_id)
    if type(rows) is not tuple or any(
        not isinstance(row, SelectionCandidate) for row in rows
    ):
        raise SelectionError("selection_input_invalid")
    bound = tuple(row for row in rows if row.session_id == session_id)
    candidates = bound if session_id and bound else rows
    return max(
        candidates,
        key=lambda row: (row.updated_lex, row.created_lex, row.assignment_id),
        default=None,
    )
