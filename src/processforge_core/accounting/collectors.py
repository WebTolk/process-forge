"""Bounded, replayable provider adapters; no source discovery or query logic."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path
from typing import Any

from processforge_core.accounting.binding import CollectionBinding, timestamp
from processforge_core.accounting.composition import read_json
from processforge_core.accounting.model import (
    ActivityInterval,
    FactKey,
    Provenance,
    Quality,
    SourceCapability,
    SourceCursor,
    SourceStatus,
    TokenCounts,
    UsageRecord,
)
from processforge_core.accounting.service import AccountingService

MAX_LINE = 1024 * 1024
MAX_FILE = 64 * 1024 * 1024
ADAPTER_VERSION = "pf-usage-1"


def source_capability(
    binding: CollectionBinding, status: SourceStatus
) -> SourceCapability:
    """Declare only the pinned adapter's metrics and current collection freshness."""
    metrics: tuple[str, ...] = ("input_total", "output_total", "input_cache_read")
    if binding.profile == "codex-exec-v1":
        metrics += ("input_cache_write", "output_reasoning", "activity")
    elif binding.profile == "kimi-code-2.3.0-v1":
        metrics += ("input_cache_write",)
    else:
        metrics = ()
    return SourceCapability(
        origin_id=binding.origin_id,
        source_id=binding.source_id,
        project_id=binding.attribution.project_id or "",
        adapter_version=ADAPTER_VERSION,
        observed_at=datetime.now(binding.observed_at.tzinfo),
        supported_metrics=metrics,
        status=status,
    )


@dataclass(frozen=True, kw_only=True)
class CollectionResult:
    """Safe receipt import outcome without source paths or provider bodies."""

    stored: int
    lines: int
    status: str
    error: str | None = None

    def to_dict(self) -> dict[str, object]:
        """Return the public collection result."""
        return {
            "stored": self.stored,
            "lines": self.lines,
            "status": self.status,
            "error": self.error,
            "complete": False,
        }


def _counter(data: dict[str, Any], name: str) -> int | None:
    value = data.get(name)
    if value is not None and (type(value) is not int or not 0 <= value <= 2**63 - 1):
        raise ValueError("invalid_usage_counter")
    return value


class ProviderCollector:
    """Normalize only the two pinned explicit primary-receipt profiles."""

    def normalize(
        self,
        event: dict[str, Any],
        binding: CollectionBinding,
        *,
        line: int,
        raw: bytes,
    ) -> UsageRecord | None:
        """Map one occurrence, retaining missing counters and observation quality."""
        if binding.profile == "kimi-cli-legacy-unsupported":
            return None
        kind = event.get("type")
        if binding.profile == "codex-exec-v1":
            if kind != "turn.completed":
                return None
            usage = event.get("usage")
            if not isinstance(usage, dict):
                raise ValueError("missing_usage_object")
            tokens = TokenCounts(
                input_total=_counter(usage, "input_tokens"),
                output_total=_counter(usage, "output_tokens"),
                input_cache_read=_counter(usage, "cached_input_tokens"),
                input_cache_write=_counter(usage, "cache_write_input_tokens"),
                output_reasoning=_counter(usage, "reasoning_output_tokens"),
            )
            # The managed attempt is the stable stream; every physical JSON
            # occurrence has a distinct identity even with identical counters.
            record_id = f"line:{line}"
            attr = binding.attribution
        else:
            if kind != "usage.record":
                return None
            # This is the PF qualified import envelope, not an assumed native
            # wire layout. Never ingest summary mirrors or compaction counts.
            if event.get("session_id") != binding.attribution.session_id:
                raise ValueError("source_session_mismatch")
            occurrence = event.get("occurrence_id")
            if not isinstance(occurrence, str):
                raise ValueError("invalid record_id")
            identifier_value = FactKey(
                origin_id=binding.origin_id,
                source_id=binding.source_id,
                record_id=occurrence,
            )
            record_id = identifier_value.record_id
            if event.get("agentId") != binding.attribution.agent_instance_id:
                raise ValueError("source_agent_mismatch")
            if event.get("primary") is not True:
                raise ValueError("primary_occurrence_required")
            if event.get("usageScope") not in (None, "session", "turn"):
                raise ValueError("unsupported_usage_scope")
            usage = event.get("usage")
            if not isinstance(usage, dict):
                raise ValueError("missing_usage_object")
            parts = [
                _counter(usage, name)
                for name in ("inputOther", "inputCacheRead", "inputCacheCreation")
            ]
            total = (
                sum(part for part in parts if part is not None)
                if all(part is not None for part in parts)
                else None
            )
            tokens = TokenCounts(
                input_total=total,
                output_total=_counter(usage, "output"),
                input_cache_read=parts[1],
                input_cache_write=parts[2],
            )
            model = event.get("model")
            if (
                binding.attribution.model is not None
                and model != binding.attribution.model
            ):
                raise ValueError("source_model_mismatch")
            attr = replace(binding.attribution, model=model)
        occurred_at = (
            timestamp(event["timestamp"])
            if "timestamp" in event
            else binding.observed_at
        )
        quality: Quality = (
            "measured"
            if "timestamp" in event and tokens.total is not None
            else "partial"
        )
        return UsageRecord(
            key=FactKey(
                origin_id=binding.origin_id,
                source_id=binding.source_id,
                record_id=record_id,
            ),
            revision=0,
            attribution=attr,
            occurred_at=occurred_at,
            tokens=tokens,
            quality=quality,
            provenance=Provenance(
                source_ref=f"occurrence:{record_id}",
                source_hash="sha256:" + hashlib.sha256(raw).hexdigest(),
                adapter_version=ADAPTER_VERSION + ":" + binding.profile,
            ),
        )

    def collect(
        self,
        path: Path,
        binding: CollectionBinding,
        service: AccountingService,
    ) -> CollectionResult:
        """Stream a bounded explicit file; atomically checkpoint batches of 100 lines.

        A checkpoint pins the complete accepted prefix and binding. Changed,
        truncated, malformed and torn streams never advance past invalid input.
        A fresh import reads at most 64 MiB; larger streams need an explicitly
        selected, stable segment/source id. Repeated reads are idempotent.
        """
        if binding.profile == "kimi-cli-legacy-unsupported":
            service.ingest(capabilities=[source_capability(binding, "unsupported")])
            return CollectionResult(
                stored=0,
                lines=0,
                status="unsupported",
                error="legacy_source_unsupported",
            )
        previous = service.repository.get_cursor(binding.origin_id, binding.source_id)
        checkpoint = json.loads(previous.position) if previous else None
        binding_hash = hashlib.sha256(
            json.dumps(
                {
                    "profile": binding.profile,
                    "attribution": vars(binding.attribution),
                    "observed_at": binding.observed_at.isoformat(),
                },
                sort_keys=True,
            ).encode()
        ).hexdigest()
        if checkpoint and checkpoint["binding"] != binding_hash:
            raise ValueError("source_binding_changed")
        digest = hashlib.sha256()
        stored = 0
        line = 0
        last = int(checkpoint["line"]) if checkpoint else 0
        batch: list[UsageRecord] = []
        revision = previous.revision if previous else 0
        committed = last
        error: str | None = None
        bytes_read = 0

        def capability(status: SourceStatus) -> SourceCapability:
            return source_capability(binding, status)

        def commit() -> None:
            nonlocal stored, revision, committed
            revision += 1
            cursor = SourceCursor(
                origin_id=binding.origin_id,
                source_id=binding.source_id,
                position=json.dumps(
                    {"line": line, "hash": digest.hexdigest(), "binding": binding_hash}
                ),
                revision=revision,
                updated_at=datetime.now(binding.observed_at.tzinfo),
            )
            stored += service.ingest(
                batch, cursor=cursor, capabilities=[capability("partial")]
            )
            batch.clear()
            committed = line

        if not path.is_file():
            service.ingest(capabilities=[capability("missing")])
            return CollectionResult(
                stored=0, lines=0, status="missing", error="receipt_missing"
            )
        if path.stat().st_size > MAX_FILE:
            service.ingest(capabilities=[capability("partial")])
            return CollectionResult(
                stored=0, lines=0, status="partial", error="receipt_size_limit"
            )
        with path.open("rb") as stream:
            while True:
                raw = stream.readline(MAX_LINE + 1)
                if not raw:
                    break
                bytes_read += len(raw)
                if bytes_read > MAX_FILE:
                    error = "receipt_size_limit"
                    break
                if len(raw) > MAX_LINE or not raw.endswith(b"\n"):
                    error = "oversized_or_torn_line"
                    break
                try:
                    event = json.loads(raw)
                    if not isinstance(event, dict):
                        raise ValueError("event_object_required")
                    # Parse old lines as well; prefix equality is established
                    # before any new facts can be committed.
                    fact = self.normalize(event, binding, line=line + 1, raw=raw)
                except (ValueError, TypeError, KeyError, OverflowError):
                    error = "malformed_receipt"
                    break
                digest.update(raw)
                line += 1
                if (
                    line == last
                    and checkpoint
                    and digest.hexdigest() != checkpoint["hash"]
                ):
                    raise ValueError("source_prefix_changed")
                if line > last:
                    if fact:
                        batch.append(fact)
                    if line - committed >= 100:
                        commit()
        if line < last:
            raise ValueError("source_truncated_or_changed")
        if line > committed:
            commit()
        service.ingest(capabilities=[capability("partial")])
        # Absence of receipts and unavailable model/metrics remain explicit;
        # exhausting a file never proves provider/device completeness.
        return CollectionResult(
            stored=stored, lines=line, status="partial", error=error
        )


def execution_interval(
    binding: CollectionBinding,
    *,
    start: datetime,
    wall_end: datetime | None,
    elapsed_seconds: float | None,
    source_hash: str,
    revision: int = 0,
) -> ActivityInterval:
    """Qualify independent wall/monotonic clocks without inventing an exact end."""
    agrees = (
        wall_end is not None
        and elapsed_seconds is not None
        and abs((wall_end - start).total_seconds() - elapsed_seconds) <= 0.000001
    )
    return ActivityInterval(
        key=FactKey(
            origin_id=binding.origin_id,
            source_id=binding.source_id,
            record_id="execution",
        ),
        revision=revision,
        attribution=binding.attribution,
        start=start,
        end=wall_end,
        elapsed_seconds=elapsed_seconds,
        quality="measured" if agrees else "partial",
        provenance=Provenance(
            source_ref="attempt-timing",
            source_hash=source_hash,
            adapter_version=ADAPTER_VERSION,
        ),
    )


def import_timing(
    path: Path, binding: CollectionBinding, service: AccountingService
) -> int:
    """Replay an exact managed interval, excluding child/presence aggregation."""
    data = read_json(path)
    if (
        data.get("schema_version") != 1
        or data.get("source_id") != binding.source_id
        or data.get("attribution") != vars(binding.attribution)
    ):
        raise ValueError("timing_binding_mismatch")
    encoded = json.dumps(data, sort_keys=True).encode()
    return service.ingest(
        activity=[
            execution_interval(
                binding,
                start=timestamp(data["start"]),
                wall_end=timestamp(data["wall_end"]) if data.get("wall_end") else None,
                elapsed_seconds=data.get("elapsed_seconds"),
                revision=data["revision"],
                source_hash="sha256:" + hashlib.sha256(encoded).hexdigest(),
            )
        ],
        capabilities=[source_capability(binding, "partial")],
    )
