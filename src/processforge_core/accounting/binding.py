"""Explicit provider/session binding at the accounting ingress boundary."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from processforge_core.accounting.model import Attribution, identifier, utc

PROFILES = {
    "codex-exec-v1": "codex",
    "kimi-code-2.3.0-v1": "kimi",
    "kimi-cli-legacy-unsupported": "kimi",
}


def timestamp(value: object) -> datetime:
    """Parse an explicit aware UTC timestamp without interpreting local time."""
    if not isinstance(value, str):
        raise ValueError("source_timestamp_string_required")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    utc(parsed, "source timestamp")
    return parsed.astimezone(timezone.utc)


@dataclass(frozen=True, kw_only=True)
class CollectionBinding:
    """Operator/managed-driver assertion for one stable primary source stream.

    A binding authorizes no project queries. Source ids identify an append-only
    stream, not its filename or payload hash. Kimi imports must first project
    qualified primary wire occurrences into the documented import envelope.
    """

    origin_id: str
    source_id: str
    profile: str
    attribution: Attribution
    observed_at: datetime

    def __post_init__(self) -> None:
        identifier(self.origin_id, "origin_id")
        identifier(self.source_id, "source_id")
        if self.profile not in PROFILES:
            raise ValueError("unsupported_source_profile")
        if self.attribution.project_id is None or not self.attribution.session_id:
            raise ValueError("explicit_project_and_session_binding_required")
        if self.attribution.provider != PROFILES[self.profile]:
            raise ValueError("provider_profile_mismatch")
        work = (
            self.attribution.run_id,
            self.attribution.assignment_id,
            self.attribution.attempt,
        )
        if any(value is not None for value in work) and not all(
            value is not None for value in work
        ):
            raise ValueError("incomplete_work_binding")
        utc(self.observed_at, "observed_at")

    @classmethod
    def from_dict(cls, data: dict[str, Any], *, project_id: str) -> CollectionBinding:
        """Validate a bounded explicit import manifest against the selected project."""
        if data.get("schema_version") != 1 or data.get("primary_records") is not True:
            raise ValueError("qualified_primary_binding_required")
        attr = data.get("attribution")
        if not isinstance(attr, dict) or attr.get("project_id") != project_id:
            raise ValueError("project_binding_mismatch")
        return cls(
            origin_id=data["origin_id"],
            source_id=data["source_id"],
            profile=data["profile"],
            attribution=Attribution(**attr),
            observed_at=timestamp(data["observed_at"]),
        )
